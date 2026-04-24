"""
小升初志愿模拟器 (Xiaoshengchu Simulator)
小伴 v3.2 — 小升初增强技能包

基于七一小学真实派位池数据，提供蒙特卡洛模拟，
帮助家长直观感受不同志愿填报策略的"掉坑"概率。
"""

import random
from typing import List, Dict

class XiaoshengchuSimulator:
    """小升初志愿模拟器"""
    
    def __init__(self):
        # 简化版派位池概率模型 (基于七一小学实测数据)
        self.pool_stats = {
            "一派": {
                "S类": {"name": "十一晋元", "prob": 0.02},
                "A类": {"name": "五十七中/人翠/101双榆树/交大附中", "prob": 0.15},
                "A-类": {"name": "交大附中分校/首师大一分校等", "prob": 0.25},
                "B+类": {"name": "育鸿/建华/北师大三附中", "prob": 0.20},
                "B类": {"name": "育英中学/玉渊潭等", "prob": 0.30},
                "C类": {"name": "进修实验香山/南校区", "prob": 0.08}
            },
            "二派": {
                "A类": {"name": "五十七中/人翠", "prob": 0.10},
                "A-类": {"name": "理工附中东校区", "prob": 0.15},
                "B+类": {"name": "育鸿", "prob": 0.20},
                "B类": {"name": "玉渊潭/育英中学", "prob": 0.55}
            }
        }

    def simulate_strategy(self, strategy_name: str, iterations: int = 1000) -> Dict:
        """
        运行蒙特卡洛模拟
        strategy_name: "激进冲高" 或 "稳妥保底"
        """
        results = {"S类": 0, "A类": 0, "A-类": 0, "B+类": 0, "B类": 0, "C类": 0}
        
        for _ in range(iterations):
            outcome = self._run_single_simulation(strategy_name)
            results[outcome] += 1
            
        # 转换为百分比
        for k in results:
            results[k] = round((results[k] / iterations) * 100, 1)
            
        return {
            "strategy": strategy_name,
            "iterations": iterations,
            "probabilities": results,
            "risk_assessment": self._assess_risk(results)
        }
        
    def _run_single_simulation(self, strategy: str) -> str:
        """单次模拟逻辑"""
        roll = random.random()
        
        if strategy == "激进冲高":
            # 一派全填A类，如果没中，直接掉入二派
            if roll < 0.15: return "A类"
            
            # 二派逻辑
            roll2 = random.random()
            if roll2 < 0.10: return "A类"
            elif roll2 < 0.25: return "A-类"
            elif roll2 < 0.45: return "B+类"
            else: return "B类"
            
        elif strategy == "稳妥保底":
            # 一派填A类和A-类
            if roll < 0.10: return "A类"
            elif roll < 0.35: return "A-类"
            
            # 二派逻辑
            roll2 = random.random()
            if roll2 < 0.05: return "A类"
            elif roll2 < 0.20: return "A-类"
            elif roll2 < 0.40: return "B+类"
            else: return "B类"
            
        return "B类"

    def _assess_risk(self, probs: Dict) -> str:
        """风险评估结论"""
        if probs.get("B类", 0) > 50:
            return "高风险：有超过一半的概率掉入保底校，建议在一派增加稳妥选项。"
        elif probs.get("A类", 0) + probs.get("A-类", 0) > 40:
            return "收益可观：有较高概率进入优质校，策略合理。"
        return "中等风险：建议结合孩子实际成绩微调。"

if __name__ == "__main__":
    sim = XiaoshengchuSimulator()
    print("=== 激进冲高策略模拟 (1000次) ===")
    print(sim.simulate_strategy("激进冲高"))
    print("\n=== 稳妥保底策略模拟 (1000次) ===")
    print(sim.simulate_strategy("稳妥保底"))
