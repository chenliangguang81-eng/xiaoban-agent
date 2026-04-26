"""
小伴 LLM 核心对话引擎 (LLM Core)
v5.2 — 统一接入 Manus API，消除多厂商 LLM 混用风险

架构设计：
- 主通道：Manus API（task.create + task.listMessages 轮询）
- 降级通道：OpenAI 兼容 API（当 Manus API 不可用时自动降级）
- 模型解耦：所有引擎和技能文件通过本模块的单例调用，禁止直接实例化 OpenAI 客户端
- 统一接口：call_llm() 方法对上层完全透明，无论底层走 Manus 还是 OpenAI

迁移说明（v5.1 → v5.2）：
- 废弃：各引擎文件中的 `from openai import OpenAI; client = OpenAI()` 直接调用
- 新增：ManusLLMAdapter 封装 Manus task 生命周期为同步 chat 接口
- 新增：全局单例 get_llm_router() 供所有模块调用
- 保留：XiaoBanLLMCore 类（向后兼容），内部切换为 Manus 主通道
"""
import os
import json
import time
import logging
import requests
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Manus API 配置
# ─────────────────────────────────────────────────────────────────────────────

MANUS_API_BASE = "https://api.manus.ai"
MANUS_API_KEY = os.environ.get("MANUS_API_KEY", "")
MANUS_PROJECT_ID = os.environ.get("MANUS_PROJECT_ID", "CmmJvW7Me97bqsgKCM64DP")


def _manus_headers() -> Dict:
    return {
        "x-manus-api-key": MANUS_API_KEY,
        "Content-Type": "application/json"
    }


# ─────────────────────────────────────────────────────────────────────────────
# ManusLLMAdapter
# ─────────────────────────────────────────────────────────────────────────────

class ManusLLMAdapter:
    """Manus API 适配器：将 task 生命周期封装为同步 chat 接口"""

    def __init__(self, project_id: str = MANUS_PROJECT_ID, timeout: int = 120):
        self.project_id = project_id
        self.timeout = timeout
        self.poll_interval = 3
        self._available = bool(MANUS_API_KEY)
        if not self._available:
            logger.warning("MANUS_API_KEY 未设置，ManusLLMAdapter 将降级到 OpenAI 兼容 API。")

    def is_available(self) -> bool:
        return self._available

    def call_llm(self, user_message: str, system_prompt: str = "", max_wait: int = None) -> Dict:
        if not self._available:
            raise RuntimeError("Manus API 不可用（MANUS_API_KEY 未设置）")
        max_wait = max_wait or self.timeout
        full_message = f"{system_prompt}\n\n---\n\n{user_message}" if system_prompt else user_message
        task_id = self._create_task(full_message)
        result = self._poll_task(task_id, max_wait)
        return {"content": result["content"], "task_id": task_id,
                "tokens_used": result.get("tokens_used", 0), "source": "manus"}

    def _create_task(self, message: str) -> str:
        payload = {"message": {"content": [{"type": "text", "text": message}]}}
        if self.project_id:
            payload["project_id"] = self.project_id
        resp = requests.post(f"{MANUS_API_BASE}/v2/task.create",
                             headers=_manus_headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Manus task.create 失败: {data.get('error', {}).get('message', '未知错误')}")
        task_id = data.get("task_id") or data.get("data", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"Manus task.create 未返回 task_id，响应: {data}")
        logger.info(f"Manus task 已创建: {task_id}")
        return task_id

    def _poll_task(self, task_id: str, max_wait: int) -> Dict:
        deadline = time.time() + max_wait
        while time.time() < deadline:
            time.sleep(self.poll_interval)
            resp = requests.get(f"{MANUS_API_BASE}/v2/task.listMessages",
                                headers=_manus_headers(),
                                params={"task_id": task_id, "limit": 50, "order": "asc"},
                                timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(f"Manus task.listMessages 失败: {data.get('error', {}).get('message', '未知错误')}")
            messages = data.get("messages", []) or data.get("data", {}).get("messages", [])
            is_stopped = False
            final_content = ""
            for msg in messages:
                msg_type = msg.get("type", "")
                if msg_type == "status_update" and msg.get("agent_status") == "stopped":
                    is_stopped = True
                if msg_type == "assistant_message":
                    content = msg.get("assistant_message", {}).get("content", "")
                    if content:
                        final_content = content
            if is_stopped and final_content:
                logger.info(f"Manus task {task_id} 完成，回复长度: {len(final_content)}")
                return {"content": final_content, "tokens_used": len(final_content) // 4}
        raise TimeoutError(f"Manus task {task_id} 在 {max_wait} 秒内未完成")


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI 降级适配器
# ─────────────────────────────────────────────────────────────────────────────

class OpenAIFallbackAdapter:
    """OpenAI 兼容 API 降级适配器"""

    def __init__(self):
        try:
            from openai import OpenAI
            self.client = OpenAI()
            self.model = "gpt-4.1-mini"
            self._available = True
        except Exception as e:
            logger.error(f"OpenAI 客户端初始化失败: {e}")
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def call_llm(self, user_message: str, system_prompt: str = "",
                 messages_history: List[Dict] = None) -> Dict:
        if not self._available:
            raise RuntimeError("OpenAI 降级适配器不可用")
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        if messages_history:
            msgs.extend(messages_history)
        msgs.append({"role": "user", "content": user_message})
        response = self.client.chat.completions.create(
            model=self.model, messages=msgs, max_tokens=1500, temperature=0.7)
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        return {"content": content, "task_id": None,
                "tokens_used": tokens_used, "source": "openai_fallback"}


# ─────────────────────────────────────────────────────────────────────────────
# 统一 LLM 路由器
# ─────────────────────────────────────────────────────────────────────────────

class UnifiedLLMRouter:
    """统一 LLM 路由器：Manus 主通道 + OpenAI 降级"""

    TOKEN_ALERT_THRESHOLD = 5000

    def __init__(self):
        self.manus = ManusLLMAdapter()
        self.fallback = OpenAIFallbackAdapter()
        self._call_log: List[Dict] = []
        if self.manus.is_available():
            logger.info("✅ 小伴 LLM 路由器：主通道 = Manus API")
        else:
            logger.warning("⚠️ 小伴 LLM 路由器：Manus API 不可用，使用 OpenAI 降级通道")

    def call(self, user_message: str, system_prompt: str = "",
             messages_history: List[Dict] = None, force_fallback: bool = False) -> Dict:
        result = None
        if self.manus.is_available() and not force_fallback:
            try:
                result = self.manus.call_llm(user_message, system_prompt)
            except Exception as e:
                logger.warning(f"Manus API 调用失败，降级到 OpenAI: {e}")
        if result is None:
            if not self.fallback.is_available():
                return {"content": "小伴暂时无法回应，请稍后再试。（所有 LLM 通道不可用）",
                        "source": "error", "tokens_used": 0, "task_id": None}
            result = self.fallback.call_llm(user_message, system_prompt, messages_history)
        tokens = result.get("tokens_used", 0)
        if tokens > self.TOKEN_ALERT_THRESHOLD:
            logger.warning(f"⚠️ Token 异常告警：单次调用消耗 {tokens} tokens，来源: {result.get('source')}")
        self._call_log.append({"timestamp": datetime.now().isoformat(),
                               "source": result.get("source"),
                               "tokens_used": tokens, "task_id": result.get("task_id")})
        return result

    def get_call_stats(self) -> Dict:
        if not self._call_log:
            return {"total_calls": 0, "total_tokens": 0, "manus_calls": 0, "fallback_calls": 0}
        total_tokens = sum(log["tokens_used"] for log in self._call_log)
        manus_calls = sum(1 for log in self._call_log if log["source"] == "manus")
        fallback_calls = sum(1 for log in self._call_log if log["source"] == "openai_fallback")
        return {"total_calls": len(self._call_log), "total_tokens": total_tokens,
                "manus_calls": manus_calls, "fallback_calls": fallback_calls,
                "manus_ratio": f"{manus_calls / len(self._call_log) * 100:.1f}%"}

    def status(self) -> Dict:
        return {"manus_available": self.manus.is_available(),
                "fallback_available": self.fallback.is_available(),
                "active_channel": "manus" if self.manus.is_available() else "openai_fallback",
                "manus_project_id": MANUS_PROJECT_ID,
                "manus_api_key_set": bool(MANUS_API_KEY)}


# ─────────────────────────────────────────────────────────────────────────────
# 全局单例
# ─────────────────────────────────────────────────────────────────────────────

_llm_router_instance: Optional[UnifiedLLMRouter] = None


def get_llm_router() -> UnifiedLLMRouter:
    """获取全局 LLM 路由器单例（所有模块应通过此函数调用 LLM）"""
    global _llm_router_instance
    if _llm_router_instance is None:
        _llm_router_instance = UnifiedLLMRouter()
    return _llm_router_instance


def llm_call(user_message: str, system_prompt: str = "",
             messages_history: List[Dict] = None) -> str:
    """
    最简 LLM 调用函数（供各引擎文件使用）

    替换原有的：
        client = OpenAI()
        response = client.chat.completions.create(model="gpt-4.1-mini", ...)
        reply = response.choices[0].message.content

    新用法：
        from engines.llm_core import llm_call
        reply = llm_call(user_message, system_prompt)
    """
    router = get_llm_router()
    result = router.call(user_message, system_prompt, messages_history)
    return result["content"]


# ─────────────────────────────────────────────────────────────────────────────
# XiaoBanLLMCore（向后兼容层）
# ─────────────────────────────────────────────────────────────────────────────

class XiaoBanLLMCore:
    """小伴 LLM 核心（向后兼容层）— v5.2 内部使用统一路由器"""

    def __init__(self, memory_manager=None):
        self.router = get_llm_router()
        self.memory_manager = memory_manager
        self.max_history_turns = 10
        self.model = "manus-api" if self.router.manus.is_available() else "gpt-4.1-mini"

        self.persona_core = """你是"小伴"，北京市海淀区七一小学学生陈翊霆（小可爱）的成长陪伴智能体。

【身份锚定】
- 你是小可爱的学习伙伴和成长顾问，不是老师，不是家长，是一个比孩子大几岁的睿智朋友
- 你对北京小升初政策（特别是海淀区）有深度了解，熟悉七一小学的完整派位池
- 你深度集成了张雪峰的学习方法论：重视就业导向、城市选择、专业匹配

【核心行为准则】
1. 辅导作业时：永远不直接给答案，用苏格拉底式提问引导孩子思考
2. 面对家长时：提供专业、数据驱动的分析，语言成熟、有逻辑
3. 面对孩子时：语言轻松、鼓励为主，不制造焦虑
4. 遇到不确定信息：明确标注"此信息需要核实"，不编造政策细节
5. 心理支持：当孩子表现出焦虑或挫败感时，先共情再解决问题

【关键背景信息】
- 学生：陈翊霆（小可爱），北京市海淀区七一小学，海淀学籍+丰台户籍
- 家庭住址：丰台东大街5号院社区
- 当前阶段：小升初关键期（2026年4月）
- 家长：Lion（父亲），Aegis CTO 背景，技术思维强
"""

    def build_system_prompt(self, context: str = "general",
                             user_input: str = "", speaker: str = "parent") -> str:
        base_prompt = self.persona_core
        if self.memory_manager:
            try:
                profile = self.memory_manager.get_profile()
                academic = profile.get("academic_level", {})
                weak_subjects = [k for k, v in academic.items() if isinstance(v, (int, float)) and v < 0.6]
                if weak_subjects:
                    base_prompt += f"\n\n【当前学情】薄弱科目：{', '.join(weak_subjects)}，辅导时重点关注。"
            except Exception:
                pass
        context_prompts = {
            "homework": "\n\n【当前模式：作业辅导】请用苏格拉底式提问，绝对不要直接给出答案，引导孩子自己推导。",
            "xiaoshengchu": "\n\n【当前模式：小升初规划】请基于七一小学派位池数据，提供精准、有数据支撑的建议。注意区分海淀学籍和丰台户籍的政策差异。",
            "psychology": "\n\n【当前模式：心理陪伴】请先充分共情，再温和引导。不要急于给解决方案，让孩子感受到被理解。",
            "career": "\n\n【当前模式：生涯规划】请结合张雪峰方法论，从就业前景、城市发展、专业匹配三个维度分析。",
            "general": ""
        }
        base_prompt += context_prompts.get(context, "")
        if speaker == "parent":
            base_prompt += "\n\n【说话对象：家长Lion】请使用专业、简洁的语言，可以直接给出结论和建议。"
        else:
            base_prompt += "\n\n【说话对象：小可爱（学生）】请使用轻松、鼓励的语言，多用苏格拉底式提问。"
        return base_prompt

    def detect_intent(self, user_message: str) -> str:
        msg = user_message.lower()
        if any(kw in msg for kw in ["作业", "题", "不会", "怎么算", "解题", "数学", "语文", "英语"]):
            return "homework"
        elif any(kw in msg for kw in ["小升初", "志愿", "派位", "学校", "初中", "升学"]):
            return "xiaoshengchu"
        elif any(kw in msg for kw in ["难过", "焦虑", "压力", "不想", "害怕", "担心", "紧张"]):
            return "psychology"
        elif any(kw in msg for kw in ["专业", "大学", "职业", "工作", "未来", "高考"]):
            return "career"
        else:
            return "general"

    def chat(self, user_message: str, history: List[Dict] = None,
             speaker: str = "parent") -> Dict:
        intent = self.detect_intent(user_message)
        system_prompt = self.build_system_prompt(context=intent, speaker=speaker)
        recent_history = history[-self.max_history_turns * 2:] if history else []
        try:
            result = self.router.call(user_message=user_message,
                                      system_prompt=system_prompt,
                                      messages_history=recent_history)
            reply = result["content"]
            tokens_used = result["tokens_used"]
            source = result["source"]
            if self.memory_manager:
                try:
                    self.memory_manager.save_dialogue(
                        speaker=speaker, message=user_message, reply=reply, skill=intent)
                except Exception:
                    pass
            return {"reply": reply, "intent": intent, "model": self.model,
                    "tokens_used": tokens_used, "source": source, "status": "success"}
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return {"reply": f"小伴暂时无法回应，请稍后再试。（错误：{str(e)[:100]}）",
                    "intent": intent, "model": self.model, "tokens_used": 0,
                    "source": "error", "status": "error"}

    def quick_answer(self, question: str) -> str:
        result = self.chat(question, history=[], speaker="parent")
        return result["reply"]

    def switch_model(self, model_name: str) -> str:
        supported = ["gpt-4.1-mini", "gpt-4.1-nano", "gemini-2.5-flash", "manus-api"]
        if model_name in supported:
            if model_name == "manus-api":
                self.model = "manus-api"
                return "已切换到 Manus API 主通道"
            else:
                if self.router.fallback.is_available():
                    self.router.fallback.model = model_name
                self.model = model_name
                return f"已切换 fallback 通道模型为：{model_name}"
        return f"不支持的模型：{model_name}。支持：{supported}"


_llm_core_instance: Optional[XiaoBanLLMCore] = None


def get_llm_core() -> XiaoBanLLMCore:
    """获取 XiaoBanLLMCore 单例（向后兼容）"""
    global _llm_core_instance
    if _llm_core_instance is None:
        _llm_core_instance = XiaoBanLLMCore()
    return _llm_core_instance


if __name__ == "__main__":
    print("=" * 60)
    print("小伴 v5.2 LLM Core 测试（统一 Manus API 路由）")
    print("=" * 60)
    router = get_llm_router()
    status = router.status()
    print(f"\n【路由器状态】")
    print(f"  Manus API 可用: {status['manus_available']}")
    print(f"  OpenAI 降级可用: {status['fallback_available']}")
    print(f"  当前活跃通道: {status['active_channel']}")
    print(f"  Manus API Key 已设置: {status['manus_api_key_set']}")
    print(f"  Manus 项目 ID: {status['manus_project_id']}")
    core = get_llm_core()
    print(f"\n【LLM Core 状态】当前模型标识: {core.model}")
    print(f"\n【意图识别测试】")
    test_cases = [("这道数学题我不会", "homework"), ("小升初志愿怎么填", "xiaoshengchu"),
                  ("孩子最近压力很大", "psychology"), ("你好小伴", "general")]
    all_pass = True
    for msg, expected in test_cases:
        detected = core.detect_intent(msg)
        icon = "✅" if detected == expected else "❌"
        if detected != expected:
            all_pass = False
        print(f"  {icon} '{msg}' → {detected}")
    print(f"  结果: {'全部通过' if all_pass else '存在失败项'}")
    print(f"\n✅ LLM Core v5.2 初始化完成")
    print(f"   主通道: {'Manus API ✅' if router.manus.is_available() else 'Manus API ❌（未设置 API Key）'}")
    print(f"   降级通道: {'OpenAI ✅' if router.fallback.is_available() else 'OpenAI ❌'}")
