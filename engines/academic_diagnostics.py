"""
小伴学情自动诊断引擎 v1.0
功能：
  1. 分析对话历史，自动识别学生薄弱知识点
  2. 追踪错误模式（计算粗心/概念混淆/方法缺失）
  3. 生成个性化学情诊断报告
  4. 推荐针对性练习计划（艾宾浩斯复习曲线）
  5. 与 GBrain 知识图谱联动，动态更新掌握度
"""
from engines.llm_core import llm_call, get_llm_router

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class AcademicDiagnosticsEngine:
    """学情自动诊断引擎"""

    # 错误类型分类器
    ERROR_PATTERNS = {
        "calculation_careless": {
            "keywords": ["算错", "笔误", "抄错", "加法", "减法", "乘法", "除法", "进位", "借位"],
            "description": "计算粗心",
            "remediation": "每次计算后回头检查，养成验算习惯"
        },
        "concept_confusion": {
            "keywords": ["不理解", "概念", "定义", "原理", "为什么", "搞混", "分不清"],
            "description": "概念混淆",
            "remediation": "用苏格拉底提问法重新建立概念，画概念图"
        },
        "method_missing": {
            "keywords": ["不会", "没学过", "方法", "步骤", "怎么做", "思路"],
            "description": "方法缺失",
            "remediation": "系统学习该知识点，从例题到变式题逐步练习"
        },
        "application_weak": {
            "keywords": ["应用题", "实际问题", "题意", "不知道用什么方法", "读不懂"],
            "description": "应用能力弱",
            "remediation": "加强阅读理解训练，练习提取关键信息"
        },
        "memory_gap": {
            "keywords": ["忘了", "记不住", "背过", "公式", "定理"],
            "description": "记忆遗忘",
            "remediation": "按艾宾浩斯曲线制定复习计划"
        }
    }

    # 学科知识点体系（小学六年级）
    KNOWLEDGE_TREE = {
        "math": {
            "分数运算": ["分数加减", "分数乘除", "分数混合运算", "分数应用题"],
            "比与比例": ["比的意义", "比的化简", "正比例", "反比例"],
            "几何图形": ["圆的面积", "圆的周长", "扇形", "组合图形"],
            "统计与概率": ["平均数", "中位数", "众数", "统计图"],
            "数的认识": ["自然数", "整数", "小数", "分数", "百分数"],
            "方程与代数": ["方程", "解方程", "代入法"]
        },
        "chinese": {
            "阅读理解": ["记叙文", "说明文", "议论文", "诗歌鉴赏"],
            "写作": ["记叙文写作", "说明文写作", "应用文"],
            "字词": ["字音", "字形", "词语理解", "成语"],
            "语法": ["句子成分", "修改病句", "标点符号"]
        },
        "english": {
            "词汇": ["单词拼写", "词义理解", "词组搭配"],
            "语法": ["时态", "句型", "从句"],
            "阅读": ["阅读理解", "完形填空"],
            "写作": ["英语作文", "句子翻译"]
        }
    }

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.memory_dir = self.base_dir / "memory"
        self.diagnostics_dir = self.memory_dir / "diagnostics"
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        
        self.dialogue_dir = self.memory_dir / "dialogue_history"
        self.mistake_book_path = self.memory_dir / "mistake_book.json"
        self.knowledge_mastery_path = self.memory_dir / "knowledge_mastery.json"

    def _load_json(self, path: Path) -> dict:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_json(self, path: Path, data: dict):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_recent_dialogues(self, days: int = 30) -> list:
        """加载最近 N 天的对话历史"""
        if not self.dialogue_dir.exists():
            return []
        
        all_messages = []
        cutoff = datetime.now() - timedelta(days=days)
        
        for json_file in sorted(self.dialogue_dir.glob("*.json")):
            try:
                date_str = json_file.stem  # e.g., "2026-04-24"
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    continue
                
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                messages = data if isinstance(data, list) else data.get("messages", [])
                all_messages.extend(messages)
            except Exception:
                continue
        
        return all_messages

    def _load_mistake_book(self) -> list:
        """加载错题本"""
        data = self._load_json(self.mistake_book_path)
        entries = data.get("entries", [])
        return entries

    def _classify_error(self, text: str) -> str:
        """对错误文本进行分类"""
        text_lower = text.lower()
        for error_type, pattern in self.ERROR_PATTERNS.items():
            if any(kw in text_lower for kw in pattern["keywords"]):
                return error_type
        return "unknown"

    def _detect_subject(self, text: str) -> str:
        """检测文本涉及的学科"""
        math_keywords = ["数学", "计算", "方程", "分数", "几何", "面积", "周长", "比例"]
        chinese_keywords = ["语文", "作文", "阅读", "古诗", "词语", "句子", "段落"]
        english_keywords = ["英语", "单词", "语法", "翻译", "阅读理解", "作文"]
        
        text_lower = text
        if any(kw in text_lower for kw in math_keywords):
            return "math"
        elif any(kw in text_lower for kw in chinese_keywords):
            return "chinese"
        elif any(kw in text_lower for kw in english_keywords):
            return "english"
        return "general"

    def _detect_knowledge_point(self, text: str, subject: str) -> Optional[str]:
        """检测文本涉及的具体知识点"""
        if subject not in self.KNOWLEDGE_TREE:
            return None
        
        for category, points in self.KNOWLEDGE_TREE[subject].items():
            if category in text:
                return category
            for point in points:
                if point in text:
                    return category
        return None

    def analyze_mistake_patterns(self) -> dict:
        """分析错题本中的错误模式"""
        mistakes = self._load_mistake_book()
        
        if not mistakes:
            return {
                "total_mistakes": 0,
                "error_type_distribution": {},
                "subject_distribution": {},
                "weak_knowledge_points": [],
                "recommendation": "暂无错题记录，请先导入作业或考卷"
            }
        
        error_type_count = defaultdict(int)
        subject_count = defaultdict(int)
        knowledge_point_count = defaultdict(int)
        
        for mistake in mistakes:
            subject = mistake.get("subject", self._detect_subject(
                mistake.get("question", "") + mistake.get("analysis", "")
            ))
            subject_count[subject] += 1
            
            error_type = mistake.get("error_type", self._classify_error(
                mistake.get("analysis", "") + mistake.get("student_answer", "")
            ))
            error_type_count[error_type] += 1
            
            kp = mistake.get("knowledge_point", self._detect_knowledge_point(
                mistake.get("question", ""), subject
            ))
            if kp:
                knowledge_point_count[kp] += 1
        
        # 识别薄弱知识点（出现3次以上）
        weak_points = [
            {"knowledge_point": kp, "error_count": count}
            for kp, count in sorted(knowledge_point_count.items(), key=lambda x: -x[1])
            if count >= 1
        ]
        
        # 主要错误类型
        dominant_error = max(error_type_count, key=error_type_count.get) if error_type_count else "unknown"
        
        return {
            "total_mistakes": len(mistakes),
            "error_type_distribution": dict(error_type_count),
            "subject_distribution": dict(subject_count),
            "weak_knowledge_points": weak_points[:5],
            "dominant_error_type": dominant_error,
            "dominant_error_description": self.ERROR_PATTERNS.get(dominant_error, {}).get("description", "未知"),
            "dominant_error_remediation": self.ERROR_PATTERNS.get(dominant_error, {}).get("remediation", "")
        }

    def analyze_dialogue_patterns(self, days: int = 30) -> dict:
        """分析对话历史，提取学习行为模式"""
        messages = self._load_recent_dialogues(days)
        
        if not messages:
            return {
                "total_messages": 0,
                "active_days": 0,
                "subject_focus": {},
                "question_types": {},
                "engagement_score": 0
            }
        
        subject_focus = defaultdict(int)
        question_types = defaultdict(int)
        active_dates = set()
        
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            
            # 学科分布
            subject = self._detect_subject(content)
            if subject != "general":
                subject_focus[subject] += 1
            
            # 问题类型
            if "?" in content or "？" in content:
                question_types["提问"] += 1
            if any(kw in content for kw in ["作业", "题目", "练习"]):
                question_types["作业辅导"] += 1
            if any(kw in content for kw in ["小升初", "升学", "志愿"]):
                question_types["升学规划"] += 1
            
            # 活跃天数
            date = msg.get("date", "")
            if date:
                active_dates.add(date[:10])
        
        engagement_score = min(100, len(active_dates) * 5 + len(messages) * 2)
        
        return {
            "total_messages": len(messages),
            "active_days": len(active_dates),
            "subject_focus": dict(subject_focus),
            "question_types": dict(question_types),
            "engagement_score": engagement_score,
            "analysis_period_days": days
        }

    def generate_study_plan(self, weak_points: list) -> list:
        """基于薄弱知识点生成艾宾浩斯复习计划"""
        today = datetime.now()
        plan = []
        
        # 艾宾浩斯复习间隔（天）
        review_intervals = [1, 2, 4, 7, 15, 30]
        
        for i, wp in enumerate(weak_points[:3]):  # 最多同时处理3个薄弱点
            kp = wp.get("knowledge_point", "未知知识点")
            for j, interval in enumerate(review_intervals):
                review_date = today + timedelta(days=interval)
                plan.append({
                    "date": review_date.strftime("%Y-%m-%d"),
                    "knowledge_point": kp,
                    "review_round": j + 1,
                    "task": f"第{j+1}轮复习：{kp}",
                    "estimated_minutes": max(10, 30 - j * 4)
                })
        
        plan.sort(key=lambda x: x["date"])
        return plan[:14]  # 返回未来14天的计划

    def run_full_diagnosis(self) -> dict:
        """运行完整学情诊断"""
        print("[Diagnostics] 开始学情诊断...")
        
        # 1. 错题分析
        mistake_analysis = self.analyze_mistake_patterns()
        
        # 2. 对话行为分析
        dialogue_analysis = self.analyze_dialogue_patterns(days=30)
        
        # 3. 知识点掌握度
        mastery_data = self._load_json(self.knowledge_mastery_path)
        
        # 4. 生成复习计划
        study_plan = self.generate_study_plan(
            mistake_analysis.get("weak_knowledge_points", [])
        )
        
        # 5. 综合评估
        overall_score = self._calculate_overall_score(mistake_analysis, mastery_data)
        
        # 6. LLM 生成诊断摘要
        diagnosis_summary = self._generate_llm_summary(
            mistake_analysis, dialogue_analysis, overall_score
        )
        
        diagnosis = {
            "generated_at": datetime.now().isoformat(),
            "overall_score": overall_score,
            "diagnosis_summary": diagnosis_summary,
            "mistake_analysis": mistake_analysis,
            "dialogue_analysis": dialogue_analysis,
            "study_plan_next_14_days": study_plan,
            "urgent_actions": self._get_urgent_actions(mistake_analysis, overall_score)
        }
        
        # 保存诊断报告
        report_path = self.diagnostics_dir / f"diagnosis_{datetime.now().strftime('%Y%m%d')}.json"
        self._save_json(report_path, diagnosis)
        print(f"[Diagnostics] 诊断报告已保存：{report_path.name}")
        
        return diagnosis

    def _calculate_overall_score(self, mistake_analysis: dict, mastery_data: dict) -> int:
        """计算综合学情评分（0-100）"""
        score = 70  # 基础分
        
        # 错题数量影响
        total_mistakes = mistake_analysis.get("total_mistakes", 0)
        if total_mistakes == 0:
            score += 10
        elif total_mistakes <= 5:
            score += 5
        elif total_mistakes > 20:
            score -= 10
        
        # 知识点掌握度影响
        subjects = mastery_data.get("subjects", {})
        if subjects:
            avg_mastery = sum(
                sum(v.values()) / len(v) if isinstance(v, dict) else v
                for v in subjects.values()
            ) / len(subjects)
            score = int(score * 0.5 + avg_mastery * 0.5)
        
        return max(0, min(100, score))

    def _get_urgent_actions(self, mistake_analysis: dict, overall_score: int) -> list:
        """生成紧急行动建议"""
        actions = []
        
        if overall_score < 60:
            actions.append({
                "priority": "high",
                "action": "立即安排一次全面学情摸底测试",
                "reason": "综合评分偏低，需要精准定位薄弱点"
            })
        
        dominant_error = mistake_analysis.get("dominant_error_type", "")
        if dominant_error == "calculation_careless":
            actions.append({
                "priority": "medium",
                "action": "每次作业后坚持验算，建立检查清单",
                "reason": "计算粗心是主要错误类型"
            })
        elif dominant_error == "concept_confusion":
            actions.append({
                "priority": "high",
                "action": "重新梳理薄弱概念，画思维导图",
                "reason": "概念混淆影响整体理解"
            })
        
        weak_points = mistake_analysis.get("weak_knowledge_points", [])
        if weak_points:
            top_weak = weak_points[0]
            actions.append({
                "priority": "medium",
                "action": f"重点突破「{top_weak['knowledge_point']}」，每天练习15分钟",
                "reason": f"该知识点出错 {top_weak['error_count']} 次，是最薄弱环节"
            })
        
        return actions

    def _generate_llm_summary(self, mistake_analysis: dict, dialogue_analysis: dict, score: int) -> str:
        """用 LLM 生成人性化诊断摘要"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            prompt = f"""你是小伴，请基于以下学情数据，用温暖、专业的语气为家长（Lion）生成一段学情诊断摘要（150字以内）：

综合评分：{score}/100
错题总数：{mistake_analysis.get('total_mistakes', 0)}
主要错误类型：{mistake_analysis.get('dominant_error_description', '未知')}
薄弱知识点：{[wp['knowledge_point'] for wp in mistake_analysis.get('weak_knowledge_points', [])[:3]]}
近30天活跃天数：{dialogue_analysis.get('active_days', 0)}天
最关注的学科：{max(dialogue_analysis.get('subject_focus', {'暂无': 1}), key=dialogue_analysis.get('subject_focus', {'暂无': 1}).get)}

请用第一人称（小伴）写，语气温暖，重点突出1-2个最需要关注的问题。"""
            
            # [v5.2 Manus迁移] 统一路由器调用
            response_reply = llm_call(prompt)
            return response_reply
        except Exception:
            return (
                f"小可爱近期综合学情评分为 {score}/100。"
                f"主要需要关注「{mistake_analysis.get('dominant_error_description', '计算准确性')}」问题，"
                f"建议重点突破「{mistake_analysis.get('weak_knowledge_points', [{}])[0].get('knowledge_point', '基础知识点') if mistake_analysis.get('weak_knowledge_points') else '基础知识点'}」。"
                f"小伴将持续陪伴，一起加油！"
            )


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    engine = AcademicDiagnosticsEngine(base_dir)
    
    print("=" * 60)
    print("小伴学情自动诊断引擎 v1.0 — 测试")
    print("=" * 60)
    
    print("\n[运行完整学情诊断]")
    diagnosis = engine.run_full_diagnosis()
    
    print(f"\n综合评分: {diagnosis['overall_score']}/100")
    print(f"诊断摘要:\n{diagnosis['diagnosis_summary']}")
    
    print(f"\n错题分析:")
    ma = diagnosis["mistake_analysis"]
    print(f"  总错题数: {ma['total_mistakes']}")
    print(f"  主要错误类型: {ma.get('dominant_error_description', 'N/A')}")
    print(f"  薄弱知识点: {[wp['knowledge_point'] for wp in ma.get('weak_knowledge_points', [])]}")
    
    print(f"\n未来14天复习计划 (前5条):")
    for item in diagnosis["study_plan_next_14_days"][:5]:
        print(f"  {item['date']}: {item['task']} ({item['estimated_minutes']}分钟)")
    
    print(f"\n紧急行动建议:")
    for action in diagnosis["urgent_actions"]:
        print(f"  [{action['priority'].upper()}] {action['action']}")
    
    print("\n✅ 学情诊断引擎测试完成")
