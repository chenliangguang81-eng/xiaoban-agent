"""
小升初备考时间轴引擎 (Xiaoshengchu Timeline Engine)
小伴 v3.2 — 小升初增强技能包

基于北京小升初的年度固定节奏，为六年级学生生成动态的、
精确到月的备考与政策关注时间轴。
"""

from datetime import datetime
from typing import List, Dict

class XiaoshengchuTimelineEngine:
    """小升初备考时间轴引擎"""
    
    # 北京小升初标准时间线 (六年级)
    STANDARD_TIMELINE = [
        {
            "month": 9,
            "phase": "六年级上学期开学",
            "focus": "学业冲刺与信息收集",
            "tasks": [
                "梳理小学阶段所有荣誉证书、特长证明",
                "关注目标初中（如五十七中、交大附中）的开放日信息",
                "保持校内成绩稳定，尤其是五六年级的期末成绩"
            ]
        },
        {
            "month": 11,
            "phase": "期中考试后",
            "focus": "定位与查漏补缺",
            "tasks": [
                "根据期中成绩，初步圈定'冲、稳、保'目标校",
                "针对薄弱学科（如数学附加题、英语阅读）进行专项提升"
            ]
        },
        {
            "month": 1,
            "phase": "寒假前/期末考试",
            "focus": "关键成绩锁定",
            "tasks": [
                "六年级上学期期末成绩非常重要，部分学校点招会参考",
                "利用寒假时间，集中攻克难点，或准备面试（如1+3项目）"
            ]
        },
        {
            "month": 3,
            "phase": "六年级下学期开学",
            "focus": "政策预热与跨区决策",
            "tasks": [
                "密切关注海淀/丰台教委即将发布的当年小升初政策",
                "【关键决策】如果考虑跨区（海淀回丰台），需在4月前做出最终决定"
            ]
        },
        {
            "month": 4,
            "phase": "政策发布月",
            "focus": "政策解读与信息核对",
            "tasks": [
                "研读当年《义务教育阶段入学工作意见》",
                "核对七一小学所在派位组的学校名单是否有变动",
                "办理跨区手续（如需）"
            ]
        },
        {
            "month": 5,
            "phase": "志愿填报月",
            "focus": "志愿填报与特长生测试",
            "tasks": [
                "完成一派（登记入学）、二派（派位）志愿填报",
                "参加特长生/特色校的专业测试（如有）",
                "民办校摇号报名"
            ]
        },
        {
            "month": 6,
            "phase": "录取与毕业",
            "focus": "结果查询与初小衔接",
            "tasks": [
                "查询各批次录取结果",
                "领取初中录取通知书",
                "开始初一预习（数学、英语为主）"
            ]
        }
    ]

    def __init__(self):
        pass

    def generate_current_action_items(self, current_date: datetime = None) -> Dict:
        """根据当前日期，生成当月及下月的核心行动项"""
        if current_date is None:
            current_date = datetime.now()
            
        current_month = current_date.month
        
        # 找到当前月份或最近的下一个关键节点
        current_phase = None
        next_phase = None
        
        # 简单排序逻辑 (9, 11, 1, 3, 4, 5, 6)
        # 转换为学年月份排序 (9=1, 11=3, 1=5, 3=7, 4=8, 5=9, 6=10)
        def month_to_school_year_order(m):
            return m if m >= 9 else m + 12
            
        sorted_timeline = sorted(self.STANDARD_TIMELINE, key=lambda x: month_to_school_year_order(x["month"]))
        
        for i, phase in enumerate(sorted_timeline):
            if month_to_school_year_order(phase["month"]) >= month_to_school_year_order(current_month):
                current_phase = phase
                if i + 1 < len(sorted_timeline):
                    next_phase = sorted_timeline[i + 1]
                break
                
        if not current_phase:
            # 如果当前是7、8月，显示9月的计划
            current_phase = sorted_timeline[0]
            next_phase = sorted_timeline[1]
            
        return {
            "current_date": current_date.strftime("%Y-%m-%d"),
            "current_focus": current_phase,
            "upcoming_focus": next_phase
        }

if __name__ == "__main__":
    engine = XiaoshengchuTimelineEngine()
    
    # 测试：假设当前是 2026年4月25日
    test_date = datetime(2026, 4, 25)
    print(f"=== {test_date.strftime('%Y-%m-%d')} 行动指南 ===")
    items = engine.generate_current_action_items(test_date)
    
    print(f"\n【当前阶段】: {items['current_focus']['phase']} (第{items['current_focus']['month']}月)")
    print(f"核心目标: {items['current_focus']['focus']}")
    for task in items['current_focus']['tasks']:
        print(f"- {task}")
        
    if items['upcoming_focus']:
        print(f"\n【即将到来】: {items['upcoming_focus']['phase']} (第{items['upcoming_focus']['month']}月)")
        print(f"核心目标: {items['upcoming_focus']['focus']}")
        for task in items['upcoming_focus']['tasks']:
            print(f"- {task}")
