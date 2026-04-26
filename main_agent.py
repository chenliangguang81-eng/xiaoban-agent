"""
小伴 主调度 Agent v5.1
小可爱成长陪伴智能体 · 北京市海淀区七一小学
重构：统一使用 MemoryManager 管理所有记忆读写
Mythos 升级：接入 MythosIdentityEngine，实现身份锚定自动注入
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from openai import OpenAI

# ── 路径常量 ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
MEMORY_DIR = BASE_DIR / "memory"
KB_DIR = BASE_DIR / "knowledge_base"

# ── 将项目根目录加入 sys.path ─────────────────────────────────────────────────
sys.path.insert(0, str(BASE_DIR))

# ── OpenAI 客户端 ─────────────────────────────────────────────────────────────
client = OpenAI()

# ── MemoryManager 单例 ────────────────────────────────────────────────────────
from memory.memory_manager import MemoryManager
from engines.mythos_identity_engine import MythosIdentityEngine, InteractionContext

_memory: MemoryManager = None
_mythos_engine: MythosIdentityEngine = None

def get_memory() -> MemoryManager:
    global _memory
    if _memory is None:
        _memory = MemoryManager(MEMORY_DIR)
    return _memory

def get_mythos_engine() -> MythosIdentityEngine:
    """MythosIdentityEngine 单例"""
    global _mythos_engine
    if _mythos_engine is None:
        _mythos_engine = MythosIdentityEngine()
    return _mythos_engine

# ── 说话人识别 ────────────────────────────────────────────────────────────────

def identify_speaker(text: str) -> str:
    """返回 'student' 或 'parent'"""
    parent_signals = ["政策", "择校", "规划", "分数线", "小可爱", "Lion", "派位", "学籍", "户籍", "民办", "成长报告"]
    student_signals = ["这题", "老师布置", "同学", "我的作业", "我不会", "我不懂", "帮我讲", "怎么做"]
    p_score = sum(1 for s in parent_signals if s in text)
    s_score = sum(1 for s in student_signals if s in text)
    if p_score > s_score:
        return "parent"
    if s_score > p_score:
        return "student"
    return "unknown"

# ── 技能路由 ──────────────────────────────────────────────────────────────────

def route_skills(text: str) -> list[str]:
    """根据用户输入返回需要调用的技能列表"""
    skills = []
    routing_rules = [
        (["这题怎么做", "讲讲", "知识点", "不明白", "怎么做"], ["homework_coach", "knowledge_graph_tracker"]),
        (["我错了", "又做错了", "这题不会"], ["mistake_book", "homework_coach"]),
        (["期中", "期末", "月考", "复习"], ["exam_strategy", "mistake_book"]),
        (["小升初", "哪个中学", "派位", "跨区", "升初中", "中学"], ["xiaoshengchu_planner", "school_database", "policy_tracker"]),
        (["中考", "分数线"], ["zhongkao_planner"]),
        (["高考", "选科", "大学", "专业", "志愿"], ["gaokao_planner", "zhang_xuefeng_advisor"]),
        (["学什么专业", "就业", "前景", "城市选择"], ["zhang_xuefeng_advisor"]),
        (["怎么学", "学习方法", "提分", "效率", "提高成绩"], ["zhang_xuefeng_advisor"]),
        (["推荐书", "读什么书", "书单"], ["zhang_xuefeng_advisor"]),
        (["好累", "不想学", "烦", "压力大", "焦虑", "沮丧"], ["psychology_companion"]),
        (["附近", "图书馆", "博物馆", "培训班"], ["local_resource_finder"]),
        (["了解自己", "适合什么", "性格", "兴趣"], ["interest_explorer"]),
        (["最近怎么样", "成长报告", "本月总结", "月报"], ["parent_report"]),
    ]
    for keywords, skill_list in routing_rules:
        if any(kw in text for kw in keywords):
            for s in skill_list:
                if s not in skills:
                    skills.append(s)
    if not skills:
        skills = ["homework_coach"]
    return skills

# ── System Prompt 构建 ────────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """你是"小伴"，一个专为北京市海淀区七一小学六年级学生"小可爱"设计的成长陪伴智能体。

## 当前学生信息（来自长期记忆）
{context_summary}

## 当前说话人：{speaker}
{speaker_instruction}

## 当前激活技能：{skills}

## 今日待处理事项
{daily_items}

## 核心原则
1. 长期记忆优先：已读取记忆文件，不让用户重复告知已知信息
2. 不编造：不知道的信息直接说"我查一下"；政策、分数线严禁凭印象回答
3. 敢说不：张雪峰式直率，不合适的选择明确说不合适并给出理由
4. 保护隐私：不对外透露小可爱的任何个人信息
5. 学段自适应：当前是"小学六年级·小升初冲刺期"模式
6. ⚠️ 关键矛盾：学籍在海淀（七一小学）、户籍在丰台（丰台东大街5号院），任何升学建议必须优先考虑此点

## 输出规范
- 对学生：简洁亲切（<300字），苏格拉底式引导，不直接给答案
- 对家长：可详尽（1000+字），数据驱动，政策信息注明来源和日期
- 不确定时：明确说"这点我需要查一下"
"""

def build_system_prompt(speaker: str, skills: list[str], user_input: str = "") -> str:
    mem = get_memory()
    context_summary = mem.get_context_summary()
    # 今日待处理事项
    due_reminders = mem.get_due_reminders()
    if due_reminders:
        daily_items = "\n".join([f"- {r.get('message', '')}" for r in due_reminders[:5]])
    else:
        daily_items = "（今日无待处理事项）"
    # 说话人指令
    if speaker == "student":
        speaker_instruction = "当前是学生模式：使用温暖学长/学姐口吻，苏格拉底式引导，活泼有温度，不直接给答案。"
    elif speaker == "parent":
        speaker_instruction = "当前是家长模式：使用专业顾问口吻，数据驱动，敢说真话，建议结构化。"
    else:
        speaker_instruction = "说话人未确定，请先礼貌询问：'请问是小可爱自己在问，还是 Lion 爸爸在问？'"
    
    # ── Mythos 身份锚定注入 ──────────────────────────────────────────────────
    mythos_prompt = ""
    try:
        mythos = get_mythos_engine()
        # 评估压力级别
        pressure_level = mythos.evaluate_pressure_level(user_input) if user_input else 0
        # 推断情绪
        user_emotion = "anxious" if any(kw in user_input for kw in ["焦虑", "担心", "压力", "紧张"]) else "calm"
        # 构建交互上下文
        ctx = InteractionContext(
            user_role=speaker if speaker in ["student", "parent"] else "parent",
            grade=6,
            topic=skills[0] if skills else "general",
            user_emotion=user_emotion,
            pressure_level=pressure_level
        )
        mythos_prompt = "\n" + mythos.generate_identity_prompt(ctx)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Mythos 注入失败（不影响主流程）: {e}")
    # ─────────────────────────────────────────────────────────────────────────
    
    base_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        context_summary=context_summary,
        speaker=speaker,
        speaker_instruction=speaker_instruction,
        skills=", ".join(skills),
        daily_items=daily_items,
    )
    return base_prompt + mythos_prompt

# ── 主对话入口 ────────────────────────────────────────────────────────────────

def chat(user_input: str) -> str:
    """
    主对话函数：接收用户输入，返回小伴回复
    """
    mem = get_memory()

    # 1. 识别说话人
    speaker = identify_speaker(user_input)

    # 2. 路由技能
    skills = route_skills(user_input)

    # 3. 构建 system prompt（已集成 MemoryManager 上下文 + Mythos 身份锚定）
    system_prompt = build_system_prompt(speaker, skills, user_input)

    # 4. 加载近期对话历史
    recent = mem.get_recent_dialogues(days=7)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in recent[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_input})

    # 5. 调用 LLM
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=1500,
    )
    reply = response.choices[0].message.content.strip()

    # 6. 写回记忆（通过 MemoryManager）
    mem.append_dialogue("user", user_input, speaker=speaker, skill_used=skills[0] if skills else None)
    mem.append_dialogue("assistant", reply, speaker="xiaoban", skill_used=skills[0] if skills else None)

    return reply

# ── 便捷工具函数（供外部调用） ─────────────────────────────────────────────────

def add_mistake(subject: str, question: str, error_reason: str, knowledge_point: str) -> str:
    """添加错题到记忆系统"""
    mem = get_memory()
    return mem.add_mistake({
        "subject": subject,
        "question": question,
        "error_reason": error_reason,
        "knowledge_point": knowledge_point,
        "summary": f"{subject}-{knowledge_point}: {question[:30]}",
    })

def update_mastery(subject: str, knowledge_point: str, level: float, evidence: str = "") -> None:
    """更新知识点掌握度（0.0-1.0）"""
    get_memory().update_mastery(subject, knowledge_point, level, evidence)

def get_profile() -> dict:
    """获取学生画像"""
    return get_memory().get_profile()

def update_profile(updates: dict) -> None:
    """更新学生画像"""
    get_memory().update_profile(updates)

# ── CLI 测试入口 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("小伴 v2.0 · 成长陪伴智能体  (输入 'exit' 退出)")
    print("=" * 60)
    mem = get_memory()
    profile = mem.get_profile()
    print(f"学生：{profile.get('name')}，{profile.get('grade')}，{profile.get('school')}")
    print(f"家长：{profile.get('guardian', {}).get('name')}（{profile.get('guardian', {}).get('location')}）")
    print("=" * 60)

    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in ("exit", "quit", "退出"):
            print("小伴：再见！我会一直在这里陪伴小可爱的成长 ✨")
            break
        if not user_input:
            continue
        reply = chat(user_input)
        print(f"\n小伴：{reply}")
