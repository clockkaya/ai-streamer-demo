"""
tests.test_vector_store
~~~~~~~~~~~~~~~~~~~~~~~

FAISSKnowledgeBase 单元测试。

所有 Gemini Embedding API 调用均通过 mock 替代，不依赖网络。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.rag.vector_store import FAISSKnowledgeBase


class TestFAISSKnowledgeBase:
    """向量知识库核心功能测试。"""

    def test_init_creates_empty_index(self, mock_gemini_client: MagicMock) -> None:
        """初始化后，FAISS 索引和 chunks 列表应为空。"""
        kb = FAISSKnowledgeBase(client=mock_gemini_client)

        assert kb.index.ntotal == 0
        assert kb.chunks == []
        assert kb.dimension == 3072

    def test_load_corpus_populates_index(
        self,
        mock_gemini_client: MagicMock,
        sample_knowledge_file: str,
    ) -> None:
        """加载知识库后，FAISS 索引和 chunks 应包含对应数据。"""
        kb = FAISSKnowledgeBase(client=mock_gemini_client)
        kb.load_corpus(sample_knowledge_file)

        # 文件有 3 段（用 \\n\\n 分隔）
        assert len(kb.chunks) == 3
        assert kb.index.ntotal == 3
        # embed_content 应被调用 3 次（每段一次）
        assert mock_gemini_client.models.embed_content.call_count == 3

    def test_load_corpus_missing_file(
        self,
        mock_gemini_client: MagicMock,
    ) -> None:
        """加载不存在的文件时，不报错，索引保持为空。"""
        kb = FAISSKnowledgeBase(client=mock_gemini_client)
        kb.load_corpus("/nonexistent/path/knowledge.txt")

        assert kb.index.ntotal == 0
        assert kb.chunks == []

    def test_search_returns_relevant_chunk(
        self,
        mock_gemini_client: MagicMock,
        sample_knowledge_file: str,
    ) -> None:
        """搜索应返回最相关的知识片段（非空字符串）。"""
        kb = FAISSKnowledgeBase(client=mock_gemini_client)
        kb.load_corpus(sample_knowledge_file)

        result: str = kb.search("武器")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_search_empty_index_returns_empty(
        self,
        mock_gemini_client: MagicMock,
    ) -> None:
        """空知识库搜索应返回空字符串。"""
        kb = FAISSKnowledgeBase(client=mock_gemini_client)

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

        kb = FAISSKnowledgeBase(client=mock_gemini_client)
        kb.load_corpus(str(empty_file))

        assert kb.index.ntotal == 0
        assert kb.chunks == []
