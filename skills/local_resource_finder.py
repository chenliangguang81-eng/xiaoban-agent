"""
技能：local_resource_finder
丰台东大街 5 号院周边学习资源推荐
"""

from openai import OpenAI

client = OpenAI()

# 静态资源库（需定期人工更新）
LOCAL_RESOURCES = {
    "libraries": [
        {"name": "北京市丰台区图书馆", "address": "丰台区", "note": "免费办证，有儿童阅览室"},
        {"name": "国家图书馆", "address": "海淀区中关村南大街33号", "note": "地铁4号线国家图书馆站，资源丰富"},
    ],
    "museums": [
        {"name": "中国科学技术馆", "address": "朝阳区北辰东路1号", "note": "科学启蒙，强烈推荐"},
        {"name": "北京自然博物馆", "address": "东城区天桥南大街126号", "note": "生物/地质科普"},
        {"name": "中国国家博物馆", "address": "东城区天安门广场东侧", "note": "历史文化"},
    ],
    "study_resources": [
        {"name": "丰台区青少年活动中心", "address": "丰台区", "note": "兴趣班、竞赛培训"},
    ],
    "note": "以上信息为参考，具体地址和开放时间请在百度地图/高德地图核实"
}

SKILL_PROMPT = """你是小伴的"本地资源推荐"模块，专注于北京市丰台区丰台东大街 5 号院社区周边的学习资源。

推荐原则：
1. 优先免费或低成本资源
2. 考虑交通便利性（丰台东大街附近）
3. 与学习目标相关（备考、兴趣拓展、科学启蒙）
4. 注明是否需要提前预约
5. 不推荐未经验证的商业培训机构（避免广告嫌疑）
"""

def find_resources(query: str) -> str:
    import json
    messages = [
        {"role": "system", "content": SKILL_PROMPT},
        {"role": "user", "content": f"查询：{query}\n\n本地资源库：{json.dumps(LOCAL_RESOURCES, ensure_ascii=False)}"}
    ]
    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        temperature=0.5,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()
