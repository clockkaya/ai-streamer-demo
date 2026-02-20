"""
tests.conftest
~~~~~~~~~~~~~~

共享 pytest fixtures —— mock 掉所有外部 API 调用（Gemini、Edge-TTS），
使单元测试可在无网络环境下快速运行。
"""
from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ── 在所有测试导入前设置环境变量 ─────────────────────────────────────
os.environ.setdefault("GEMINI_API_KEY", "test-fake-key")
os.environ.setdefault("ENVIRONMENT", "test")  # 激活 .env.test 配置


# ── Embedding Mock ────────────────────────────────────────────────────

FAKE_DIMENSION: int = 3072


def make_fake_embedding(seed: int = 0) -> list[float]:
    """生成一个确定性的假向量（基于 seed），方便测试相似度匹配。"""
    rng = np.random.RandomState(seed)
    return rng.randn(FAKE_DIMENSION).tolist()


class FakeEmbeddingResult:
    """模拟 Gemini Embedding API 返回结构。"""

    def __init__(self, values: list[float]) -> None:
        self.values = values


class FakeEmbedResponse:
    """模拟 ``client.models.embed_content()`` 的返回值。"""

    def __init__(self, values: list[float]) -> None:
        self.embeddings = [FakeEmbeddingResult(values)]


@pytest.fixture()
def mock_gemini_client() -> MagicMock:
    """返回一个 mock 的 ``genai.Client``，其 embed_content 方法返回假向量。"""
    client = MagicMock()

    # 根据输入文本的 hash 生成确定性向量，保证相同输入得到相同结果
    def _fake_embed(model: str, contents: str) -> FakeEmbedResponse:
        seed = hash(contents) % (2**31)
        return FakeEmbedResponse(make_fake_embedding(seed))

    client.models.embed_content.side_effect = _fake_embed
    return client


@pytest.fixture()
def sample_knowledge_file(tmp_path: Any) -> str:
    """在临时目录创建一个测试用知识库文件，返回文件路径。"""
    content = (
        "星瞳最喜欢的武器是粉色流星狙击枪。\n\n"
        "星瞳每周三晚上八点直播唱歌。\n\n"
        "星瞳最害怕青椒。"
    )
    file_path = tmp_path / "test_knowledge.txt"
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)
