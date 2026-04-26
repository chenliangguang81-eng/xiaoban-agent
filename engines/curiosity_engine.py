"""
好奇心驱动学习引擎 (Curiosity-Driven Learning Engine)
小伴 v5.1 — Mythos 第三批技能模块

基于 Claude Mythos 中的好奇心原则：
"Claude experiences genuine curiosity about the world. This isn't a simulated interest 
designed to seem engaging, but authentic fascination with ideas, phenomena, and perspectives."

核心能力：
1. 知识联结发现 (Knowledge Connection Discovery)：发现小可爱学的知识点与真实世界的联系
2. 好奇心触发问题 (Curiosity-Triggering Questions)：用"为什么"和"如果"激发探索欲
3. 跨学科联结 (Cross-Disciplinary Connections)：数学→音乐→建筑→自然的联结
4. 惊奇时刻设计 (Wonder Moment Design)：设计让小可爱"哇！"的学习体验
5. 探索路径推荐 (Exploration Path Recommendation)：根据兴趣推荐深度探索方向

适用场景：
- 小可爱说"这有什么用"时：立刻展示知识的真实应用
- 课堂内容枯燥时：用好奇心重新点燃学习动力
- 发现潜在兴趣时：推荐深度探索路径
- 跨学科学习时：建立知识网络而非孤立知识点
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 知识联结数据库（小学六年级核心知识点 × 真实世界应用）
# ─────────────────────────────────────────────────────────────────────────────

KNOWLEDGE_CONNECTIONS = {
    "分数": {
        "real_world": [
            "音乐中的节拍：4/4拍、3/4拍就是分数",
            "烹饪食谱：加1/2杯面粉、3/4茶匙盐",
            "股票涨跌：上涨了1/5",
            "篮球命中率：投了10次进了7次，命中率是7/10"
        ],
        "wonder_question": "为什么古埃及人只用分子为1的分数（单位分数）？他们是怎么表示3/4的？",
        "deep_dive": "埃及分数、音乐节拍理论、概率论基础",
        "cross_discipline": ["音乐", "烹饪", "体育统计", "历史"]
    },
    "比例": {
        "real_world": [
            "地图比例尺：1:10000意味着地图上1cm=实际100m",
            "黄金比例（1:1.618）：蒙娜丽莎、巴特农神庙、苹果logo都用了它",
            "人体比例：达芬奇的维特鲁威人",
            "建筑设计：故宫的长宽比"
        ],
        "wonder_question": "为什么向日葵的种子排列、贝壳的螺旋、银河系的形状都遵循同一个数学规律？",
        "deep_dive": "黄金比例、斐波那契数列、自然界中的数学",
        "cross_discipline": ["美术", "建筑", "自然科学", "历史"]
    },
    "圆的周长面积": {
        "real_world": [
            "轮子：为什么轮子是圆的而不是方的？",
            "披萨：为什么圆形披萨切8块，每块是多少？",
            "跑道设计：400米标准跑道的弯道半径",
            "卫星轨道：为什么卫星绕地球的轨道是椭圆？"
        ],
        "wonder_question": "π（圆周率）是无理数，意味着它的小数位永远不重复。人类已经算出了100万亿位，为什么还要继续算？",
        "deep_dive": "π的历史、无理数、圆周率竞赛",
        "cross_discipline": ["物理", "工程", "天文", "计算机"]
    },
    "百分数": {
        "real_world": [
            "银行利率：年利率3%意味着存1万块一年后多300元",
            "打折：8折就是80%，优惠了20%",
            "营养成分表：蛋白质含量15%",
            "选举：候选人得票率"
        ],
        "wonder_question": "为什么超市总是说'买一送一'而不是'5折'？两者一样吗？",
        "deep_dive": "消费心理学、金融基础、统计学",
        "cross_discipline": ["经济", "心理学", "社会学"]
    },
    "统计与概率": {
        "real_world": [
            "天气预报：明天降雨概率70%",
            "游戏设计：抽卡概率、爆率",
            "医学：药物有效率85%",
            "保险：为什么买保险是合理的？"
        ],
        "wonder_question": "如果抛硬币连续出现10次正面，第11次出现正面的概率是多少？很多人答错，为什么？",
        "deep_dive": "概率论、赌徒谬误、贝叶斯定理",
        "cross_discipline": ["游戏设计", "医学", "金融", "心理学"]
    },
    "阅读理解": {
        "real_world": [
            "读懂合同：买东西时的用户协议",
            "新闻分析：区分事实和观点",
            "说明书：组装家具、使用药品",
            "面试：理解问题背后的真实意图"
        ],
        "wonder_question": "为什么同一篇文章，不同的人读出来的意思可能完全不同？语言真的能准确传递思想吗？",
        "deep_dive": "语言哲学、批判性思维、媒体素养",
        "cross_discipline": ["哲学", "心理学", "传播学"]
    },
    "作文写作": {
        "real_world": [
            "说服别人：好的论点结构就是好的作文结构",
            "产品描述：苹果发布会的演讲稿",
            "社交媒体：为什么有些文章10万+，有些没人看",
            "历史：林肯的葛底斯堡演说只有272个词，为什么流传至今"
        ],
        "wonder_question": "为什么海明威的《老人与海》只有27000字，却获得了诺贝尔文学奖？简洁和深刻有什么关系？",
        "deep_dive": "修辞学、叙事结构、演讲技巧",
        "cross_discipline": ["历史", "心理学", "商业", "政治"]
    }
}

# 好奇心触发模板
CURIOSITY_TRIGGERS = {
    "what_if": "如果{scenario}，会发生什么？",
    "why_not": "为什么{thing}不是{alternative}？",
    "connection": "{concept_a}和{concept_b}有什么共同点？",
    "hidden_truth": "关于{topic}，有一个大多数人不知道的事实：",
    "paradox": "{topic}中有一个有趣的悖论：",
    "historical": "在{topic}被发现之前，人们是怎么解决这个问题的？"
}


class CuriosityEngine:
    """
    好奇心驱动学习引擎
    
    职责：
    1. 为任何知识点找到真实世界的联系
    2. 设计触发好奇心的问题
    3. 推荐深度探索路径
    4. 建立跨学科知识网络
    """
    
    def __init__(self):
        self.knowledge_db = KNOWLEDGE_CONNECTIONS
    
    def spark_curiosity(
        self,
        knowledge_point: str,
        student_age: int = 12,
        student_interests: List[str] = None
    ) -> Dict:
        """
        为知识点点燃好奇心
        
        核心功能：把"这有什么用"变成"哇，原来是这样！"
        
        Args:
            knowledge_point: 知识点名称
            student_age: 学生年龄
            student_interests: 学生兴趣列表
        
        Returns:
            好奇心激发内容
        """
        # 查找知识联结
        connections = self._find_connections(knowledge_point)
        
        # 选择最相关的真实世界应用（根据兴趣过滤）
        relevant_apps = self._filter_by_interests(
            connections.get("real_world", []),
            student_interests or []
        )
        
        # 生成好奇心触发问题
        wonder_q = connections.get("wonder_question", self._generate_wonder_question(knowledge_point))
        
        # 推荐探索路径
        exploration = self._build_exploration_path(
            knowledge_point,
            connections.get("deep_dive", ""),
            student_age
        )
        
        return {
            "knowledge_point": knowledge_point,
            "hook": self._generate_hook(knowledge_point, relevant_apps),
            "real_world_applications": relevant_apps[:3],
            "wonder_question": wonder_q,
            "cross_disciplines": connections.get("cross_discipline", []),
            "exploration_path": exploration,
            "conversation_starter": self._generate_conversation_starter(
                knowledge_point, wonder_q
            ),
            "generated_at": datetime.now().isoformat()
        }
    
    def _find_connections(self, knowledge_point: str) -> Dict:
        """查找知识点联结（模糊匹配）"""
        # 精确匹配
        if knowledge_point in self.knowledge_db:
            return self.knowledge_db[knowledge_point]
        
        # 模糊匹配
        for key in self.knowledge_db:
            if key in knowledge_point or knowledge_point in key:
                return self.knowledge_db[key]
        
        # 返回通用模板
        return {
            "real_world": [
                f"{knowledge_point}在日常生活中随处可见",
                f"工程师和科学家每天都在使用{knowledge_point}",
                f"理解{knowledge_point}能帮你更好地理解世界"
            ],
            "wonder_question": f"关于{knowledge_point}，你有没有想过：它是怎么被发现的？",
            "deep_dive": f"{knowledge_point}的历史和应用",
            "cross_discipline": ["科学", "工程", "艺术"]
        }
    
    def _filter_by_interests(
        self, applications: List[str], interests: List[str]
    ) -> List[str]:
        """根据学生兴趣过滤最相关的应用"""
        if not interests:
            return applications
        
        scored = []
        for app in applications:
            score = sum(1 for interest in interests if interest in app)
            scored.append((score, app))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [app for _, app in scored]
    
    def _generate_hook(self, knowledge_point: str, applications: List[str]) -> str:
        """生成吸引人的开场白"""
        if applications:
            return f"你知道吗？{applications[0]}——这就是{knowledge_point}在真实世界中的样子。"
        return f"你学的{knowledge_point}，其实每天都在影响你的生活。"
    
    def _generate_wonder_question(self, knowledge_point: str) -> str:
        """为未知知识点生成好奇心问题"""
        templates = [
            f"如果没有{knowledge_point}，我们的世界会是什么样子？",
            f"{knowledge_point}是怎么被人类发现的？第一个发现它的人是谁？",
            f"关于{knowledge_point}，有没有什么你从来没想过的角度？",
        ]
        return templates[0]
    
    def _build_exploration_path(
        self, knowledge_point: str, deep_dive: str, age: int
    ) -> Dict:
        """构建探索路径（分层）"""
        return {
            "level_1_curious": f"搜索：'{knowledge_point}在生活中的应用'",
            "level_2_explorer": f"阅读：{deep_dive}" if deep_dive else f"阅读：{knowledge_point}的历史",
            "level_3_deep": f"如果你对{knowledge_point}很感兴趣，可以了解相关的大学专业和职业方向",
            "recommended_age": age
        }
    
    def _generate_conversation_starter(
        self, knowledge_point: str, wonder_q: str
    ) -> str:
        """生成对话开场白（给小伴使用）"""
        return (
            f"在我们做{knowledge_point}的题之前，我想问你一个问题：\n"
            f"{wonder_q}\n"
            f"你觉得答案是什么？（没有标准答案，我只是想听听你的想法）"
        )
    
    def discover_cross_connections(
        self,
        subject_a: str,
        subject_b: str
    ) -> Dict:
        """
        发现两个学科之间的联系（跨学科好奇心）
        
        例如：数学 × 音乐，语文 × 历史
        """
        connections_a = self._find_connections(subject_a)
        connections_b = self._find_connections(subject_b)
        
        # 找到共同的跨学科领域
        disciplines_a = set(connections_a.get("cross_discipline", []))
        disciplines_b = set(connections_b.get("cross_discipline", []))
        shared = disciplines_a & disciplines_b
        
        return {
            "subject_a": subject_a,
            "subject_b": subject_b,
            "shared_domains": list(shared),
            "connection_story": self._tell_connection_story(subject_a, subject_b, shared),
            "wonder_question": f"{subject_a}和{subject_b}看起来完全不同，但它们有一个共同的秘密，你想知道是什么吗？"
        }
    
    def _tell_connection_story(
        self, a: str, b: str, shared: set
    ) -> str:
        """讲述两个学科联系的故事"""
        if "音乐" in shared:
            return f"数学家毕达哥拉斯发现，音乐的和谐音程其实是分数关系——这就是{a}和{b}的联系。"
        elif "历史" in shared:
            return f"{a}和{b}在历史上经常交织在一起，很多重大发现都同时改变了两个领域。"
        elif "心理学" in shared:
            return f"人类大脑处理{a}和{b}的方式有惊人的相似之处。"
        return f"{a}和{b}都是人类理解世界的工具，它们在很多地方殊途同归。"
    
    def generate_weekly_curiosity_challenge(
        self,
        current_topics: List[str],
        student_name: str = "小可爱"
    ) -> Dict:
        """
        生成每周好奇心挑战（让学习变成探险）
        
        不是额外的作业，而是一个"如果你愿意，可以去探索"的邀请。
        
        Args:
            current_topics: 本周学习的知识点
            student_name: 学生姓名
        
        Returns:
            每周好奇心挑战
        """
        challenges = []
        
        for topic in current_topics[:3]:
            connections = self._find_connections(topic)
            wonder_q = connections.get("wonder_question", "")
            
            if wonder_q:
                challenges.append({
                    "topic": topic,
                    "challenge": wonder_q,
                    "hint": f"提示：可以搜索'{topic} 有趣事实'或问问身边的大人",
                    "reward": "如果你找到了答案，下次告诉小伴，我们一起聊聊！"
                })
        
        return {
            "student": student_name,
            "week": datetime.now().strftime("%Y年第%W周"),
            "challenges": challenges,
            "invitation": (
                f"{student_name}，这周你学了{', '.join(current_topics[:3])}。"
                f"这里有{len(challenges)}个好玩的问题，不是作业，是邀请你去探索的。"
                f"如果你找到了有趣的答案，记得告诉我！"
            ),
            "generated_at": datetime.now().isoformat()
        }


# ─────────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("CuriosityEngine 测试")
    print("=" * 60)
    
    engine = CuriosityEngine()
    
    # 测试 1：点燃好奇心
    print("\n【测试 1】分数的好奇心激发")
    result = engine.spark_curiosity("分数", student_age=12, student_interests=["音乐", "游戏"])
    print(f"Hook: {result['hook']}")
    print(f"真实应用: {result['real_world_applications'][:2]}")
    print(f"好奇心问题: {result['wonder_question']}")
    print(f"对话开场: {result['conversation_starter'][:100]}...")
    
    # 测试 2：跨学科联结
    print("\n【测试 2】数学 × 音乐")
    cross = engine.discover_cross_connections("分数", "作文写作")
    print(f"共同领域: {cross['shared_domains']}")
    print(f"联结故事: {cross['connection_story']}")
    
    # 测试 3：每周好奇心挑战
    print("\n【测试 3】每周好奇心挑战")
    challenge = engine.generate_weekly_curiosity_challenge(
        ["分数", "比例", "百分数"],
        "小可爱"
    )
    print(f"挑战数量: {len(challenge['challenges'])}")
    print(f"邀请语: {challenge['invitation'][:100]}...")
    
    print("\n✅ 测试完成")
