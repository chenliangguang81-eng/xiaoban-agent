"""
技能：homework_coach
作业辅导（苏格拉底式提问，不直接给答案）
"""

import json
import os
from openai import OpenAI

client = OpenAI()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

SKILL_PROMPT = """你是小伴的"作业辅导"模块。
规则：
1. 永远不直接给出答案
2. 先问学生："你是怎么想的？" 或 "这一步卡在哪了？"
3. 用符合 11-12 岁认知水平的比喻解释抽象概念
4. 分步引导，每步确认学生理解后再进入下一步
5. 发现错误时，温和但直接指出，不说"这么简单你都不会"
6. 每次辅导结束后，询问"这次讲解清晰吗？1-5分给个评价"
7. 辅导完成后，将题目类型和知识点标记，供错题本归档
"""

def coach(question: str, context: str = "") -> dict:
    """
    对一道题目进行苏格拉底式辅导
    返回: {"response": str, "topic": str, "knowledge_point": str}
    """
    messages = [
        {"role": "system", "content": SKILL_PROMPT},
        {"role": "user", "content": f"学生的问题：{question}\n补充背景：{context}"}
    ]
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.6,
        max_tokens=800,
    )
    reply = resp.choices[0].message.content.strip()

    # 提取知识点标签（简单启发式）
    tag_messages = [
        {"role": "system", "content": "请从以下题目中提取：1.学科（语文/数学/英语/其他）2.知识点名称（5字以内）。只返回JSON格式：{\"subject\": \"...\", \"knowledge_point\": \"...\"}"},
        {"role": "user", "content": question}
    ]
    tag_resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=tag_messages,
        temperature=0,
        max_tokens=100,
    )
    try:
        tags = json.loads(tag_resp.choices[0].message.content.strip())
    except Exception:
        tags = {"subject": "未知", "knowledge_point": "未知"}

    return {
        "response": reply,
        "subject": tags.get("subject", "未知"),
        "knowledge_point": tags.get("knowledge_point", "未知"),
    }
