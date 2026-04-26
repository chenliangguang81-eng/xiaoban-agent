"""
小升初规划师技能（北京版）v2.0
针对小可爱：七一小学学籍（海淀）+ 丰台东大街5号院户籍
"""
from engines.llm_core import llm_call, get_llm_router

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
BASE_DIR = Path(__file__).parent.parent
KB_DIR = BASE_DIR / "knowledge_base"


class XiaoshengchuPlanner:
    """小升初规划师（面向对象版）"""

    PATHWAYS = {
        "登记入学": "面向本区学籍学生的登记入学（部分优质校开放少量名额）",
        "公办寄宿": "公办寄宿制学校（全市摇号）",
        "民办校": "民办校电脑派位（全区报名，超额摇号）",
        "一般公办就近登记": "保底兜底路径",
        "特色校/特长生": "艺术、体育、科技特长",
        "单校/多校划片": "按户籍或学籍划片派位",
        "跨区": "海淀→丰台或反之，需满足户籍/工作调动条件",
    }

    def __init__(self, memory_manager=None, kb_dir: Path = None):
        self.memory = memory_manager
        self.kb_dir = kb_dir or KB_DIR
        self.school_db = self._load_school_db()

    def _load_school_db(self) -> dict:
        db_file = self.kb_dir / "schools_database" / "beijing_middle_schools.json"
        if db_file.exists():
            with open(db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_school_db()

    def _default_school_db(self) -> dict:
        """初始数据，需持续补充并写入知识库"""
        return {
            "海淀区": [
                {
                    "name": "人大附中", "tier": "S", "type": "公办",
                    "tags": ["顶级", "竞赛", "国际部"],
                    "entry_paths": ["登记入学(极少)", "特殊途径"],
                    "note": "海淀六小强之首，七一小学学籍可参与海淀派位",
                },
                {
                    "name": "十一学校", "tier": "S", "type": "公办",
                    "tags": ["走班制", "素质教育"],
                    "entry_paths": ["登记入学", "派位"],
                },
                {
                    "name": "北大附中", "tier": "S", "type": "公办",
                    "tags": ["自由氛围", "书院制"],
                    "entry_paths": ["登记入学", "派位"],
                },
                {
                    "name": "清华附中", "tier": "S", "type": "公办",
                    "tags": ["顶级"],
                    "entry_paths": ["登记入学"],
                },
                {
                    "name": "首师大附中", "tier": "A", "type": "公办",
                    "tags": ["海淀六小强"],
                    "entry_paths": ["登记入学", "派位"],
                },
                {
                    "name": "101中学", "tier": "A", "type": "公办",
                    "tags": ["海淀六小强"],
                    "entry_paths": ["登记入学", "派位"],
                },
                {
                    "name": "理工大附中", "tier": "A-", "type": "公办",
                    "entry_paths": ["派位", "登记入学"],
                },
                {
                    "name": "交大附中", "tier": "A-", "type": "公办",
                    "entry_paths": ["派位"],
                },
            ],
            "丰台区": [
                {
                    "name": "北京十二中", "tier": "A", "type": "公办",
                    "tags": ["丰台龙头", "本校区+科丰校区"],
                    "entry_paths": ["单校划片", "多校划片", "登记入学"],
                    "note": "东大街5号院需查划片，属丰台顶级校",
                },
                {
                    "name": "北京十八中", "tier": "A-", "type": "公办",
                    "tags": ["丰台强校"],
                    "entry_paths": ["划片", "登记入学"],
                },
                {
                    "name": "丰台二中", "tier": "B+", "type": "公办",
                    "entry_paths": ["划片"],
                },
                {
                    "name": "北京八中怡海分校", "tier": "B+", "type": "民办",
                    "entry_paths": ["全区摇号"],
                },
                {
                    "name": "首师大附属丽泽中学", "tier": "B", "type": "公办",
                    "entry_paths": ["划片"],
                },
            ],
        }

    def analyze_pathways(self, student_profile: dict = None) -> dict:
        """分析可行的小升初路径"""
        if student_profile is None and self.memory:
            student_profile = self.memory.get_profile()
        if student_profile is None:
            student_profile = {}

        school_district = student_profile.get("school_district", "海淀区")
        home_district = student_profile.get("home_district", "丰台区")

        viable = []

        # 海淀学籍主路径
        if school_district == "海淀区":
            viable.append({
                "pathway": "海淀区登记入学 + 派位",
                "likelihood": "高（默认路径）",
                "detail": "七一小学是海淀学籍，默认参与海淀区小升初派位。"
                          "派位组中优质校比例需查当年政策。",
                "action": "关注海淀区教委每年 5 月发布的《小升初入学工作意见》",
                "key_date": "每年 4-5 月",
            })
            viable.append({
                "pathway": "海淀一般初中校登记入学",
                "likelihood": "中-高",
                "detail": "填报一般初中校可享受'校额到校'政策，"
                          "后续中考有机会降分进入优质高中。",
                "pros": "中考升学路径更宽",
                "cons": "初中三年学习氛围可能不如六小强",
            })

        # 丰台户籍备选路径
        if home_district == "丰台区":
            viable.append({
                "pathway": "跨区回丰台升学",
                "likelihood": "可选（需主动申请）",
                "detail": "学籍在海淀、户籍在丰台，可申请'回户籍区升学'。"
                          "申请后放弃海淀学籍资格。",
                "pros": "丰台竞争相对缓和，十二中、十八中有机会",
                "cons": "放弃海淀优质教育资源，一旦申请不可撤销",
                "action": "4-5 月前决策，向七一小学提交跨区申请",
                "key_date": "每年 4 月底前",
            })

        # 民办路径
        viable.append({
            "pathway": "民办校全区摇号",
            "likelihood": "看运气（补充路径）",
            "detail": "海淀/丰台民办校全区摇号，可作为补充。"
                      "注意民办校学费较高，且学籍锁定。",
        })

        # 特长生
        viable.append({
            "pathway": "科技/艺术/体育特长招生",
            "likelihood": "因人而异",
            "detail": "近年特长生招生名额持续缩减，需核查当年政策。",
            "action": "挖掘小可爱的特长，准备证书和作品集",
        })

        recommended = self._recommend_schools(student_profile)
        action_plan = self._generate_action_plan(student_profile)
        risks = self._identify_risks(student_profile)

        result = {
            "student_summary": {
                "学籍": f"{school_district}七一小学",
                "户籍": f"{home_district}丰台东大街5号院",
                "年级": student_profile.get("grade", "六年级"),
                "关键矛盾": "学籍与户籍跨区，需在海淀 vs 丰台之间做取舍",
                "关键节点": "每年 4-5 月为跨区申请窗口",
            },
            "viable_pathways": viable,
            "recommended_schools": recommended,
            "action_plan": action_plan,
            "risks_and_cautions": risks,
            "generated_at": datetime.now().isoformat(),
            "disclaimer": "政策每年调整，请以当年海淀/丰台教委官方文件为准。",
        }

        # 写入规划记忆
        if self.memory:
            self.memory.save_planning_snapshot("xiaoshengchu", result)

        return result

    def _recommend_schools(self, profile: dict) -> dict:
        """冲稳保三档推荐"""
        chong, wen, bao = [], [], []

        for s in self.school_db.get("海淀区", []):
            if s["tier"] == "S":
                chong.append({**s, "district": "海淀区", "strategy": "冲"})
            elif s["tier"] == "A":
                wen.append({**s, "district": "海淀区", "strategy": "稳"})
            elif s["tier"] == "A-":
                bao.append({**s, "district": "海淀区", "strategy": "保"})

        for s in self.school_db.get("丰台区", []):
            if s["tier"] in ["A", "A-"]:
                wen.append({**s, "district": "丰台区", "strategy": "稳（跨区回丰台）"})
            elif s["tier"] == "B+":
                bao.append({**s, "district": "丰台区", "strategy": "保"})

        return {
            "冲": chong[:3],
            "稳": wen[:4],
            "保": bao[:3],
            "note": "根据小可爱实际学习水平，最终冲稳保名单需动态调整。",
        }

    def _generate_action_plan(self, profile: dict) -> list:
        """生成行动计划（时间线）"""
        return [
            {
                "阶段": "即刻（现在-明年3月）",
                "任务": [
                    "确认七一小学是否在海淀派位组，查清本校对应派位中学列表",
                    "调研东大街5号院在丰台区的划片中学（致电丰台教委或咨询居委会）",
                    "梳理小可爱的特长证书、竞赛获奖（白名单赛事）",
                    "学科查漏补缺：重点抓语文阅读写作、数学应用题、英语词汇量",
                ],
            },
            {
                "阶段": "寒假（2025年1-2月）",
                "任务": [
                    "冲刺班/模考，对齐海淀六小强的实际录取水平",
                    "家长参加目标校开放日、咨询会",
                    "决策：留海淀 vs 回丰台（初步倾向）",
                ],
            },
            {
                "阶段": "政策窗口期（2025年3-5月）",
                "任务": [
                    "3月：关注海淀/丰台教委当年《小升初意见》发布",
                    "4月：最终决策跨区与否，提交申请",
                    "5月：完成登记入学/派位/民办摇号等志愿填报",
                    "5月：参加特长生测试（若走此路径）",
                ],
            },
            {
                "阶段": "录取确认（2025年6-8月）",
                "任务": [
                    "查询派位结果",
                    "若结果不理想，启动备选方案（民办、跨区等）",
                    "暑假：初一预习（数学、英语、物理预热）",
                ],
            },
        ]

    def _identify_risks(self, profile: dict) -> list:
        """风险提示（张雪峰式直率）"""
        return [
            {
                "风险": "海淀派位盲盒",
                "说明": "海淀派位组内学校质量参差不齐，"
                        "可能派到普通校。需提前确认七一小学所在派位组构成。",
            },
            {
                "风险": "跨区决策单向不可逆",
                "说明": "一旦提交跨区回丰台，海淀学籍作废。"
                        "建议务必在 4 月前充分调研丰台目标校划片情况。",
            },
            {
                "风险": "政策年度变动",
                "说明": "北京小升初政策几乎每年调整（如登记入学名额、"
                        "特长生比例、民办摇号规则），必须追踪当年文件。",
            },
            {
                "风险": "民办校学费与学籍锁定",
                "说明": "民办校一旦录取，学籍随校走，跨区转学困难。",
            },
        ]

    def compare_haidian_vs_fengtai(self) -> dict:
        """海淀留守 vs 丰台回流 对比决策表"""
        return {
            "海淀方案": {
                "优势": [
                    "学籍所在地，默认路径最省事",
                    "教育资源全市顶级",
                    "同学圈层层次高",
                    "高中校额到校政策对一般初中校有利",
                ],
                "劣势": [
                    "竞争惨烈，派位有风险",
                    "课外培训成本高",
                    "通勤：丰台居住→海淀上学，每天路上 1-2 小时",
                ],
                "适合条件": "孩子学习能力强、家长能支持高强度学习",
            },
            "丰台方案": {
                "优势": [
                    "通勤方便，就近入学",
                    "十二中、十八中在丰台属顶级，竞争相对缓和",
                    "相对更容易在区内脱颖而出（中考排名）",
                ],
                "劣势": [
                    "整体教育资源不如海淀",
                    "需主动申请跨区，不可逆",
                    "初中同学圈层不如海淀",
                ],
                "适合条件": "看重通勤、希望孩子在相对宽松环境成长",
            },
            "建议决策顺序": [
                "先查东大街5号院的丰台划片中学是哪几所",
                "再查七一小学对应的海淀派位组构成",
                "对比两个'最坏情况'——哪个能接受就选哪条路",
            ],
        }

    def format_analysis_for_parent(self, analysis: dict) -> str:
        """将分析结果格式化为家长可读的 Markdown 报告"""
        lines = ["# 小升初路径分析报告\n"]
        lines.append(f"> 生成时间：{analysis.get('generated_at', '')[:10]}")
        lines.append(f"> ⚠️ {analysis.get('disclaimer', '')}\n")

        summary = analysis.get("student_summary", {})
        lines.append("## 学生情况摘要\n")
        lines.append("| 项目 | 内容 |")
        lines.append("|---|---|")
        for k, v in summary.items():
            lines.append(f"| {k} | {v} |")

        lines.append("\n## 可行路径\n")
        for i, p in enumerate(analysis.get("viable_pathways", []), 1):
            lines.append(f"### {i}. {p['pathway']} — {p.get('likelihood', '')}")
            lines.append(p.get("detail", ""))
            if p.get("pros"):
                lines.append(f"**优点**：{p['pros']}")
            if p.get("cons"):
                lines.append(f"**缺点**：{p['cons']}")
            if p.get("action"):
                lines.append(f"**行动项**：{p['action']}")
            lines.append("")

        lines.append("## 冲稳保学校推荐\n")
        rec = analysis.get("recommended_schools", {})
        for tier in ["冲", "稳", "保"]:
            schools = rec.get(tier, [])
            if schools:
                lines.append(f"**{tier}**：" + "、".join([s["name"] for s in schools]))
        lines.append(f"\n> {rec.get('note', '')}\n")

        lines.append("## 风险提示\n")
        for risk in analysis.get("risks_and_cautions", []):
            lines.append(f"**⚠️ {risk['风险']}**：{risk['说明']}\n")

        return "\n".join(lines)


# ── 函数式接口（向后兼容） ────────────────────────────────────────────────────

def analyze_path(query: str, extra_context: str = "", memory_manager=None) -> str:
    """函数式接口，供主调度 Agent 调用"""
    planner = XiaoshengchuPlanner(memory_manager=memory_manager)

    # 如果有 memory_manager，获取学生档案
    if memory_manager:
        profile = memory_manager.get_profile()
        analysis = planner.analyze_pathways(profile)
        report = planner.format_analysis_for_parent(analysis)
    else:
        # 降级到 LLM 直接回答
        messages = [
            {"role": "system", "content": "你是北京小升初规划专家，专注于海淀学籍+丰台户籍的特殊情况分析。"},
            {"role": "user", "content": f"家长咨询：{query}\n补充背景：{extra_context}"}
        ]
        # [v5.2 Manus迁移] 统一路由器调用
        _llm_sys_resp = next((x['content'] for x in messages if x['role']=='system'), '')
        _llm_usr_resp = next((x['content'] for x in reversed(messages) if x['role']=='user'), '')
        _llm_hist_resp = [x for x in messages if x['role'] not in ('system',)][:-1]
        resp_reply = llm_call(_llm_usr_resp, _llm_sys_resp, _llm_hist_resp)
        report = resp_reply.strip()

    return report


def get_timeline() -> list:
    """返回小升初关键时间节点"""
    return [
        {"month": "每年1-2月", "action": "关注海淀/丰台区教委发布小升初政策通知"},
        {"month": "每年3月", "action": "民办校报名窗口（通常3月中旬开放）"},
        {"month": "每年4月", "action": "特长生报名与测试；跨区申请截止"},
        {"month": "每年5月", "action": "电脑派位（公办）；志愿填报"},
        {"month": "每年6月", "action": "录取结果公示，确认入学学校"},
        {"month": "当前（六年级上学期）", "action": "确认户籍/学籍信息，研究目标学校，准备特长材料"},
    ]
