"""
app.rag.vector_store
~~~~~~~~~~~~~~~~~~~~

基于 FAISS 的本地向量知识库，使用 Gemini Embedding API 将文本转为向量。

用于 RAG（检索增强生成）流程中的知识检索环节。Agent 可独立优化检索算法
（如改用 HNSW 索引、调整分段策略）而不影响 LLM 调用逻辑。
"""
from __future__ import annotations

import os

import faiss
import numpy as np
from google import genai

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.client import create_gemini_client

logger = get_logger(__name__)


class FAISSKnowledgeBase:
    """基于 FAISS IndexFlatL2 的向量知识库。

    Attributes:
        dimension: 向量维度（需与 Embedding 模型输出一致）。
        index: FAISS 索引实例。
        chunks: 已入库的原始文本段落列表。
    """

    def __init__(
        self,
        dimension: int | None = None,
        client: genai.Client | None = None,
    ) -> None:
        """初始化知识库。

        Args:
            dimension: 向量维度，默认读取 ``settings.EMBEDDING_DIMENSION``。
            client: 可选的 ``genai.Client`` 实例（用于测试注入 mock）。
        """
        self.dimension: int = dimension or settings.EMBEDDING_DIMENSION
        # L2 距离索引，适合中小规模知识库的精确检索
        self.index: faiss.IndexFlatL2 = faiss.IndexFlatL2(self.dimension)
        self.chunks: list[str] = []
        self._client: genai.Client = client or create_gemini_client()

    def _get_embedding(self, text: str) -> list[float]:
        """调用 Gemini Embedding API 将文本转换为向量。

        Args:
            text: 待向量化的文本。

        Returns:
            浮点数列表，长度等于 ``self.dimension``。
        """
        result = self._client.models.embed_content(
            model=settings.EMBEDDING_MODEL,
            contents=text,
        )
        return result.embeddings[0].values

    def load_corpus(self, file_path: str) -> None:
        """从文本文件加载知识库，按空行分段后逐段嵌入并添加到 FAISS 索引。

        Args:
            file_path: 知识库文本文件的绝对路径。
        """
        if not os.path.exists(file_path):
            logger.warning("找不到知识库文件: %s", file_path)
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 按空行分段，每段作为一个独立的知识条目
        raw_chunks: list[str] = [c.strip() for c in content.split("\n\n") if c.strip()]
        if not raw_chunks:
            return

        # 逐段生成向量并批量写入 FAISS 索引
        embeddings: list[list[float]] = []
        for chunk in raw_chunks:
            self.chunks.append(chunk)
            embeddings.append(self._get_embedding(chunk))

        emb_matrix: np.ndarray = np.array(embeddings, dtype=np.float32)
        self.index.add(emb_matrix)
        logger.info("RAG 知识库加载完成，共入库 %d 条设定", len(self.chunks))

    def search(self, query: str, top_k: int = 1) -> str:
        """检索与查询最相似的知识片段。

        Args:
            query: 用户查询文本。
            top_k: 返回的最大结果数。

        Returns:
            拼接后的知识文本。若知识库为空或无匹配，返回空字符串。
        """
        if self.index.ntotal == 0:
            return ""

        # 将查询文本向量化，然后在 FAISS 索引中做近邻搜索
        q_emb: np.ndarray = np.array(
            [self._get_embedding(query)], dtype=np.float32,
        )
        _distances, indices = self.index.search(q_emb, top_k)

        # 过滤无效索引（-1 表示不足 top_k 个结果）
        results: list[str] = []
        for idx in indices[0]:
            if idx != -1 and idx < len(self.chunks):
                results.append(self.chunks[idx])

        return "\n".join(results)