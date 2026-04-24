"""
MemoryManager：统一管理所有记忆文件的读写
所有技能代码必须通过此类访问 memory/，不允许直接操作 JSON 文件
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional
from threading import Lock


class MemoryManager:
    """长期记忆管理器"""

    def __init__(self, memory_dir: Path):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 子目录
        self.dialogue_dir = self.memory_dir / "dialogue_history"
        self.planning_dir = self.memory_dir / "planning_snapshots"
        self.dialogue_dir.mkdir(exist_ok=True)
        self.planning_dir.mkdir(exist_ok=True)

        self._lock = Lock()  # 并发写入保护

        # 初始化核心文件
        self._ensure_file("student_profile.json", self._default_profile())
        self._ensure_file("knowledge_mastery.json", {})
        self._ensure_file("mistake_book.json", {"entries": []})
        self._ensure_file("reminders.json", {"pending": []})
        self._ensure_file("growth_journal.json", {"events": []})
        self._ensure_file("parent_feedback.json", {"feedback": []})

    # ---------- 基础 IO ----------

    def _ensure_file(self, filename: str, default: Any):
        path = self.memory_dir / filename
        if not path.exists():
            self._write_json(path, default)

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: Any):
        with self._lock:
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)  # 原子替换，避免写入中断导致文件损坏

    # ---------- 默认画像 ----------

    def _default_profile(self) -> dict:
        return {
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

    # ---------- 学生画像 ----------

    def get_profile(self) -> dict:
        return self._read_json(self.memory_dir / "student_profile.json")

    def update_profile(self, updates: dict):
        profile = self.get_profile()
        profile.update(updates)
        profile["updated_at"] = datetime.now().isoformat()
        self._write_json(self.memory_dir / "student_profile.json", profile)

    def update_profile_field(self, field_path: str, value: Any):
        """支持嵌套字段更新，如 'academic_level.math'"""
        profile = self.get_profile()
        keys = field_path.split(".")
        cur = profile
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        cur[keys[-1]] = value
        profile["updated_at"] = datetime.now().isoformat()
        self._write_json(self.memory_dir / "student_profile.json", profile)

    # ---------- 对话历史 ----------

    def append_dialogue(self, role: str, content: str, speaker: str = "unknown",
                        skill_used: Optional[str] = None):
        """追加对话，按日期分文件存储"""
        today = datetime.now().strftime("%Y-%m-%d")
        path = self.dialogue_dir / f"{today}.json"
        data = self._read_json(path) or {"date": today, "messages": []}
        data["messages"].append({
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "role": role,
            "content": content,
            "skill_used": skill_used,
        })
        self._write_json(path, data)

    def get_recent_dialogues(self, days: int = 7) -> list:
        """获取最近 N 天对话"""
        messages = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            path = self.dialogue_dir / f"{date}.json"
            data = self._read_json(path)
            if data:
                messages.extend(data.get("messages", []))
        return sorted(messages, key=lambda m: m["timestamp"])

    # ---------- 知识掌握度 ----------

    def get_mastery(self) -> dict:
        return self._read_json(self.memory_dir / "knowledge_mastery.json")

    def update_mastery(self, subject: str, knowledge_point: str,
                       mastery_level: float, evidence: str = ""):
        """mastery_level: 0.0-1.0"""
        data = self.get_mastery()
        data.setdefault(subject, {})[knowledge_point] = {
            "level": mastery_level,
            "last_updated": datetime.now().isoformat(),
            "evidence": evidence,
        }
        self._write_json(self.memory_dir / "knowledge_mastery.json", data)

    def get_weak_points(self, threshold: float = 0.6) -> list:
        """返回掌握度低于阈值的薄弱知识点"""
        data = self.get_mastery()
        weak = []
        for subject, kps in data.items():
            for kp, info in kps.items():
                level = info.get("level", 0) if isinstance(info, dict) else info
                if level < threshold:
                    weak.append({
                        "subject": subject,
                        "knowledge_point": kp,
                        "level": level,
                    })
        return sorted(weak, key=lambda x: x["level"])

    # ---------- 错题本 ----------

    def add_mistake(self, mistake: dict) -> str:
        """添加错题，自动生成艾宾浩斯复习提醒"""
        data = self._read_json(self.memory_dir / "mistake_book.json")
        mistake_id = f"m_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        mistake["id"] = mistake_id
        mistake["created_at"] = datetime.now().isoformat()
        mistake["review_count"] = 0
        data["entries"].append(mistake)
        self._write_json(self.memory_dir / "mistake_book.json", data)

        # 生成艾宾浩斯复习提醒（1天、3天、7天、15天、30天）
        for days in [1, 3, 7, 15, 30]:
            self.add_reminder({
                "type": "mistake_review",
                "mistake_id": mistake_id,
                "trigger_date": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"),
                "message": f"复习错题：{mistake.get('summary', mistake_id)}"
            })
        return mistake_id

    def get_mistakes(self, subject: Optional[str] = None) -> list:
        data = self._read_json(self.memory_dir / "mistake_book.json")
        entries = data.get("entries", [])
        if subject:
            entries = [e for e in entries if e.get("subject") == subject]
        return entries

    def mark_mistake_reviewed(self, mistake_id: str):
        data = self._read_json(self.memory_dir / "mistake_book.json")
        for e in data["entries"]:
            if e["id"] == mistake_id:
                e["review_count"] = e.get("review_count", 0) + 1
                e["last_reviewed"] = datetime.now().isoformat()
        self._write_json(self.memory_dir / "mistake_book.json", data)

    def get_due_mistake_reviews(self, target_date: str = None) -> list:
        """获取今天需要复习的错题"""
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")
        reminders = self.get_due_reminders()
        return [r for r in reminders if r.get("type") == "mistake_review"
                and r.get("trigger_date", "") <= target_date]

    # ---------- 提醒 ----------

    def add_reminder(self, reminder: dict):
        data = self._read_json(self.memory_dir / "reminders.json")
        reminder["created_at"] = datetime.now().isoformat()
        reminder["triggered"] = False
        data["pending"].append(reminder)
        self._write_json(self.memory_dir / "reminders.json", data)

    def get_due_reminders(self) -> list:
        """获取今天应触发的提醒"""
        data = self._read_json(self.memory_dir / "reminders.json")
        today = datetime.now().strftime("%Y-%m-%d")
        due = [r for r in data["pending"]
               if not r.get("triggered") and r.get("trigger_date", "") <= today]
        return due

    def mark_reminder_triggered(self, reminder_idx: int):
        data = self._read_json(self.memory_dir / "reminders.json")
        if 0 <= reminder_idx < len(data["pending"]):
            data["pending"][reminder_idx]["triggered"] = True
            data["pending"][reminder_idx]["triggered_at"] = datetime.now().isoformat()
        self._write_json(self.memory_dir / "reminders.json", data)

    # ---------- 成长日记 ----------

    def add_growth_event(self, event: dict):
        data = self._read_json(self.memory_dir / "growth_journal.json")
        event["recorded_at"] = datetime.now().isoformat()
        data["events"].append(event)
        self._write_json(self.memory_dir / "growth_journal.json", data)

    def get_growth_events(self, limit: int = 20) -> list:
        data = self._read_json(self.memory_dir / "growth_journal.json")
        return data.get("events", [])[-limit:]

    # ---------- 家长反馈 ----------

    def add_parent_feedback(self, feedback: dict):
        data = self._read_json(self.memory_dir / "parent_feedback.json")
        feedback["recorded_at"] = datetime.now().isoformat()
        data["feedback"].append(feedback)
        self._write_json(self.memory_dir / "parent_feedback.json", data)

    # ---------- 规划快照 ----------

    def save_planning_snapshot(self, plan_type: str, snapshot: dict):
        """保存规划快照（如小升初分析结果）"""
        filename = f"{plan_type}_{datetime.now().strftime('%Y%m%d')}.json"
        self._write_json(self.planning_dir / filename, snapshot)

    def get_latest_planning_snapshot(self, plan_type: str) -> Optional[dict]:
        """获取最新的规划快照"""
        files = sorted([
            f for f in self.planning_dir.iterdir()
            if f.name.startswith(plan_type)
        ], reverse=True)
        if files:
            return self._read_json(files[0])
        return None

    # ---------- 便捷摘要 ----------

    def get_context_summary(self) -> str:
        """生成供 LLM 使用的上下文摘要"""
        profile = self.get_profile()
        mastery = self.get_mastery()
        due_reminders = self.get_due_reminders()
        mistakes = self.get_mistakes()

        lines = [
            f"学生：{profile.get('name')}，{profile.get('grade')}，{profile.get('school')}",
            f"学籍：{profile.get('school_district')}，户籍：{profile.get('home_district')}",
            f"家长：{profile.get('guardian', {}).get('name')}（{profile.get('guardian', {}).get('location')}）",
            f"错题库：共 {len(mistakes)} 条，今日待复习 {len(due_reminders)} 项",
        ]

        # 薄弱点摘要
        weak = self.get_weak_points(threshold=0.7)
        if weak:
            weak_str = "、".join([f"{w['subject']}-{w['knowledge_point']}" for w in weak[:5]])
            lines.append(f"薄弱知识点：{weak_str}")

        return "\n".join(lines)
