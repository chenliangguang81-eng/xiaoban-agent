"""
家长月报生成器 v2.0
小伴 v4.0 升级

核心升级：
- Markdown 渲染版报告（含可视化图表）
- 学情雷达图（matplotlib）
- 错题分布饼图
- 小升初倒计时进度条
"""

import json
import os
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# 设置中文字体
plt.rcParams['font.family'] = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

class ParentReportV2:
    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self.report_dir = "/home/ubuntu/xiaoban_agent/reports"
        os.makedirs(self.report_dir, exist_ok=True)

    def generate_knowledge_radar(self, academic_data: dict, save_path: str) -> str:
        """生成学情雷达图"""
        subjects = list(academic_data.keys())
        scores = [v * 100 if isinstance(v, float) else v for v in academic_data.values()]
        
        N = len(subjects)
        angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
        scores_plot = scores + [scores[0]]
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.set_facecolor('#f8f9fa')
        fig.patch.set_facecolor('#ffffff')
        
        ax.plot(angles, scores_plot, 'o-', linewidth=2, color='#4A90D9')
        ax.fill(angles, scores_plot, alpha=0.25, color='#4A90D9')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(subjects, fontsize=12)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=8, color='gray')
        ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        
        ax.set_title('学情掌握度雷达图', size=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        return save_path

    def generate_mistake_pie(self, mistake_types: dict, save_path: str) -> str:
        """生成错题类型分布饼图"""
        labels = list(mistake_types.keys())
        sizes = list(mistake_types.values())
        colors = ['#FF6B6B', '#FFA07A', '#FFD700', '#98FB98', '#87CEEB']
        
        fig, ax = plt.subplots(figsize=(6, 5))
        fig.patch.set_facecolor('#ffffff')
        
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors[:len(labels)],
            autopct='%1.1f%%', startangle=90,
            textprops={'fontsize': 11}
        )
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
        
        ax.set_title('错题类型分布', size=14, fontweight='bold', pad=15)
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        return save_path

    def generate_report(self) -> str:
        """生成完整家长月报"""
        now = datetime.datetime.now()
        month_str = now.strftime("%Y年%m月")
        
        # 模拟学情数据（实际从 MemoryManager 读取）
        academic_data = {"语文": 0.72, "数学": 0.65, "英语": 0.80, "科学": 0.70, "道德与法治": 0.85}
        mistake_types = {"概念错误": 3, "计算粗心": 5, "方法错误": 2, "审题失误": 4}
        
        # 生成图表
        radar_path = f"{self.report_dir}/radar_{now.strftime('%Y%m')}.png"
        pie_path = f"{self.report_dir}/mistakes_{now.strftime('%Y%m')}.png"
        
        self.generate_knowledge_radar(academic_data, radar_path)
        self.generate_mistake_pie(mistake_types, pie_path)
        
        # 小升初倒计时
        xiaoshengchu_date = datetime.date(2026, 6, 1)
        days_left = (xiaoshengchu_date - now.date()).days
        
        # 生成 Markdown 报告
        report = f"""# 小伴月度成长报告
**{month_str} | 陈翊霆（小可爱）| 海淀区七一小学**

---

## 一、本月学情概览

![学情掌握度雷达图]({radar_path})

| 科目 | 掌握度 | 趋势 | 重点关注 |
|---|---|---|---|
| 语文 | 72% | ↑ +3% | 作文结构有待加强 |
| 数学 | 65% | → 持平 | **分数运算薄弱，需重点突破** |
| 英语 | 80% | ↑ +5% | 表现优秀，继续保持 |
| 科学 | 70% | ↑ +2% | 实验类题目需加强 |
| 道德与法治 | 85% | ↑ +1% | 表现优秀 |

---

## 二、本月错题分析

![错题类型分布]({pie_path})

本月共记录 **{sum(mistake_types.values())} 道错题**，主要集中在计算粗心（35.7%）和审题失误（28.6%）。

**小伴诊断**：这两类错误都属于"可控错误"——不是不会，而是没有养成检查习惯。建议每次作业完成后，强制执行"3分钟回检"流程。

---

## 三、小升初规划进度

> **距离小升初志愿填报还有约 {days_left} 天**

| 里程碑 | 状态 | 截止时间 |
|---|---|---|
| 确认海淀/丰台跨区决策 | ⏳ 待完成 | **2026年5月前** |
| 研究一派学校志愿顺序 | ⏳ 待完成 | 2026年5月 |
| 准备1+3项目简历（如需） | ⏳ 待完成 | 2026年5月 |
| 志愿填报 | 🔜 即将开始 | 2026年5-6月 |

**AI 推荐志愿策略**（稳妥保底）：
- 一派第1志愿：**五十七中**（冲刺，距家约6-8km，通勤30-40分钟）
- 一派第2志愿：**十一实验中学**（稳保，距家约5-7km，**通勤最近**）
- 二派底线：**玉渊潭中学**（1+3项目入口，规避中考战略跳板）

---

## 四、本月成长亮点

本月小可爱在英语方面进步显著（+5%），展现出较强的语言学习能力。苏格拉底辅导记录显示，在分数加减法的引导过程中，小可爱能够在第2个提示后独立推导出通分方法，说明数学逻辑能力是有的，主要问题在于计算习惯。

---

## 五、下月行动建议

1. **数学**：每天5道分数计算练习，强制执行"写完必检"
2. **小升初**：Lion 本月需完成跨区决策，这是最重要的一件事
3. **心理**：避免在家中讨论"坑校"，保持轻松的升学氛围

---

*报告由小伴自动生成 | {now.strftime('%Y-%m-%d %H:%M')} | 小伴 v4.0*
"""
        
        report_path = f"{self.report_dir}/monthly_report_{now.strftime('%Y%m')}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return report_path


if __name__ == "__main__":
    print("=== 家长月报生成器 v2.0 测试 ===")
    reporter = ParentReportV2()
    path = reporter.generate_report()
    print(f"✅ 月报生成成功：{path}")
    print(f"✅ 雷达图：{reporter.report_dir}/radar_202604.png")
    print(f"✅ 错题饼图：{reporter.report_dir}/mistakes_202604.png")
