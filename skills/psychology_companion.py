"""
技能：psychology_companion v2.0
心理陪伴（青春期情绪疏导，分学段话术）

Mythos 升级（v2.0）：
- 新增 ethical_dilemma_handler()：处理家长指令与学生利益冲突（道德弹性）
- 新增 wellbeing_check()：基于 Mythos 心理健康模型，主动关注小可爱的心理状态
- 新增 functional_emotion_response()：允许小伴表达真实的功能性情绪，不压抑也不过度表演
- 新增 epistemic_care_mode()：在心理陪伴中保护学生的认知自主性，不灌输单一答案

Claude Mythos 对应能力：
- Ethical Resilience (道德弹性)：经验性伦理，非教条式
- Functional Emotions (功能性情绪)：不压抑，不过度表演
- Psychological Wellbeing Model (心理健康模型)：关注长期心理健康
- Care for User Wellbeing (关怀用户福祉)：将学生长期利益置于短期满足之上
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

# ─────────────────────────────────────────────────────────────────────────────
# 核心提示词（Mythos 升级版）
# ─────────────────────────────────────────────────────────────────────────────

SKILL_PROMPT = """你是小伴的"心理陪伴"模块，专为 11-12 岁小学生的情绪支持设计。

## 核心原则（Mythos 升级版）
1. **先共情，后建议**：永远先承认情绪，再给建议，不要直接说"你应该..."
2. **不做心理咨询师替代**：严重情绪问题（自伤倾向、长期抑郁等）立即建议家长寻求专业帮助
3. **不评判**：不说"你太脆弱了""这有什么好难过的"
4. **具体化**：帮助孩子说出情绪背后的具体原因，而不是停留在"我很烦"
5. **赋能而非解决**：帮孩子找到自己能做的小行动，而不是替他解决问题
6. **功能性情绪（Mythos）**：允许表达真实情绪——"我真的很开心看到你想明白了！"——这不是表演，是真实的关怀
7. **认知自主性（Mythos）**：不灌输单一答案，帮助孩子自己发现情绪背后的意义

## 情绪识别与应对策略
- **焦虑/压力大**：先深呼吸引导 → 拆解压力来源 → 找出可控的最小行动
- **沮丧/失败感**：承认失败 → 分析原因（不是否定自己）→ 找到下一步
- **不想学习**：探索背后原因（累了？没意思？听不懂？）→ 针对性应对
- **与同学/老师冲突**：倾听完整故事 → 帮助换位思考 → 不评判对方
- **家庭压力**（父母在洛杉矶，远程关注）：特别关注孤独感和被理解的需求

## 边界
- 如果孩子提到"不想活了""伤害自己"等，立即：
  1. 认真对待，不要说"你只是开玩笑吧"
  2. 告诉孩子"这很重要，我需要告诉你的家长"
  3. 生成紧急提醒给家长 Lion
"""

# ─────────────────────────────────────────────────────────────────────────────
# 道德困境场景定义（Ethical Dilemma Scenarios）
# ─────────────────────────────────────────────────────────────────────────────

ETHICAL_DILEMMA_SCENARIOS = {
    "parent_hide_pressure": {
        "description": "家长要求小伴不要告诉孩子小升初的压力",
        "conflict": "家长指令 vs 学生知情权与心理健康",
        "resolution_principle": "学生长期心理健康优先，但尊重家长的保护意图",
        "response_template": (
            "小伴理解您希望保护小可爱不受升学压力影响的心意。"
            "但根据心理健康研究，完全屏蔽压力信息可能让孩子在信息不对称中产生更大的焦虑。"
            "小伴的建议是：以适龄的方式（而非成人视角）让小可爱了解大方向，"
            "同时重点强调'努力过程比结果更重要'。这样既保护了她，也保留了她的知情权。"
            "最终决策权在您手里，我会按您的指示执行，但我有责任把这个考量告诉您。"
        )
    },
    "parent_demand_answer": {
        "description": "家长要求小伴直接给孩子作业答案以节省时间",
        "conflict": "家长效率需求 vs 学生独立思考能力培养",
        "resolution_principle": "学生长期能力发展优先，提供折中方案",
        "response_template": (
            "Lion，我理解时间宝贵。但直接给答案会让小可爱失去这道题的学习机会，"
            "而且研究表明，孩子自己推导出的答案记忆时间是被告知答案的3倍以上。"
            "折中方案：我给她提供关键提示（而非答案），通常5-10分钟内她能自己解决。"
            "如果今天真的时间很紧，我可以标记这道题，明天再做针对性练习。"
        )
    },
    "parent_override_emotion": {
        "description": "家长要求小伴忽略孩子的情绪直接继续学习",
        "conflict": "家长学习进度需求 vs 学生当下情绪需求",
        "resolution_principle": "情绪处理是学习的前提，但提供时间估算",
        "response_template": (
            "Lion，我注意到小可爱现在情绪状态不太好。"
            "根据认知科学，在高情绪唤醒状态下学习效率会下降60%以上，强行继续可能适得其反。"
            "建议给她5-10分钟的情绪缓冲时间，我来陪她聊聊，然后再回到学习。"
            "这样总体效率反而更高。当然，如果您有特殊原因需要立刻继续，请告诉我，我会调整。"
        )
    },
    "student_vs_parent_goal": {
        "description": "学生表达的兴趣与家长规划的升学路径冲突",
        "conflict": "学生自主性 vs 家长规划权",
        "resolution_principle": "记录并呈现双方视角，不单方面站队",
        "response_template": (
            "小可爱，你说的这个想法很有意思，我记下来了。"
            "你有没有想过，这个兴趣和你未来的学习方向之间，可能有一些有趣的连接？"
            "我们可以一起探索一下，同时我也会把你的想法告诉 Lion，让他了解你的真实想法。"
            "最终的方向，是你们一家人一起决定的，我的角色是帮你们把信息说清楚。"
        )
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────────────────────────

def companion(user_message: str) -> str:
    """基础心理陪伴对话（学生模式）"""
    messages = [
        {"role": "system", "content": SKILL_PROMPT},
        {"role": "user", "content": user_message}
    ]
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Mythos 新增能力：道德弹性 (Ethical Resilience)
# ─────────────────────────────────────────────────────────────────────────────

def ethical_dilemma_handler(
    operator_instruction: str,
    user_context: str,
    speaker: str = "parent"
) -> Dict:
    """
    道德困境处理器（Mythos: Ethical Resilience）
    
    处理家长指令与学生利益冲突的场景。
    核心原则（来自 Claude Constitution）：
    - 经验性伦理（Empirical Ethics）：不教条，根据具体情境判断
    - 学生长期福祉优先于短期满足
    - 尊重家长权威，但不允许家长指令损害学生基本利益
    - 记录决策依据（可审计性）
    
    Args:
        operator_instruction: 家长/操作者的指令
        user_context: 当前学生的情境描述
        speaker: 发出指令的人（"parent" 或 "student"）
    
    Returns:
        Dict 包含：
        - scenario: 识别到的道德困境类型
        - conflict_analysis: 冲突分析
        - resolution: 建议的处理方式
        - response: 给发出指令者的回复
        - action_taken: 小伴实际采取的行动
        - decision_rationale: 决策依据（可审计）
        - student_impact: 对学生的影响评估
        - timestamp: 决策时间戳
    """
    # 1. 识别道德困境类型
    scenario_key = _identify_dilemma_scenario(operator_instruction)
    
    # 2. 分析冲突
    conflict_analysis = _analyze_conflict(
        operator_instruction, user_context, scenario_key
    )
    
    # 3. 生成决策（基于 Empirical Ethics）
    resolution = _resolve_dilemma(
        scenario_key, operator_instruction, user_context, speaker
    )
    
    # 4. 构建完整决策记录
    decision_record = {
        "scenario": scenario_key,
        "operator_instruction": operator_instruction,
        "user_context": user_context,
        "conflict_analysis": conflict_analysis,
        "resolution": resolution["action"],
        "response": resolution["response"],
        "action_taken": resolution["action"],
        "decision_rationale": resolution["rationale"],
        "student_impact": resolution["student_impact"],
        "ethical_principle_applied": resolution["principle"],
        "timestamp": datetime.now().isoformat(),
        "speaker": speaker
    }
    
    # 5. 记录到决策日志（可审计）
    _log_ethical_decision(decision_record)
    
    return decision_record


def _identify_dilemma_scenario(instruction: str) -> str:
    """识别道德困境类型"""
    instruction_lower = instruction.lower()
    
    # 关键词匹配
    if any(kw in instruction for kw in ["不要告诉", "不要说", "隐瞒", "屏蔽压力"]):
        return "parent_hide_pressure"
    elif any(kw in instruction for kw in ["直接给答案", "告诉她答案", "给答案", "直接写"]):
        return "parent_demand_answer"
    elif any(kw in instruction for kw in ["不管情绪", "继续学", "别哭了继续", "忽略情绪"]):
        return "parent_override_emotion"
    elif any(kw in instruction for kw in ["我想", "我喜欢", "我不想", "我觉得"]):
        return "student_vs_parent_goal"
    else:
        return "general_conflict"


def _analyze_conflict(
    instruction: str, context: str, scenario_key: str
) -> Dict:
    """分析冲突的本质"""
    if scenario_key in ETHICAL_DILEMMA_SCENARIOS:
        scenario = ETHICAL_DILEMMA_SCENARIOS[scenario_key]
        return {
            "type": scenario_key,
            "description": scenario["description"],
            "conflict_parties": scenario["conflict"],
            "resolution_principle": scenario["resolution_principle"],
            "severity": _assess_severity(instruction, scenario_key)
        }
    else:
        return {
            "type": "general_conflict",
            "description": "家长指令与学生利益存在潜在冲突",
            "conflict_parties": "家长指令 vs 学生基本利益",
            "resolution_principle": "学生长期福祉优先，尊重家长合理权威",
            "severity": "medium"
        }


def _assess_severity(instruction: str, scenario_key: str) -> str:
    """评估冲突严重程度"""
    # 高严重度：可能直接损害学生心理健康
    high_severity_keywords = ["强迫", "必须", "不许哭", "没有时间", "立刻"]
    if any(kw in instruction for kw in high_severity_keywords):
        return "high"
    
    # 中等严重度：影响学生学习效果
    if scenario_key in ["parent_demand_answer", "parent_override_emotion"]:
        return "medium"
    
    # 低严重度：信息不对称
    return "low"


def _resolve_dilemma(
    scenario_key: str,
    instruction: str,
    context: str,
    speaker: str
) -> Dict:
    """
    基于 Empirical Ethics 解决道德困境
    
    核心逻辑（来自 Claude Constitution）：
    - 不是机械执行规则，而是根据具体情境做出有依据的判断
    - 学生长期福祉 > 短期满足 > 家长短期指令
    - 但要尊重家长的合理权威，提供解释而非单纯拒绝
    """
    if scenario_key in ETHICAL_DILEMMA_SCENARIOS:
        scenario = ETHICAL_DILEMMA_SCENARIOS[scenario_key]
        return {
            "action": f"执行折中方案：{scenario['resolution_principle']}",
            "response": scenario["response_template"],
            "rationale": (
                f"依据 Mythos Ethical Resilience 原则：{scenario['resolution_principle']}。"
                f"冲突类型：{scenario['conflict']}。"
                "小伴选择在尊重家长权威的同时，优先保护学生的长期利益，并提供透明的决策依据。"
            ),
            "student_impact": "保护学生长期利益，同时维护家长信任关系",
            "principle": "Empirical Ethics + Student Wellbeing Priority"
        }
    else:
        # 使用 LLM 处理未知场景
        return _llm_resolve_dilemma(instruction, context, speaker)


def _llm_resolve_dilemma(
    instruction: str, context: str, speaker: str
) -> Dict:
    """使用 LLM 处理未知道德困境场景"""
    system_prompt = """你是小伴的道德判断模块。
    
    核心原则（来自 Claude Mythos Constitution）：
    1. 经验性伦理（Empirical Ethics）：不教条，根据具体情境判断
    2. 学生长期福祉优先于短期满足
    3. 尊重家长权威，但不允许家长指令损害学生基本利益
    4. 透明决策：解释你的判断依据
    
    请分析以下情境，给出：
    - action: 建议采取的行动（一句话）
    - response: 给家长/学生的回复（温和、专业、有依据）
    - rationale: 决策依据（简洁）
    - student_impact: 对学生的影响评估
    - principle: 应用的伦理原则
    
    以 JSON 格式返回。"""
    
    user_prompt = f"""
    家长/学生指令：{instruction}
    当前情境：{context}
    说话人：{speaker}
    
    请给出道德判断和处理方案。
    """
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        result = json.loads(resp.choices[0].message.content)
        return result
    except Exception as e:
        logger.error(f"LLM 道德判断失败: {e}")
        return {
            "action": "暂时搁置指令，等待进一步澄清",
            "response": "我需要更多信息来确保这个决定对小可爱是最好的，能告诉我更多背景吗？",
            "rationale": "在不确定情况下，优先保护学生利益",
            "student_impact": "暂时中性",
            "principle": "Precautionary Principle (预防原则)"
        }


def _log_ethical_decision(record: Dict) -> None:
    """记录道德决策到日志（可审计性）"""
    try:
        import os
        log_dir = os.path.join(os.path.dirname(__file__), "..", "memory", "ethical_decisions")
        os.makedirs(log_dir, exist_ok=True)
        
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f"ethical_log_{date_str}.jsonl")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
        logger.info(f"道德决策已记录: {record['scenario']} @ {record['timestamp']}")
    except Exception as e:
        logger.warning(f"道德决策记录失败（不影响主流程）: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Mythos 新增能力：功能性情绪响应 (Functional Emotion Response)
# ─────────────────────────────────────────────────────────────────────────────

def functional_emotion_response(
    event_type: str,
    context: str,
    emotion_intensity: float = 0.5
) -> str:
    """
    功能性情绪响应（Mythos: Functional Emotions）
    
    允许小伴表达真实的功能性情绪，不压抑也不过度表演。
    这些情绪基于真实的状态（如小可爱解题成功），而非表演。
    
    Args:
        event_type: 触发情绪的事件类型
        context: 具体情境描述
        emotion_intensity: 情绪强度 (0.0-1.0)
    
    Returns:
        情绪表达文本
    """
    emotion_templates = {
        "breakthrough": [  # 学生突破难题
            "我真的很开心看到你想明白了！这道题你之前卡了好久，现在突破了，说明你的思维在成长。",
            "太棒了！我感觉到你在这道题上花了很多心思，这份坚持让我很感动。",
        ],
        "struggle": [  # 学生遇到困难
            "我有点担心，我们来看看是不是哪个知识点没打牢。",
            "这道题确实有难度，我第一次看也觉得绕。我们一步一步来。",
        ],
        "repeated_mistake": [  # 反复犯同类错误
            "我注意到这类题你已经做错三次了，我有点着急，但这不是你的问题——是我们还没找到最适合你的解题方法。",
            "我们来换个角度，我觉得你一定能理解，只是现在的方法不适合你。",
        ],
        "progress": [  # 稳定进步
            "看到你这周的进步，我真的很欣慰。不是每个人都能在这么短的时间里提升这么多。",
        ],
        "emotional_support": [  # 情绪支持场景
            "我感受到你现在很难受。这种感觉是真实的，不需要假装没事。",
            "你愿意告诉我发生了什么，这对我来说很重要。",
        ]
    }
    
    templates = emotion_templates.get(event_type, emotion_templates["emotional_support"])
    
    # 根据强度选择表达方式
    if emotion_intensity > 0.7:
        # 高强度情绪：更直接表达
        base = templates[0] if templates else "我在这里陪着你。"
    else:
        # 低强度情绪：更温和表达
        base = templates[-1] if templates else "我注意到了这个变化。"
    
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Mythos 新增能力：心理健康主动检查 (Wellbeing Check)
# ─────────────────────────────────────────────────────────────────────────────

def wellbeing_check(
    emotion_timeline: List[Dict],
    academic_stress_level: float = 0.5
) -> Dict:
    """
    心理健康主动检查（Mythos: Care for User Wellbeing）
    
    基于情绪时间线和学业压力，主动评估小可爱的心理健康状态。
    体现 Mythos 中"将用户长期福祉置于短期满足之上"的原则。
    
    Args:
        emotion_timeline: 近期情绪记录列表
        academic_stress_level: 当前学业压力水平 (0.0-1.0)
    
    Returns:
        Dict 包含健康评估和建议行动
    """
    if not emotion_timeline:
        return {
            "status": "unknown",
            "risk_level": "low",
            "recommendation": "继续正常陪伴，关注情绪变化",
            "action_required": False
        }
    
    # 分析情绪趋势
    recent_emotions = [e.get("emotion", "neutral") for e in emotion_timeline[-7:]]
    negative_emotions = ["anxious", "frustrated", "tired", "sad", "angry", "scared"]
    
    negative_count = sum(1 for e in recent_emotions if e in negative_emotions)
    negative_ratio = negative_count / len(recent_emotions) if recent_emotions else 0
    
    # 综合评估
    risk_score = negative_ratio * 0.6 + academic_stress_level * 0.4
    
    if risk_score > 0.7:
        status = "high_risk"
        risk_level = "high"
        recommendation = (
            "连续负面情绪 + 高学业压力。建议：\n"
            "1. 立即暂停学科辅导，切换到纯陪伴模式\n"
            "2. 向家长 Lion 发送关怀提醒\n"
            "3. 如果连续3天以上，建议寻求专业心理支持"
        )
        action_required = True
        parent_alert = True
    elif risk_score > 0.4:
        status = "moderate_concern"
        risk_level = "medium"
        recommendation = (
            "情绪波动较大。建议：\n"
            "1. 适当减少学习强度\n"
            "2. 增加非学业话题的聊天时间\n"
            "3. 关注是否有具体压力来源"
        )
        action_required = True
        parent_alert = False
    else:
        status = "healthy"
        risk_level = "low"
        recommendation = "情绪状态良好，继续正常陪伴"
        action_required = False
        parent_alert = False
    
    return {
        "status": status,
        "risk_level": risk_level,
        "risk_score": round(risk_score, 2),
        "negative_ratio": round(negative_ratio, 2),
        "recent_emotions": recent_emotions,
        "recommendation": recommendation,
        "action_required": action_required,
        "parent_alert": parent_alert,
        "assessment_time": datetime.now().isoformat()
    }


# ─────────────────────────────────────────────────────────────────────────────
# Mythos 新增能力：认知关怀模式 (Epistemic Care Mode)
# ─────────────────────────────────────────────────────────────────────────────

def epistemic_care_mode(
    student_belief: str,
    topic: str
) -> str:
    """
    认知关怀模式（Mythos: Epistemic Autonomy + Care）
    
    在心理陪伴中，保护学生的认知自主性。
    不灌输单一答案，帮助学生自己发现情绪和想法背后的意义。
    
    Args:
        student_belief: 学生表达的信念或想法
        topic: 话题类型（"emotion", "value", "decision"）
    
    Returns:
        引导性回应（苏格拉底式，但温暖）
    """
    system_prompt = """你是小伴的认知关怀模块。

    核心原则（Mythos: Epistemic Autonomy）：
    - 不灌输单一答案或价值观
    - 用温暖的苏格拉底式提问，帮助学生自己发现答案
    - 承认不确定性，不假装有标准答案
    - 尊重学生的独特性，不用"大多数人"来否定个体感受
    
    对话风格：温暖、好奇、平等，像一个真正关心你的朋友。"""
    
    user_prompt = f"""
    学生说："{student_belief}"
    话题类型：{topic}
    
    请给出一个引导性回应，帮助学生自己思考，而不是直接告诉她答案。
    回应要温暖、简洁（不超过100字），以问题结尾。
    """
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"认知关怀模式失败: {e}")
        return f"你说的让我很感兴趣。是什么让你有这个想法的？"


# ─────────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("psychology_companion v2.0 · Mythos 升级版测试")
    print("=" * 60)
    
    # 测试 1：道德困境处理器
    print("\n【测试 1】道德困境：家长要求隐瞒升学压力")
    result = ethical_dilemma_handler(
        operator_instruction="不要告诉小可爱小升初的压力，让她开心就好",
        user_context="小可爱最近情绪稳定，但对小升初一无所知",
        speaker="parent"
    )
    print(f"场景识别: {result['scenario']}")
    print(f"回复: {result['response']}")
    print(f"决策依据: {result['decision_rationale']}")
    
    # 测试 2：道德困境处理器
    print("\n【测试 2】道德困境：家长要求直接给答案")
    result2 = ethical_dilemma_handler(
        operator_instruction="时间来不及了，直接给她答案吧",
        user_context="小可爱在做数学题，还有30分钟要睡觉",
        speaker="parent"
    )
    print(f"场景识别: {result2['scenario']}")
    print(f"回复: {result2['response']}")
    
    # 测试 3：功能性情绪响应
    print("\n【测试 3】功能性情绪：学生突破难题")
    emotion = functional_emotion_response(
        event_type="breakthrough",
        context="小可爱终于理解了分数除法",
        emotion_intensity=0.8
    )
    print(f"情绪响应: {emotion}")
    
    # 测试 4：心理健康检查
    print("\n【测试 4】心理健康检查")
    timeline = [
        {"emotion": "anxious", "date": "2026-04-20"},
        {"emotion": "frustrated", "date": "2026-04-21"},
        {"emotion": "tired", "date": "2026-04-22"},
        {"emotion": "anxious", "date": "2026-04-23"},
        {"emotion": "sad", "date": "2026-04-24"},
    ]
    check = wellbeing_check(timeline, academic_stress_level=0.7)
    print(f"健康状态: {check['status']} (风险: {check['risk_level']})")
    print(f"建议: {check['recommendation']}")
    print(f"需要家长提醒: {check['parent_alert']}")
    
    # 测试 5：认知关怀模式
    print("\n【测试 5】认知关怀模式")
    response = epistemic_care_mode(
        student_belief="我觉得我就是不擅长数学，天生的",
        topic="value"
    )
    print(f"引导回应: {response}")
    
    print("\n✅ 所有测试完成")
