"""
记忆文件迁移脚本 v1 → v2
将旧格式 JSON 迁移为 MemoryManager 标准格式
"""
import json
import os
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path("memory")

def write_json(path, data):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    print(f"  写入: {path.name}")

# 1. student_profile.json — 重建为标准格式
profile = {
    "name": "小可爱",
    "grade": "六年级",
    "school": "北京市海淀区七一小学",
    "school_district": "海淀区",
    "home_address": "北京市丰台区丰台东大街5号院",
    "home_district": "丰台区",
    "guardian": {
        "name": "Lion",
        "email": "24525837@qq.com",
        "location": "洛杉矶"
    },
    "personality": {},
    "interests": [],
    "strengths": [],
    "weaknesses": [],
    "academic_level": {},
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
}
write_json(MEMORY_DIR / "student_profile.json", profile)

# 2. knowledge_mastery.json — 清空为空字典（MemoryManager 格式）
write_json(MEMORY_DIR / "knowledge_mastery.json", {})

# 3. mistake_book.json — 迁移旧错题到新格式
old_mb_path = MEMORY_DIR / "backup_v1" / "mistake_book.json"
old_mb = {}
if old_mb_path.exists():
    with open(old_mb_path) as f:
        old_mb = json.load(f)

new_entries = []
# 旧格式是 {"chinese": [], "math": [...], "english": []}
for subject, entries in old_mb.items():
    if isinstance(entries, list):
        for e in entries:
            new_entry = {
                "id": e.get("id", f"m_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "subject": subject,
                "question": e.get("question", ""),
                "error_reason": e.get("error_analysis", e.get("error_reason", "")),
                "knowledge_point": e.get("knowledge_point", ""),
                "summary": f"{subject}-{e.get('knowledge_point', '')}: {e.get('question', '')[:30]}",
                "created_at": e.get("created_at", datetime.now().isoformat()),
                "review_count": e.get("review_count", 0),
                "review_schedule": e.get("review_schedule", []),
            }
            new_entries.append(new_entry)

write_json(MEMORY_DIR / "mistake_book.json", {"entries": new_entries})
print(f"  迁移错题: {len(new_entries)} 条")

# 4. reminders.json — 标准格式
write_json(MEMORY_DIR / "reminders.json", {"pending": []})

# 5. growth_journal.json
write_json(MEMORY_DIR / "growth_journal.json", {"events": []})

# 6. parent_feedback.json
write_json(MEMORY_DIR / "parent_feedback.json", {"feedback": []})

print("\n✅ 记忆文件迁移完成（v1 → v2 MemoryManager 格式）")
