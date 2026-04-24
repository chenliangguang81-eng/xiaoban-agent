"""
小升初面试教练 (Xiaoshengchu Interview Coach)
小伴 v3.2 — 小升初增强技能包

针对 1+3 项目（如五十七中、玉渊潭）及部分民办校的面试环节，
提供结构化的模拟面试、回答框架指导与心理建设。
"""

from typing import List, Dict

class XiaoshengchuInterviewCoach:
    """小升初面试教练"""
    
    # 常见面试题库分类
    QUESTION_BANK = {
        "自我认知": [
            "请用一分钟做一个简单的自我介绍。",
            "你觉得自己最大的优点和缺点是什么？",
            "在小学阶段，你最骄傲的一件事是什么？"
        ],
        "学习习惯": [
            "你平时是怎么安排周末时间的？",
            "遇到不会的难题，你通常会怎么解决？",
            "你最喜欢哪一门课？为什么？"
        ],
        "抗压与情绪": [
            "如果这次考试你没有考好，你会怎么调整自己的心情？",
            "在团队合作中，如果别人不听你的意见，你会怎么办？"
        ],
        "学校匹配度": [
            "你为什么想来我们学校（如五十七中）？",
            "你对初中生活有什么期待？"
        ]
    }

    def __init__(self):
        pass

    def generate_interview_plan(self, target_school: str) -> Dict:
        """生成针对特定学校的面试准备计划"""
        plan = {
            "target_school": target_school,
            "core_focus": "",
            "suggested_framework": "STAR法则 (Situation情境, Task任务, Action行动, Result结果)",
            "practice_schedule": []
        }
        
        if "五十七中" in target_school:
            plan["core_focus"] = "五十七中看重理科思维、抗压能力和自我驱动力。面试中要展现出不怕吃苦、目标明确的特质。"
            plan["practice_schedule"] = [
                "第1周：打磨1分钟自我介绍（突出理科优势或特长）",
                "第2周：准备'遇到挫折如何克服'的真实案例（STAR法则）",
                "第3周：全真模拟面试（家长扮演考官，控制时间）"
            ]
        elif "玉渊潭" in target_school:
            plan["core_focus"] = "玉渊潭 1+3 项目看重综合素质和稳定性。面试中要展现出踏实、听话、有一定特长的特质。"
            plan["practice_schedule"] = [
                "第1周：梳理小学阶段的获奖和特长",
                "第2周：准备'为什么选择玉渊潭'的回答（结合1+3项目的优势）",
                "第3周：礼仪与表达流畅度训练"
            ]
        else:
            plan["core_focus"] = "展现阳光、自信、有礼貌的综合素质。"
            plan["practice_schedule"] = [
                "第1周：基础自我介绍",
                "第2周：常见问题梳理",
                "第3周：模拟演练"
            ]
            
        return plan

    def evaluate_answer(self, question: str, student_answer: str) -> str:
        """
        评估学生的回答并给出建议
        （实际应用中可接入 LLM 进行语义分析，此处为规则演示）
        """
        feedback = "【小伴面试点评】\n"
        
        if len(student_answer) < 20:
            feedback += "⚠️ 回答太简短啦！考官可能觉得你没有准备好。试着多说一些细节。\n"
        
        if "因为" not in student_answer and "所以" not in student_answer:
            feedback += "💡 建议：在回答中多用'因为...所以...'，展现你的逻辑思考能力。\n"
            
        if "我" in student_answer and "我们" not in student_answer:
            feedback += "💡 建议：如果是团队合作的问题，记得多提'我们'，展现你的团队精神。\n"
            
        feedback += "\n🌟 睿智挚友提示：面试不是考试，而是让老师认识你这个有趣的人。深呼吸，你已经做得很棒了！"
        
        return feedback

if __name__ == "__main__":
    coach = XiaoshengchuInterviewCoach()
    print("=== 五十七中面试准备计划 ===")
    plan = coach.generate_interview_plan("五十七中")
    for k, v in plan.items():
        print(f"{k}: {v}")
        
    print("\n=== 回答评估测试 ===")
    q = "你为什么想来我们学校？"
    a = "我觉得你们学校很好。"
    print(f"Q: {q}\nA: {a}")
    print(coach.evaluate_answer(q, a))
