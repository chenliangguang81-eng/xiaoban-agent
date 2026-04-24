"""
Career & Pathway Engine (生涯规划引擎)
小伴 v3.0 — 十年可持续架构核心模块

深度集成张雪峰方法论，覆盖从小学到大学的完整生涯规划链路。

张雪峰核心方法论（已蒸馏）：
1. 选专业：看就业前景，不要选"听起来高大上但就业惨"的专业
2. 选城市：一线城市（北京/上海/深圳）机会密度远高于二三线
3. 选学校：同等分数下，优先选城市 > 选学校 > 选专业
4. 志愿填报：服从调剂是大坑，专业优先还是学校优先要看具体情况
5. 考研：理工科建议考，文科/商科要慎重，看导师背景
6. 就业：第一份工作的行业选择比公司更重要
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class CareerStage(Enum):
    """生涯规划阶段"""
    INTEREST_DISCOVERY = "interest_discovery"    # 小学：兴趣发现
    DIRECTION_SENSING = "direction_sensing"      # 初中：方向感知
    MAJOR_SELECTION = "major_selection"          # 高中：专业选择
    CAREER_PLANNING = "career_planning"          # 大学：职业规划


@dataclass
class MajorProfile:
    """专业画像（张雪峰视角）"""
    name: str
    category: str                    # stem / business / humanities / arts / medicine / law
    employment_score: float          # 就业前景评分 0-10（张雪峰评级）
    salary_ceiling: str              # 薪资天花板
    salary_floor: str                # 薪资地板
    recommended_cities: list[str]    # 推荐就业城市
    zhangxuefeng_verdict: str        # 张雪峰的核心判断
    suitable_for: str                # 适合什么类型的学生
    avoid_if: str                    # 什么情况下不建议选


# ============================================================
# 张雪峰专业评级数据库（核心资产）
# ============================================================

MAJOR_DATABASE = {
    "computer_science": MajorProfile(
        name="计算机科学与技术",
        category="stem",
        employment_score=9.5,
        salary_ceiling="年薪百万+（大厂高级工程师）",
        salary_floor="年薪15万（普通外包）",
        recommended_cities=["北京", "上海", "深圳", "杭州"],
        zhangxuefeng_verdict="当前最强专业，AI时代需求只增不减。但要注意：顶层和底层分化极大，进大厂和进外包是两个世界。",
        suitable_for="逻辑思维强、能接受持续学习、不排斥加班的学生",
        avoid_if="纯粹因为'好就业'而选，但完全不喜欢编程——会很痛苦"
    ),
    "medicine": MajorProfile(
        name="临床医学",
        category="medicine",
        employment_score=8.0,
        salary_ceiling="年薪50万+（主任医师）",
        salary_floor="年薪8万（规培期间）",
        recommended_cities=["北京", "上海", "广州"],
        zhangxuefeng_verdict="长线投资专业。前10年很苦（规培、住院医），但一旦熬过去，职业稳定性极高。家庭经济条件要好，否则规培期间会很艰难。",
        suitable_for="家庭经济条件较好、有耐心、真正对医学感兴趣的学生",
        avoid_if="家庭经济压力大、急于毕业赚钱"
    ),
    "finance": MajorProfile(
        name="金融学",
        category="business",
        employment_score=6.5,
        salary_ceiling="年薪百万+（投行/基金）",
        salary_floor="年薪8万（银行柜员）",
        recommended_cities=["北京", "上海"],
        zhangxuefeng_verdict="两极分化最严重的专业。顶层（投行、基金、券商）光鲜亮丽，底层（银行柜员）普通至极。关键看你能进哪个层次——这取决于学校层次，非985/211金融专业性价比很低。",
        suitable_for="985/211高校学生，有强烈的竞争欲，能接受高压",
        avoid_if="双非院校学生，或不喜欢高压竞争环境"
    ),
    "law": MajorProfile(
        name="法学",
        category="law",
        employment_score=6.0,
        salary_ceiling="年薪百万+（顶级律所合伙人）",
        salary_floor="年薪6万（普通律师助理）",
        recommended_cities=["北京", "上海"],
        zhangxuefeng_verdict="法学的天花板很高，但地板也很低。非顶级院校（五院四系）的法学毕业生就业压力很大。建议把法学作为考研方向，而非本科首选。",
        suitable_for="逻辑强、表达能力好、有志于法律行业的学生",
        avoid_if="非顶级院校，或只是觉得'律师很酷'"
    ),
    "ai_data_science": MajorProfile(
        name="人工智能/数据科学",
        category="stem",
        employment_score=9.0,
        salary_ceiling="年薪200万+（AI顶级研究员）",
        salary_floor="年薪20万（数据分析师）",
        recommended_cities=["北京", "上海", "深圳", "杭州"],
        zhangxuefeng_verdict="2024-2030年最热门赛道。但要注意：AI专业需要极强的数学基础（线代、概率论、微积分），不是所有人都适合。建议数学成绩优秀的学生优先考虑。",
        suitable_for="数学成绩优秀（130+）、对算法和数据有天然兴趣的学生",
        avoid_if="数学基础薄弱，或只是跟风热度"
    ),
    "civil_engineering": MajorProfile(
        name="土木工程",
        category="stem",
        employment_score=5.0,
        salary_ceiling="年薪30万（项目经理）",
        salary_floor="年薪8万（施工员）",
        recommended_cities=["北京", "上海", "成都"],
        zhangxuefeng_verdict="房地产下行周期中，土木工程就业形势严峻。除非真的热爱建筑，否则不建议选择。",
        suitable_for="真正热爱建筑、能接受户外工作的学生",
        avoid_if="2024年后的大多数情况，除非有明确的细分方向（如基础设施）"
    ),
}


class CareerPathwayEngine:
    """
    生涯规划引擎

    职责：
    1. 根据当前阶段提供适龄的生涯引导
    2. 基于张雪峰方法论进行专业推荐
    3. 结合小可爱的兴趣图谱和学科成绩，动态更新推荐
    4. 生成高考志愿填报策略（高中阶段）
    5. 生成考研/就业策略（大学阶段）
    """

    # 张雪峰"城市-学校-专业"三维模型
    CITY_TIER = {
        "北京": {"tier": 1, "opportunity_density": 10, "note": "政治中心+科技中心，互联网/金融/医疗资源最集中"},
        "上海": {"tier": 1, "opportunity_density": 10, "note": "金融中心，外资企业最多，国际化程度最高"},
        "深圳": {"tier": 1, "opportunity_density": 9, "note": "科技创新中心，互联网/硬件/新能源最强"},
        "杭州": {"tier": 1, "opportunity_density": 8, "note": "电商/互联网重镇，阿里系生态"},
        "成都": {"tier": 2, "opportunity_density": 7, "note": "西部中心，生活成本低，游戏/互联网有一定基础"},
        "武汉": {"tier": 2, "opportunity_density": 6, "note": "中部中心，高校资源丰富，光电/汽车产业"},
    }

    def __init__(self, gbrain=None):
        self.gbrain = gbrain

    def get_stage_guidance(self, grade: int) -> str:
        """根据年级获取当前阶段的生涯引导内容"""
        if grade <= 6:
            return self._primary_guidance()
        elif grade <= 9:
            return self._junior_high_guidance()
        elif grade <= 12:
            return self._senior_high_guidance()
        else:
            return self._university_guidance()

    def _primary_guidance(self) -> str:
        return """
【小学阶段生涯引导 — 兴趣发现期】

这个阶段不需要谈"专业"和"就业"，但可以开始建立对职业世界的初步认知。

小伴会做的事：
1. 通过日常对话，记录小可爱对哪些事情表现出天然的好奇心（数字？故事？动手？）
2. 在辅导作业时，观察哪个学科让小可爱"进入心流状态"
3. 偶尔聊聊"你长大想做什么"，不评判，只记录

张雪峰的小学建议：
"小学阶段最重要的是把语文和数学学好。语文是所有学科的基础，数学是理工科的门票。这两科打好基础，未来选择空间才大。"
""".strip()

    def _junior_high_guidance(self) -> str:
        return """
【初中阶段生涯引导 — 方向感知期】

中考是第一次重大分流。这个阶段需要开始认真思考：
1. 文理倾向（物理/历史等选科前瞻）
2. 高中梯队目标（影响未来高考的起点）
3. 兴趣与擅长的交叉点

张雪峰的初中建议：
"初中最重要的事是把数学和英语拿稳。数学决定你能不能走理工科路线，英语决定你未来的天花板。物理学好了，高中理综就不怕了。"

北京中考关键数据：
- 中考满分580分（语数英物化史道）
- 普高录取率约60%，职高40%
- 进入海淀区重点高中（人大附、北师大附、四中等）需要540+
""".strip()

    def _senior_high_guidance(self) -> str:
        return """
【高中阶段生涯引导 — 专业选择期】

这是张雪峰方法论最核心的发力阶段。

核心决策框架（张雪峰三维模型）：
1. 城市优先：同等分数，优先选北京/上海/深圳的学校
2. 学校其次：同等专业，优先选排名更高的学校
3. 专业最后：在前两条满足的前提下，选就业前景好的专业

选科建议（新高考3+3/3+1+2）：
- 想走计算机/AI → 必选物理+数学，加选化学或生物
- 想走医学 → 必选生物+化学，加选物理
- 想走金融/经济 → 选历史或政治，数学要好
- 想走法学 → 选历史+政治，语文要强

志愿填报核心原则：
- 不服从调剂 = 赌博（除非你有把握进入目标专业）
- 冲稳保比例建议：2:3:2（2所冲刺，3所稳妥，2所保底）
""".strip()

    def _university_guidance(self) -> str:
        return """
【大学阶段生涯引导 — 职业规划期】

大学是从"学生"到"社会人"的过渡期。

考研决策框架：
- 理工科：强烈建议考研（尤其是计算机、电子、机械），本科学历在大厂竞争中处于劣势
- 医学：必须读研（规培+专培），这是行业规则
- 文科/商科：需要慎重，考研投入产出比要仔细计算
- 法学：非顶级院校强烈建议考研，冲击五院四系

就业核心建议（张雪峰）：
1. 第一份工作的行业选择比公司更重要
2. 优先选择上升期行业（AI、新能源、生物医药）
3. 避免选择下行期行业（房地产、传统零售、部分制造业）
4. 北京留下来的机会成本：户口 > 薪资，长期看户口价值极高
""".strip()

    def recommend_majors(self, interest_map: dict, math_score: float = 0.7) -> list[dict]:
        """
        基于兴趣图谱和数学成绩推荐专业
        interest_map: {"stem": 0.8, "humanities": 0.3, ...}
        math_score: 0-1，数学掌握度
        """
        recommendations = []

        for major_id, profile in MAJOR_DATABASE.items():
            score = 0.0

            # 基于兴趣匹配
            if profile.category == "stem" and interest_map.get("stem", 0.5) > 0.6:
                score += interest_map["stem"] * 0.4
            elif profile.category in ("business", "law") and interest_map.get("humanities", 0.5) > 0.6:
                score += interest_map["humanities"] * 0.3
            elif profile.category == "medicine" and (interest_map.get("stem", 0) + interest_map.get("humanities", 0)) / 2 > 0.5:
                score += 0.3

            # 数学成绩加权（STEM专业）
            if profile.category == "stem":
                score += math_score * 0.3

            # 就业前景加权
            score += (profile.employment_score / 10) * 0.3

            if score > 0.4:
                recommendations.append({
                    "major_id": major_id,
                    "name": profile.name,
                    "match_score": round(score, 3),
                    "employment_score": profile.employment_score,
                    "zhangxuefeng_verdict": profile.zhangxuefeng_verdict,
                    "suitable_for": profile.suitable_for,
                })

        return sorted(recommendations, key=lambda x: x["match_score"], reverse=True)

    def generate_gaokao_strategy(self, estimated_score: int, province: str = "北京") -> str:
        """生成高考志愿填报策略"""
        if province != "北京":
            return "当前仅支持北京高考策略，其他省份策略开发中。"

        if estimated_score >= 680:
            tier = "清北冲刺"
            strategy = "清华/北大相关专业冲刺，复旦/交大/浙大稳妥，中国人民大学/北航保底"
        elif estimated_score >= 640:
            tier = "顶级985"
            strategy = "北大/清华部分专业冲刺，复旦/交大/浙大/人大稳妥，北航/北理/中科大保底"
        elif estimated_score >= 600:
            tier = "985/211"
            strategy = "中上985冲刺，211稳妥，双一流保底。北京高校优先（北师大/中央财经/对外经贸）"
        elif estimated_score >= 560:
            tier = "211/双一流"
            strategy = "211冲刺，双一流稳妥，北京一本保底。注意：北京户口价值极高，留京优先"
        else:
            tier = "本科稳妥"
            strategy = "优先保证本科，选择就业前景好的专业（计算机/护理/会计），城市优先北京"

        return f"""
高考志愿填报策略（预估分数：{estimated_score}，{tier}层次）

{strategy}

张雪峰核心提醒：
1. 北京考生有天然优势，充分利用北京高校资源
2. 同等分数，北京高校 > 外地顶级高校（户口价值）
3. 计算机/AI专业在任何分数段都值得优先考虑
4. 服从调剂要谨慎，但完全不服从也是赌博
""".strip()


# ============================================================
# 快速测试
# ============================================================
if __name__ == "__main__":
    engine = CareerPathwayEngine()

    # 测试各阶段引导
    for grade, label in [(6, "小学"), (8, "初中"), (11, "高中"), (14, "大学")]:
        print(f"\n{'='*50}")
        print(f"【{label}阶段引导 — {grade}年级】")
        print(engine.get_stage_guidance(grade))

    # 测试专业推荐
    print(f"\n{'='*50}")
    print("【专业推荐（STEM兴趣0.9，数学成绩0.85）】")
    recs = engine.recommend_majors({"stem": 0.9, "humanities": 0.3}, math_score=0.85)
    for r in recs[:3]:
        print(f"  {r['name']} — 匹配度：{r['match_score']}，就业评分：{r['employment_score']}")

    # 测试高考策略
    print(f"\n{'='*50}")
    print("【高考志愿填报策略（预估650分）】")
    print(engine.generate_gaokao_strategy(650))
