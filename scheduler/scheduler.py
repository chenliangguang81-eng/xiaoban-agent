"""
小伴 定时任务调度器
负责：
1. 艾宾浩斯错题复习提醒
2. 月度家长报告自动生成
3. 政策更新检查（每月）
4. 年级自动切换（每年9月1日）
"""

import json
import os
import sys
from datetime import datetime

# 将项目根目录加入 path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

MEMORY_DIR = os.path.join(BASE_DIR, "memory")
REMINDERS_FILE = os.path.join(MEMORY_DIR, "reminders.json")


def load_reminders() -> list:
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_reminders(data: list):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_reminder(reminder_type: str, message: str, trigger_date: str, target: str = "student"):
    reminders = load_reminders()
    reminders.append({
        "id": f"reminder_{len(reminders)+1:04d}",
        "type": reminder_type,
        "message": message,
        "trigger_date": trigger_date,
        "target": target,
        "triggered": False,
        "created_at": datetime.now().isoformat(),
    })
    save_reminders(reminders)


def get_due_reminders(target_date: str = None) -> list:
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")
    reminders = load_reminders()
    due = [r for r in reminders if r["trigger_date"] <= target_date and not r["triggered"]]
    return due


def mark_reminder_done(reminder_id: str):
    reminders = load_reminders()
    for r in reminders:
        if r["id"] == reminder_id:
            r["triggered"] = True
    save_reminders(reminders)


def run_daily_check():
    """每日启动时执行的检查任务"""
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    results = []

    # 1. 检查错题复习提醒
    try:
        from skills.mistake_book import get_due_reviews
        due_reviews = get_due_reviews(today_str)
        if due_reviews:
            results.append({
                "type": "mistake_review",
                "count": len(due_reviews),
                "items": due_reviews,
                "message": f"今天有 {len(due_reviews)} 道错题需要复习！",
            })
    except Exception as e:
        results.append({"type": "error", "message": f"错题检查失败: {e}"})

    # 2. 检查是否月初（生成家长报告）
    if today.day == 1:
        try:
            from skills.parent_report import generate_report
            period = today.strftime("%Y年%m月")
            report = generate_report(period)
            results.append({
                "type": "parent_report",
                "message": f"已自动生成 {period} 家长报告",
                "report_preview": report[:200] + "...",
            })
        except Exception as e:
            results.append({"type": "error", "message": f"家长报告生成失败: {e}"})

    # 3. 检查年级切换（9月1日）
    if today.month == 9 and today.day == 1:
        try:
            profile_path = os.path.join(MEMORY_DIR, "student_profile.json")
            with open(profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
            grade_map = {
                "小学六年级": "初一",
                "初一": "初二",
                "初二": "初三",
                "初三": "高一",
                "高一": "高二",
                "高二": "高三",
            }
            current_grade = profile.get("grade", "")
            new_grade = grade_map.get(current_grade)
            if new_grade:
                profile["grade"] = new_grade
                with open(profile_path, "w", encoding="utf-8") as f:
                    json.dump(profile, f, ensure_ascii=False, indent=2)
                results.append({
                    "type": "grade_upgrade",
                    "message": f"🎉 年级已自动升级：{current_grade} → {new_grade}",
                })
        except Exception as e:
            results.append({"type": "error", "message": f"年级切换失败: {e}"})

    # 4. 检查自定义提醒
    due_reminders = get_due_reminders(today_str)
    for r in due_reminders:
        results.append({
            "type": "custom_reminder",
            "message": r["message"],
            "target": r["target"],
        })
        mark_reminder_done(r["id"])

    return results


if __name__ == "__main__":
    print("=" * 50)
    print(f"小伴调度器 · 每日检查 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    results = run_daily_check()
    if results:
        for r in results:
            print(f"\n[{r['type'].upper()}] {r['message']}")
    else:
        print("\n今日无待处理事项。")
