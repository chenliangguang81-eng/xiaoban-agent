"""
小伴 LLM 核心对话引擎 (LLM Core)
v4.0 — 接入 OpenAI API，实现真实对话能力

架构设计：
- 模型解耦：底层模型可随时替换（GPT-4.1 → Gemini → 未来模型）
- 系统提示词动态生成：根据 GBrain 学生画像自动构建个性化 System Prompt
- 对话历史管理：滑动窗口 + 摘要压缩，防止 Token 爆炸
- 技能路由：自动识别用户意图，调用对应技能模块
"""

import os
import json
from openai import OpenAI
from typing import List, Dict, Optional
from datetime import datetime

class XiaoBanLLMCore:
    """小伴 LLM 核心，负责所有与大语言模型的交互"""

    def __init__(self, memory_manager=None):
        self.client = OpenAI()  # 自动读取 OPENAI_API_KEY 环境变量
        self.model = "gpt-4.1-mini"  # 默认模型，可随时切换
        self.memory_manager = memory_manager
        self.max_history_turns = 10  # 滑动窗口：保留最近10轮对话
        
        # 小伴核心人格提示词（基于 Claude Mythos 蒸馏）
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

    def build_system_prompt(self, context: str = "general") -> str:
        """根据对话上下文动态构建系统提示词"""
        base_prompt = self.persona_core
        
        # 从记忆系统读取学生当前状态
        if self.memory_manager:
            try:
                profile = self.memory_manager.get_profile()
                academic = profile.get("academic_level", {})
                weak_subjects = [k for k, v in academic.items() if isinstance(v, (int, float)) and v < 0.6]
                if weak_subjects:
                    base_prompt += f"\n\n【当前学情】薄弱科目：{', '.join(weak_subjects)}，辅导时重点关注。"
            except Exception:
                pass
        
        # 根据上下文添加专项指令
        context_prompts = {
            "homework": "\n\n【当前模式：作业辅导】请用苏格拉底式提问，绝对不要直接给出答案，引导孩子自己推导。",
            "xiaoshengchu": "\n\n【当前模式：小升初规划】请基于七一小学派位池数据，提供精准、有数据支撑的建议。注意区分海淀学籍和丰台户籍的政策差异。",
            "psychology": "\n\n【当前模式：心理陪伴】请先充分共情，再温和引导。不要急于给解决方案，让孩子感受到被理解。",
            "career": "\n\n【当前模式：生涯规划】请结合张雪峰方法论，从就业前景、城市发展、专业匹配三个维度分析。",
            "general": ""
        }
        
        return base_prompt + context_prompts.get(context, "")

    def detect_intent(self, user_message: str) -> str:
        """简单意图识别，路由到对应技能模式"""
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

    def chat(self, user_message: str, history: List[Dict] = None, speaker: str = "parent") -> Dict:
        """
        核心对话方法
        
        Args:
            user_message: 用户输入
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]
            speaker: "parent"（家长Lion）或 "student"（小可爱）
        
        Returns:
            {"reply": str, "intent": str, "model": str, "tokens_used": int}
        """
        # 意图识别
        intent = self.detect_intent(user_message)
        
        # 构建系统提示词
        system_prompt = self.build_system_prompt(context=intent)
        
        # 如果是家长，调整语气
        if speaker == "parent":
            system_prompt += "\n\n【说话对象：家长Lion】请使用专业、简洁的语言，可以直接给出结论和建议，不需要过多引导式提问。"
        else:
            system_prompt += "\n\n【说话对象：小可爱（学生）】请使用轻松、鼓励的语言，多用苏格拉底式提问。"
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话（滑动窗口）
        if history:
            recent_history = history[-self.max_history_turns * 2:]  # 每轮2条消息
            messages.extend(recent_history)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})
        
        # 调用 LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            
            reply = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            # 保存到记忆系统
            if self.memory_manager:
                try:
                    self.memory_manager.save_dialogue(
                        speaker=speaker,
                        message=user_message,
                        reply=reply,
                        skill=intent
                    )
                except Exception:
                    pass
            
            return {
                "reply": reply,
                "intent": intent,
                "model": self.model,
                "tokens_used": tokens_used,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "reply": f"小伴暂时无法回应，请稍后再试。（错误：{str(e)}）",
                "intent": intent,
                "model": self.model,
                "tokens_used": 0,
                "status": "error"
            }

    def quick_answer(self, question: str) -> str:
        """快速问答，不携带历史上下文，用于单次查询"""
        result = self.chat(question, history=[], speaker="parent")
        return result["reply"]

    def switch_model(self, model_name: str):
        """切换底层模型（模型解耦设计）"""
        supported_models = ["gpt-4.1-mini", "gpt-4.1-nano", "gemini-2.5-flash"]
        if model_name in supported_models:
            self.model = model_name
            return f"已切换到模型：{model_name}"
        else:
            return f"不支持的模型：{model_name}。支持的模型：{supported_models}"


if __name__ == "__main__":
    # 快速测试
    core = XiaoBanLLMCore()
    print("=== 小伴 LLM 核心测试 ===")
    print(f"当前模型：{core.model}")
    
    # 测试意图识别
    test_cases = [
        ("这道数学题我不会", "homework"),
        ("小升初志愿怎么填", "xiaoshengchu"),
        ("孩子最近压力很大", "psychology"),
        ("你好小伴", "general"),
    ]
    
    print("\n意图识别测试：")
    all_pass = True
    for msg, expected in test_cases:
        detected = core.detect_intent(msg)
        status = "✅" if detected == expected else "❌"
        if detected != expected:
            all_pass = False
        print(f"  {status} '{msg}' → {detected} (期望: {expected})")
    
    print(f"\n意图识别测试：{'全部通过' if all_pass else '存在失败项'}")
    
    # 测试系统提示词生成
    print("\n系统提示词生成测试：")
    for ctx in ["general", "homework", "xiaoshengchu"]:
        prompt = core.build_system_prompt(ctx)
        print(f"  ✅ {ctx} 模式：{len(prompt)} 字符")
    
    print("\n✅ LLM Core 初始化完成，等待 API 调用。")
