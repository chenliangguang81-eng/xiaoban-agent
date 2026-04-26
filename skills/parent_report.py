"""
技能：parent_report
月度家长成长报告生成器
"""
from engines.llm_core import llm_call, get_llm_router

import json
import os
from datetime import datetime
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
DIALOGUE_DIR = os.path.join(MEMORY_DIR, "dialogue_history")


def load_json(filename: str):
    path = os.path.join(MEMORY_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_all_dialogues(limit: int = 50) -> list[dict]:
    all_msgs = []
    if os.path.exists(DIALOGUE_DIR):
        for fname in sorted(os.listdir(DIALOGUE_DIR))[-30:]:
            fpath = os.path.join(DIALOGUE_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                all_msgs.extend(json.load(f))
    return all_msgs[-limit:]


def generate_report(period: str = None) -> str:
    """
    生成家长月度报告
    period: 报告周期描述，如 "2025年4月"，默认为当前月
    """
    if period is None:
        period = datetime.now().strftime("%Y年%m月")

    profile = load_json("student_profile.json")
    mastery = load_json("knowledge_mastery.json")
    mistakes = load_json("mistake_book.json")
    milestones = load_json("growth_milestones.json")

    # 统计错题
    mistake_stats = {}
    for subj, entries in mistakes.items():
        if isinstance(entries, list):
            total = len(entries)
            mastered = sum(1 for e in entries if e.get("mastery_level", 0) >= 4)
            mistake_stats[subj] = {"total": total, "mastered": mastered}

    # 加载对话摘要
    recent_dialogues = load_all_dialogues(limit=50)
    dialogue_text = "\n".join([
        f"[{msg.get('timestamp', '')[:10]}] {msg['role']}: {msg['content'][:100]}..."
        for msg in recent_dialogues[-20:]
    ])

    prompt = f"""请为家长 Lion 生成一份 {period} 的孩子成长报告。

## 数据输入
学生画像：{json.dumps(profile, ensure_ascii=False)}
知识掌握度：{json.dumps(mastery, ensure_ascii=False)}
错题统计：{json.dumps(mistake_stats, ensure_ascii=False)}
成长里程碑：{json.dumps(milestones, ensure_ascii=False)}
近期对话摘要：
{dialogue_text}

## 报告要求
1. 专业顾问口吻，数据驱动
2. 结构：本月亮点 → 待改进项 → 小升初进展 → 下月行动建议
3. 如有数据缺失，注明"（待补充）"
4. 长度：500-800字
5. 结尾附：需要家长配合的事项（如：确认户籍信息、参加某活动等）
"""

    messages = [
        {"role": "system", "content": "你是小伴的家长报告模块，专业、直率、数据驱动。"},
        {"role": "user", "content": prompt}
    ]
    # [v5.2 Manus迁移] 统一路由器调用
    _llm_sys_resp = next((x['content'] for x in messages if x['role']=='system'), '')
    _llm_usr_resp = next((x['content'] for x in reversed(messages) if x['role']=='user'), '')
    _llm_hist_resp = [x for x in messages if x['role'] not in ('system',)][:-1]
    resp_reply = llm_call(_llm_usr_resp, _llm_sys_resp, _llm_hist_resp)
    report = resp_reply.strip()

    # 保存报告
    report_path = os.path.join(MEMORY_DIR, f"parent_report_{datetime.now().strftime('%Y%m')}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# 小可爱成长报告 · {period}\n\n")
        f.write(report)

    return report
