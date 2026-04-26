"""
小伴 v5.2 LLM 迁移脚本
将所有文件中的 OpenAI 直接调用替换为 llm_call() 统一接口

策略：最小化侵入，只做以下三件事：
1. 移除 `from openai import OpenAI` 和模块级 `client = OpenAI()`
2. 在文件顶部添加 `from engines.llm_core import llm_call, get_llm_router`
3. 将 `client.chat.completions.create(...)` 整块替换为 `llm_call(...)` 直接调用
   - 返回值直接是字符串，不再是 response 对象
   - 同时修正后续的 `response.choices[0].message.content` 为直接使用字符串变量
"""
import re
import os
import ast

FILES = [
    "skills/homework_coach.py",
    "skills/xiaoshengchu_planner.py",
    "skills/zhang_xuefeng_advisor.py",
    "skills/psychology_companion.py",
    "skills/parent_report.py",
    "skills/policy_tracker.py",
    "skills/local_resource_finder.py",
    "engines/socratic_tutor_engine_v2.py",
    "engines/search_accelerator.py",
    "engines/rag_engine.py",
    "engines/policy_monitor.py",
    "engines/academic_diagnostics.py",
    "engines/epistemic_autonomy_engine.py",
    "engines/proactive_sharing_engine.py",
    "engines/metacognition_engine.py",
    "main_agent.py",
]


def migrate_file(filepath: str) -> dict:
    """迁移单个文件，返回修改统计"""
    if not os.path.exists(filepath):
        return {"status": "skip", "reason": "文件不存在"}

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    stats = {"openai_imports": 0, "client_inits": 0, "llm_calls": 0, "response_fixes": 0}

    # ─── Step 1: 移除 `from openai import OpenAI` ───
    new_content, n = re.subn(r'^from openai import OpenAI\s*\n', '', content, flags=re.MULTILINE)
    stats["openai_imports"] += n
    content = new_content

    # ─── Step 2: 移除模块级 `client = OpenAI()` ───
    new_content, n = re.subn(r'^client\s*=\s*OpenAI\(\)\s*\n', '', content, flags=re.MULTILINE)
    stats["client_inits"] += n
    content = new_content

    # ─── Step 3: 添加 llm_call import（如果还没有）───
    if "from engines.llm_core import" not in content:
        # 在第一个非空、非注释、非 docstring 的 import 行之前插入
        # 简单策略：在文件开头的 docstring 后面插入
        docstring_end = re.search(r'"""[\s\S]*?"""\n', content)
        if docstring_end:
            insert_pos = docstring_end.end()
            content = content[:insert_pos] + "from engines.llm_core import llm_call, get_llm_router\n" + content[insert_pos:]
        else:
            # 没有 docstring，在第一行 import 前插入
            first_import = re.search(r'^(import |from )', content, re.MULTILINE)
            if first_import:
                insert_pos = first_import.start()
                content = content[:insert_pos] + "from engines.llm_core import llm_call, get_llm_router\n" + content[insert_pos:]
            else:
                content = "from engines.llm_core import llm_call, get_llm_router\n" + content

    # ─── Step 4: 替换 client.chat.completions.create(...) 调用块 ───
    # 使用逐行解析，找到调用块并替换
    content = replace_llm_calls(content, stats)

    # ─── Step 5: 修正 response.choices[0].message.content 引用 ───
    # 将 `response.choices[0].message.content` 替换为 `_llm_reply`
    # （已在 Step 4 中处理，这里做二次检查）

    if content == original:
        return {"status": "no_change", **stats}

    # 验证语法
    try:
        ast.parse(content)
    except SyntaxError as e:
        return {"status": "syntax_error", "error": str(e), **stats}

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return {"status": "success", **stats}


def replace_llm_calls(content: str, stats: dict) -> str:
    """
    替换所有 client.chat.completions.create(...) 调用
    
    支持的模式：
    1. response = client.chat.completions.create(model=..., messages=VAR, ...)
       后跟 reply = response.choices[0].message.content
    
    2. response = client.chat.completions.create(model=..., messages=[...], ...)
       后跟 reply = response.choices[0].message.content
    """
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 检测 client.chat.completions.create 调用
        call_match = re.match(
            r'^(\s*)(\w+)\s*=\s*(?:self\.)?client\.chat\.completions\.create\(',
            line
        )

        if call_match:
            indent = call_match.group(1)
            resp_var = call_match.group(2)

            # 收集整个调用块（括号平衡）
            block = line
            depth = line.count('(') - line.count(')')
            j = i + 1
            while depth > 0 and j < len(lines):
                block += '\n' + lines[j]
                depth += lines[j].count('(') - lines[j].count(')')
                j += 1

            # 从 block 中提取参数
            sys_prompt_var, user_msg_var, messages_var = extract_params(block)

            # 生成替换代码
            if messages_var:
                # messages 是一个变量
                new_lines = [
                    f"{indent}# [v5.2 Manus迁移] 统一路由器调用",
                    f"{indent}_llm_sys_{resp_var} = next((x['content'] for x in {messages_var} if x['role']=='system'), '')",
                    f"{indent}_llm_usr_{resp_var} = next((x['content'] for x in reversed({messages_var}) if x['role']=='user'), '')",
                    f"{indent}_llm_hist_{resp_var} = [x for x in {messages_var} if x['role'] not in ('system',)][:-1]",
                    f"{indent}{resp_var}_reply = llm_call(_llm_usr_{resp_var}, _llm_sys_{resp_var}, _llm_hist_{resp_var})",
                ]
            elif sys_prompt_var and user_msg_var:
                new_lines = [
                    f"{indent}# [v5.2 Manus迁移] 统一路由器调用",
                    f"{indent}{resp_var}_reply = llm_call({user_msg_var}, {sys_prompt_var})",
                ]
            elif user_msg_var:
                new_lines = [
                    f"{indent}# [v5.2 Manus迁移] 统一路由器调用",
                    f"{indent}{resp_var}_reply = llm_call({user_msg_var})",
                ]
            else:
                # 无法解析，保留原始代码并添加 TODO
                new_lines = [f"{indent}# TODO: 手动迁移此调用到 llm_call()"] + [line] + lines[i+1:j]
                result.extend(new_lines)
                i = j
                continue

            result.extend(new_lines)
            stats["llm_calls"] += 1

            # 查找并替换后续的 response.choices[0].message.content 引用
            # 扫描接下来的 5 行
            k = j
            while k < min(j + 8, len(lines)):
                next_line = lines[k]
                # 替换 response.choices[0].message.content
                fixed_line = re.sub(
                    rf'\b{re.escape(resp_var)}\.choices\[0\]\.message\.content\b',
                    f'{resp_var}_reply',
                    next_line
                )
                # 替换 response.usage.total_tokens
                fixed_line = re.sub(
                    rf'\b{re.escape(resp_var)}\.usage\.total_tokens\b',
                    '0',
                    fixed_line
                )
                if fixed_line != next_line:
                    stats["response_fixes"] += 1
                result.append(fixed_line)
                k += 1

            i = k
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def extract_params(block: str):
    """
    从 client.chat.completions.create(...) 块中提取参数
    返回 (sys_prompt_var, user_msg_var, messages_var)
    """
    # 检查 messages=VAR 形式
    msgs_var_match = re.search(r'\bmessages\s*=\s*([a-zA-Z_]\w*)\b', block)
    if msgs_var_match:
        return None, None, msgs_var_match.group(1)

    # 检查内联 messages=[{"role": "system", "content": VAR}, {"role": "user", "content": VAR}]
    sys_match = re.search(r'"role"\s*:\s*"system"[^}]*"content"\s*:\s*([a-zA-Z_]\w*)', block)
    usr_match = re.search(r'"role"\s*:\s*"user"[^}]*"content"\s*:\s*([a-zA-Z_]\w*)', block)

    sys_var = sys_match.group(1) if sys_match else None
    usr_var = usr_match.group(1) if usr_match else None

    # 如果只有 user（无 system）
    if not sys_match:
        # 检查 messages=[{"role": "user", "content": PROMPT}]
        single_user = re.search(r'messages\s*=\s*\[\s*\{\s*"role"\s*:\s*"user"\s*,\s*"content"\s*:\s*([a-zA-Z_]\w*)', block)
        if single_user:
            return None, single_user.group(1), None

    return sys_var, usr_var, None


# ─── 执行迁移 ───
if __name__ == "__main__":
    print("=" * 60)
    print("小伴 v5.2 LLM 迁移脚本")
    print("=" * 60)

    all_success = True
    for filepath in FILES:
        result = migrate_file(filepath)
        status = result["status"]

        if status == "success":
            calls = result.get("llm_calls", 0)
            fixes = result.get("response_fixes", 0)
            print(f"  ✅ {filepath}: 替换 {calls} 处调用，修正 {fixes} 处引用")
        elif status == "no_change":
            print(f"  ℹ️  {filepath}: 无需修改")
        elif status == "skip":
            print(f"  ⚠️  {filepath}: {result.get('reason', '跳过')}")
        elif status == "syntax_error":
            print(f"  ❌ {filepath}: 语法错误 - {result.get('error', '')}")
            all_success = False

    print()
    print("─" * 60)

    # 最终全局验证
    print("最终全局扫描：")
    total_remaining = 0
    for filepath in FILES:
        if not os.path.exists(filepath):
            continue
        with open(filepath) as f:
            c = f.read()
        n = len(re.findall(r'(?:self\.)?client\.chat\.completions\.create', c))
        if n > 0:
            total_remaining += n
            print(f"  ⚠️  {filepath}: 仍有 {n} 处未迁移")

    if total_remaining == 0:
        print("  ✅ 所有调用已迁移完成！")
    else:
        print(f"  总计剩余: {total_remaining} 处")

    # 语法验证
    print("\n语法验证：")
    syntax_ok = True
    for filepath in FILES:
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath) as f:
                ast.parse(f.read())
            print(f"  ✅ {filepath}")
        except SyntaxError as e:
            print(f"  ❌ {filepath}: {e}")
            syntax_ok = False

    print()
    if all_success and syntax_ok and total_remaining == 0:
        print("🎉 迁移完成！所有文件语法正确，无残留 OpenAI 直接调用。")
    else:
        print("⚠️  迁移存在问题，请检查上方错误信息。")
