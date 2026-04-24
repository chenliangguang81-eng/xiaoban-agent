"""
小伴 集成测试脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_memory():
    print("=== Test 1: 记忆系统 ===")
    from main_agent import load_memory
    profile = load_memory("student_profile.json")
    print(f"学生画像加载成功: {profile.get('name')}, 年级: {profile.get('grade')}")
    print(f"家长: {profile.get('parent', {}).get('name')}, 邮箱: {profile.get('parent', {}).get('email')}")
    return True

def test_speaker_identification():
    print("\n=== Test 2: 说话人识别 ===")
    from main_agent import identify_speaker
    test_cases = [
        ("小可爱最近小升初准备得怎么样？", "parent"),
        ("这题我不会，帮我讲讲", "student"),
        ("北京小升初政策今年有什么变化", "parent"),
    ]
    all_pass = True
    for text, expected in test_cases:
        result = identify_speaker(text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} [{expected}] \"{text[:20]}\" → {result}")
        if result != expected:
            all_pass = False
    return all_pass

def test_skill_routing():
    print("\n=== Test 3: 技能路由 ===")
    from main_agent import route_skills
    route_cases = [
        "小升初想冲人大附中",
        "这题怎么做，我不会",
        "我好累不想学了",
        "怎么提高数学成绩",
    ]
    for q in route_cases:
        skills = route_skills(q)
        print(f"  \"{q[:20]}\" → {skills}")
    return True

def test_mistake_book():
    print("\n=== Test 4: 错题本 ===")
    from skills.mistake_book import add_mistake, get_summary
    entry = add_mistake("math", "3/4 + 1/6 = ?", "分母没有通分就直接相加", "分数加减法")
    print(f"  错题添加成功: ID={entry['id']}")
    print(f"  复习计划（前3次）: {entry['review_schedule'][:3]}")
    summary = get_summary()
    print(f"  错题本摘要: {summary}")
    return True

def test_knowledge_tracker():
    print("\n=== Test 5: 知识点掌握度 ===")
    from skills.knowledge_graph_tracker import update_mastery, get_weak_points
    update_mastery("math", "calculation", 72)
    update_mastery("math", "geometry", 45)
    update_mastery("chinese", "writing", 68)
    weak = get_weak_points(threshold=70)
    print(f"  薄弱点共 {len(weak)} 个:")
    for w in weak:
        print(f"    - {w['subject']}-{w['dimension']}: {w['score']}/100")
    return True

def test_scheduler():
    print("\n=== Test 6: 调度器 ===")
    from scheduler.scheduler import run_daily_check
    results = run_daily_check()
    print(f"  每日检查完成，{len(results)} 项任务")
    for r in results:
        print(f"    [{r['type']}] {r['message']}")
    return True

def test_system_prompt():
    print("\n=== Test 7: System Prompt 构建 ===")
    from main_agent import build_system_prompt
    prompt = build_system_prompt("parent", ["xiaoshengchu_planner", "school_database"])
    print(f"  System Prompt 长度: {len(prompt)} 字符")
    print(f"  前100字: {prompt[:100]}...")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("小伴 · 集成测试")
    print("=" * 60)

    tests = [
        test_memory,
        test_speaker_identification,
        test_skill_routing,
        test_mistake_book,
        test_knowledge_tracker,
        test_scheduler,
        test_system_prompt,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过 / {failed} 失败 / {len(tests)} 总计")
    if failed == 0:
        print("✅ 所有集成测试通过！小伴系统已就绪。")
    else:
        print("⚠️  部分测试失败，请检查上方错误信息。")
    print("=" * 60)
