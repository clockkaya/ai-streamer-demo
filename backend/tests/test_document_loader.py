"""
tests.test_document_loader
~~~~~~~~~~~~~~~~~

KnowledgeLoader 单元测试。
"""
from __future__ import annotations

import json
from typing import Any

from app.rag.document_loader import KnowledgeLoader


class TestKnowledgeLoader:
    """多格式知识库加载器测试。"""

    def test_load_txt_file(self, tmp_path: Any) -> None:
        """加载 .txt 文件应返回文件全文。"""
        f = tmp_path / "test.txt"
        f.write_text("你好世界", encoding="utf-8")

        loader = KnowledgeLoader()
        result = loader.load_file(str(f))
        assert result == "你好世界"

    def test_load_md_file(self, tmp_path: Any) -> None:
        """加载 .md 文件应返回 Markdown 原文。"""
        content = "# 标题\n\n这是正文。\n\n- 列表项"
        f = tmp_path / "test.md"
        f.write_text(content, encoding="utf-8")

        loader = KnowledgeLoader()
        result = loader.load_file(str(f))
        assert result == content

    def test_load_json_list_str(self, tmp_path: Any) -> None:
        """加载 list[str] 格式的 .json 文件应拼接所有字符串。"""
        data = ["第一条知识", "第二条知识", "第三条知识"]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        loader = KnowledgeLoader()
        result = loader.load_file(str(f))
        assert "第一条知识" in result
        assert "第二条知识" in result
        assert "第三条知识" in result

    def test_load_json_list_dict(self, tmp_path: Any) -> None:
        """加载 list[dict] 格式的 .json 文件应取 value 拼接。"""
        data = [
            {"question": "什么是AI", "answer": "人工智能"},
            {"question": "什么是ML", "answer": "机器学习"},
        ]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        loader = KnowledgeLoader()
        result = loader.load_file(str(f))
        assert "人工智能" in result
        assert "机器学习" in result

    def test_load_unsupported_format(self, tmp_path: Any) -> None:
        """不支持的格式应返回空字符串。"""
        f = tmp_path / "test.csv"
        f.write_text("a,b,c", encoding="utf-8")

        loader = KnowledgeLoader()
        result = loader.load_file(str(f))
        assert result == ""

    def test_load_nonexistent_file(self) -> None:
        """文件不存在应返回空字符串，不报错。"""
        loader = KnowledgeLoader()
        result = loader.load_file("/nonexistent/path/file.txt")
        assert result == ""

    def test_load_directory(self, tmp_path: Any) -> None:
        """load_directory 应递归加载目录中所有支持的文件。"""
        # 创建多种格式的文件
        (tmp_path / "a.txt").write_text("文本内容", encoding="utf-8")
        (tmp_path / "b.md").write_text("# MD 标题", encoding="utf-8")
        (tmp_path / "c.json").write_text(
            json.dumps(["JSON知识"], ensure_ascii=False), encoding="utf-8",
        )
        # 不支持的格式
        (tmp_path / "d.csv").write_text("skip", encoding="utf-8")

        loader = KnowledgeLoader()
        results = loader.load_directory(str(tmp_path))

        assert len(results) == 3
        paths = [r[0] for r in results]
        texts = [r[1] for r in results]
        assert any("文本内容" in t for t in texts)
        assert any("MD 标题" in t for t in texts)
        assert any("JSON知识" in t for t in texts)

    def test_load_directory_nonexistent(self) -> None:
        """目录不存在应返回空列表。"""
        loader = KnowledgeLoader()
        result = loader.load_directory("/nonexistent/dir")
        assert result == []

    def test_load_json_invalid(self, tmp_path: Any) -> None:
        """非法 JSON 应返回空字符串。"""
        f = tmp_path / "bad.json"
        f.write_text("{not valid json", encoding="utf-8")

        loader = KnowledgeLoader()
        result = loader.load_file(str(f))
        assert result == ""
