"""
GBrain — Growth Brain (成长大脑)
小伴 v3.0 — 十年可持续架构核心模块

这是小伴的"灵魂"，也是整个系统最核心的资产。
GBrain 是一个自演化的记忆系统，随着小可爱的成长不断更新自身。

核心能力：
1. 基因序列图谱 (Gene Sequence Map)：以"强制执行指令"形式存储核心人格与学习特征
2. 知识图谱追踪 (Knowledge Graph)：将小学到高中所有知识点构建为有向图，追踪掌握度
3. 情绪时间线 (Emotion Timeline)：记录情绪状态变化，用于心理陪伴
4. 自演化机制 (Self-Evolution)：定期分析数据，自动更新学习画像
"""

import json
import os
import threading
from datetime import datetime
from typing import Optional, Any
from pathlib import Path


class GBrain:
    """
    成长大脑 — 小伴的核心记忆与自演化系统

    存储结构（本地文件系统，JSON格式，确保十年可迁移性）：
    gbrain/
    ├── gene_map.json          # 基因序列图谱（核心人格、学习特征）
    ├── knowledge_graph.json   # 知识图谱（所有学科知识点掌握度）
    ├── emotion_timeline.json  # 情绪时间线
    ├── annual_snapshots/      # 年度规划快照（每年归档）
    │   ├── 2026_grade6.json
    │   ├── 2027_grade7.json
    │   └── ...
    └── evolution_log.json     # 自演化日志
    """

    # 知识图谱：小学到高中的核心知识点层级结构
    # 格式：{学科: {知识点ID: {name, parent, grade_introduced, prerequisites}}}
    KNOWLEDGE_GRAPH_SCHEMA = {
        "math": {
            "primary_arithmetic": {"name": "四则运算", "grade_introduced": 1, "prerequisites": []},
            "primary_fractions": {"name": "分数", "grade_introduced": 3, "prerequisites": ["primary_arithmetic"]},
            "primary_geometry": {"name": "平面几何基础", "grade_introduced": 4, "prerequisites": ["primary_arithmetic"]},
            "junior_algebra": {"name": "代数式与方程", "grade_introduced": 7, "prerequisites": ["primary_fractions"]},
            "junior_geometry": {"name": "平面几何证明", "grade_introduced": 7, "prerequisites": ["primary_geometry"]},
            "junior_functions": {"name": "函数基础", "grade_introduced": 8, "prerequisites": ["junior_algebra"]},
            "senior_trigonometry": {"name": "三角函数", "grade_introduced": 10, "prerequisites": ["junior_functions"]},
            "senior_calculus_intro": {"name": "导数与微积分入门", "grade_introduced": 11, "prerequisites": ["senior_trigonometry"]},
            "senior_probability": {"name": "概率与统计", "grade_introduced": 10, "prerequisites": ["junior_functions"]},
        },
        "chinese": {
            "primary_reading": {"name": "阅读理解基础", "grade_introduced": 1, "prerequisites": []},
            "primary_writing": {"name": "基础写作", "grade_introduced": 2, "prerequisites": ["primary_reading"]},
            "junior_literary_analysis": {"name": "文学作品鉴赏", "grade_introduced": 7, "prerequisites": ["primary_reading"]},
            "junior_classical_chinese": {"name": "文言文阅读", "grade_introduced": 7, "prerequisites": ["primary_reading"]},
            "senior_argumentative": {"name": "议论文写作", "grade_introduced": 10, "prerequisites": ["junior_literary_analysis"]},
            "senior_classical_advanced": {"name": "文言文高级阅读", "grade_introduced": 10, "prerequisites": ["junior_classical_chinese"]},
        },
        "english": {
            "primary_vocabulary": {"name": "基础词汇", "grade_introduced": 3, "prerequisites": []},
            "primary_grammar": {"name": "基础语法", "grade_introduced": 4, "prerequisites": ["primary_vocabulary"]},
            "junior_reading": {"name": "英语阅读理解", "grade_introduced": 7, "prerequisites": ["primary_grammar"]},
            "junior_writing": {"name": "英语写作", "grade_introduced": 7, "prerequisites": ["primary_grammar"]},
            "senior_complex_grammar": {"name": "复杂句式与语法", "grade_introduced": 10, "prerequisites": ["junior_reading"]},
            "senior_advanced_writing": {"name": "高考英语写作", "grade_introduced": 10, "prerequisites": ["junior_writing"]},
        },
        "physics": {
            "junior_mechanics": {"name": "力学基础", "grade_introduced": 8, "prerequisites": []},
            "junior_electricity": {"name": "电学基础", "grade_introduced": 9, "prerequisites": ["junior_mechanics"]},
            "senior_kinematics": {"name": "运动学", "grade_introduced": 10, "prerequisites": ["junior_mechanics"]},
            "senior_dynamics": {"name": "动力学（牛顿定律）", "grade_introduced": 10, "prerequisites": ["senior_kinematics"]},
            "senior_electromagnetism": {"name": "电磁学", "grade_introduced": 11, "prerequisites": ["junior_electricity", "senior_dynamics"]},
        },
    }

    def __init__(self, base_dir: str = "/home/ubuntu/xiaoban_agent/gbrain"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "annual_snapshots").mkdir(exist_ok=True)
        self._lock = threading.Lock()

        # 初始化所有核心文件
        self._init_gene_map()
        self._init_knowledge_graph()
        self._init_emotion_timeline()
        self._init_evolution_log()

    # ============================================================
    # 1. 基因序列图谱 (Gene Sequence Map)
    # ============================================================

    def _init_gene_map(self):
        """初始化基因序列图谱"""
        path = self.base_dir / "gene_map.json"
        if not path.exists():
            gene_map = {
                "_meta": {
                    "version": "3.0",
                    "created_at": datetime.now().isoformat(),
                    "description": "小伴的核心人格与学习特征基因图谱。无论使用哪个AI模型，读取此文件即可还原小伴的核心能力。"
                },
                "student": {
                    "name": "小可爱",
                    "school": "北京市海淀区七一小学",
                    "hukou_district": "丰台区",
                    "xuejí_district": "海淀区",
                    "current_grade": 6,
                    "birth_year": 2014,
                },
                "parent": {
                    "name": "Lion",
                    "role": "主要沟通家长",
                },
                "learning_dna": {
                    "learning_style": "待观察",       # visual / auditory / kinesthetic / reading
                    "strength_subjects": [],
                    "weak_subjects": [],
                    "attention_span_minutes": 30,      # 专注时长（分钟），随年龄增长
                    "motivation_type": "待观察",       # intrinsic / extrinsic / social
                    "stress_response": "待观察",       # resilient / sensitive / avoidant
                },
                "personality_traits": {
                    "curiosity_level": 0.5,            # 0-1，好奇心强度
                    "persistence_level": 0.5,          # 0-1，坚持度
                    "social_orientation": 0.5,         # 0-1，社交倾向（0=内向，1=外向）
                    "creativity_level": 0.5,           # 0-1，创造力
                },
                "interest_map": {
                    "stem": 0.5,                       # 理工科兴趣
                    "humanities": 0.5,                 # 人文兴趣
                    "arts": 0.5,                       # 艺术兴趣
                    "sports": 0.5,                     # 体育兴趣
                    "specific_interests": [],          # 具体兴趣标签
                },
                "xiaoban_core_directives": [
                    "永远不直接给答案，用苏格拉底式提问引导思考",
                    "关注小可爱的情绪状态，学习辅导永远排在心理健康之后",
                    "海淀学籍+丰台户籍的跨区问题，在所有升学建议中优先分析",
                    "张雪峰方法论：选专业看就业，选城市看发展，从小学开始建立职业认知",
                    "每次对话后更新知识点掌握度，保持学习轨迹的连续性",
                ]
            }
            self._write_json(path, gene_map)

    def update_gene(self, key_path: str, value: Any):
        """
        更新基因图谱中的某个字段
        key_path 支持点号路径，如 "learning_dna.learning_style"
        """
        with self._lock:
            path = self.base_dir / "gene_map.json"
            data = self._read_json(path)
            keys = key_path.split(".")
            target = data
            for k in keys[:-1]:
                target = target.setdefault(k, {})
            target[keys[-1]] = value
            data["_meta"]["last_updated"] = datetime.now().isoformat()
            self._write_json(path, data)

    def read_gene_map(self) -> dict:
        """读取完整基因图谱"""
        return self._read_json(self.base_dir / "gene_map.json")

    # ============================================================
    # 2. 知识图谱追踪 (Knowledge Graph)
    # ============================================================

    def _init_knowledge_graph(self):
        """初始化知识图谱，为所有知识点设置初始掌握度"""
        path = self.base_dir / "knowledge_graph.json"
        if not path.exists():
            graph = {"_meta": {"version": "3.0", "created_at": datetime.now().isoformat()}}
            for subject, nodes in self.KNOWLEDGE_GRAPH_SCHEMA.items():
                graph[subject] = {}
                for node_id, node_info in nodes.items():
                    graph[subject][node_id] = {
                        **node_info,
                        "mastery": 0.5,            # 初始掌握度 0-1
                        "confidence": 0.5,          # 自信心 0-1
                        "last_tested": None,
                        "test_count": 0,
                        "error_count": 0,
                    }
            self._write_json(path, graph)

    def update_mastery(self, subject: str, node_id: str, new_score: float,
                       is_error: bool = False):
        """
        更新某个知识点的掌握度（使用指数移动平均，避免单次波动过大）
        alpha=0.3 意味着新数据占30%权重，历史数据占70%
        """
        with self._lock:
            path = self.base_dir / "knowledge_graph.json"
            data = self._read_json(path)

            if subject not in data or node_id not in data[subject]:
                return

            node = data[subject][node_id]
            alpha = 0.3
            old_mastery = node["mastery"]
            node["mastery"] = round(alpha * new_score + (1 - alpha) * old_mastery, 3)
            node["last_tested"] = datetime.now().isoformat()
            node["test_count"] += 1
            if is_error:
                node["error_count"] += 1

            self._write_json(path, data)

    def get_weak_nodes(self, subject: Optional[str] = None, threshold: float = 0.6) -> list[dict]:
        """获取掌握度低于阈值的薄弱知识点"""
        data = self._read_json(self.base_dir / "knowledge_graph.json")
        weak = []
        subjects = [subject] if subject else [k for k in data if not k.startswith("_")]
        for subj in subjects:
            for node_id, node in data.get(subj, {}).items():
                if node.get("mastery", 1.0) < threshold:
                    weak.append({"subject": subj, "node_id": node_id, **node})
        return sorted(weak, key=lambda x: x["mastery"])

    def get_knowledge_summary(self) -> dict:
        """生成知识图谱摘要（用于家长报告）"""
        data = self._read_json(self.base_dir / "knowledge_graph.json")
        summary = {}
        for subject in [k for k in data if not k.startswith("_")]:
            nodes = data[subject]
            masteries = [n["mastery"] for n in nodes.values()]
            summary[subject] = {
                "average_mastery": round(sum(masteries) / len(masteries), 3) if masteries else 0,
                "total_nodes": len(nodes),
                "mastered_nodes": sum(1 for m in masteries if m >= 0.8),
                "weak_nodes": sum(1 for m in masteries if m < 0.6),
            }
        return summary

    # ============================================================
    # 3. 情绪时间线 (Emotion Timeline)
    # ============================================================

    def _init_emotion_timeline(self):
        path = self.base_dir / "emotion_timeline.json"
        if not path.exists():
            self._write_json(path, {"entries": [], "_meta": {"version": "3.0"}})

    def log_emotion(self, emotion: str, intensity: float, trigger: str = "", grade: int = 6):
        """
        记录一次情绪状态
        emotion: happy / anxious / frustrated / confident / tired / excited
        intensity: 0-1
        """
        with self._lock:
            path = self.base_dir / "emotion_timeline.json"
            data = self._read_json(path)
            data["entries"].append({
                "timestamp": datetime.now().isoformat(),
                "grade": grade,
                "emotion": emotion,
                "intensity": intensity,
                "trigger": trigger,
            })
            # 只保留最近500条记录
            if len(data["entries"]) > 500:
                data["entries"] = data["entries"][-500:]
            self._write_json(path, data)

    # ============================================================
    # 4. 年度快照 (Annual Snapshots)
    # ============================================================

    def create_annual_snapshot(self, grade: int, year: int, notes: str = ""):
        """创建年度规划快照，永久归档当年的决策与状态"""
        snapshot = {
            "year": year,
            "grade": grade,
            "created_at": datetime.now().isoformat(),
            "notes": notes,
            "gene_map_snapshot": self.read_gene_map(),
            "knowledge_summary": self.get_knowledge_summary(),
            "weak_nodes": self.get_weak_nodes(),
        }
        filename = f"{year}_grade{grade}.json"
        path = self.base_dir / "annual_snapshots" / filename
        self._write_json(path, snapshot)
        return snapshot

    # ============================================================
    # 5. 自演化日志 (Evolution Log)
    # ============================================================

    def _init_evolution_log(self):
        path = self.base_dir / "evolution_log.json"
        if not path.exists():
            self._write_json(path, {"entries": [], "_meta": {"version": "3.0"}})

    def log_evolution(self, event_type: str, description: str, data: dict = None):
        """记录一次自演化事件（如：发现新的学习偏好、检测到阶段跃迁等）"""
        with self._lock:
            path = self.base_dir / "evolution_log.json"
            log = self._read_json(path)
            log["entries"].append({
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "description": description,
                "data": data or {},
            })
            self._write_json(path, log)

    # ============================================================
    # 工具方法
    # ============================================================

    def _read_json(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: dict):
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)


# ============================================================
# 快速测试
# ============================================================
if __name__ == "__main__":
    brain = GBrain("/tmp/xiaoban_gbrain_test")

    # 测试基因图谱
    brain.update_gene("learning_dna.learning_style", "visual")
    brain.update_gene("interest_map.stem", 0.8)
    brain.update_gene("personality_traits.curiosity_level", 0.9)
    print("✅ 基因图谱更新成功")

    # 测试知识图谱
    brain.update_mastery("math", "primary_fractions", 0.3, is_error=True)
    brain.update_mastery("math", "primary_arithmetic", 0.95)
    weak = brain.get_weak_nodes(threshold=0.6)
    print(f"✅ 薄弱知识点数量：{len(weak)}")
    for w in weak[:3]:
        print(f"   [{w['subject']}] {w['name']} — 掌握度：{w['mastery']}")

    # 测试知识摘要
    summary = brain.get_knowledge_summary()
    print("\n✅ 知识图谱摘要：")
    for subj, s in summary.items():
        print(f"   {subj}: 平均掌握度={s['average_mastery']}, 已掌握={s['mastered_nodes']}/{s['total_nodes']}")

    # 测试情绪记录
    brain.log_emotion("anxious", 0.7, "小升初志愿填报压力", grade=6)
    print("✅ 情绪记录成功")

    # 测试年度快照
    brain.create_annual_snapshot(grade=6, year=2026, notes="小升初关键年，派位池分析完成")
    print("✅ 年度快照创建成功")

    print("\n🎉 GBrain 所有测试通过")
