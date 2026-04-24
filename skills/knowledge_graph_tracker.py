"""
技能：knowledge_graph_tracker
知识点掌握度图谱追踪
"""

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
MASTERY_FILE = os.path.join(MEMORY_DIR, "knowledge_mastery.json")

# 小学六年级知识点图谱（核心节点）
KNOWLEDGE_GRAPH = {
    "chinese": {
        "reading": ["记叙文阅读", "说明文阅读", "诗歌鉴赏", "文言文阅读"],
        "writing": ["记叙文写作", "说明文写作", "应用文写作"],
        "grammar": ["词性", "句子成分", "修辞手法"],
        "vocabulary": ["成语", "近义词辨析", "字音字形"],
    },
    "math": {
        "calculation": ["整数运算", "小数运算", "分数运算", "混合运算"],
        "geometry": ["平面图形面积", "立体图形体积", "图形变换"],
        "logic": ["排列组合", "逻辑推理", "数学归纳"],
        "application": ["行程问题", "工程问题", "比例问题", "统计图表"],
    },
    "english": {
        "listening": ["日常对话理解", "短文听力"],
        "speaking": ["日常交际用语", "口头表达"],
        "reading": ["短文阅读", "词汇理解"],
        "writing": ["句型仿写", "短文写作"],
    },
}


def load_mastery() -> dict:
    if os.path.exists(MASTERY_FILE):
        with open(MASTERY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {subj: {dim: 0 for dim in dims} for subj, dims in KNOWLEDGE_GRAPH.items()}


def save_mastery(data: dict):
    with open(MASTERY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_mastery(subject: str, dimension: str, score: float):
    """
    更新某学科某维度的掌握度（0-100）
    采用指数移动平均，避免单次波动影响过大
    """
    data = load_mastery()
    if subject in data and dimension in data[subject]:
        old = data[subject][dimension]
        # 指数移动平均：alpha=0.3
        data[subject][dimension] = round(old * 0.7 + score * 0.3, 1)
        save_mastery(data)
        return data[subject][dimension]
    return None


def get_weak_points(threshold: float = 60.0) -> list[dict]:
    """
    返回掌握度低于阈值的薄弱点
    """
    data = load_mastery()
    weak = []
    for subj, dims in data.items():
        for dim, score in dims.items():
            if score < threshold:
                weak.append({
                    "subject": subj,
                    "dimension": dim,
                    "score": score,
                    "knowledge_nodes": KNOWLEDGE_GRAPH.get(subj, {}).get(dim, []),
                })
    return sorted(weak, key=lambda x: x["score"])


def get_summary_report() -> str:
    """
    生成知识点掌握度文字摘要
    """
    data = load_mastery()
    lines = ["## 知识点掌握度报告\n"]
    for subj, dims in data.items():
        subj_name = {"chinese": "语文", "math": "数学", "english": "英语"}.get(subj, subj)
        avg = sum(dims.values()) / len(dims) if dims else 0
        lines.append(f"### {subj_name}（平均 {avg:.0f}/100）")
        for dim, score in dims.items():
            bar = "█" * int(score // 10) + "░" * (10 - int(score // 10))
            status = "✅" if score >= 80 else ("⚠️" if score >= 60 else "❌")
            lines.append(f"- {dim}: {bar} {score:.0f}/100 {status}")
        lines.append("")
    return "\n".join(lines)
