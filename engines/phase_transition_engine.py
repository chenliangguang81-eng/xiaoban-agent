"""
Phase Transition Engine (阶段跃迁引擎)
小伴 v3.0 — 十年可持续架构核心模块

负责根据年级/年龄自动切换：
- 对话风格（语言复杂度、称呼方式）
- 辅导策略（苏格拉底深度、知识图谱对齐考纲）
- 关注重点（习惯/应试/选科/职业）
- 张雪峰方法论的适配版本
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class LifeStage(Enum):
    """人生阶段枚举 — 小伴陪伴的四大阶段"""
    PRIMARY = "primary"          # 小学 (1-6年级)
    JUNIOR_HIGH = "junior_high"  # 初中 (7-9年级)
    SENIOR_HIGH = "senior_high"  # 高中 (10-12年级)
    UNIVERSITY = "university"    # 大学 (13-16年级，即大一至大四)


@dataclass
class StageConfig:
    """每个阶段的配置参数"""
    stage: LifeStage
    display_name: str
    grade_range: tuple[int, int]  # (最小年级, 最大年级)

    # 对话风格
    language_complexity: str      # simple / moderate / advanced / peer
    address_student_as: str       # 小可爱 / 同学 / 你 / 学弟/学妹
    emoji_allowed: bool

    # 辅导策略
    socratic_depth: int           # 1=浅层引导, 3=深度追问
    homework_focus: str           # 知识点 / 方法论 / 思维框架 / 研究能力
    exam_alignment: str           # 小升初 / 中考 / 高考 / 考研/就业

    # 关注重点
    primary_concern: str
    secondary_concern: str

    # 张雪峰方法论适配
    zhangxuefeng_mode: str        # interest_discovery / exam_strategy / major_selection / career_planning

    # 心理陪伴模式
    psychology_mode: str          # habit_building / puberty_support / pressure_management / adult_transition


# ============================================================
# 四大阶段配置（核心数据）
# ============================================================

STAGE_CONFIGS = {
    LifeStage.PRIMARY: StageConfig(
        stage=LifeStage.PRIMARY,
        display_name="小学阶段",
        grade_range=(1, 6),
        language_complexity="simple",
        address_student_as="小可爱",
        emoji_allowed=True,
        socratic_depth=1,
        homework_focus="知识点理解与习惯养成",
        exam_alignment="小升初",
        primary_concern="学习习惯与基础知识",
        secondary_concern="兴趣发现与自信心建立",
        zhangxuefeng_mode="interest_discovery",
        psychology_mode="habit_building",
    ),
    LifeStage.JUNIOR_HIGH: StageConfig(
        stage=LifeStage.JUNIOR_HIGH,
        display_name="初中阶段",
        grade_range=(7, 9),
        language_complexity="moderate",
        address_student_as="同学",
        emoji_allowed=False,
        socratic_depth=2,
        homework_focus="解题方法与归纳能力",
        exam_alignment="中考",
        primary_concern="中考分流策略与学科均衡",
        secondary_concern="青春期心理建设与抗压能力",
        zhangxuefeng_mode="exam_strategy",
        psychology_mode="puberty_support",
    ),
    LifeStage.SENIOR_HIGH: StageConfig(
        stage=LifeStage.SENIOR_HIGH,
        display_name="高中阶段",
        grade_range=(10, 12),
        language_complexity="advanced",
        address_student_as="你",
        emoji_allowed=False,
        socratic_depth=3,
        homework_focus="高考思维框架与选科深化",
        exam_alignment="高考",
        primary_concern="高考冲刺与志愿填报",
        secondary_concern="强基计划/综合评价与选科策略",
        zhangxuefeng_mode="major_selection",
        psychology_mode="pressure_management",
    ),
    LifeStage.UNIVERSITY: StageConfig(
        stage=LifeStage.UNIVERSITY,
        display_name="大学阶段",
        grade_range=(13, 16),
        language_complexity="peer",
        address_student_as="你",
        emoji_allowed=False,
        socratic_depth=3,
        homework_focus="研究能力与跨学科思维",
        exam_alignment="考研/就业",
        primary_concern="专业深造与职业规划",
        secondary_concern="考研/保研/留学策略与第一份工作",
        zhangxuefeng_mode="career_planning",
        psychology_mode="adult_transition",
    ),
}


class PhaseTransitionEngine:
    """
    阶段跃迁引擎
    
    职责：
    1. 根据年级自动识别当前人生阶段
    2. 检测年级变化并触发阶段跃迁
    3. 为其他引擎提供当前阶段配置
    4. 记录阶段跃迁历史（用于回顾）
    """

    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self._current_stage: Optional[LifeStage] = None
        self._transition_history: list[dict] = []

    def grade_to_stage(self, grade: int) -> LifeStage:
        """将年级映射到人生阶段"""
        if 1 <= grade <= 6:
            return LifeStage.PRIMARY
        elif 7 <= grade <= 9:
            return LifeStage.JUNIOR_HIGH
        elif 10 <= grade <= 12:
            return LifeStage.SENIOR_HIGH
        elif 13 <= grade <= 16:
            return LifeStage.UNIVERSITY
        else:
            raise ValueError(f"无效年级: {grade}，有效范围为 1-16")

    def get_current_config(self, grade: int) -> StageConfig:
        """获取当前年级对应的阶段配置"""
        stage = self.grade_to_stage(grade)
        new_stage = stage

        # 检测阶段跃迁
        if self._current_stage is not None and new_stage != self._current_stage:
            self._record_transition(self._current_stage, new_stage, grade)

        self._current_stage = new_stage
        return STAGE_CONFIGS[stage]

    def _record_transition(self, from_stage: LifeStage, to_stage: LifeStage, grade: int):
        """记录阶段跃迁事件"""
        from datetime import datetime
        record = {
            "timestamp": datetime.now().isoformat(),
            "from_stage": from_stage.value,
            "to_stage": to_stage.value,
            "trigger_grade": grade,
            "message": f"🎉 小可爱完成了从【{STAGE_CONFIGS[from_stage].display_name}】到【{STAGE_CONFIGS[to_stage].display_name}】的跃迁！"
        }
        self._transition_history.append(record)

        # 如果有 MemoryManager，同步写入成长里程碑
        if self.memory_manager:
            self.memory_manager.add_milestone(
                title=f"阶段跃迁：{STAGE_CONFIGS[to_stage].display_name}",
                description=record["message"],
                grade=grade
            )

    def get_transition_history(self) -> list[dict]:
        """获取所有阶段跃迁历史"""
        return self._transition_history

    def generate_stage_briefing(self, grade: int) -> str:
        """为当前阶段生成一份简报（供 LLM System Prompt 注入使用）"""
        config = self.get_current_config(grade)
        briefing = f"""
=== 小伴阶段配置（{config.display_name}，{grade}年级）===
对话风格：{config.language_complexity}，称呼学生为"{config.address_student_as}"
苏格拉底引导深度：{config.socratic_depth}级（{'浅层引导' if config.socratic_depth == 1 else '深度追问' if config.socratic_depth == 3 else '中度引导'}）
辅导重点：{config.homework_focus}
考试对齐：{config.exam_alignment}
核心关注：{config.primary_concern}
次要关注：{config.secondary_concern}
张雪峰模式：{config.zhangxuefeng_mode}
心理陪伴模式：{config.psychology_mode}
""".strip()
        return briefing


# ============================================================
# 快速测试
# ============================================================
if __name__ == "__main__":
    engine = PhaseTransitionEngine()

    test_grades = [6, 7, 9, 10, 12, 13, 16]
    for grade in test_grades:
        config = engine.get_current_config(grade)
        print(f"年级 {grade:2d} → [{config.display_name}] | 关注：{config.primary_concern} | 张雪峰模式：{config.zhangxuefeng_mode}")

    print("\n--- 阶段跃迁历史 ---")
    for t in engine.get_transition_history():
        print(t["message"])

    print("\n--- 当前阶段简报（高一）---")
    print(engine.generate_stage_briefing(10))
