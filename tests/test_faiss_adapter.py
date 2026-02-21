"""
tests.test_faiss_adapter
~~~~~~~~~~~~~~~~~~~~~~~

FAISSAdapter 单元测试。

所有 Gemini Embedding API 调用均通过 mock 替代，不依赖网络。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.rag.faiss_adapter import FAISSAdapter


class TestFAISSAdapter:
    """向量知识库核心功能测试。"""

    def test_init_creates_empty_index(self, mock_gemini_client: MagicMock) -> None:
        """初始化后，FAISS 索引和 chunks 列表应为空。"""
        kb = FAISSAdapter(client=mock_gemini_client)

        assert kb.index.ntotal == 0
        assert kb.chunks == []
        assert kb.dimension == 3072

    def test_load_corpus_populates_index(
        self,
        mock_gemini_client: MagicMock,
        sample_knowledge_file: str,
    ) -> None:
        """加载知识库后，FAISS 索引和 chunks 应包含对应数据。"""
        kb = FAISSAdapter(client=mock_gemini_client)
        kb.load_corpus(sample_knowledge_file)

        # 使用滑动窗口分段，段数可能与原始空行分段不同
        assert len(kb.chunks) > 0
        assert kb.index.ntotal == len(kb.chunks)
        # embed_content 应被调用（每段一次）
        assert mock_gemini_client.models.embed_content.call_count == len(kb.chunks)

    def test_load_corpus_missing_file(
        self,
        mock_gemini_client: MagicMock,
    ) -> None:
        """加载不存在的文件时，不报错，索引保持为空。"""
        kb = FAISSAdapter(client=mock_gemini_client)
        kb.load_corpus("/nonexistent/path/knowledge.txt")

        assert kb.index.ntotal == 0
        assert kb.chunks == []

    def test_search_returns_relevant_chunk(
        self,
        mock_gemini_client: MagicMock,
        sample_knowledge_file: str,
    ) -> None:
        """搜索应返回最相关的知识片段（非空字符串），前提是距离在阈值内。"""
        # 使用足够大的阈值确保能命中（mock 随机向量的 L2 距离很大）
        kb = FAISSAdapter(
            client=mock_gemini_client, distance_threshold=1e9,
        )
        kb.load_corpus(sample_knowledge_file)

        result: str = kb.search("武器")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_empty_index_returns_empty(
        self,
        mock_gemini_client: MagicMock,
    ) -> None:
        """空知识库搜索应返回空字符串。"""
        kb = FAISSAdapter(client=mock_gemini_client)

        result: str = kb.search("任意查询")

        assert result == ""

    def test_load_corpus_empty_content(
        self,
        mock_gemini_client: MagicMock,
        tmp_path: object,
    ) -> None:
        """加载空文件时，索引应保持为空。"""
        empty_file = tmp_path / "empty.txt"  # type: ignore[union-attr]
        empty_file.write_text("", encoding="utf-8")

        kb = FAISSAdapter(client=mock_gemini_client)
        kb.load_corpus(str(empty_file))

        assert kb.index.ntotal == 0
        assert kb.chunks == []

    def test_distance_threshold_filters_results(
        self,
        mock_gemini_client: MagicMock,
        sample_knowledge_file: str,
    ) -> None:
        """距离超过阈值的结果应被过滤掉。"""
        # 设置极小的阈值，确保所有 mock 结果都超阈值
        kb = FAISSAdapter(
            client=mock_gemini_client, distance_threshold=0.0001,
        )
        kb.load_corpus(sample_knowledge_file)

        result: str = kb.search("任意查询")
        # 阈值极小，应该什么都命中不了
        assert result == ""

    def test_load_corpus_md_format(
        self,
        mock_gemini_client: MagicMock,
        sample_knowledge_md_file: str,
    ) -> None:
        """加载 .md 格式的知识库文件。"""
        kb = FAISSAdapter(client=mock_gemini_client)
        kb.load_corpus(sample_knowledge_md_file)

        assert len(kb.chunks) > 0
        assert kb.index.ntotal == len(kb.chunks)

    def test_load_corpus_json_format(
        self,
        mock_gemini_client: MagicMock,
        sample_knowledge_json_file: str,
    ) -> None:
        """加载 .json 格式的知识库文件。"""
        kb = FAISSAdapter(client=mock_gemini_client)
        kb.load_corpus(sample_knowledge_json_file)

        assert len(kb.chunks) > 0
        assert kb.index.ntotal == len(kb.chunks)

    def test_load_directory(
        self,
        mock_gemini_client: MagicMock,
        sample_knowledge_dir: str,
    ) -> None:
        """load_directory 应加载目录中所有支持格式的文件。"""
        kb = FAISSAdapter(client=mock_gemini_client)
        kb.load_directory(sample_knowledge_dir)

        # 目录中有 3 个文件（txt, md, json），每个至少产生 1 个 chunk
        assert len(kb.chunks) >= 3
        assert kb.index.ntotal == len(kb.chunks)
