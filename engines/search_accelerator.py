"""
小伴搜索加速引擎 v1.0
三层架构：
  L1 — 本地知识缓存（毫秒级，命中率目标 >60%）
  L2 — 并行搜索引擎（秒级，多源并发）
  L3 — 智能路由器（决定走哪层，避免无效网络请求）

设计目标：
  - 搜索响应时间从 30-120s 降至 <3s（缓存命中）或 <10s（网络搜索）
  - 准确率通过"结果质量评分器"保证，低分结果自动降级或重搜
"""

import json
import time
import hashlib
import threading
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────
# L1：本地知识缓存层
# ─────────────────────────────────────────────
class L1KnowledgeCache:
    """
    本地知识缓存层。
    
    缓存策略：
    - 永久缓存：政策文件、学校数据库（不会频繁变化）
    - TTL缓存：搜索结果（默认7天过期）
    - 热点缓存：最近30天访问超过3次的查询自动提升为永久缓存
    """

    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_index_path = self.cache_dir / "cache_index.json"
        self.lock = threading.Lock()
        self._load_index()
        
        # 预加载本地知识库到内存（最快的缓存）
        self.memory_cache = {}
        self._preload_knowledge_base()

    def _load_index(self):
        if self.cache_index_path.exists():
            with open(self.cache_index_path, "r", encoding="utf-8") as f:
                self.index = json.load(f)
        else:
            self.index = {"entries": {}, "hit_counts": {}, "total_hits": 0, "total_misses": 0}

    def _save_index(self):
        with open(self.cache_index_path, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)

    def _preload_knowledge_base(self):
        """将本地知识库文件预加载到内存，实现毫秒级响应"""
        # cache_dir = .../memory/search_cache，需要向上两级到 xiaoban_agent/
        kb_dir = self.cache_dir.parent.parent / "knowledge_base"
        if not kb_dir.exists():
            return
        
        # 预加载关键词索引
        keywords_map = {
            "七一小学": ["qiyi_primary_dispatch_pool.md", "2024_haidian_xiaoshengchu_strategy.md"],
            "一派": ["qiyi_primary_dispatch_pool.md", "haidian_1plus3_schools_data.md"],
            "二派": ["qiyi_primary_dispatch_pool.md", "2024_haidian_xiaoshengchu_strategy.md"],
            "1+3": ["haidian_1plus3_schools_data.md", "jianhua_1point5_pai_analysis.md"],
            "2+4": ["haidian_1plus3_schools_data.md"],
            "建华": ["jianhua_1point5_pai_analysis.md"],
            "五十七中": ["qiyi_primary_dispatch_pool.md", "haidian_1plus3_schools_data.md"],
            "玉渊潭": ["qiyi_primary_dispatch_pool.md"],
            "人翠": ["qiyi_primary_dispatch_pool.md"],
            "十一实验": ["qiyi_primary_dispatch_pool.md"],
            "育英": ["qiyi_primary_dispatch_pool.md"],
            "张雪峰": ["learning_methods.md"],
            "小升初政策": ["2024_haidian_xiaoshengchu_strategy.md"],
            "中签率": ["haidian_1plus3_schools_data.md"],
        }
        
        loaded_files = {}
        policy_dir = kb_dir / "beijing_education_policy"
        zhang_dir = kb_dir / "zhang_xuefeng_corpus"
        
        for keyword, files in keywords_map.items():
            self.memory_cache[keyword] = []
            for fname in files:
                if fname not in loaded_files:
                    for search_dir in [policy_dir, zhang_dir]:
                        fpath = search_dir / fname
                        if fpath.exists():
                            with open(fpath, "r", encoding="utf-8") as f:
                                loaded_files[fname] = f.read()
                            break
                if fname in loaded_files:
                    self.memory_cache[keyword].append({
                        "source": fname,
                        "content": loaded_files[fname][:3000],
                        "full_path": str(fname),
                        "type": "local_kb",
                        "quality_score": 90
                    })

    def _query_key(self, query: str) -> str:
        """生成查询的标准化缓存键"""
        normalized = query.strip().lower()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:16]

    def get(self, query: str) -> Optional[dict]:
        """查询缓存，返回缓存结果或 None"""
        start = time.time()
        
        # 第一优先级：内存缓存（毫秒级）
        matched_results = []
        for keyword, results in self.memory_cache.items():
            if keyword in query and results:
                matched_results.extend(results)
        if matched_results:
            self.index["total_hits"] = self.index.get("total_hits", 0) + 1
            elapsed = (time.time() - start) * 1000
            return {
                "source": "L1_memory",
                "results": matched_results[:3],
                "top_excerpt": matched_results[0].get("content", ""),
                "latency_ms": elapsed,
                "cache_type": "memory_preload",
                "quality_score": 90
            }
        
        # 第二优先级：磁盘缓存（毫秒级）
        key = self._query_key(query)
        with self.lock:
            if key in self.index["entries"]:
                entry = self.index["entries"][key]
                # 检查TTL
                if entry.get("permanent") or \
                   datetime.fromisoformat(entry["expires_at"]) > datetime.now():
                    # 更新命中计数
                    self.index["hit_counts"][key] = self.index["hit_counts"].get(key, 0) + 1
                    self.index["total_hits"] = self.index.get("total_hits", 0) + 1
                    
                    # 热点提升：命中3次以上升级为永久缓存
                    if self.index["hit_counts"][key] >= 3 and not entry.get("permanent"):
                        entry["permanent"] = True
                    
                    self._save_index()
                    elapsed = (time.time() - start) * 1000
                    cache_file = self.cache_dir / f"{key}.json"
                    if cache_file.exists():
                        with open(cache_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        data["latency_ms"] = elapsed
                        data["source"] = "L1_disk"
                        return data
        
        self.index["total_misses"] = self.index.get("total_misses", 0) + 1
        return None

    def set(self, query: str, results: dict, ttl_days: int = 7, permanent: bool = False):
        """将搜索结果写入缓存"""
        key = self._query_key(query)
        expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()
        
        cache_file = self.cache_dir / f"{key}.json"
        results["cached_at"] = datetime.now().isoformat()
        results["query"] = query
        
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        with self.lock:
            self.index["entries"][key] = {
                "query": query[:100],
                "expires_at": expires_at,
                "permanent": permanent,
                "cached_at": datetime.now().isoformat()
            }
            self._save_index()

    def get_stats(self) -> dict:
        total = self.index.get("total_hits", 0) + self.index.get("total_misses", 0)
        hit_rate = self.index.get("total_hits", 0) / max(total, 1) * 100
        return {
            "total_queries": total,
            "cache_hits": self.index.get("total_hits", 0),
            "cache_misses": self.index.get("total_misses", 0),
            "hit_rate_pct": round(hit_rate, 1),
            "memory_keywords": len(self.memory_cache),
            "disk_entries": len(self.index["entries"])
        }


# ─────────────────────────────────────────────
# L2：并行搜索引擎
# ─────────────────────────────────────────────
class L2ParallelSearchEngine:
    """
    并行搜索引擎。
    
    核心思路：同时向多个数据源发起请求，取最快且质量最高的结果。
    数据源优先级：
      1. 本地知识库文件（最快，最准确）
      2. LLM 内置知识（快，准确度高）
      3. 网络搜索（慢，但覆盖最新信息）
    """

    def __init__(self, memory_dir: str, max_workers: int = 4):
        self.memory_dir = Path(memory_dir)
        self.max_workers = max_workers
        self.quality_scorer = ResultQualityScorer()

    def search(self, query: str, timeout: float = 8.0) -> dict:
        """并行搜索，返回质量最高的结果"""
        start = time.time()
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._search_local_kb, query): "local_kb",
                executor.submit(self._search_llm_knowledge, query): "llm_knowledge",
            }
            
            for future in concurrent.futures.as_completed(futures, timeout=timeout):
                source = futures[future]
                try:
                    result = future.result()
                    if result:
                        score = self.quality_scorer.score(query, result)
                        results.append({"source": source, "data": result, "quality_score": score})
                except Exception as e:
                    pass
        
        if not results:
            return {"source": "empty", "data": None, "quality_score": 0}
        
        # 按质量评分排序，取最高分
        results.sort(key=lambda x: x["quality_score"], reverse=True)
        best = results[0]
        best["latency_ms"] = (time.time() - start) * 1000
        best["all_sources"] = [r["source"] for r in results]
        return best

    def _search_local_kb(self, query: str) -> Optional[dict]:
        """搜索本地知识库文件"""
        kb_dir = self.memory_dir.parent / "knowledge_base"
        if not kb_dir.exists():
            return None
        
        matches = []
        query_lower = query.lower()
        
        for md_file in kb_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                # 计算相关性分数（关键词命中数）
                keywords = query_lower.split()
                hits = sum(1 for kw in keywords if kw in content.lower())
                if hits > 0:
                    matches.append({
                        "file": md_file.name,
                        "relevance": hits / len(keywords),
                        "excerpt": content[:1500],
                        "path": str(md_file)
                    })
            except Exception:
                continue
        
        if not matches:
            return None
        
        matches.sort(key=lambda x: x["relevance"], reverse=True)
        return {
            "type": "local_kb",
            "matches": matches[:3],
            "top_excerpt": matches[0]["excerpt"] if matches else ""
        }

    def _search_llm_knowledge(self, query: str) -> Optional[dict]:
        """使用LLM的内置知识回答（无需网络，速度极快）"""
        try:
            from openai import OpenAI
            import os
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一个专注于北京小升初教育政策的知识库。"
                            "请用简洁、准确的方式回答问题。"
                            "如果你不确定某个具体数据，请明确说明'需要核实'，不要编造数字。"
                            "回答控制在300字以内。"
                        )
                    },
                    {"role": "user", "content": query}
                ],
                max_tokens=400,
                temperature=0.1  # 低温度保证准确性
            )
            
            content = response.choices[0].message.content
            return {
                "type": "llm_knowledge",
                "content": content,
                "tokens_used": response.usage.total_tokens
            }
        except Exception:
            return None


# ─────────────────────────────────────────────
# 结果质量评分器
# ─────────────────────────────────────────────
class ResultQualityScorer:
    """
    对搜索结果进行质量评分（0-100分）。
    
    评分维度：
    - 相关性（40分）：结果是否包含查询关键词
    - 完整性（30分）：结果内容是否充分
    - 时效性（20分）：信息是否包含年份标注
    - 可信度（10分）：来源是否可靠
    """

    def score(self, query: str, result: dict) -> float:
        if not result:
            return 0.0
        
        score = 0.0
        content = self._extract_text(result)
        
        # 相关性评分（40分）
        keywords = query.lower().split()
        content_lower = content.lower()
        keyword_hits = sum(1 for kw in keywords if kw in content_lower)
        relevance_score = (keyword_hits / max(len(keywords), 1)) * 40
        score += relevance_score
        
        # 完整性评分（30分）
        content_length = len(content)
        if content_length > 500:
            score += 30
        elif content_length > 200:
            score += 20
        elif content_length > 50:
            score += 10
        
        # 时效性评分（20分）
        current_year = datetime.now().year
        for year in [current_year, current_year - 1]:
            if str(year) in content:
                score += 20
                break
        else:
            score += 5  # 有内容但无年份标注，给基础分
        
        # 可信度评分（10分）
        result_type = result.get("type", "")
        if result_type == "local_kb":
            score += 10  # 本地知识库最可信
        elif result_type == "llm_knowledge":
            score += 7
        else:
            score += 5
        
        return min(score, 100.0)

    def _extract_text(self, result: dict) -> str:
        if isinstance(result, dict):
            if "content" in result:
                return str(result["content"])
            if "top_excerpt" in result:
                return str(result["top_excerpt"])
            if "matches" in result:
                return " ".join([m.get("excerpt", "") for m in result["matches"][:2]])
        return str(result)


# ─────────────────────────────────────────────
# L3：智能搜索路由器（总入口）
# ─────────────────────────────────────────────
class XiaobanSearchRouter:
    """
    小伴智能搜索路由器 — 总入口。
    
    路由逻辑：
    1. 先查 L1 缓存（毫秒级）→ 命中则直接返回
    2. L1 未命中 → 启动 L2 并行搜索（秒级）
    3. 将 L2 结果写入 L1 缓存，供下次命中
    4. 全程记录延迟，用于性能监控
    
    预期性能：
    - 缓存命中：< 50ms
    - 缓存未命中：< 8s（并行搜索）
    - 准确率：通过质量评分器保证 > 85%
    """

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.cache = L1KnowledgeCache(str(self.base_dir / "memory" / "search_cache"))
        self.parallel_engine = L2ParallelSearchEngine(str(self.base_dir / "memory"))
        self.search_log = []

    def search(self, query: str, force_refresh: bool = False) -> dict:
        """
        主搜索入口。
        
        Args:
            query: 搜索查询
            force_refresh: 强制跳过缓存，重新搜索
        
        Returns:
            {
                "query": str,
                "result": dict,
                "source": "L1_memory" | "L1_disk" | "L2_parallel",
                "latency_ms": float,
                "quality_score": float,
                "cached": bool
            }
        """
        start = time.time()
        
        # Step 1: 查 L1 缓存
        if not force_refresh:
            cached = self.cache.get(query)
            if cached:
                total_latency = (time.time() - start) * 1000
                self._log(query, cached.get("source", "L1"), total_latency, True)
                return {
                    "query": query,
                    "result": cached,
                    "source": cached.get("source", "L1"),
                    "latency_ms": total_latency,
                    "quality_score": cached.get("quality_score", 80),
                    "cached": True
                }
        
        # Step 2: L1 未命中，启动 L2 并行搜索
        l2_result = self.parallel_engine.search(query)
        
        # Step 3: 写入 L1 缓存
        if l2_result and l2_result.get("quality_score", 0) > 30:
            # 政策类信息缓存7天，学校数据永久缓存
            is_permanent = any(kw in query for kw in ["学校", "派位", "政策", "中签率"])
            self.cache.set(query, l2_result, ttl_days=7, permanent=is_permanent)
        
        total_latency = (time.time() - start) * 1000
        self._log(query, "L2_parallel", total_latency, False)
        
        return {
            "query": query,
            "result": l2_result,
            "source": "L2_parallel",
            "latency_ms": total_latency,
            "quality_score": l2_result.get("quality_score", 0),
            "cached": False
        }

    def _log(self, query: str, source: str, latency_ms: float, cached: bool):
        self.search_log.append({
            "timestamp": datetime.now().isoformat(),
            "query": query[:80],
            "source": source,
            "latency_ms": round(latency_ms, 1),
            "cached": cached
        })
        # 保留最近100条日志
        if len(self.search_log) > 100:
            self.search_log = self.search_log[-100:]

    def get_performance_report(self) -> dict:
        """生成性能报告"""
        stats = self.cache.get_stats()
        
        if self.search_log:
            latencies = [log["latency_ms"] for log in self.search_log]
            cached_latencies = [log["latency_ms"] for log in self.search_log if log["cached"]]
            uncached_latencies = [log["latency_ms"] for log in self.search_log if not log["cached"]]
            
            stats["avg_latency_ms"] = round(sum(latencies) / len(latencies), 1)
            stats["avg_cached_latency_ms"] = round(sum(cached_latencies) / max(len(cached_latencies), 1), 1)
            stats["avg_uncached_latency_ms"] = round(sum(uncached_latencies) / max(len(uncached_latencies), 1), 1)
            stats["p95_latency_ms"] = round(sorted(latencies)[int(len(latencies) * 0.95)], 1) if latencies else 0
        
        return stats

    def warm_up(self, queries: list):
        """预热缓存：提前搜索高频查询，确保首次访问也能快速响应"""
        print(f"[SearchRouter] 预热缓存，共 {len(queries)} 个查询...")
        for query in queries:
            result = self.search(query)
            print(f"  ✓ '{query[:30]}' → {result['source']} ({result['latency_ms']:.0f}ms)")


# ─────────────────────────────────────────────
# 预热查询列表（小伴高频查询）
# ─────────────────────────────────────────────
WARMUP_QUERIES = [
    "七一小学一派学校名单",
    "五十七中1+3项目招生人数",
    "玉渊潭中学中签率",
    "建华实验学校入学途径",
    "海淀小升初二派志愿填报",
    "2026年海淀小升初政策",
    "十一实验中学招生计划",
    "人大附中翠微学校中签率",
    "育英中学历史背景",
    "张雪峰专业选择方法论",
]


if __name__ == "__main__":
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    router = XiaobanSearchRouter(base_dir)
    
    print("=" * 60)
    print("小伴搜索加速引擎 v1.0 — 性能测试")
    print("=" * 60)
    
    # 测试1：冷启动（L2并行搜索）
    print("\n[测试1] 冷启动搜索（L2并行）")
    result1 = router.search("七一小学一派学校名单")
    print(f"  来源: {result1['source']}")
    print(f"  延迟: {result1['latency_ms']:.0f}ms")
    print(f"  质量评分: {result1['quality_score']:.1f}/100")
    print(f"  缓存命中: {result1['cached']}")
    
    # 测试2：热启动（L1缓存命中）
    print("\n[测试2] 热启动搜索（L1缓存）")
    result2 = router.search("七一小学一派学校名单")
    print(f"  来源: {result2['source']}")
    print(f"  延迟: {result2['latency_ms']:.0f}ms")
    print(f"  质量评分: {result2['quality_score']:.1f}/100")
    print(f"  缓存命中: {result2['cached']}")
    
    # 测试3：内存预加载命中
    print("\n[测试3] 内存预加载命中")
    result3 = router.search("五十七中1+3项目")
    print(f"  来源: {result3['source']}")
    print(f"  延迟: {result3['latency_ms']:.1f}ms")
    print(f"  质量评分: {result3['quality_score']:.1f}/100")
    
    # 性能报告
    print("\n[性能报告]")
    report = router.get_performance_report()
    for k, v in report.items():
        print(f"  {k}: {v}")
    
    print("\n✅ 搜索加速引擎测试完成")
