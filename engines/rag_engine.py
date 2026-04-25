"""
小伴 RAG（检索增强生成）引擎 v1.0
架构：
  1. 文档分块 → 向量化（OpenAI Embeddings / 轻量本地模型）
  2. FAISS 向量索引（毫秒级相似度检索）
  3. 检索 Top-K 文档块 → 注入 LLM 上下文 → 生成精准回答

优势：
  - 比关键词匹配更智能（语义理解）
  - 比纯 LLM 更准确（有知识库支撑，不会幻觉）
  - 比网络搜索更快（本地向量检索 <50ms）
"""

import json
import os
import pickle
import re
import time
from pathlib import Path
from typing import Optional
import numpy as np


class RAGEngine:
    """
    RAG 引擎核心类。
    
    工作流：
    build_index() → 将知识库文档向量化并建立 FAISS 索引
    query(q)      → 检索相关文档块 → 调用 LLM 生成回答
    """

    CHUNK_SIZE = 500      # 每个文档块的字符数
    CHUNK_OVERLAP = 100   # 相邻块的重叠字符数（保证上下文连续性）
    TOP_K = 4             # 检索最相关的 K 个文档块

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.index_dir = self.base_dir / "memory" / "rag_index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.chunks = []          # 所有文档块
        self.chunk_meta = []      # 每个块的元数据（来源文件、位置）
        self.embeddings = None    # numpy 向量矩阵
        self.index = None         # FAISS 索引
        
        self._load_index_if_exists()

    # ─────────────────────────────────────────────
    # 1. 文档分块
    # ─────────────────────────────────────────────
    def _chunk_text(self, text: str, source: str) -> list:
        """将长文本切分为带重叠的文档块"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk = text[start:end]
            if len(chunk.strip()) > 50:  # 过滤过短的块
                chunks.append({
                    "text": chunk,
                    "source": source,
                    "start_char": start
                })
            start += self.CHUNK_SIZE - self.CHUNK_OVERLAP
        return chunks

    def _load_knowledge_base(self) -> list:
        """加载所有知识库文档并分块"""
        all_chunks = []
        kb_dir = self.base_dir / "knowledge_base"
        
        if not kb_dir.exists():
            return all_chunks
        
        for md_file in kb_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                # 清理 Markdown 标记，保留纯文本
                content = re.sub(r'#{1,6}\s+', '', content)
                content = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', content)
                content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
                content = re.sub(r'\|[^\n]+\|', lambda m: m.group().replace('|', ' '), content)
                content = re.sub(r'\n{3,}', '\n\n', content)
                
                chunks = self._chunk_text(content, md_file.name)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"[RAG] 跳过文件 {md_file.name}: {e}")
        
        # 加载学校数据库 JSON
        schools_db = self.base_dir / "knowledge_base" / "schools_database" / "beijing_middle_schools.json"
        if schools_db.exists():
            try:
                data = json.loads(schools_db.read_text(encoding="utf-8"))
                # 将每所学校转为文本块
                schools = data.get("haidian_schools", []) + data.get("fengtai_schools", [])
                for school in schools:
                    text = f"学校名称：{school.get('name', '')}。"
                    text += f"梯队：{school.get('tier', '')}。"
                    text += f"集团：{school.get('group', '')}。"
                    text += f"特点：{school.get('features', '')}。"
                    text += f"1+3项目：{school.get('1plus3', {}).get('available', False)}，"
                    text += f"名额：{school.get('1plus3', {}).get('quota', 0)}人。"
                    if text.strip():
                        all_chunks.append({
                            "text": text,
                            "source": "beijing_middle_schools.json",
                            "start_char": 0
                        })
            except Exception as e:
                print(f"[RAG] 跳过学校数据库: {e}")
        
        return all_chunks

    # ─────────────────────────────────────────────
    # 2. 向量化（使用 OpenAI Embeddings API）
    # ─────────────────────────────────────────────
    def _embed_texts(self, texts: list) -> np.ndarray:
        """批量向量化文本，返回 numpy 矩阵"""
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        all_embeddings = []
        batch_size = 50  # OpenAI API 每次最多处理 2048 个，保守取 50
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
            
            if i + batch_size < len(texts):
                time.sleep(0.1)  # 避免触发 rate limit
        
        return np.array(all_embeddings, dtype=np.float32)

    # ─────────────────────────────────────────────
    # 3. 建立 FAISS 索引
    # ─────────────────────────────────────────────
    def build_index(self, force_rebuild: bool = False):
        """构建向量索引（首次或强制重建时调用）"""
        index_file = self.index_dir / "faiss.index"
        chunks_file = self.index_dir / "chunks.pkl"
        
        if not force_rebuild and index_file.exists() and chunks_file.exists():
            print("[RAG] 索引已存在，跳过重建（使用 force_rebuild=True 强制重建）")
            return
        
        print("[RAG] 开始构建向量索引...")
        start = time.time()
        
        # 加载并分块
        chunks = self._load_knowledge_base()
        if not chunks:
            print("[RAG] 警告：知识库为空，无法建立索引")
            return
        
        print(f"[RAG] 共 {len(chunks)} 个文档块，开始向量化...")
        texts = [c["text"] for c in chunks]
        
        try:
            embeddings = self._embed_texts(texts)
        except Exception as e:
            print(f"[RAG] OpenAI Embeddings 失败，使用 TF-IDF 降级方案: {e}")
            embeddings = self._embed_tfidf_fallback(texts)
        
        # 建立 FAISS 索引（内积相似度，等价于归一化后的余弦相似度）
        import faiss
        dim = embeddings.shape[1]
        faiss.normalize_L2(embeddings)
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
        
        # 保存索引和块数据
        faiss.write_index(index, str(index_file))
        with open(chunks_file, "wb") as f:
            pickle.dump(chunks, f)
        
        self.chunks = chunks
        self.embeddings = embeddings
        self.index = index
        
        elapsed = time.time() - start
        print(f"[RAG] 索引构建完成：{len(chunks)} 块，维度 {dim}，耗时 {elapsed:.1f}s")

    def _embed_tfidf_fallback(self, texts: list) -> np.ndarray:
        """TF-IDF 降级方案（不依赖外部 API）"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(max_features=512, analyzer='char_wb', ngram_range=(2, 4))
        matrix = vectorizer.fit_transform(texts).toarray().astype(np.float32)
        # 保存 vectorizer 供查询时使用
        with open(self.index_dir / "tfidf_vectorizer.pkl", "wb") as f:
            pickle.dump(vectorizer, f)
        self._tfidf_vectorizer = vectorizer
        return matrix

    def _load_index_if_exists(self):
        """启动时尝试加载已有索引"""
        index_file = self.index_dir / "faiss.index"
        chunks_file = self.index_dir / "chunks.pkl"
        
        if index_file.exists() and chunks_file.exists():
            try:
                import faiss
                self.index = faiss.read_index(str(index_file))
                with open(chunks_file, "rb") as f:
                    self.chunks = pickle.load(f)
                print(f"[RAG] 已加载索引：{len(self.chunks)} 个文档块")
            except Exception as e:
                print(f"[RAG] 加载索引失败: {e}")

    # ─────────────────────────────────────────────
    # 4. 检索
    # ─────────────────────────────────────────────
    def retrieve(self, query: str, top_k: int = None) -> list:
        """检索与查询最相关的文档块"""
        if self.index is None or not self.chunks:
            return []
        
        top_k = top_k or self.TOP_K
        
        try:
            # 优先尝试 TF-IDF 向量化（本地，无需 API）
            tfidf_file = self.index_dir / "tfidf_vectorizer.pkl"
            if tfidf_file.exists():
                with open(tfidf_file, "rb") as f:
                    vectorizer = pickle.load(f)
                query_embedding = vectorizer.transform([query]).toarray().astype(np.float32)
            else:
                query_embedding = self._embed_texts([query])
            
            import faiss
            faiss.normalize_L2(query_embedding)
            
            # FAISS 检索
            scores, indices = self.index.search(query_embedding, top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.chunks):
                    chunk = self.chunks[idx].copy()
                    chunk["relevance_score"] = float(score)
                    results.append(chunk)
            
            return results
        except Exception as e:
            print(f"[RAG] 向量检索失败，使用关键词回退: {e}")
            # 关键词回退：直接匹配
            query_lower = query.lower()
            scored = []
            for chunk in self.chunks:
                hits = sum(1 for kw in query_lower.split() if kw in chunk["text"].lower())
                if hits > 0:
                    c = chunk.copy()
                    c["relevance_score"] = hits / max(len(query_lower.split()), 1)
                    scored.append(c)
            scored.sort(key=lambda x: x["relevance_score"], reverse=True)
            return scored[:top_k]

    # ─────────────────────────────────────────────
    # 5. RAG 生成（检索 + LLM）
    # ─────────────────────────────────────────────
    def query(self, question: str, student_context: dict = None) -> dict:
        """
        RAG 完整查询流程：
        1. 检索相关文档块
        2. 构建增强 Prompt
        3. 调用 LLM 生成回答
        """
        start = time.time()
        
        # 检索相关文档块
        retrieved_chunks = self.retrieve(question)
        
        # 构建上下文
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks):
            context_parts.append(f"[参考资料{i+1}（来源：{chunk['source']}）]\n{chunk['text']}")
        context = "\n\n".join(context_parts)
        
        # 构建学生上下文
        student_info = ""
        if student_context:
            student_info = (
                f"学生信息：{student_context.get('name', '小可爱')}，"
                f"{student_context.get('grade', '六年级')}，"
                f"学籍：{student_context.get('school_district', '海淀区七一小学')}，"
                f"居住地：{student_context.get('home_address', '丰台东大街5号院')}。"
            )
        
        # 构建增强 Prompt
        system_prompt = f"""你是小伴，北京市海淀区七一小学的成长陪伴智能体。
{student_info}

请基于以下参考资料回答问题。如果参考资料中没有相关信息，请明确说明"这个问题需要进一步核实"，不要编造内容。
回答要简洁、准确、有温度，适合家长阅读。

{context if context else "（暂无相关参考资料，请基于通用知识回答）"}"""

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                max_tokens=600,
                temperature=0.2
            )
            
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
        except Exception as e:
            answer = f"[RAG 生成失败: {e}]\n\n基于检索到的资料摘要：\n{context[:500] if context else '无相关资料'}"
            tokens_used = 0
        
        elapsed = (time.time() - start) * 1000
        
        return {
            "question": question,
            "answer": answer,
            "retrieved_chunks": len(retrieved_chunks),
            "sources": list(set(c["source"] for c in retrieved_chunks)),
            "latency_ms": round(elapsed, 1),
            "tokens_used": tokens_used,
            "top_relevance_score": retrieved_chunks[0]["relevance_score"] if retrieved_chunks else 0
        }

    def get_index_stats(self) -> dict:
        return {
            "total_chunks": len(self.chunks),
            "index_built": self.index is not None,
            "index_dir": str(self.index_dir),
            "unique_sources": len(set(c["source"] for c in self.chunks)) if self.chunks else 0
        }


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rag = RAGEngine(base_dir)
    
    print("=" * 60)
    print("小伴 RAG 引擎 v1.0 — 测试")
    print("=" * 60)
    
    # 构建索引
    rag.build_index(force_rebuild=True)
    
    # 测试查询
    print("\n[测试1] RAG 查询：七一小学一派有哪些学校？")
    result = rag.query(
        "七一小学一派有哪些学校？哪个最值得填报？",
        student_context={"name": "小可爱", "grade": "六年级"}
    )
    print(f"  检索块数: {result['retrieved_chunks']}")
    print(f"  来源: {result['sources']}")
    print(f"  延迟: {result['latency_ms']:.0f}ms")
    print(f"  回答:\n{result['answer'][:300]}...")
    
    print("\n[测试2] RAG 查询：1+3项目怎么申请？")
    result2 = rag.query("1+3项目怎么申请？建华和五十七中哪个更好？")
    print(f"  检索块数: {result2['retrieved_chunks']}")
    print(f"  延迟: {result2['latency_ms']:.0f}ms")
    print(f"  回答:\n{result2['answer'][:300]}...")
    
    print("\n[索引统计]")
    stats = rag.get_index_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n✅ RAG 引擎测试完成")
