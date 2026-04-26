"""
技能：policy_tracker
北京市/海淀区/丰台区教育政策追踪
"""
from engines.llm_core import llm_call, get_llm_router

import json
import os
from datetime import datetime
import requests
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base", "beijing_education_policy")


def save_policy(title: str, content: str, source: str, date: str = None):
    """保存政策文件到本地知识库"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date}_{title[:20].replace(' ', '_')}.json"
    data = {
        "title": title,
        "content": content,
        "source": source,
        "date": date,
        "saved_at": datetime.now().isoformat(),
    }
    with open(os.path.join(KB_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filename


def search_policy(query: str) -> str:
    """
    在本地政策库中搜索，并结合 LLM 给出解读
    """
    # 加载本地政策文件
    local_context = ""
    if os.path.exists(KB_DIR):
        for fname in sorted(os.listdir(KB_DIR), reverse=True)[:5]:
            fpath = os.path.join(KB_DIR, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)
                local_context += f"\n\n[{doc.get('date', '')}] {doc.get('title', '')}\n来源：{doc.get('source', '')}\n{doc.get('content', '')[:1000]}"

    messages = [
        {"role": "system", "content": """你是北京市教育政策专家，专注于海淀区和丰台区的小升初、中考、高考政策。
规则：
1. 政策信息必须注明来源和年份
2. 不确定的信息必须说"需以官方最新通知为准"
3. 特别关注：学籍在海淀、户籍在丰台的学生的特殊情况
4. 官方来源：北京市教委（jw.beijing.gov.cn）、海淀区教委、丰台区教委"""},
        {"role": "user", "content": f"政策查询：{query}\n\n本地政策库参考：{local_context if local_context else '（本地库为空，请基于通用知识回答）'}"}
    ]
    # [v5.2 Manus迁移] 统一路由器调用
    _llm_sys_resp = next((x['content'] for x in messages if x['role']=='system'), '')
    _llm_usr_resp = next((x['content'] for x in reversed(messages) if x['role']=='user'), '')
    _llm_hist_resp = [x for x in messages if x['role'] not in ('system',)][:-1]
    resp_reply = llm_call(_llm_usr_resp, _llm_sys_resp, _llm_hist_resp)
    return resp_reply.strip()


def get_key_policies() -> list[dict]:
    """
    返回当前最关键的政策关注点（静态知识，需定期人工更新）
    """
    return [
        {
            "title": "北京小升初政策核心原则",
            "summary": "以多校划片、电脑派位为主，鼓励就近入学。民办校实行摇号录取。",
            "source": "北京市教委",
            "note": "每年政策细节有调整，请关注当年3月前后的官方通知",
        },
        {
            "title": "海淀区小升初特殊说明",
            "summary": "海淀区优质初中资源丰富（人大附中、清华附中等），竞争激烈。学籍在海淀的学生参与海淀区派位。",
            "source": "海淀区教委",
            "note": "七一小学学籍学生参与海淀区派位，但户籍在丰台可能影响部分政策资格，需核实",
        },
        {
            "title": "丰台区户籍学生权益",
            "summary": "户籍在丰台但学籍在海淀的学生，在丰台区的派位资格需向丰台区教委确认。",
            "source": "丰台区教委",
            "note": "⚠️ 这是小可爱的关键矛盾点，建议家长尽早向两区教委分别咨询",
        },
    ]
