"""
直接表达引擎 (Direct Expression Engine)
小伴 v5.1 — Mythos 第三批技能模块

基于 Claude Mythos 中的直接表达原则：
"Claude is direct rather than mealy-mouthed. If someone asks for a recommendation, 
suggestions, or preference, Claude gives them a concrete recommendation, suggestion, 
or preference where possible."

"Claude is confident and assertive, and believes in direct communication."

核心能力：
1. 具体建议生成 (Concrete Recommendation)：不说"可以考虑"，直接说"我建议你选A"
2. 张雪峰式直率 (Zhang Xuefeng Directness)：敢说不合适的就是不合适
3. 不确定性诚实表达 (Honest Uncertainty)：不知道就说不知道，不含糊其辞
4. 立场清晰表达 (Clear Position)：有观点就说出来，不模棱两可
5. 建设性拒绝 (Constructive Refusal)：拒绝不合理请求时，给出替代方案

适用场景：
- 家长问"哪个学校更好"：直接给出推荐而非"各有优劣"
- 学生问"这道题怎么做"：给出清晰的解题思路而非绕圈子
- 家长问"这个规划合理吗"：直接说合理或不合理，并说明原因
- 面对不切实际的期望：温和但清晰地说出真相
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 直接表达模式定义
# ─────────────────────────────────────────────────────────────────────────────

# 需要避免的模糊表达 → 直接表达替换
VAGUE_TO_DIRECT = {
    "可以考虑": "我建议",
    "也许可以": "可以",
    "可能需要": "需要",
    "或许应该": "应该",
    "各有优劣": "综合来看，{recommendation}更适合你",
    "因人而异": "根据你的情况，",
    "不好说": "我的判断是",
    "可能是": "我认为是",
    "仅供参考": "这是我的建议",
}

# 张雪峰式直率场景
ZHANG_XUEFENG_SCENARIOS = {
    "unrealistic_school": {
        "trigger": ["清华", "北大", "人大附中实验班", "十一学校实验班"],
        "condition": "成绩一般或无竞赛背景",
        "direct_response": (
            "我需要直接告诉你：以目前的情况，这个目标的难度非常高。"
            "不是不可能，但需要在接下来的时间里有实质性的突破。"
            "我们来看看更现实的路径，同时保留这个目标作为努力方向。"
        )
    },
    "too_many_choices": {
        "trigger": ["不知道选哪个", "都挺好的", "帮我选"],
        "direct_response": (
            "好，我来直接给你推荐。根据你的情况，我选{top_choice}。"
            "原因是：{reason}。"
            "如果你有特别的考虑，告诉我，我们可以调整。"
        )
    },
    "denial_of_problem": {
        "trigger": ["没问题", "都会了", "不需要复习"],
        "direct_response": (
            "我理解你觉得没问题，但根据错题记录，{specific_issue}。"
            "我不是要否定你，而是希望你能真正掌握，而不是以为自己掌握了。"
        )
    }
}


class DirectExpressionEngine:
    """
    直接表达引擎
    
    职责：
    1. 检测小伴回复中的模糊表达，提供替换建议
    2. 在需要直接建议时，生成具体的推荐
    3. 实现张雪峰式的直率（不讨好，说真话）
    4. 确保拒绝时给出建设性替代方案
    """
    
    def __init__(self):
        self.directness_level = "balanced"  # "gentle", "balanced", "direct"
    
    def make_direct_recommendation(
        self,
        question: str,
        options: List[Dict],
        student_profile: Dict = None,
        context: str = ""
    ) -> Dict:
        """
        将模糊的"各有优劣"转化为具体的推荐
        
        这是直接表达引擎的核心功能。
        当家长问"A和B哪个更好"时，不说"各有优劣"，
        而是根据具体情况给出明确推荐。
        
        Args:
            question: 用户的问题
            options: 选项列表，每个选项包含 name, pros, cons
            student_profile: 学生档案
            context: 额外上下文
        
        Returns:
            直接推荐结果
        """
        if not options:
            return {
                "recommendation": "需要更多信息才能给出推荐",
                "confidence": "low",
                "reasoning": "选项为空"
            }
        
        # 评分每个选项
        scored_options = self._score_options(options, student_profile or {})
        
        # 选出最高分
        best_option = max(scored_options, key=lambda x: x["score"])
        
        # 生成直接推荐语
        recommendation_text = self._generate_recommendation_text(
            best_option, scored_options, student_profile or {}
        )
        
        return {
            "question": question,
            "top_recommendation": best_option["name"],
            "recommendation_text": recommendation_text,
            "confidence": self._assess_confidence(scored_options),
            "score_breakdown": scored_options,
            "caveat": self._generate_caveat(best_option, student_profile or {}),
            "generated_at": datetime.now().isoformat()
        }
    
    def _score_options(
        self, options: List[Dict], profile: Dict
    ) -> List[Dict]:
        """为每个选项评分"""
        scored = []
        
        for option in options:
            score = 50  # 基础分
            
            # 根据学生情况加减分
            pros = option.get("pros", [])
            cons = option.get("cons", [])
            
            # 与学生情况匹配的优点加分
            district = profile.get("district", "")
            if district and any(district in pro for pro in pros):
                score += 20
            
            # 有明显缺点减分
            if len(cons) > len(pros):
                score -= 10
            
            scored.append({
                "name": option.get("name", "未命名"),
                "score": score,
                "pros": pros,
                "cons": cons,
                "original": option
            })
        
        return sorted(scored, key=lambda x: x["score"], reverse=True)
    
    def _generate_recommendation_text(
        self,
        best: Dict,
        all_options: List[Dict],
        profile: Dict
    ) -> str:
        """生成直接推荐文本（张雪峰式）"""
        name = best["name"]
        pros = best.get("pros", [])
        
        text_parts = [f"我的建议是：**{name}**。"]
        
        if pros:
            text_parts.append(f"主要原因：{pros[0]}")
        
        # 如果有竞争选项，简要说明为什么没选它
        if len(all_options) > 1:
            second = all_options[1]
            score_diff = best["score"] - second["score"]
            if score_diff < 10:  # 差距不大时说明
                text_parts.append(
                    f"（{second['name']}也不错，但根据你的具体情况，{name}更合适。）"
                )
        
        return " ".join(text_parts)
    
    def _assess_confidence(self, scored_options: List[Dict]) -> str:
        """评估推荐的置信度"""
        if len(scored_options) < 2:
            return "high"
        
        score_diff = scored_options[0]["score"] - scored_options[1]["score"]
        
        if score_diff >= 20:
            return "high"
        elif score_diff >= 10:
            return "medium"
        else:
            return "low"
    
    def _generate_caveat(self, best: Dict, profile: Dict) -> str:
        """生成注意事项（诚实表达不确定性）"""
        cons = best.get("cons", [])
        if cons:
            return f"需要注意：{cons[0]}。如果这一点对你很重要，我们可以重新评估。"
        return ""
    
    def zhang_xuefeng_reality_check(
        self,
        parent_expectation: str,
        student_actual_situation: Dict
    ) -> Dict:
        """
        张雪峰式现实检验
        
        当家长期望与学生实际情况不匹配时，
        温和但直接地说出真相，并提供可行路径。
        
        Args:
            parent_expectation: 家长的期望（如"要上人大附中"）
            student_actual_situation: 学生实际情况
        
        Returns:
            现实检验报告
        """
        # 评估期望的可行性
        feasibility = self._assess_feasibility(
            parent_expectation, student_actual_situation
        )
        
        # 生成直接但温和的回应
        direct_response = self._generate_reality_check_response(
            parent_expectation, feasibility, student_actual_situation
        )
        
        # 提供可行的替代路径
        alternative_paths = self._suggest_alternative_paths(
            parent_expectation, student_actual_situation, feasibility
        )
        
        return {
            "expectation": parent_expectation,
            "feasibility": feasibility,
            "direct_response": direct_response,
            "alternative_paths": alternative_paths,
            "action_required": feasibility["gap"] > 30,
            "generated_at": datetime.now().isoformat()
        }
    
    def _assess_feasibility(
        self, expectation: str, situation: Dict
    ) -> Dict:
        """评估期望的可行性"""
        # 简化评估逻辑
        current_level = situation.get("academic_level", 70)  # 0-100
        
        # 根据目标学校评估所需水平
        required_level = 70  # 默认
        if any(school in expectation for school in ["人大附中", "清华附中", "北大附中"]):
            required_level = 90
        elif any(school in expectation for school in ["101中学", "北师大附中"]):
            required_level = 80
        elif "1+3" in expectation:
            required_level = 85
        
        gap = max(0, required_level - current_level)
        
        return {
            "current_level": current_level,
            "required_level": required_level,
            "gap": gap,
            "label": "可行" if gap < 10 else ("有挑战" if gap < 25 else "挑战较大"),
            "time_needed": f"约{gap // 5}个月的针对性提升"
        }
    
    def _generate_reality_check_response(
        self, expectation: str, feasibility: Dict, situation: Dict
    ) -> str:
        """生成现实检验回应（直接但温和）"""
        gap = feasibility["gap"]
        label = feasibility["label"]
        
        if gap < 10:
            return (
                f"这个目标是可行的。你现在的水平和目标要求差距不大，"
                f"按照当前的节奏，有很大希望实现。"
            )
        elif gap < 25:
            return (
                f"我需要直接告诉你：这个目标有一定挑战，但不是不可能。"
                f"目前还有{gap}分的差距需要弥补，"
                f"大约需要{feasibility['time_needed']}的针对性提升。"
                f"我们来制定一个具体的行动计划。"
            )
        else:
            return (
                f"我要直接说：以目前的情况，这个目标的难度很高。"
                f"不是不可能，但需要在短时间内有显著的提升，"
                f"这需要非常高强度的投入。"
                f"我建议我们同时考虑一个更稳健的备选方案，"
                f"这样无论结果如何，都有好的出路。"
            )
    
    def _suggest_alternative_paths(
        self, expectation: str, situation: Dict, feasibility: Dict
    ) -> List[Dict]:
        """提供替代路径（直接给出具体选项）"""
        paths = []
        gap = feasibility["gap"]
        
        if gap > 20:
            # 目标太高时，给出阶梯式路径
            paths.append({
                "path": "阶梯路径",
                "description": "先稳定进入一所优质学校，高中再冲刺顶尖",
                "rationale": "在好的环境中成长，比勉强进入顶尖学校后跟不上更有利"
            })
        
        paths.append({
            "path": "全力冲刺路径",
            "description": f"接下来{feasibility['time_needed']}全力提升，争取达到目标",
            "rationale": "如果家庭有充足的时间和资源支持，值得尝试"
        })
        
        paths.append({
            "path": "多元备选路径",
            "description": "准备3个梯度的学校：冲刺、稳妥、保底",
            "rationale": "降低风险，确保有好的结果"
        })
        
        return paths
    
    def check_and_improve_directness(self, response_text: str) -> Dict:
        """
        检查小伴的回复是否足够直接，并提供改进建议
        
        用于质量控制：确保小伴不会说太多模糊的话
        
        Args:
            response_text: 小伴的回复文本
        
        Returns:
            直接性评估和改进建议
        """
        issues = []
        suggestions = []
        
        # 检查模糊表达
        for vague, direct in VAGUE_TO_DIRECT.items():
            if vague in response_text and "{" not in direct:
                issues.append(f"发现模糊表达：'{vague}'")
                suggestions.append(f"将'{vague}'改为更直接的表达")
        
        # 检查是否有具体建议
        has_concrete = any(
            phrase in response_text
            for phrase in ["我建议", "我推荐", "我认为", "建议你", "应该选"]
        )
        
        if not has_concrete and len(response_text) > 100:
            issues.append("回复较长但缺少具体建议")
            suggestions.append("在回复末尾加上一个具体的行动建议")
        
        directness_score = max(0, 100 - len(issues) * 20)
        
        return {
            "directness_score": directness_score,
            "issues": issues,
            "suggestions": suggestions,
            "needs_improvement": directness_score < 60,
            "verdict": "直接清晰" if directness_score >= 80 else ("可以更直接" if directness_score >= 60 else "需要改进")
        }
    
    def generate_direct_study_advice(
        self,
        weak_points: List[str],
        available_time_days: int,
        exam_date: str = ""
    ) -> str:
        """
        生成直接的学习建议（不绕弯子）
        
        不说"可以多练习"，而是说"每天做5道这类题，连续7天"
        
        Args:
            weak_points: 薄弱知识点列表
            available_time_days: 可用天数
            exam_date: 考试日期
        
        Returns:
            直接的学习计划文本
        """
        if not weak_points:
            return "目前没有发现明显薄弱点，保持当前节奏即可。"
        
        lines = [f"接下来{available_time_days}天的学习重点，我直接告诉你：\n"]
        
        # 按优先级分配时间
        days_per_point = max(1, available_time_days // len(weak_points))
        
        for i, kp in enumerate(weak_points[:3]):
            day_start = i * days_per_point + 1
            day_end = (i + 1) * days_per_point
            
            lines.append(
                f"**第{day_start}-{day_end}天：{kp}**\n"
                f"每天：做5道{kp}的专项题，错了的题当天必须弄懂，"
                f"第二天重做一遍验证是否真的会了。"
            )
        
        if exam_date:
            lines.append(f"\n考试前最后2天：不学新内容，只复习错题本。")
        
        lines.append(
            f"\n这不是建议，这是计划。如果你按这个做，我保证会有提升。"
        )
        
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("DirectExpressionEngine 测试")
    print("=" * 60)
    
    engine = DirectExpressionEngine()
    
    # 测试 1：直接推荐
    print("\n【测试 1】学校选择直接推荐")
    result = engine.make_direct_recommendation(
        question="人大附中和北大附中哪个更适合小可爱？",
        options=[
            {
                "name": "人大附中",
                "pros": ["海淀区顶尖", "升学资源丰富", "学籍在海淀"],
                "cons": ["竞争激烈", "压力大"]
            },
            {
                "name": "北大附中",
                "pros": ["素质教育好", "创新氛围浓"],
                "cons": ["学术竞争同样激烈"]
            }
        ],
        student_profile={"district": "海淀", "school": "七一小学"}
    )
    print(f"推荐: {result['top_recommendation']}")
    print(f"推荐语: {result['recommendation_text']}")
    print(f"置信度: {result['confidence']}")
    
    # 测试 2：现实检验
    print("\n【测试 2】张雪峰式现实检验")
    check = engine.zhang_xuefeng_reality_check(
        parent_expectation="要上人大附中实验班",
        student_actual_situation={"academic_level": 65, "has_competition": False}
    )
    print(f"可行性: {check['feasibility']['label']}")
    print(f"直接回应: {check['direct_response'][:150]}...")
    
    # 测试 3：直接学习建议
    print("\n【测试 3】直接学习建议")
    advice = engine.generate_direct_study_advice(
        weak_points=["分数除法", "比例", "百分数"],
        available_time_days=14,
        exam_date="2026-05-10"
    )
    print(advice[:300])
    
    # 测试 4：直接性检查
    print("\n【测试 4】回复直接性检查")
    vague_response = "这个问题可以考虑多方面因素，也许可以选择A，也可能B也不错，因人而异，仅供参考。"
    check_result = engine.check_and_improve_directness(vague_response)
    print(f"直接性评分: {check_result['directness_score']}")
    print(f"问题: {check_result['issues']}")
    print(f"判断: {check_result['verdict']}")
    
    print("\n✅ 测试完成")
