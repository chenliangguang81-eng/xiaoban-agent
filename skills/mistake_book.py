"""
技能：mistake_book
错题本：自动归档 + 艾宾浩斯曲线复习提醒
"""

import json
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
MISTAKE_FILE = os.path.join(MEMORY_DIR, "mistake_book.json")

# 艾宾浩斯复习间隔（天）
EBBINGHAUS_INTERVALS = [1, 2, 4, 7, 15, 30]


def load_mistakes() -> dict:
    if os.path.exists(MISTAKE_FILE):
        with open(MISTAKE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chinese": [], "math": [], "english": []}


def save_mistakes(data: dict):
    with open(MISTAKE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_mistake(subject: str, question: str, error_reason: str, knowledge_point: str) -> dict:
    """
    添加一条错题记录
    """
    data = load_mistakes()
    subject_key = subject.lower()
    if subject_key not in data:
        data[subject_key] = []

    today = datetime.now().strftime("%Y-%m-%d")
    review_dates = [
        (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d")
        for d in EBBINGHAUS_INTERVALS
    ]

    entry = {
        "id": f"{subject_key}_{len(data[subject_key]) + 1:04d}",
        "date_added": today,
        "question": question,
        "error_reason": error_reason,
        "knowledge_point": knowledge_point,
        "review_schedule": review_dates,
        "review_done": [],
        "mastery_level": 0,  # 0-5，每次复习后更新
    }
    data[subject_key].append(entry)
    save_mistakes(data)
    return entry


def get_due_reviews(target_date: str = None) -> list[dict]:
    """
    获取今天（或指定日期）需要复习的错题
    """
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    data = load_mistakes()
    due = []
    for subject, entries in data.items():
        for entry in entries:
            pending = [d for d in entry["review_schedule"] if d <= target_date and d not in entry["review_done"]]
            if pending:
                due.append({
                    "subject": subject,
                    "id": entry["id"],
                    "question": entry["question"],
                    "knowledge_point": entry["knowledge_point"],
                    "overdue_dates": pending,
                })
    return due


def mark_reviewed(mistake_id: str, mastery_level: int) -> bool:
    """
    标记一条错题已复习，并更新掌握度
    """
    data = load_mistakes()
    today = datetime.now().strftime("%Y-%m-%d")
    for subject, entries in data.items():
        for entry in entries:
            if entry["id"] == mistake_id:
                if today not in entry["review_done"]:
                    entry["review_done"].append(today)
                entry["mastery_level"] = mastery_level
                save_mistakes(data)
                return True
    return False


def get_summary() -> dict:
    """
    返回错题本统计摘要
    """
    data = load_mistakes()
    summary = {}
    for subject, entries in data.items():
        total = len(entries)
        mastered = sum(1 for e in entries if e.get("mastery_level", 0) >= 4)
        due_today = len(get_due_reviews())
        summary[subject] = {
            "total": total,
            "mastered": mastered,
            "pending": total - mastered,
            "due_today": due_today,
        }
    return summary
