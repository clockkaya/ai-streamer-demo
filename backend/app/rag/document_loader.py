"""
app.rag.document_loader
~~~~~~~~~~~~~~

多格式知识库文件加载器，支持 ``.txt`` / ``.md`` / ``.json``。

将不同格式的文件统一转换为纯文本，供分段器和向量知识库使用。
"""
from __future__ import annotations

import json
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

# 支持的文件扩展名集合
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md", ".json"})


class KnowledgeLoader:
    """多格式知识库加载器。

    根据文件扩展名自动选择解析策略，将文件内容转换为纯文本字符串。
    """

    def load_file(self, file_path: str | Path) -> str:
        """加载单个文件并返回纯文本。

        Args:
            file_path: 文件路径（绝对或相对）。

        Returns:
            文件内容的纯文本表示。不支持的格式或文件不存在时返回空字符串。
        """
        path = Path(file_path)
        if not path.is_file():
            logger.warning("文件不存在: %s", path)
            return ""

        ext: str = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.debug("跳过不支持的文件格式: %s", path)
            return ""

        try:
            raw: str = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning("读取文件失败 %s: %s", path, e)
            return ""

        if ext in (".txt", ".md"):
            return raw

        if ext == ".json":
            return self._parse_json(raw, str(path))

        return ""

    def load_directory(self, dir_path: str | Path) -> list[tuple[str, str]]:
        """递归遍历目录，加载所有支持格式的文件。

        Args:
            dir_path: 目录路径（绝对或相对）。

        Returns:
            列表，每项为 ``(file_path, text)`` 元组。
            仅包含内容非空的文件。
        """
        directory = Path(dir_path)
        if not directory.is_dir():
            logger.warning("目录不存在: %s", directory)
            return []

        results: list[tuple[str, str]] = []
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                text: str = self.load_file(file_path)
                if text:
                    results.append((str(file_path), text))

        logger.info("从目录 %s 加载了 %d 个知识库文件", directory, len(results))
        return results

    @staticmethod
    def _parse_json(raw: str, file_path: str) -> str:
        """解析 JSON 知识库文件。

        支持两种格式：
        - ``list[str]``: 直接拼接所有字符串
        - ``list[dict]``: 取每个 dict 的所有 value 拼接为一段

        Args:
            raw: JSON 原始字符串。
            file_path: 文件路径（用于日志）。

        Returns:
            拼接后的纯文本。格式不符时返回空字符串。
        """
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("JSON 解析失败 %s: %s", file_path, e)
            return ""

        if not isinstance(data, list) or not data:
            logger.warning("JSON 知识库 %s 顶层应为非空列表", file_path)
            return ""

        # list[str] — 直接拼接
        if all(isinstance(item, str) for item in data):
            return "\n\n".join(item for item in data if item.strip())

        # list[dict] — 取每个 dict 的 value 拼接
        if all(isinstance(item, dict) for item in data):
            segments: list[str] = []
            for item in data:
                values = [str(v) for v in item.values() if str(v).strip()]
                if values:
                    segments.append("\n".join(values))
            return "\n\n".join(segments)

        logger.warning("JSON 知识库 %s 格式不支持（需 list[str] 或 list[dict]）", file_path)
        return ""
