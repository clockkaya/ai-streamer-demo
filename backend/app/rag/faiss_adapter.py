"""
app.rag.faiss_adapter
~~~~~~~~~~~~~~~~~~~~

基于 FAISS 的本地向量知识库，使用 Gemini Embedding API 将文本转为向量。

用于 RAG（检索增强生成）流程中的知识检索环节。
支持滑动窗口分段、L2 距离阈值过滤、多格式知识库加载。
"""
from __future__ import annotations

import os

import faiss
import numpy as np
from google import genai

from app.core.settings import settings
from app.core.logging import get_logger
from app.llm.client import create_gemini_client
from app.rag.text_chunker import SlidingWindowChunker
from app.rag.document_loader import KnowledgeLoader

logger = get_logger(__name__)


class FAISSAdapter:
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
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        distance_threshold: float | None = None,
    ) -> None:
        """初始化知识库。

        Args:
            dimension: 向量维度，默认读取 ``settings.EMBEDDING_DIMENSION``。
            client: 可选的 ``genai.Client`` 实例（用于测试注入 mock）。
            chunk_size: 滑动窗口分段大小，默认读取 ``settings.RAG_CHUNK_SIZE``。
            chunk_overlap: 分段重叠字符数，默认读取 ``settings.RAG_CHUNK_OVERLAP``。
            distance_threshold: L2 距离阈值，默认读取 ``settings.RAG_DISTANCE_THRESHOLD``。
        """
        self.dimension: int = dimension or settings.EMBEDDING_DIMENSION
        # L2 距离索引，适合中小规模知识库的精确检索
        self.index: faiss.IndexFlatL2 = faiss.IndexFlatL2(self.dimension)
        self.chunks: list[str] = []
        self._client: genai.Client = client or create_gemini_client()

        # 分段器与阈值
        _chunk_size: int = chunk_size or settings.RAG_CHUNK_SIZE
        _chunk_overlap: int = chunk_overlap if chunk_overlap is not None else settings.RAG_CHUNK_OVERLAP
        self._chunker: SlidingWindowChunker = SlidingWindowChunker(
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap,
        )
        self._distance_threshold: float = (
            distance_threshold if distance_threshold is not None
            else settings.RAG_DISTANCE_THRESHOLD
        )
        self._loader: KnowledgeLoader = KnowledgeLoader()

    async def _get_embedding(self, text: str) -> list[float]:
        """调用 Gemini Embedding API 将文本转换为向量 (非阻塞)。

        Args:
            text: 待向量化的文本。

        Returns:
            浮点数列表，长度等于 ``self.dimension``。
        """
        result = await self._client.aio.models.embed_content(
            model=settings.EMBEDDING_MODEL,
            contents=text,
        )
        return result.embeddings[0].values

    async def _add_text(self, text: str) -> int:
        """将纯文本经分段、向量化后添加到 FAISS 索引。

        Args:
            text: 待入库的纯文本。

        Returns:
            本次新增的 chunk 数量。
        """
        new_chunks: list[str] = self._chunker.chunk(text)
        if not new_chunks:
            return 0

        embeddings: list[list[float]] = []
        for chunk in new_chunks:
            self.chunks.append(chunk)
            embeddings.append(await self._get_embedding(chunk))

        emb_matrix: np.ndarray = np.array(embeddings, dtype=np.float32)
        self.index.add(emb_matrix)
        return len(new_chunks)

    async def load_corpus(self, file_path: str) -> None:
        """从文件加载知识库，使用滑动窗口分段后逐段嵌入并添加到 FAISS 索引。

        支持 ``.txt`` / ``.md`` / ``.json`` 格式。

        Args:
            file_path: 知识库文件的绝对路径。
        """
        text: str = self._loader.load_file(file_path)
        if not text:
            return

        count: int = await self._add_text(text)
        logger.info("RAG 知识库加载完成 [%s]，共入库 %d 条设定", file_path, count)

    async def load_directory(self, dir_path: str) -> None:
        """从目录递归加载所有支持格式的知识库文件。

        Args:
            dir_path: 知识库目录的绝对路径。
        """
        file_texts: list[tuple[str, str]] = self._loader.load_directory(dir_path)
        total: int = 0
        for file_path, text in file_texts:
            count: int = await self._add_text(text)
            logger.debug("  加载文件 %s → %d 条", file_path, count)
            total += count

        logger.info("RAG 目录加载完成 [%s]，共入库 %d 条设定", dir_path, total)

    async def search(self, query: str, top_k: int = 1) -> str:
        """检索与查询最相似的知识片段。

        使用 L2 距离阈值过滤：距离超过 ``distance_threshold`` 的结果被视为不命中。

        Args:
            query: 用户查询文本。
            top_k: 返回的最大结果数。

        Returns:
            拼接后的知识文本。若知识库为空、无匹配或全部超阈值，返回空字符串。
        """
        if self.index.ntotal == 0:
            return ""

        # 将查询文本向量化，然后在 FAISS 索引中做近邻搜索
        embedding = await self._get_embedding(query)
        q_emb: np.ndarray = np.array(
            [embedding], dtype=np.float32,
        )
        distances, indices = self.index.search(q_emb, top_k)

        # 过滤无效索引（-1）和距离超阈值的结果
        results: list[str] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx < len(self.chunks) and dist <= self._distance_threshold:
                results.append(self.chunks[idx])

        return "\n".join(results)