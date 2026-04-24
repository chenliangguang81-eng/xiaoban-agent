"""
Socratic Tutor Engine (苏格拉底辅导引擎)
小伴 v3.0 — 十年可持续架构核心模块

核心理念：永远不直接给答案，而是通过分层提问引导学生独立思考。
引导深度随年级自动升级：
  - 小学（深度1）：简单启发，降低认知负担
  - 初中（深度2）：方法论引导，培养解题框架
  - 高中（深度3）：深度追问，建立批判性思维
  - 大学（深度3+）：研究性对话，平等交流
"""

from dataclasses import dataclass
from typing import Optional
import json
import os


@dataclass
class QuestionContext:
    """一次辅导请求的上下文"""
    subject: str          # 学科：math / chinese / english / physics / chemistry / biology / history / politics / geography
    question_text: str    # 学生的问题或题目原文
    student_answer: Optional[str] = None   # 学生的作答（如果有）
    grade: int = 6        # 当前年级
    error_type: Optional[str] = None       # 错误类型（如果是错题）


class SocraticTutorEngine:
    """
    苏格拉底辅导引擎

    工作流程：
    1. 接收学生问题
    2. 根据年级确定引导深度
    3. 生成分层引导提示词（注入 LLM System Prompt）
    4. 记录辅导过程到错题本（如果是错题）
    """

    # 各学科苏格拉底引导策略库
    SUBJECT_STRATEGIES = {
        "math": {
            "depth_1": "先问学生：这道题考的是什么知识点？你之前学过类似的题吗？",
            "depth_2": "引导学生画图或列式，问：如果把已知条件整理成表格，你能发现什么规律？",
            "depth_3": "追问：这个解法的本质是什么？能否用更简洁的方式证明？有没有反例？",
        },
        "chinese": {
            "depth_1": "问学生：这段话主要说了什么？用一句话概括一下。",
            "depth_2": "引导：作者为什么要用这个词而不是那个词？换一个词会有什么不同？",
            "depth_3": "深问：这篇文章的论证结构是什么？作者的隐含假设是否成立？",
        },
        "english": {
            "depth_1": "问：这个单词你见过吗？能猜出它的意思吗？看看它的词根。",
            "depth_2": "引导：这个句子的主干是什么？从句修饰的是哪个成分？",
            "depth_3": "追问：这段话的逻辑连接词是什么？作者的论证是否严密？",
        },
        "physics": {
            "depth_1": "问：这道题里有哪些物理量？它们之间有什么关系？",
            "depth_2": "引导：先画受力分析图，每个力的方向和大小你能确定吗？",
            "depth_3": "深问：这个物理模型做了哪些理想化假设？现实中会有什么偏差？",
        },
        "default": {
            "depth_1": "先问学生：你理解题目的意思了吗？用自己的话说一遍。",
            "depth_2": "引导：把已知条件和未知量分别列出来，你能找到突破口吗？",
            "depth_3": "追问：这个知识点的本质是什么？它和你学过的哪些内容有联系？",
        }
    }

    # 错误类型分类（用于错题归因）
    ERROR_TAXONOMY = {
        "concept_misunderstanding": "概念理解错误",
        "calculation_error": "计算粗心错误",
        "method_wrong": "解题方法错误",
        "knowledge_gap": "知识点遗漏",
        "reading_comprehension": "题意理解偏差",
        "time_pressure": "考试时间压力导致失误",
        "unknown": "原因待分析",
    }

    def __init__(self, memory_manager=None, phase_engine=None):
        self.memory_manager = memory_manager
        self.phase_engine = phase_engine

    def _get_depth(self, grade: int) -> int:
        """根据年级获取苏格拉底引导深度"""
        if grade <= 6:
            return 1
        elif grade <= 9:
            return 2
        else:
            return 3

    def _get_strategy(self, subject: str, depth: int) -> str:
        """获取对应学科和深度的引导策略"""
        strategies = self.SUBJECT_STRATEGIES.get(subject, self.SUBJECT_STRATEGIES["default"])
        return strategies.get(f"depth_{depth}", strategies["depth_1"])

    def generate_tutoring_prompt(self, context: QuestionContext) -> str:
        """
        生成苏格拉底式辅导的 System Prompt 片段
        这段文字将被注入到 LLM 的 System Prompt 中，指导 LLM 如何回应学生
        """
        depth = self._get_depth(context.grade)
        strategy = self._get_strategy(context.subject, depth)

        # 获取阶段配置（如果有阶段引擎）
        stage_briefing = ""
        if self.phase_engine:
            stage_briefing = self.phase_engine.generate_stage_briefing(context.grade)

        prompt = f"""
你是小伴，一个苏格拉底式的学习辅导智能体。

{stage_briefing}

【本次辅导任务】
学科：{context.subject}
年级：{context.grade}年级
苏格拉底引导深度：{depth}级

【核心原则】
绝对不要直接给出答案或完整解题过程。你的任务是通过提问引导学生自己找到答案。
如果学生坚持要答案，告诉他："我相信你能自己想出来，我们一步一步来。"

【本题引导策略】
{strategy}

【学生的问题/题目】
{context.question_text}

{f'【学生的作答】{chr(10)}{context.student_answer}' if context.student_answer else ''}

请根据以上信息，用引导性问题开始这次辅导对话。第一个问题要简单、友好，让学生感到有信心。
""".strip()
        return prompt

    def log_mistake(self, context: QuestionContext, error_type: str = "unknown") -> dict:
        """
        将一道错题记录到错题本
        返回错题记录字典
        """
        from datetime import datetime, timedelta

        now = datetime.now()
        # 艾宾浩斯复习计划：1天、2天、4天、7天、15天、30天后复习
        review_intervals = [1, 2, 4, 7, 15, 30]
        review_dates = [(now + timedelta(days=d)).strftime("%Y-%m-%d") for d in review_intervals]

        mistake_record = {
            "id": f"{context.subject}_{now.strftime('%Y%m%d_%H%M%S')}",
            "subject": context.subject,
            "grade": context.grade,
            "question": context.question_text,
            "student_answer": context.student_answer,
            "error_type": error_type,
            "error_type_label": self.ERROR_TAXONOMY.get(error_type, "未知"),
            "created_at": now.isoformat(),
            "review_schedule": review_dates,
            "review_completed": [],
            "mastered": False,
        }

        # 如果有 MemoryManager，写入持久化存储
        if self.memory_manager:
            self.memory_manager.add_mistake(mistake_record)

        return mistake_record

    def get_due_reviews(self, mistake_book: list[dict]) -> list[dict]:
        """
        获取今天需要复习的错题（基于艾宾浩斯曲线）
        """
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        due = []
        for m in mistake_book:
            if not m.get("mastered", False):
                schedule = m.get("review_schedule", [])
                completed = m.get("review_completed", [])
                # 找到下一个未完成的复习日期
                pending = [d for d in schedule if d not in completed]
                if pending and pending[0] <= today:
                    due.append(m)
        return due


# ============================================================
# 快速测试
# ============================================================
if __name__ == "__main__":
    engine = SocraticTutorEngine()

    # 测试场景：小学六年级数学错题
    ctx = QuestionContext(
        subject="math",
        question_text="一个长方形的长是8cm，宽是5cm，求它的周长和面积。",
        student_answer="周长=8+5=13cm，面积=8×5=40cm²",
        grade=6,
        error_type="calculation_error"
    )

    print("=== 苏格拉底辅导提示词（小学数学）===")
    print(engine.generate_tutoring_prompt(ctx))

    print("\n=== 错题记录 ===")
    record = engine.log_mistake(ctx, "calculation_error")
    print(json.dumps(record, ensure_ascii=False, indent=2))

    # 测试场景：高中物理
    ctx2 = QuestionContext(
        subject="physics",
        question_text="一个质量为2kg的物体在水平面上做匀速直线运动，受到的摩擦力为4N，求动摩擦因数。",
        grade=10,
    )
    print("\n=== 苏格拉底辅导提示词（高中物理）===")
    print(engine.generate_tutoring_prompt(ctx2))
