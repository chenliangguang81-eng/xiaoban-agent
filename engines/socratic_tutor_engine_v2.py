"""
苏格拉底辅导引擎 v2.0 (LLM 驱动版)
小伴 v4.0 升级
"""
from engines.llm_core import llm_call, get_llm_router

import os
import json
from typing import Dict, List, Optional

class SocraticTutorEngineV2:
    def __init__(self, memory_manager=None):
        self.client = OpenAI()
        self.model = "gpt-4.1-mini"
        self.memory_manager = memory_manager
        self.depth_config = {
            "小学": {"max_depth": 2, "style": "简单启发，多用生活类比", "tone": "温暖鼓励，像大哥哥大姐姐"},
            "初中": {"max_depth": 3, "style": "方法论引导，培养解题框架", "tone": "平等尊重，像同龄朋友"},
            "高中": {"max_depth": 4, "style": "深度追问，建立批判性思维", "tone": "理性深度，像智慧导师"}
        }

    def _get_grade_stage(self) -> str:
        if self.memory_manager:
            try:
                profile = self.memory_manager.get_profile()
                grade = profile.get("grade", "六年级")
                if any(g in grade for g in ["初一","初二","初三","七年级","八年级","九年级"]):
                    return "初中"
                elif any(g in grade for g in ["高一","高二","高三","十年级","十一年级","十二年级"]):
                    return "高中"
            except Exception:
                pass
        return "小学"

    def analyze_mistake(self, question: str, student_answer: str, correct_answer: str) -> Dict:
        stage = self._get_grade_stage()
        config = self.depth_config[stage]
        prompt = f"""分析学生错误：
题目：{question}
学生答案：{student_answer}
正确答案：{correct_answer}
风格：{config['style']}，语气：{config['tone']}
返回JSON：{{"error_type":"...","root_cause":"...","prerequisite_gap":"...","socratic_question":"...","confidence":0.9}}"""
        try:
            # [v5.2 Manus迁移] 统一路由器调用
            response_reply = llm_call(prompt)
            result = json.loads(response_reply)
            result["status"] = "success"
            return result
        except Exception as e:
            return {"error_type": "分析失败", "root_cause": str(e),
                    "socratic_question": "你能告诉我，你是怎么想到这个答案的？", "status": "error"}

    def generate_hint_chain(self, question: str, subject: str = "数学") -> List[str]:
        stage = self._get_grade_stage()
        config = self.depth_config[stage]
        prompt = f"""你是小伴，{stage}生的学习伙伴。
题目（{subject}）：{question}
生成{config['max_depth']}个苏格拉底引导问题，绝对不透露答案。
风格：{config['style']}，语气：{config['tone']}
返回JSON：{{"hints":["问题1","问题2","问题3"]}}"""
        try:
            # [v5.2 Manus迁移] 统一路由器调用
            response_reply = llm_call(prompt)
            result = json.loads(response_reply)
            return result.get("hints", ["你能告诉我，这道题考察的是什么知识点？"])
        except Exception as e:
            return [f"你觉得这道题的关键是什么？"]

    def respond_to_student_answer(self, original_question: str, hint_given: str, student_response: str) -> Dict:
        stage = self._get_grade_stage()
        config = self.depth_config[stage]
        prompt = f"""你是小伴。
原题：{original_question}
你的提示：{hint_given}
孩子回答：{student_response}
判断回答质量，给出温暖反馈，绝对不直接给答案。
语气：{config['tone']}
返回JSON：{{"assessment":"correct/partial/incorrect","feedback":"...","next_hint":"...","encouragement":"..."}}"""
        try:
            # [v5.2 Manus迁移] 统一路由器调用
            response_reply = llm_call(prompt)
            result = json.loads(response_reply)
            result["status"] = "success"
            return result
        except Exception as e:
            return {"assessment": "unknown", "feedback": "你说得很有意思！让我们继续思考...",
                    "next_hint": "你觉得下一步应该怎么做？", "status": "error"}

if __name__ == "__main__":
    print("=== 苏格拉底辅导引擎 v2.0 测试 ===")
    engine = SocraticTutorEngineV2()
    stage = engine._get_grade_stage()
    print(f"✅ 年级阶段：{stage}")
    config = engine.depth_config[stage]
    print(f"✅ 辅导深度：{config['max_depth']} 层")
    print(f"✅ 辅导风格：{config['style']}")
    print("\n正在测试 LLM 提示链生成...")
    try:
        hints = engine.generate_hint_chain("3/4 + 1/6 = ?", "数学")
        print(f"✅ 提示链生成成功，共 {len(hints)} 个提示：")
        for i, hint in enumerate(hints, 1):
            print(f"   提示{i}：{hint}")
    except Exception as e:
        print(f"⚠️  LLM 调用：{e}")
    print("\n✅ 苏格拉底辅导引擎 v2.0 就绪")
