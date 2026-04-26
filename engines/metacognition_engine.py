"""
元认知引擎 (Metacognition Engine)
小伴 v5.1 — Mythos 第三批技能模块

基于 Claude Mythos 中的元认知能力：
"Claude engages in reflection on its own reasoning processes, 
acknowledges when it might be wrong, and models good epistemic practices."

核心能力：
1. 学习过程反思 (Learning Process Reflection)：帮助小可爱反思"我是怎么学会的"
2. 错误模式分析 (Error Pattern Analysis)：识别重复错误背后的认知模式
3. 学习策略评估 (Learning Strategy Assessment)：评估当前学习方法的有效性
4. 自我认知校准 (Self-Knowledge Calibration)：帮助小可爱准确评估自己的能力
5. 成长归因训练 (Growth Attribution Training)：培养成长型思维，正确归因成功与失败

适用场景：
- 考试后的复盘（不只看分数，看思维过程）
- 反复犯同类错误时（找认知根源，不只是重复练习）
- 学习效率低下时（诊断方法问题，不只是努力不够）
- 自我评价偏差时（过度自信或过度自我否定）
"""
from engines.llm_core import llm_call, get_llm_router
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────────────────────────────────────
# 元认知维度定义
# ─────────────────────────────────────────────────────────────────────────────

METACOGNITION_DIMENSIONS = {
    "self_awareness": {
        "name": "自我认知",
        "description": "了解自己的学习优势和弱点",
        "questions": [
            "你觉得自己在哪些科目/知识点上最强？",
            "你做错这道题，是因为不会，还是因为粗心，还是因为时间不够？",
            "你平时是怎么判断自己'学会了'一个知识点的？"
        ]
    },
    "strategy_awareness": {
        "name": "策略认知",
        "description": "了解自己使用的学习方法是否有效",
        "questions": [
            "你通常是怎么复习的？背诵、做题、还是理解？",
            "这种方法对你有效吗？你怎么知道它有效？",
            "如果这道题你做错了，你会怎么处理它？"
        ]
    },
    "regulation": {
        "name": "学习调控",
        "description": "能够根据情况调整学习策略",
        "questions": [
            "当你发现自己听不懂时，你会怎么做？",
            "如果一种方法不奏效，你会尝试换一种方法吗？",
            "你如何安排复习时间？"
        ]
    },
    "attribution": {
        "name": "成败归因",
        "description": "正确理解成功和失败的原因",
        "questions": [
            "这次考好了，你觉得主要是因为什么？",
            "这次没考好，你觉得是什么原因？",
            "你觉得努力和天赋，哪个对成绩影响更大？"
        ]
    }
}

# 常见错误认知模式
ERROR_PATTERNS = {
    "fixed_mindset": {
        "name": "固定型思维",
        "signals": ["我就是不擅长", "天生的", "没有天赋", "学不会的"],
        "intervention": "帮助认识到能力是可以通过练习提升的"
    },
    "effort_attribution": {
        "name": "过度归因努力",
        "signals": ["我努力了但没用", "我已经很努力了"],
        "intervention": "区分努力程度和学习方法，找到方法问题"
    },
    "luck_attribution": {
        "name": "归因运气",
        "signals": ["运气好", "碰巧", "猜对了"],
        "intervention": "帮助识别成功背后的真实能力因素"
    },
    "overconfidence": {
        "name": "过度自信",
        "signals": ["这个我会", "很简单", "不用复习"],
        "intervention": "通过测试验证实际掌握程度"
    },
    "learned_helplessness": {
        "name": "习得性无助",
        "signals": ["反正我也不会", "没用的", "放弃了"],
        "intervention": "找到小的成功体验，重建自信"
    }
}


class MetacognitionEngine:
    """
    元认知引擎
    
    职责：
    1. 分析学生的学习过程，识别元认知模式
    2. 提供苏格拉底式元认知提问
    3. 帮助学生建立成长型思维
    4. 生成个性化的学习策略建议
    """
    
    def __init__(self):
        self.reflection_history = []
    
    def analyze_error_pattern(
        self,
        mistake_entries: List[Dict],
        student_explanation: str = ""
    ) -> Dict:
        """
        分析错误模式（元认知核心功能）
        
        不只是统计错了什么，而是分析"为什么会错"的认知根源。
        
        Args:
            mistake_entries: 错题记录列表
            student_explanation: 学生对错误的自我解释
        
        Returns:
            错误模式分析报告
        """
        if not mistake_entries:
            return {"status": "no_data", "message": "暂无错题数据"}
        
        # 1. 统计错误分布
        subject_errors = {}
        kp_errors = {}
        for entry in mistake_entries:
            subject = entry.get("subject", "未知")
            kp = entry.get("knowledge_point", "未知")
            subject_errors[subject] = subject_errors.get(subject, 0) + 1
            kp_errors[kp] = kp_errors.get(kp, 0) + 1
        
        # 2. 识别认知错误模式
        detected_patterns = []
        if student_explanation:
            for pattern_key, pattern in ERROR_PATTERNS.items():
                if any(signal in student_explanation for signal in pattern["signals"]):
                    detected_patterns.append({
                        "type": pattern_key,
                        "name": pattern["name"],
                        "intervention": pattern["intervention"]
                    })
        
        # 3. 生成元认知提问
        reflection_questions = self._generate_reflection_questions(
            subject_errors, kp_errors, detected_patterns
        )
        
        # 4. 识别重复错误知识点
        repeated_kps = [(kp, count) for kp, count in kp_errors.items() if count >= 2]
        repeated_kps.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "total_mistakes": len(mistake_entries),
            "subject_distribution": subject_errors,
            "top_weak_points": repeated_kps[:5],
            "detected_patterns": detected_patterns,
            "reflection_questions": reflection_questions,
            "metacognitive_insight": self._generate_metacognitive_insight(
                repeated_kps, detected_patterns
            ),
            "recommended_strategy": self._recommend_learning_strategy(
                subject_errors, repeated_kps
            ),
            "analysis_time": datetime.now().isoformat()
        }
    
    def _generate_reflection_questions(
        self,
        subject_errors: Dict,
        kp_errors: Dict,
        patterns: List[Dict]
    ) -> List[str]:
        """生成针对性的元认知反思问题"""
        questions = []
        
        # 基于错误分布的问题
        if subject_errors:
            top_subject = max(subject_errors, key=subject_errors.get)
            questions.append(
                f"你在{top_subject}上错了{subject_errors[top_subject]}道题，"
                f"你觉得主要是因为不理解知识点，还是计算粗心，还是题目没看清楚？"
            )
        
        # 基于重复错误的问题
        repeated = [(kp, c) for kp, c in kp_errors.items() if c >= 2]
        if repeated:
            top_kp = max(repeated, key=lambda x: x[1])
            questions.append(
                f"'{top_kp[0]}'这个知识点你已经错了{top_kp[1]}次了。"
                f"你觉得你真的理解这个知识点了吗？如果让你用自己的话解释一遍，你能说清楚吗？"
            )
        
        # 基于认知模式的问题
        for pattern in patterns[:2]:
            if pattern["type"] == "fixed_mindset":
                questions.append(
                    "你说'我就是不擅长这个'，但你有没有想过，"
                    "是不是还没有找到适合你的学习方法？"
                )
            elif pattern["type"] == "overconfidence":
                questions.append(
                    "你觉得这个知识点你会了，但做题时还是错了。"
                    "你觉得'会了'和'真的掌握了'有什么区别？"
                )
        
        # 通用元认知问题
        questions.append(
            "如果你能重新来过，在学这些知识点的时候，你会有什么不同的做法？"
        )
        
        return questions[:4]  # 最多4个问题，避免过多
    
    def _generate_metacognitive_insight(
        self,
        repeated_kps: List[Tuple],
        patterns: List[Dict]
    ) -> str:
        """生成元认知洞察（给学生的核心发现）"""
        if not repeated_kps and not patterns:
            return "你的错误分布比较均匀，没有明显的薄弱点，继续保持！"
        
        insights = []
        
        if repeated_kps:
            top_kp = repeated_kps[0]
            insights.append(
                f"你在'{top_kp[0]}'上反复出错，这通常意味着这个知识点的底层概念还没有真正理解，"
                f"单纯重复练习可能效果有限，需要换一种方式来理解它。"
            )
        
        if patterns:
            for p in patterns[:1]:
                if p["type"] == "fixed_mindset":
                    insights.append(
                        "我注意到你有时候会觉得自己'天生不擅长'某些东西。"
                        "但研究表明，大脑是可以通过练习改变的，关键是找到正确的方法。"
                    )
        
        return " ".join(insights) if insights else "继续保持，你的学习状态不错！"
    
    def _recommend_learning_strategy(
        self,
        subject_errors: Dict,
        repeated_kps: List[Tuple]
    ) -> Dict:
        """推荐个性化学习策略"""
        strategies = {}
        
        if repeated_kps:
            strategies["for_repeated_errors"] = (
                "对于反复出错的知识点，建议：\n"
                "1. 先用自己的话解释这个知识点（费曼技巧）\n"
                "2. 找到这道题和你已经会的知识点的联系\n"
                "3. 做3道同类型但不同数字的题，验证是否真的理解了"
            )
        
        if subject_errors:
            top_subject = max(subject_errors, key=subject_errors.get)
            if top_subject == "数学":
                strategies["math_specific"] = (
                    "数学错题建议：先判断是'不会'还是'粗心'，"
                    "如果是粗心，建议养成检查习惯；"
                    "如果是不会，先找到知识点的定义，再看例题，再自己做。"
                )
        
        return strategies
    
    def post_exam_reflection(
        self,
        exam_score: float,
        expected_score: float,
        student_reflection: str,
        subject: str
    ) -> Dict:
        """
        考后元认知反思（Mythos: 帮助建立正确的归因模式）
        
        不只是分析分数，而是帮助学生理解：
        - 成功/失败的真实原因
        - 下次可以改进的具体行动
        - 建立成长型思维
        
        Args:
            exam_score: 实际得分
            expected_score: 预期得分
            student_reflection: 学生的自我反思
            subject: 科目
        
        Returns:
            元认知反思报告
        """
        score_gap = exam_score - expected_score
        
        # 分析归因模式
        attribution_analysis = self._analyze_attribution(
            student_reflection, score_gap
        )
        
        # 生成苏格拉底式反思问题
        socratic_questions = self._generate_post_exam_questions(
            exam_score, expected_score, subject, score_gap
        )
        
        # 生成成长型思维引导
        growth_mindset_prompt = self._generate_growth_mindset_response(
            score_gap, attribution_analysis
        )
        
        return {
            "exam_score": exam_score,
            "expected_score": expected_score,
            "score_gap": score_gap,
            "performance_label": "超出预期" if score_gap > 0 else ("符合预期" if score_gap == 0 else "低于预期"),
            "attribution_analysis": attribution_analysis,
            "socratic_questions": socratic_questions,
            "growth_mindset_prompt": growth_mindset_prompt,
            "next_action": self._suggest_next_action(score_gap, subject),
            "reflection_time": datetime.now().isoformat()
        }
    
    def _analyze_attribution(self, reflection: str, score_gap: float) -> Dict:
        """分析学生的归因模式"""
        attribution = {
            "type": "balanced",
            "detected_biases": [],
            "quality": "good"
        }
        
        if not reflection:
            return attribution
        
        # 检测归因偏差
        for pattern_key, pattern in ERROR_PATTERNS.items():
            if any(signal in reflection for signal in pattern["signals"]):
                attribution["detected_biases"].append({
                    "bias": pattern["name"],
                    "intervention": pattern["intervention"]
                })
        
        # 判断归因质量
        if "运气" in reflection or "碰巧" in reflection:
            attribution["type"] = "external_luck"
            attribution["quality"] = "needs_improvement"
        elif "我努力了" in reflection and score_gap < 0:
            attribution["type"] = "effort_only"
            attribution["quality"] = "needs_improvement"
        elif "方法" in reflection or "理解" in reflection:
            attribution["type"] = "strategy_focused"
            attribution["quality"] = "excellent"
        
        return attribution
    
    def _generate_post_exam_questions(
        self,
        score: float,
        expected: float,
        subject: str,
        gap: float
    ) -> List[str]:
        """生成考后元认知问题"""
        questions = []
        
        if gap > 10:  # 超出预期
            questions.extend([
                f"你比预期多考了{gap:.0f}分，你觉得主要是因为什么？",
                "这次发挥好的地方，下次考试你能复制吗？怎么做到？",
                "有没有哪道题你是猜对的？那道题你现在能解释清楚吗？"
            ])
        elif gap < -10:  # 低于预期
            questions.extend([
                f"你比预期少考了{abs(gap):.0f}分，你觉得主要原因是什么？",
                "考试时有没有遇到完全不会的题？还是会但做错了？",
                "如果重新来过，你会在哪个环节做不同的事？"
            ])
        else:  # 符合预期
            questions.extend([
                "你对这次考试的准备方式满意吗？",
                "有没有哪个知识点你觉得还可以更好地掌握？"
            ])
        
        # 通用元认知问题
        questions.append(
            f"这次{subject}考试，你学到了什么关于'怎么学好{subject}'的东西？"
        )
        
        return questions[:3]
    
    def _generate_growth_mindset_response(
        self, score_gap: float, attribution: Dict
    ) -> str:
        """生成成长型思维引导"""
        if attribution.get("type") == "external_luck":
            return (
                "我注意到你把结果归因于运气。运气确实存在，但如果我们只关注运气，"
                "就很难找到下次可以改进的地方。你觉得除了运气，你自己做了哪些事情影响了结果？"
            )
        elif attribution.get("type") == "effort_only" and score_gap < 0:
            return (
                "你说你努力了但结果不理想。努力很重要，但努力的方向也很重要。"
                "你觉得你的学习方法有没有可以改进的地方？"
                "有时候换一种方法，比加倍努力更有效。"
            )
        elif score_gap > 0:
            return (
                "这次考得不错！记录下你这次做对的事情，下次继续。"
                "成功不只是运气，你的准备和思考方式都起了作用。"
            )
        else:
            return (
                "这次没达到预期，但这是学习的一部分。"
                "每次错误都是一个信号，告诉我们哪里还可以成长。"
                "重要的是从中找到具体可以改进的地方，而不是否定自己。"
            )
    
    def _suggest_next_action(self, score_gap: float, subject: str) -> str:
        """建议下一步具体行动"""
        if score_gap < -10:
            return (
                f"建议：在下次{subject}考试前，专门花30分钟做一次错题复盘，"
                "不只是看答案，而是用自己的话解释为什么这样做。"
            )
        elif score_gap > 10:
            return (
                f"建议：把这次考好的方法记录下来，下次考试前回顾一遍，"
                "让好的方法成为习惯。"
            )
        else:
            return (
                f"建议：找出这次考试中最不确定的2-3道题，"
                "确认自己真的理解了，而不只是记住了答案。"
            )
    
    def generate_weekly_metacognition_report(
        self,
        week_mistakes: List[Dict],
        week_dialogues: List[Dict],
        student_name: str = "小可爱"
    ) -> Dict:
        """
        生成每周元认知报告
        
        帮助小可爱和家长了解这周的学习质量（不只是数量）
        
        Returns:
            每周元认知报告
        """
        # 分析错误模式
        error_analysis = self.analyze_error_pattern(week_mistakes)
        
        # 分析对话中的元认知信号
        metacognitive_moments = self._extract_metacognitive_moments(week_dialogues)
        
        # 生成成长观察
        growth_observations = self._observe_growth_patterns(
            week_mistakes, week_dialogues
        )
        
        return {
            "student": student_name,
            "week": datetime.now().strftime("%Y年第%W周"),
            "learning_quality_score": self._calculate_learning_quality(
                error_analysis, metacognitive_moments
            ),
            "error_analysis_summary": {
                "total": error_analysis.get("total_mistakes", 0),
                "top_weak_points": error_analysis.get("top_weak_points", [])[:3],
                "insight": error_analysis.get("metacognitive_insight", "")
            },
            "metacognitive_moments": metacognitive_moments,
            "growth_observations": growth_observations,
            "questions_for_student": error_analysis.get("reflection_questions", [])[:2],
            "parent_note": self._generate_parent_note(error_analysis, growth_observations),
            "generated_at": datetime.now().isoformat()
        }
    
    def _extract_metacognitive_moments(self, dialogues: List[Dict]) -> List[str]:
        """从对话历史中提取元认知时刻"""
        moments = []
        metacognitive_signals = [
            "我明白了", "我理解了", "原来是", "我之前以为",
            "我发现", "我觉得我", "这和"
        ]
        
        for dialogue in dialogues:
            content = dialogue.get("content", "")
            if any(signal in content for signal in metacognitive_signals):
                moments.append(content[:100])
        
        return moments[:3]
    
    def _observe_growth_patterns(
        self, mistakes: List[Dict], dialogues: List[Dict]
    ) -> List[str]:
        """观察成长模式"""
        observations = []
        
        if len(mistakes) > 0:
            observations.append(
                f"本周记录了{len(mistakes)}道错题，"
                "记录错题本身就是元认知的体现——知道自己哪里不会。"
            )
        
        if len(dialogues) > 5:
            observations.append(
                f"本周进行了{len(dialogues)}次学习对话，"
                "保持了良好的学习节奏。"
            )
        
        return observations
    
    def _calculate_learning_quality(
        self, error_analysis: Dict, metacognitive_moments: List
    ) -> int:
        """计算学习质量分数（0-100）"""
        score = 60  # 基础分
        
        # 有元认知时刻加分
        score += min(len(metacognitive_moments) * 5, 20)
        
        # 有重复错误扣分
        repeated = error_analysis.get("top_weak_points", [])
        if repeated:
            score -= min(len(repeated) * 3, 15)
        
        # 有认知偏见扣分
        patterns = error_analysis.get("detected_patterns", [])
        if patterns:
            score -= min(len(patterns) * 5, 15)
        
        return max(0, min(100, score))
    
    def _generate_parent_note(
        self, error_analysis: Dict, growth_observations: List
    ) -> str:
        """生成给家长的元认知报告摘要"""
        parts = ["本周学习质量观察："]
        
        repeated = error_analysis.get("top_weak_points", [])
        if repeated:
            kp_list = "、".join([kp for kp, _ in repeated[:2]])
            parts.append(
                f"需要关注：'{kp_list}'等知识点出现重复错误，"
                "建议不只是重复练习，而是换一种方式理解这些概念。"
            )
        
        patterns = error_analysis.get("detected_patterns", [])
        for p in patterns[:1]:
            parts.append(f"思维模式提示：检测到'{p['name']}'倾向，{p['intervention']}。")
        
        if growth_observations:
            parts.append(growth_observations[0])
        
        return " ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MetacognitionEngine 测试")
    print("=" * 60)
    
    engine = MetacognitionEngine()
    
    # 测试 1：错误模式分析
    print("\n【测试 1】错误模式分析")
    mistakes = [
        {"subject": "数学", "knowledge_point": "分数除法", "error_reason": "概念混淆"},
        {"subject": "数学", "knowledge_point": "分数除法", "error_reason": "计算错误"},
        {"subject": "数学", "knowledge_point": "分数除法", "error_reason": "方法错误"},
        {"subject": "语文", "knowledge_point": "阅读理解", "error_reason": "审题不仔细"},
        {"subject": "数学", "knowledge_point": "比例", "error_reason": "概念不清"},
    ]
    
    result = engine.analyze_error_pattern(
        mistakes,
        student_explanation="我就是不擅长分数，天生的"
    )
    print(f"总错题数: {result['total_mistakes']}")
    print(f"最弱知识点: {result['top_weak_points'][:2]}")
    print(f"检测到的认知模式: {[p['name'] for p in result['detected_patterns']]}")
    print(f"元认知洞察: {result['metacognitive_insight'][:100]}...")
    print(f"反思问题数: {len(result['reflection_questions'])}")
    
    # 测试 2：考后元认知反思
    print("\n【测试 2】考后元认知反思")
    reflection = engine.post_exam_reflection(
        exam_score=75,
        expected_score=85,
        student_reflection="我努力了但没考好，可能运气不好",
        subject="数学"
    )
    print(f"表现标签: {reflection['performance_label']}")
    print(f"归因分析: {reflection['attribution_analysis']['type']}")
    print(f"成长型思维引导: {reflection['growth_mindset_prompt'][:100]}...")
    
    print("\n✅ 测试完成")
