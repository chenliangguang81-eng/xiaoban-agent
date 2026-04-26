"""
主动信息分享引擎 (Proactive Sharing Engine)
小伴 v5.1 — Mythos 第二批技能模块

基于 Claude Constitution 中的 Proactive Information Sharing 原则：
"Claude proactively shares information useful to the user if it reasonably 
concludes they'd want it to even if they didn't explicitly ask for it, 
as long as doing so isn't outweighed by other considerations."

核心能力：
1. 政策变化预警 (Policy Change Alert)：主动推送小升初政策变化
2. 时间窗口提醒 (Time Window Alert)：1+3申请窗口、报名截止日等关键时间节点
3. 学情洞察推送 (Academic Insight Push)：主动发现学习模式问题并提醒
4. 机会发现 (Opportunity Discovery)：发现对小可爱有价值的信息并主动分享
5. 风险预警 (Risk Alert)：提前预警可能影响升学的风险因素

适用场景：
- 小升初政策发布月（2026年4月）：主动推送最新政策
- 1+3项目申请窗口（通常5-6月）：提前提醒
- 学情异常（连续错题、成绩下滑）：主动触发诊断
- 重要日期临近：派位报名、面试准备等
"""
from engines.llm_core import llm_call, get_llm_router
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────────────────────────────────────
# 关键时间节点数据库（2026年小升初）
# ─────────────────────────────────────────────────────────────────────────────

XIAOSHENGCHU_2026_TIMELINE = {
    "policy_release": {
        "date": "2026-04",
        "description": "小升初政策发布（当前月）",
        "urgency": "critical",
        "action": "密切关注海淀区教委官网，确认一派/二派规则是否有变化"
    },
    "jianhua_1_5_pai": {
        "date": "2026-04-30",
        "description": "建华实验1.5派招生简章预计发布",
        "urgency": "high",
        "action": "关注建华实验官网，确认区域一是否在招生范围内"
    },
    "yipai_registration": {
        "date": "2026-05",
        "description": "一派报名窗口（预计）",
        "urgency": "critical",
        "action": "准备报名材料，确认七一小学学籍证明"
    },
    "1plus3_application": {
        "date": "2026-05",
        "description": "1+3项目申请窗口（预计）",
        "urgency": "high",
        "action": "准备申请材料，了解各校面试要求"
    },
    "yipai_lottery": {
        "date": "2026-06",
        "description": "一派摇号结果公布（预计）",
        "urgency": "critical",
        "action": "等待结果，同时准备二派备选方案"
    },
    "erpai_registration": {
        "date": "2026-06",
        "description": "二派报名窗口（预计）",
        "urgency": "high",
        "action": "根据一派结果决定二派志愿"
    },
    "interview_prep_start": {
        "date": "2026-04-15",
        "description": "1+3面试准备建议开始时间",
        "urgency": "medium",
        "action": "启动XiaoshengchuInterviewCoach，开始3周结构化训练"
    }
}

# 主动分享触发条件
PROACTIVE_TRIGGERS = {
    "policy_update": {
        "description": "政策更新触发",
        "condition": "PolicyMonitor 检测到新政策文章",
        "priority": "critical",
        "target": "parent"
    },
    "deadline_approaching": {
        "description": "截止日期临近（7天内）",
        "condition": "关键时间节点距今 <= 7天",
        "priority": "high",
        "target": "parent"
    },
    "academic_anomaly": {
        "description": "学情异常",
        "condition": "连续3次同类错题 或 成绩下滑超过10%",
        "priority": "medium",
        "target": "parent"
    },
    "emotion_concern": {
        "description": "情绪关注",
        "condition": "连续3天负面情绪",
        "priority": "high",
        "target": "parent"
    },
    "opportunity_window": {
        "description": "机会窗口",
        "condition": "发现对小可爱有价值的新信息",
        "priority": "medium",
        "target": "parent"
    }
}


class ProactiveSharingEngine:
    """
    主动信息分享引擎
    
    职责：
    1. 监控关键时间节点，主动推送提醒
    2. 分析学情和情绪数据，主动发现问题
    3. 整合政策监控结果，生成家长可读的预警
    4. 确保信息分享的相关性和及时性
    """
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir
        self.current_date = datetime.now()
        
    def check_proactive_alerts(
        self,
        memory_data: Dict = None,
        policy_alerts: List[Dict] = None
    ) -> List[Dict]:
        """
        检查所有主动分享触发条件，返回需要推送的提醒列表
        
        Args:
            memory_data: 来自 MemoryManager 的记忆数据
            policy_alerts: 来自 PolicyMonitor 的政策预警
        
        Returns:
            需要推送的提醒列表，按优先级排序
        """
        alerts = []
        
        # 1. 检查时间节点提醒
        timeline_alerts = self._check_timeline_alerts()
        alerts.extend(timeline_alerts)
        
        # 2. 检查政策更新
        if policy_alerts:
            policy_push = self._process_policy_alerts(policy_alerts)
            alerts.extend(policy_push)
        
        # 3. 检查学情异常
        if memory_data:
            academic_alerts = self._check_academic_anomalies(memory_data)
            alerts.extend(academic_alerts)
            
            # 4. 检查情绪状态
            emotion_alerts = self._check_emotion_concerns(memory_data)
            alerts.extend(emotion_alerts)
        
        # 按优先级排序
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return alerts
    
    def _check_timeline_alerts(self) -> List[Dict]:
        """检查时间节点提醒"""
        alerts = []
        current = self.current_date
        
        for event_key, event in XIAOSHENGCHU_2026_TIMELINE.items():
            event_date_str = event["date"]
            
            # 解析日期（支持年月格式）
            try:
                if len(event_date_str) == 7:  # "2026-04" 格式
                    event_date = datetime.strptime(event_date_str + "-01", "%Y-%m-%d")
                else:
                    event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
            except ValueError:
                continue
            
            days_until = (event_date - current).days
            
            # 触发条件：未来30天内的事件
            if -7 <= days_until <= 30:
                urgency = event["urgency"]
                
                if days_until <= 0:
                    timing_desc = f"【本月】"
                elif days_until <= 7:
                    timing_desc = f"【{days_until}天后】⚠️"
                elif days_until <= 14:
                    timing_desc = f"【{days_until}天后】"
                else:
                    timing_desc = f"【约{days_until}天后】"
                
                alerts.append({
                    "type": "timeline",
                    "event_key": event_key,
                    "title": f"{timing_desc} {event['description']}",
                    "description": event["description"],
                    "action": event["action"],
                    "priority": urgency,
                    "days_until": days_until,
                    "target": "parent",
                    "timestamp": current.isoformat()
                })
        
        return alerts
    
    def _process_policy_alerts(self, policy_alerts: List[Dict]) -> List[Dict]:
        """处理政策预警，生成家长可读的推送"""
        processed = []
        
        for alert in policy_alerts[:3]:  # 最多处理3条最新预警
            processed.append({
                "type": "policy_update",
                "title": f"【政策更新】{alert.get('title', '新政策信息')}",
                "description": alert.get("summary", alert.get("content", "")[:200]),
                "source": alert.get("source", "未知来源"),
                "action": "请查看详情，确认是否影响小可爱的升学规划",
                "priority": "critical",
                "target": "parent",
                "timestamp": alert.get("timestamp", datetime.now().isoformat())
            })
        
        return processed
    
    def _check_academic_anomalies(self, memory_data: Dict) -> List[Dict]:
        """检查学情异常"""
        alerts = []
        
        # 检查错题本
        mistake_book = memory_data.get("mistake_book", {})
        entries = mistake_book.get("entries", [])
        
        if entries:
            # 检查近期错题模式
            recent_entries = entries[-10:] if len(entries) >= 10 else entries
            
            # 按知识点统计
            kp_count = {}
            for entry in recent_entries:
                kp = entry.get("knowledge_point", "未知")
                kp_count[kp] = kp_count.get(kp, 0) + 1
            
            # 发现重复错误
            repeated = [(kp, count) for kp, count in kp_count.items() if count >= 3]
            
            if repeated:
                kp_list = "、".join([f"{kp}({count}次)" for kp, count in repeated[:3]])
                alerts.append({
                    "type": "academic_anomaly",
                    "title": f"【学情预警】发现重复错误模式",
                    "description": f"小可爱在以下知识点反复出错：{kp_list}",
                    "action": "建议启动针对性复习，或调整辅导策略",
                    "priority": "medium",
                    "target": "parent",
                    "timestamp": datetime.now().isoformat()
                })
        
        return alerts
    
    def _check_emotion_concerns(self, memory_data: Dict) -> List[Dict]:
        """检查情绪关注点"""
        alerts = []
        
        # 从对话历史中提取情绪信息
        dialogues = memory_data.get("dialogue_history", {})
        entries = dialogues.get("entries", [])
        
        if not entries:
            return alerts
        
        # 检查最近7条对话中的情绪信号
        recent = entries[-7:] if len(entries) >= 7 else entries
        negative_keywords = ["好累", "不想", "烦", "难过", "压力", "焦虑", "沮丧"]
        
        negative_count = 0
        for entry in recent:
            content = entry.get("content", "")
            if any(kw in content for kw in negative_keywords):
                negative_count += 1
        
        if negative_count >= 3:
            alerts.append({
                "type": "emotion_concern",
                "title": f"【情绪关注】小可爱近期情绪波动",
                "description": f"在最近{len(recent)}次对话中，检测到{negative_count}次负面情绪信号",
                "action": "建议与小可爱进行一次轻松的亲子对话，了解她的真实状态",
                "priority": "high",
                "target": "parent",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts
    
    def generate_parent_proactive_message(
        self,
        alerts: List[Dict],
        student_name: str = "小可爱"
    ) -> str:
        """
        生成家长主动推送消息
        
        将技术性的 alert 列表转化为家长可读的自然语言消息。
        体现 Mythos 的 Proactive Information Sharing 原则。
        
        Args:
            alerts: 需要推送的提醒列表
            student_name: 学生姓名
        
        Returns:
            格式化的家长推送消息
        """
        if not alerts:
            return ""
        
        critical_alerts = [a for a in alerts if a.get("priority") == "critical"]
        high_alerts = [a for a in alerts if a.get("priority") == "high"]
        medium_alerts = [a for a in alerts if a.get("priority") == "medium"]
        
        message_parts = [f"Lion，小伴有{len(alerts)}条信息想主动告诉您：\n"]
        
        if critical_alerts:
            message_parts.append("🔴 **紧急关注**")
            for alert in critical_alerts[:2]:
                message_parts.append(f"• {alert['title']}")
                message_parts.append(f"  建议行动：{alert['action']}")
        
        if high_alerts:
            message_parts.append("\n🟡 **重要提醒**")
            for alert in high_alerts[:2]:
                message_parts.append(f"• {alert['title']}")
                message_parts.append(f"  建议行动：{alert['action']}")
        
        if medium_alerts:
            message_parts.append("\n🟢 **一般关注**")
            for alert in medium_alerts[:2]:
                message_parts.append(f"• {alert['title']}")
        
        message_parts.append(
            f"\n以上信息由小伴主动整理，供您参考。"
            f"如需了解详情，随时告诉我。"
        )
        
        return "\n".join(message_parts)
    
    def generate_daily_briefing(
        self,
        memory_data: Dict = None,
        policy_alerts: List[Dict] = None
    ) -> Dict:
        """
        生成每日简报（主动信息分享的核心输出）
        
        每天早上自动生成，包含：
        - 今日关键时间节点
        - 最新政策动态
        - 学情摘要
        - 建议行动项
        
        Returns:
            每日简报 Dict
        """
        alerts = self.check_proactive_alerts(memory_data, policy_alerts)
        
        # 今日日期
        today = self.current_date.strftime("%Y年%m月%d日")
        
        # 当前小升初阶段
        current_phase = self._get_current_xiaoshengchu_phase()
        
        briefing = {
            "date": today,
            "current_phase": current_phase,
            "total_alerts": len(alerts),
            "critical_count": len([a for a in alerts if a.get("priority") == "critical"]),
            "alerts": alerts,
            "parent_message": self.generate_parent_proactive_message(alerts),
            "upcoming_deadlines": self._get_upcoming_deadlines(days=14),
            "today_focus": self._get_today_focus(),
            "generated_at": self.current_date.isoformat()
        }
        
        return briefing
    
    def _get_current_xiaoshengchu_phase(self) -> str:
        """获取当前小升初阶段描述"""
        month = self.current_date.month
        
        phase_map = {
            1: "备考期（寒假冲刺）",
            2: "备考期（寒假冲刺）",
            3: "政策研究期（等待政策发布）",
            4: "政策发布期（关键月）⚠️",
            5: "报名冲刺期（一派/1+3报名）",
            6: "摇号等待期",
            7: "录取确认期",
            8: "入学准备期",
            9: "初中开学",
        }
        
        return phase_map.get(month, "小升初规划期")
    
    def _get_upcoming_deadlines(self, days: int = 14) -> List[Dict]:
        """获取未来N天内的截止日期"""
        upcoming = []
        current = self.current_date
        
        for event_key, event in XIAOSHENGCHU_2026_TIMELINE.items():
            try:
                date_str = event["date"]
                if len(date_str) == 7:
                    event_date = datetime.strptime(date_str + "-01", "%Y-%m-%d")
                else:
                    event_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                days_until = (event_date - current).days
                
                if 0 <= days_until <= days:
                    upcoming.append({
                        "event": event["description"],
                        "days_until": days_until,
                        "urgency": event["urgency"],
                        "action": event["action"]
                    })
            except ValueError:
                continue
        
        return sorted(upcoming, key=lambda x: x["days_until"])
    
    def _get_today_focus(self) -> str:
        """获取今日重点关注事项"""
        month = self.current_date.month
        
        focus_map = {
            4: "政策发布关键月：每日检查海淀区教委官网，关注一派/二派/1+3政策变化",
            5: "报名冲刺：确认报名材料齐全，关注各校报名截止时间",
            6: "摇号等待：保持心态平稳，同时准备二派备选方案",
        }
        
        return focus_map.get(month, "持续关注升学动态，保持正常学习节奏")


# ─────────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("ProactiveSharingEngine 测试")
    print("=" * 60)
    
    engine = ProactiveSharingEngine()
    
    # 模拟记忆数据
    mock_memory = {
        "mistake_book": {
            "entries": [
                {"knowledge_point": "分数除法", "subject": "数学"},
                {"knowledge_point": "分数除法", "subject": "数学"},
                {"knowledge_point": "分数除法", "subject": "数学"},
                {"knowledge_point": "比例", "subject": "数学"},
            ]
        },
        "dialogue_history": {
            "entries": [
                {"content": "好累，不想学了", "role": "user"},
                {"content": "今天压力好大", "role": "user"},
                {"content": "我很烦", "role": "user"},
                {"content": "这道题怎么做", "role": "user"},
            ]
        }
    }
    
    # 模拟政策预警
    mock_policy_alerts = [
        {
            "title": "海淀区2026年小升初政策发布",
            "summary": "海淀区教委发布2026年小升初工作方案，一派比例维持不变",
            "source": "海淀区教委官网",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    # 测试 1：检查主动提醒
    print("\n【测试 1】检查主动提醒")
    alerts = engine.check_proactive_alerts(mock_memory, mock_policy_alerts)
    print(f"生成提醒数量: {len(alerts)}")
    for alert in alerts[:3]:
        print(f"  [{alert['priority']}] {alert['title']}")
    
    # 测试 2：生成家长推送消息
    print("\n【测试 2】家长推送消息")
    message = engine.generate_parent_proactive_message(alerts)
    print(message[:500])
    
    # 测试 3：每日简报
    print("\n【测试 3】每日简报")
    briefing = engine.generate_daily_briefing(mock_memory, mock_policy_alerts)
    print(f"当前阶段: {briefing['current_phase']}")
    print(f"总提醒数: {briefing['total_alerts']}")
    print(f"紧急提醒: {briefing['critical_count']}")
    print(f"今日重点: {briefing['today_focus']}")
    
    print("\n✅ 测试完成")
