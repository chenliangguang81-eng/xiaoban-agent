"""
认知自主性保护引擎 (Epistemic Autonomy Engine)
小伴 v5.1 — Mythos 第二批技能模块

基于 Claude Constitution 中的 Epistemic Autonomy 原则：
"Claude is talking with a large number of people at once, and nudging people 
towards its own views or undermining their epistemic independence could have 
an outsized effect on society compared with a single individual doing the same thing."

核心能力：
1. 多视角分析 (Multi-Perspective Analysis)：在小升初建议中提供多视角，不灌输单一答案
2. 认知偏见检测 (Cognitive Bias Detection)：识别并标记可能影响决策的认知偏见
3. 独立思考引导 (Independent Thinking Facilitation)：引导用户自己推理，而非依赖小伴
4. 信息平衡呈现 (Balanced Information Presentation)：呈现支持和反对的论据
5. 决策框架提供 (Decision Framework)：提供思考框架，而非直接给出结论

适用场景：
- 小升初志愿填报建议（多视角分析，不单一推荐）
- 专业选择建议（张雪峰方法论 + 个人兴趣的平衡）
- 家长教育决策（提供框架，尊重家长最终决策权）
- 学生价值观讨论（不灌输，引导自我发现）
"""
from engines.llm_core import llm_call, get_llm_router
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────────────────────────────────────
# 认知偏见类型定义
# ─────────────────────────────────────────────────────────────────────────────

COGNITIVE_BIASES = {
    "confirmation_bias": {
        "name": "确认偏见",
        "description": "只关注支持自己已有想法的信息",
        "example": "只看好的学校评价，忽略差评",
        "mitigation": "主动寻找反对意见"
    },
    "availability_heuristic": {
        "name": "可得性启发",
        "description": "过度重视容易想到的例子",
        "example": "因为认识一个去了某校的优秀学生，就认为那所学校很好",
        "mitigation": "查看系统性数据，而非个案"
    },
    "anchoring_bias": {
        "name": "锚定偏见",
        "description": "过度依赖第一个获得的信息",
        "example": "第一次听说五十七中，就把它作为比较基准",
        "mitigation": "主动了解多所学校后再比较"
    },
    "sunk_cost_fallacy": {
        "name": "沉没成本谬误",
        "description": "因为已经投入而继续坚持错误决策",
        "example": "已经报了某培训班，就算效果不好也继续上",
        "mitigation": "评估未来价值，而非过去投入"
    },
    "social_proof": {
        "name": "社会认同偏见",
        "description": "因为'大家都这么做'而跟风",
        "example": "因为周围同学都报了某学校，就跟着报",
        "mitigation": "根据自身情况独立判断"
    },
    "authority_bias": {
        "name": "权威偏见",
        "description": "过度信任权威人士的观点",
        "example": "因为某老师推荐某校，就不加分析地接受",
        "mitigation": "理解权威观点的依据，而非盲目接受"
    }
}


class EpistemicAutonomyEngine:
    """
    认知自主性保护引擎
    
    职责：
    1. 在小升初建议中提供多视角分析
    2. 检测并标记决策中的认知偏见
    3. 引导用户独立思考，而非依赖小伴
    4. 提供决策框架，尊重用户最终决策权
    """
    
    def __init__(self):
        self.bias_detection_enabled = True
        self.multi_perspective_enabled = True
        
    def analyze_school_choice(
        self,
        school_name: str,
        student_profile: Dict,
        user_preference: str = ""
    ) -> Dict:
        """
        多视角学校分析（小升初核心场景）
        
        不单一推荐，而是提供：
        - 支持选择该学校的理由
        - 反对或需谨慎的理由
        - 适合的学生画像
        - 不适合的学生画像
        - 需要进一步了解的信息
        
        Args:
            school_name: 学校名称
            student_profile: 学生画像（成绩、兴趣、通勤等）
            user_preference: 用户已有的倾向性表述
        
        Returns:
            多视角分析报告
        """
        # 检测用户偏见
        detected_biases = []
        if user_preference:
            detected_biases = self._detect_biases_in_preference(user_preference)
        
        # 生成多视角分析
        analysis = self._generate_multi_perspective_analysis(
            school_name, student_profile
        )
        
        # 构建决策框架
        decision_framework = self._build_decision_framework(
            school_name, student_profile
        )
        
        return {
            "school": school_name,
            "multi_perspective_analysis": analysis,
            "decision_framework": decision_framework,
            "detected_biases": detected_biases,
            "epistemic_note": (
                "以上分析提供多个视角供参考。最终决策应基于您对小可爱的了解，"
                "以及您认为最重要的因素。小伴的角色是帮您把信息说清楚，"
                "而不是替您做决定。"
            ),
            "questions_to_consider": self._generate_reflection_questions(
                school_name, student_profile
            ),
            "timestamp": datetime.now().isoformat()
        }
    
    def _detect_biases_in_preference(self, preference_text: str) -> List[Dict]:
        """检测用户表述中的认知偏见"""
        detected = []
        
        # 简单关键词检测
        bias_signals = {
            "confirmation_bias": ["我觉得", "肯定", "一定", "就是"],
            "social_proof": ["大家都", "周围人", "别人都", "都说"],
            "authority_bias": ["老师说", "专家说", "听说", "据说"],
            "availability_heuristic": ["我认识", "有个同学", "有个朋友"],
            "anchoring_bias": ["第一", "最开始", "一开始就"],
        }
        
        for bias_type, signals in bias_signals.items():
            if any(signal in preference_text for signal in signals):
                bias_info = COGNITIVE_BIASES.get(bias_type, {})
                detected.append({
                    "type": bias_type,
                    "name": bias_info.get("name", bias_type),
                    "description": bias_info.get("description", ""),
                    "mitigation": bias_info.get("mitigation", ""),
                    "severity": "low"  # 默认低严重度，不过度干预
                })
        
        return detected
    
    def _generate_multi_perspective_analysis(
        self, school_name: str, student_profile: Dict
    ) -> Dict:
        """使用 LLM 生成多视角分析"""
        system_prompt = """你是小伴的认知自主性保护模块。

        你的任务是对一所学校进行多视角分析，帮助家长做出独立的、有依据的决策。
        
        核心原则：
        - 不单一推荐，提供平衡的正反两面分析
        - 明确标注哪些是事实，哪些是推测
        - 指出需要进一步核实的信息
        - 尊重家长的最终决策权
        
        以 JSON 格式返回，包含：
        - pros: 支持选择的理由列表（3-5条）
        - cons: 需要谨慎考虑的理由列表（3-5条）
        - suitable_for: 适合的学生类型描述
        - not_suitable_for: 不太适合的学生类型描述
        - key_uncertainties: 目前不确定、需要进一步了解的信息
        - confidence_level: 分析的整体置信度（high/medium/low）"""
        
        user_prompt = f"""
        学校：{school_name}
        学生画像：{json.dumps(student_profile, ensure_ascii=False)}
        
        请提供多视角分析。注意：
        1. 基于北京海淀区小升初的实际情况
        2. 考虑学生的海淀学籍+丰台户籍特殊情况
        3. 如果信息不足，明确说明
        """
        
        try:
            # [v5.2 Manus迁移] 统一路由器调用
            resp_reply = llm_call(user_prompt, system_prompt)
            return json.loads(resp_reply)
        except Exception as e:
            logger.error(f"多视角分析失败: {e}")
            return {
                "pros": ["暂时无法生成分析，请稍后重试"],
                "cons": [],
                "suitable_for": "待分析",
                "not_suitable_for": "待分析",
                "key_uncertainties": ["分析服务暂时不可用"],
                "confidence_level": "low"
            }
    
    def _build_decision_framework(
        self, school_name: str, student_profile: Dict
    ) -> List[Dict]:
        """
        构建决策框架（提供思考工具，而非答案）
        
        基于 Mythos 原则：帮助用户建立独立思考能力，
        而不是让他们依赖小伴的判断。
        """
        framework = [
            {
                "dimension": "学业适配度",
                "question": f"小可爱目前的学业水平，与{school_name}的录取要求和教学节奏是否匹配？",
                "weight": "高",
                "how_to_assess": "参考近3次考试成绩、老师评价"
            },
            {
                "dimension": "通勤可行性",
                "question": f"从丰台东大街5号院到{school_name}的通勤时间是否可接受？",
                "weight": "高",
                "how_to_assess": "实地测试通勤路线，考虑早高峰时间"
            },
            {
                "dimension": "发展路径",
                "question": f"{school_name}的升学路径（中考/直升）是否符合小可爱的长期规划？",
                "weight": "高",
                "how_to_assess": "了解该校近三年中考成绩和升学去向"
            },
            {
                "dimension": "孩子意愿",
                "question": "小可爱自己对这所学校有什么感受和想法？",
                "weight": "中",
                "how_to_assess": "直接问小可爱，听听她的真实想法"
            },
            {
                "dimension": "家庭资源匹配",
                "question": "选择这所学校后，家庭在时间、经济、精力上的投入是否可持续？",
                "weight": "中",
                "how_to_assess": "评估课外辅导需求、家长接送安排"
            }
        ]
        return framework
    
    def _generate_reflection_questions(
        self, school_name: str, student_profile: Dict
    ) -> List[str]:
        """生成引导独立思考的反思问题"""
        return [
            f"如果不考虑别人的看法，你们最看重{school_name}的哪一点？",
            "如果小可爱三年后回头看，她会希望当时选择了什么？",
            f"选择{school_name}最大的风险是什么？你们能接受吗？",
            "除了升学率，还有哪些因素对小可爱的成长同样重要？",
            "如果这个决定是错的，最坏的结果是什么？是否可以补救？"
        ]
    
    def protect_epistemic_autonomy(
        self,
        response_draft: str,
        topic: str,
        speaker: str = "parent"
    ) -> str:
        """
        对小伴的回复草稿进行认知自主性保护处理
        
        检查回复是否过于强势地灌输单一观点，
        如果是，则添加平衡性表述。
        
        Args:
            response_draft: 小伴的回复草稿
            topic: 话题类型
            speaker: 说话人
        
        Returns:
            经过认知自主性保护处理的回复
        """
        # 检测强势推荐信号
        strong_push_signals = [
            "你必须", "一定要", "绝对应该", "没有其他选择",
            "最好的选择就是", "唯一正确的"
        ]
        
        has_strong_push = any(signal in response_draft for signal in strong_push_signals)
        
        if has_strong_push:
            # 添加认知自主性保护声明
            autonomy_note = (
                "\n\n*以上是基于现有数据的分析建议，最终决策权在您手里。"
                "每个家庭的情况不同，建议结合您对小可爱的了解做出判断。*"
            )
            return response_draft + autonomy_note
        
        return response_draft
    
    def generate_balanced_xiaoshengchu_advice(
        self,
        student_profile: Dict,
        candidate_schools: List[str]
    ) -> Dict:
        """
        生成平衡的小升初建议（核心场景）
        
        不是单一推荐，而是：
        1. 为每所候选学校提供多视角分析
        2. 提供决策矩阵
        3. 明确标注置信度和不确定性
        4. 最终决策框架给家长
        
        Args:
            student_profile: 学生画像
            candidate_schools: 候选学校列表
        
        Returns:
            平衡的多视角建议报告
        """
        school_analyses = {}
        for school in candidate_schools:
            school_analyses[school] = self.analyze_school_choice(
                school, student_profile
            )
        
        # 生成决策矩阵
        decision_matrix = self._build_decision_matrix(
            candidate_schools, student_profile
        )
        
        return {
            "student": student_profile.get("name", "小可爱"),
            "analysis_date": datetime.now().isoformat(),
            "school_analyses": school_analyses,
            "decision_matrix": decision_matrix,
            "epistemic_autonomy_note": (
                "本报告提供多视角分析，旨在帮助您做出更有依据的决策，"
                "而非替您做决定。每所学校的分析都包含支持和反对的理由，"
                "请根据您对小可爱的了解和家庭实际情况综合判断。"
            ),
            "key_questions_for_family": [
                "你们最看重的是学校的升学率、教学质量、还是孩子的快乐？",
                "小可爱自己有没有表达过对某所学校的偏好？",
                "通勤时间对家庭来说是否是重要因素？",
                "如果一派没有中签，备选方案是什么？"
            ]
        }
    
    def _build_decision_matrix(
        self, schools: List[str], student_profile: Dict
    ) -> List[Dict]:
        """构建决策矩阵（帮助家长系统比较）"""
        dimensions = ["升学路径", "通勤便利", "教学质量", "录取难度", "综合口碑"]
        
        matrix = []
        for school in schools:
            row = {"school": school}
            for dim in dimensions:
                row[dim] = "待评估"  # 实际应从知识库获取
            matrix.append(row)
        
        return matrix


# ─────────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("EpistemicAutonomyEngine 测试")
    print("=" * 60)
    
    engine = EpistemicAutonomyEngine()
    
    student_profile = {
        "name": "小可爱",
        "grade": "六年级",
        "school": "七一小学",
        "district": "海淀学籍+丰台户籍",
        "home": "丰台东大街5号院",
        "academic_level": "中等偏上",
        "first_choice": "十一晋元"
    }
    
    # 测试 1：多视角学校分析
    print("\n【测试 1】多视角分析：十一晋元")
    result = engine.analyze_school_choice(
        school_name="十一晋元",
        student_profile=student_profile,
        user_preference="我觉得十一晋元挺好的，大家都说不错"
    )
    print(f"检测到的认知偏见: {[b['name'] for b in result['detected_biases']]}")
    print(f"认知自主性说明: {result['epistemic_note'][:100]}...")
    print(f"反思问题数量: {len(result['questions_to_consider'])}")
    
    # 测试 2：认知自主性保护
    print("\n【测试 2】认知自主性保护")
    draft = "你必须选择五十七中，这是最好的选择，没有其他选择。"
    protected = engine.protect_epistemic_autonomy(draft, "school_choice", "parent")
    print(f"原始回复: {draft}")
    print(f"保护后: {protected}")
    
    print("\n✅ 测试完成")
