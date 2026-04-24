"""
政策追踪与通勤数据库 (Policy Tracker v2.0)
小伴 v4.0 升级

核心升级：
- 引入"置信度标注"（Calibrated Uncertainty），对政策信息进行分级
- 集成学校通勤数据库（基于丰台东大街5号院的距离计算）
"""

import json
import os
from typing import Dict, List

class PolicyTrackerV2:
    def __init__(self):
        self.kb_dir = "/home/ubuntu/xiaoban_agent/knowledge_base"
        
        # 政策置信度分级
        self.confidence_levels = {
            "HIGH": "【高置信度】官方已发布红头文件，政策已固化。",
            "MEDIUM": "【中置信度】基于往年惯例推测，大概率延续，但需等待当年细则。",
            "LOW": "【低置信度】坊间传闻或处于政策调整期，存在较大变数，仅供参考。"
        }
        
        # 丰台东大街5号院 通勤数据库
        self.commute_db = {
            "五十七中": {"distance": "6-8km", "time": "30-40分钟", "method": "地铁9转1", "suitability": "走读优选"},
            "十一实验中学": {"distance": "5-7km", "time": "20-30分钟", "method": "公交/驾车", "suitability": "走读首选"},
            "玉渊潭中学": {"distance": "6-8km", "time": "30-40分钟", "method": "地铁9转1", "suitability": "走读优选"},
            "育英中学": {"distance": "6-8km", "time": "30-40分钟", "method": "地铁9转1", "suitability": "走读优选"},
            "人大附中翠微学校": {"distance": "7-9km", "time": "40-50分钟", "method": "地铁1号线", "suitability": "可走读"},
            "育鸿学校": {"distance": "7-9km", "time": "40-50分钟", "method": "地铁1号线", "suitability": "可走读"},
            "101中学双榆树校区": {"distance": "12-15km", "time": "60分钟+", "method": "跨区长途", "suitability": "建议寄宿"},
            "交大附中": {"distance": "15-18km", "time": "70分钟+", "method": "跨区长途", "suitability": "强烈建议寄宿"}
        }

    def get_policy_info(self, topic: str) -> Dict:
        """获取带有置信度标注的政策信息"""
        if "跨区" in topic or "学籍" in topic or "户籍" in topic:
            return {
                "topic": "海淀学籍 vs 丰台户籍 跨区升学",
                "content": "根据北京市教委规定，学生可选择在学籍所在区（海淀）或户籍所在区（丰台）参加小升初派位。一旦办理跨区手续（回丰台），将完全丧失海淀派位资格，且不可逆。",
                "confidence": "HIGH",
                "annotation": self.confidence_levels["HIGH"]
            }
        elif "1+3" in topic or "五十七中" in topic or "玉渊潭" in topic:
            return {
                "topic": "1+3 培养试验项目",
                "content": "五十七中和玉渊潭中学往年均有 1+3 项目名额（初二结束后直升本校高中，免中考）。",
                "confidence": "MEDIUM",
                "annotation": self.confidence_levels["MEDIUM"] + " 需关注2026年7月发布的最新1+3项目学校名单。"
            }
        elif "点招" in topic or "密考" in topic:
            return {
                "topic": "点招与密考",
                "content": "官方严禁任何形式的考试招生。目前主要通过简历投递或机构推荐。",
                "confidence": "LOW",
                "annotation": self.confidence_levels["LOW"] + " 政策严打期，信息极度不透明，切勿轻信机构保过承诺。"
            }
        else:
            return {
                "topic": topic,
                "content": "暂无相关政策记录。",
                "confidence": "LOW",
                "annotation": self.confidence_levels["LOW"]
            }

    def get_commute_info(self, school_name: str) -> Dict:
        """获取学校通勤信息"""
        for key, info in self.commute_db.items():
            if key in school_name or school_name in key:
                return info
        return {"distance": "未知", "time": "未知", "method": "未知", "suitability": "需实地考察"}

if __name__ == "__main__":
    print("=== 政策追踪与通勤数据库 v2.0 测试 ===")
    tracker = PolicyTrackerV2()
    
    print("\n1. 政策置信度测试：")
    policy = tracker.get_policy_info("1+3项目")
    print(f"主题：{policy['topic']}")
    print(f"内容：{policy['content']}")
    print(f"标注：{policy['annotation']}")
    
    print("\n2. 通勤数据库测试：")
    commute = tracker.get_commute_info("十一实验中学")
    print(f"十一实验中学通勤：{commute}")
    
    print("\n✅ Policy Tracker v2.0 就绪")
