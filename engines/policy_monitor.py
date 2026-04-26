"""
小伴政策监控爬虫 v1.0
功能：
  1. 每日自动抓取海淀/丰台教委、知名升学网站的最新政策
  2. 与现有知识库内容对比，识别新增/变更信息
  3. 自动写入知识库并触发 RAG 索引重建
  4. 向家长发送变更摘要通知

监控来源：
  - 海淀区教委官网
  - 丰台区教委官网
  - 小升初网 (xschu.com)
  - 小升初信息网 (xscxx.com)
  - 知乎升学专栏
"""
from engines.llm_core import llm_call, get_llm_router

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import requests
from bs4 import BeautifulSoup


class PolicyMonitor:
    """实时政策监控爬虫"""

    # 监控目标列表
    WATCH_TARGETS = [
        {
            "name": "海淀区教委-义务教育入学",
            "url": "http://www.hdedu.gov.cn/xxgk/tzgg/",
            "keywords": ["小升初", "登记入学", "派位", "招生", "义务教育"],
            "priority": "high",
            "district": "haidian"
        },
        {
            "name": "小升初网-海淀政策",
            "url": "https://www.xschu.com/zhengcezixun/",
            "keywords": ["海淀", "小升初", "2026", "登记入学", "一派", "二派"],
            "priority": "high",
            "district": "haidian"
        },
        {
            "name": "小升初信息网-海淀",
            "url": "https://www.xscxx.com/xiaoshengchu/hdqxsc/",
            "keywords": ["海淀", "2026", "七一", "万寿路", "羊坊店"],
            "priority": "high",
            "district": "haidian"
        },
        {
            "name": "丰台区教委",
            "url": "http://www.fengtai.gov.cn/jyj/",
            "keywords": ["小升初", "入学", "招生", "派位"],
            "priority": "medium",
            "district": "fengtai"
        },
        {
            "name": "1+3项目政策",
            "url": "https://www.xscxx.com/zhonggaokao/13xm/",
            "keywords": ["1+3", "贯通", "2026", "申请", "招生"],
            "priority": "high",
            "district": "haidian"
        }
    ]

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.policy_dir = self.base_dir / "knowledge_base" / "beijing_education_policy"
        self.monitor_dir = self.base_dir / "memory" / "policy_monitor"
        self.monitor_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.monitor_dir / "monitor_state.json"
        self.alerts_file = self.monitor_dir / "policy_alerts.json"
        self.state = self._load_state()
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9"
        })

    def _load_state(self) -> dict:
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "last_check": None,
            "page_hashes": {},
            "known_articles": [],
            "total_checks": 0,
            "total_alerts": 0
        }

    def _save_state(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def _fetch_page(self, url: str, timeout: int = 10) -> Optional[str]:
        """抓取页面内容"""
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except Exception as e:
            print(f"[Monitor] 抓取失败 {url}: {e}")
            return None

    def _extract_articles(self, html: str, target: dict) -> list:
        """从页面提取文章列表"""
        if not html:
            return []
        
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        # 提取所有链接
        for a_tag in soup.find_all("a", href=True):
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")
            
            if len(title) < 5:
                continue
            
            # 检查是否包含关键词
            title_lower = title.lower()
            matched_keywords = [kw for kw in target["keywords"] if kw in title]
            
            if not matched_keywords:
                continue
            
            # 构建完整 URL
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(target["url"])
                full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
            else:
                full_url = target["url"].rstrip("/") + "/" + href
            
            articles.append({
                "title": title,
                "url": full_url,
                "source": target["name"],
                "keywords_matched": matched_keywords,
                "priority": target["priority"],
                "district": target["district"],
                "detected_at": datetime.now().isoformat()
            })
        
        return articles

    def _is_new_article(self, article: dict) -> bool:
        """判断是否为新文章（未见过的 URL）"""
        return article["url"] not in self.state["known_articles"]

    def _fetch_article_content(self, url: str) -> str:
        """抓取文章正文"""
        html = self._fetch_page(url)
        if not html:
            return ""
        
        soup = BeautifulSoup(html, "html.parser")
        
        # 移除脚本和样式
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        
        # 尝试提取正文
        content_selectors = [
            "article", ".content", ".article-content", ".post-content",
            "#content", ".detail", ".news-content", "main"
        ]
        
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text[:3000]
        
        # 回退：取 body 文本
        body = soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)[:3000]
        
        return ""

    def _summarize_with_llm(self, title: str, content: str) -> str:
        """用 LLM 生成政策摘要"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            prompt = f"""请对以下北京小升初政策文章进行简洁摘要（200字以内），重点提取：
1. 关键政策变化
2. 重要时间节点
3. 对海淀区七一小学学生的影响

文章标题：{title}
文章内容：{content[:1500]}"""
            
            # [v5.2 Manus迁移] 统一路由器调用
            response_reply = llm_call(prompt)
            return response_reply
        except Exception as e:
            # 降级：返回内容前200字
            return content[:200] + "..."

    def _save_to_knowledge_base(self, article: dict, content: str, summary: str):
        """将新政策文章保存到知识库"""
        date_str = datetime.now().strftime("%Y%m%d")
        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', article["title"])[:30]
        filename = f"policy_{date_str}_{safe_title}.md"
        filepath = self.policy_dir / filename
        
        md_content = f"""# {article["title"]}

**来源**：{article["source"]}
**URL**：{article["url"]}
**发现时间**：{article["detected_at"]}
**关键词**：{', '.join(article["keywords_matched"])}
**优先级**：{article["priority"]}

## 摘要

{summary}

## 原文内容

{content[:2000]}
"""
        
        filepath.write_text(md_content, encoding="utf-8")
        print(f"[Monitor] 已保存新政策：{filename}")
        return str(filepath)

    def _save_alert(self, alerts: list):
        """保存预警记录"""
        existing = []
        if self.alerts_file.exists():
            with open(self.alerts_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        
        existing.extend(alerts)
        # 只保留最近 100 条
        existing = existing[-100:]
        
        with open(self.alerts_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def check_once(self, max_new_articles: int = 5) -> dict:
        """
        执行一次政策检查
        返回：检查结果摘要
        """
        start = time.time()
        new_articles_found = []
        errors = []
        
        print(f"[Monitor] 开始政策检查，监控 {len(self.WATCH_TARGETS)} 个来源...")
        
        for target in self.WATCH_TARGETS:
            try:
                html = self._fetch_page(target["url"])
                if not html:
                    errors.append(f"{target['name']}: 抓取失败")
                    continue
                
                # 检查页面是否有变化
                page_hash = hashlib.md5(html.encode()).hexdigest()
                prev_hash = self.state["page_hashes"].get(target["url"])
                
                if prev_hash == page_hash:
                    print(f"[Monitor] {target['name']}: 无变化")
                    continue
                
                self.state["page_hashes"][target["url"]] = page_hash
                
                # 提取文章列表
                articles = self._extract_articles(html, target)
                new_articles = [a for a in articles if self._is_new_article(a)]
                
                print(f"[Monitor] {target['name']}: 发现 {len(new_articles)} 篇新文章")
                
                for article in new_articles[:max_new_articles]:
                    # 抓取正文
                    content = self._fetch_article_content(article["url"])
                    if not content:
                        continue
                    
                    # LLM 摘要
                    summary = self._summarize_with_llm(article["title"], content)
                    article["summary"] = summary
                    
                    # 保存到知识库
                    saved_path = self._save_to_knowledge_base(article, content, summary)
                    article["saved_path"] = saved_path
                    
                    # 记录已知文章
                    self.state["known_articles"].append(article["url"])
                    new_articles_found.append(article)
                    
                    time.sleep(1)  # 礼貌爬取间隔
                
            except Exception as e:
                errors.append(f"{target['name']}: {str(e)}")
                print(f"[Monitor] 错误 {target['name']}: {e}")
        
        # 更新状态
        self.state["last_check"] = datetime.now().isoformat()
        self.state["total_checks"] = self.state.get("total_checks", 0) + 1
        self.state["total_alerts"] = self.state.get("total_alerts", 0) + len(new_articles_found)
        self._save_state()
        
        # 保存预警
        if new_articles_found:
            self._save_alert(new_articles_found)
            # 触发 RAG 索引重建
            self._rebuild_rag_index()
        
        elapsed = time.time() - start
        
        result = {
            "check_time": self.state["last_check"],
            "sources_checked": len(self.WATCH_TARGETS),
            "new_articles": len(new_articles_found),
            "errors": errors,
            "elapsed_seconds": round(elapsed, 1),
            "articles": [
                {
                    "title": a["title"],
                    "source": a["source"],
                    "summary": a.get("summary", ""),
                    "priority": a["priority"]
                }
                for a in new_articles_found
            ]
        }
        
        return result

    def _rebuild_rag_index(self):
        """触发 RAG 索引重建"""
        try:
            import sys
            sys.path.insert(0, str(self.base_dir))
            from engines.rag_engine import RAGEngine
            rag = RAGEngine(str(self.base_dir))
            rag.build_index(force_rebuild=True)
            print("[Monitor] RAG 索引已重建")
        except Exception as e:
            print(f"[Monitor] RAG 索引重建失败: {e}")

    def get_recent_alerts(self, days: int = 7) -> list:
        """获取最近 N 天的政策预警"""
        if not self.alerts_file.exists():
            return []
        
        with open(self.alerts_file, "r", encoding="utf-8") as f:
            alerts = json.load(f)
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [a for a in alerts if a.get("detected_at", "") >= cutoff]

    def generate_parent_alert_message(self) -> str:
        """生成发送给家长的政策预警消息"""
        recent = self.get_recent_alerts(days=3)
        if not recent:
            return ""
        
        high_priority = [a for a in recent if a.get("priority") == "high"]
        
        lines = ["📢 **小伴政策预警**\n"]
        lines.append(f"过去3天发现 **{len(recent)}** 条新政策动态，其中 **{len(high_priority)}** 条高优先级：\n")
        
        for article in recent[:5]:
            priority_icon = "🔴" if article.get("priority") == "high" else "🟡"
            lines.append(f"{priority_icon} **{article['title']}**")
            lines.append(f"   来源：{article['source']}")
            if article.get("summary"):
                lines.append(f"   摘要：{article['summary'][:100]}...")
            lines.append("")
        
        lines.append("建议 Lion 及时查看以上政策变化，如有疑问请告知小伴。")
        return "\n".join(lines)

    def get_status(self) -> dict:
        return {
            "last_check": self.state.get("last_check"),
            "total_checks": self.state.get("total_checks", 0),
            "total_alerts": self.state.get("total_alerts", 0),
            "known_articles_count": len(self.state.get("known_articles", [])),
            "watch_targets": len(self.WATCH_TARGETS)
        }


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    monitor = PolicyMonitor(base_dir)
    
    print("=" * 60)
    print("小伴政策监控爬虫 v1.0 — 测试")
    print("=" * 60)
    
    print("\n[状态]")
    status = monitor.get_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    print("\n[执行一次检查（限速，仅检查前2个来源）]")
    # 测试时只检查前2个来源
    monitor.WATCH_TARGETS = monitor.WATCH_TARGETS[:2]
    result = monitor.check_once(max_new_articles=2)
    
    print(f"  检查来源: {result['sources_checked']}")
    print(f"  新文章数: {result['new_articles']}")
    print(f"  耗时: {result['elapsed_seconds']}s")
    if result['errors']:
        print(f"  错误: {result['errors']}")
    if result['articles']:
        print(f"  新发现:")
        for a in result['articles']:
            print(f"    [{a['priority']}] {a['title'][:50]}")
    
    print("\n✅ 政策监控爬虫测试完成")
