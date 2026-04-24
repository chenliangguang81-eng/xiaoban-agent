"""
小伴 v2.0 集成测试脚本
验证 MemoryManager + XiaoshengchuPlanner + 主调度 Agent 的完整集成
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  ✅ {label}")
        PASS += 1
    else:
        print(f"  ❌ {label}" + (f" — {detail}" if detail else ""))
        FAIL += 1

# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("小伴 v2.0 · 集成测试")
print("=" * 60)

# ── Test 1: MemoryManager 初始化 ─────────────────────────────
print("\n[1] MemoryManager 初始化")
from memory.memory_manager import MemoryManager
mem = MemoryManager(Path("memory"))
profile = mem.get_profile()
check("学生画像加载", profile.get("name") == "小可爱")
check("学籍区", profile.get("school_district") == "海淀区")
check("户籍区", profile.get("home_district") == "丰台区")
check("家长信息", profile.get("guardian", {}).get("name") == "Lion")
check("家长邮箱", profile.get("guardian", {}).get("email") == "24525837@qq.com")

# ── Test 2: MemoryManager 写入 ────────────────────────────────
print("\n[2] MemoryManager 写入操作")
mem.update_profile_field("personality.learning_style", "视觉型")
profile2 = mem.get_profile()
check("嵌套字段更新", profile2.get("personality", {}).get("learning_style") == "视觉型")

mem.update_mastery("math", "fractions", 0.45, "分数加减法错题")
mastery = mem.get_mastery()
check("知识掌握度写入", mastery.get("math", {}).get("fractions", {}).get("level") == 0.45)

# ── Test 3: 错题本 + 艾宾浩斯提醒 ────────────────────────────
print("\n[3] 错题本 + 艾宾浩斯提醒")
mistake_id = mem.add_mistake({
    "subject": "math",
    "question": "3/4 + 1/6 = ?",
    "error_reason": "分母没有通分就直接相加",
    "knowledge_point": "分数加减法",
    "summary": "math-分数加减法: 3/4+1/6",
})
check("错题添加成功", mistake_id.startswith("m_"))
mistakes = mem.get_mistakes("math")
check("错题可检索", len(mistakes) >= 1)
reminders = mem.get_due_reminders()
# 提醒应该在未来，今天不触发
all_reminders_data = mem._read_json(mem.memory_dir / "reminders.json")
pending = all_reminders_data.get("pending", [])
mistake_reminders = [r for r in pending if r.get("mistake_id") == mistake_id]
check("艾宾浩斯提醒已创建(5条)", len(mistake_reminders) == 5)

# ── Test 4: 对话历史 ──────────────────────────────────────────
print("\n[4] 对话历史")
mem.append_dialogue("user", "小升初怎么规划？", speaker="parent", skill_used="xiaoshengchu_planner")
mem.append_dialogue("assistant", "根据您的情况，建议...", speaker="xiaoban", skill_used="xiaoshengchu_planner")
recent = mem.get_recent_dialogues(days=1)
check("对话历史写入", len(recent) >= 2)
check("说话人字段正确", any(m.get("speaker") == "parent" for m in recent))

# ── Test 5: 上下文摘要 ────────────────────────────────────────
print("\n[5] 上下文摘要生成")
summary = mem.get_context_summary()
check("摘要包含学生姓名", "小可爱" in summary)
check("摘要包含学籍信息", "海淀" in summary)
check("摘要包含家长信息", "Lion" in summary)

# ── Test 6: XiaoshengchuPlanner OOP ──────────────────────────
print("\n[6] XiaoshengchuPlanner（面向对象版）")
from skills.xiaoshengchu_planner import XiaoshengchuPlanner
planner = XiaoshengchuPlanner(memory_manager=mem)
analysis = planner.analyze_pathways()
check("路径分析成功", "viable_pathways" in analysis)
check("包含海淀路径", any("海淀" in p["pathway"] for p in analysis["viable_pathways"]))
check("包含丰台跨区路径", any("丰台" in p["pathway"] for p in analysis["viable_pathways"]))
check("冲稳保推荐", "recommended_schools" in analysis)
check("风险提示", len(analysis.get("risks_and_cautions", [])) >= 3)
check("规划快照已保存", (mem.planning_dir / f"xiaoshengchu_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.json").exists())

# 对比决策表
compare = planner.compare_haidian_vs_fengtai()
check("海淀方案分析", "海淀方案" in compare)
check("丰台方案分析", "丰台方案" in compare)
check("决策建议", "建议决策顺序" in compare)

# Markdown 报告格式化
report = planner.format_analysis_for_parent(analysis)
check("Markdown 报告生成", "小升初路径分析报告" in report and len(report) > 500)

# ── Test 7: 主调度 Agent ──────────────────────────────────────
print("\n[7] 主调度 Agent")
from main_agent import identify_speaker, route_skills, build_system_prompt, get_memory

test_cases = [
    ("小可爱最近小升初准备得怎么样？", "parent"),
    ("这题我不会，帮我讲讲", "student"),
    ("北京小升初政策今年有什么变化", "parent"),
    ("我好累不想学了", "unknown"),
]
for text, expected in test_cases:
    result = identify_speaker(text)
    check(f"说话人识别: {text[:15]}...", result == expected, f"期望{expected}，得到{result}")

route_cases = [
    ("小升初想冲人大附中", "xiaoshengchu_planner"),
    ("这题怎么做，我不会", "homework_coach"),
    ("我好累不想学了", "psychology_companion"),
]
for text, expected_skill in route_cases:
    skills = route_skills(text)
    check(f"技能路由: {text[:12]}...", expected_skill in skills, f"期望含{expected_skill}，得到{skills}")

# System Prompt 构建
prompt = build_system_prompt("parent", ["xiaoshengchu_planner"])
check("System Prompt 包含学生信息", "小可爱" in prompt)
check("System Prompt 包含关键矛盾提示", "海淀" in prompt and "丰台" in prompt)
check("System Prompt 长度合理", len(prompt) > 300)

# ── Test 8: MemoryManager 单例 ────────────────────────────────
print("\n[8] MemoryManager 单例一致性")
mem1 = get_memory()
mem2 = get_memory()
check("单例模式（同一对象）", mem1 is mem2)

# ── 汇总 ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"测试结果：{PASS} 通过 / {FAIL} 失败 / {PASS + FAIL} 总计")
if FAIL == 0:
    print("✅ 所有测试通过！小伴 v2.0 系统已就绪。")
else:
    print(f"⚠️  {FAIL} 项测试失败，请检查上方错误信息。")
print("=" * 60)
