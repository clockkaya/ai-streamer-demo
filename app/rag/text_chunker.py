"""
app.rag.text_chunker
~~~~~~~~~~~~~~~

滑动窗口文本分段器，将长文本切分为定长、可重叠的 chunk。

相比简单按空行分段，滑动窗口能保证：
- 每段长度可控（不超过 ``chunk_size``）
- 相邻段之间有 ``chunk_overlap`` 字符的重叠，减少语义截断
"""
from __future__ import annotations


class SlidingWindowChunker:
    """基于字符长度的滑动窗口分段器。

    按自然段落（``\\n\\n`` 或 ``\\n``）预分割文本，再贪心合并段落直至达到
    ``chunk_size``，回退 ``chunk_overlap`` 字符作为下一窗口的起点。

    Attributes:
        chunk_size: 每段最大字符数。
        chunk_overlap: 相邻段重叠字符数。
    """

    def __init__(self, chunk_size: int = 256, chunk_overlap: int = 64) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须为正整数")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能为负数")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")

        self.chunk_size: int = chunk_size
        self.chunk_overlap: int = chunk_overlap

    def chunk(self, text: str) -> list[str]:
        """将文本切分为重叠的 chunk 列表。

        Args:
            text: 待分段的原始文本。

        Returns:
            非空字符串列表，每段长度不超过 ``chunk_size``。
            输入为空时返回空列表。
        """
        if not text or not text.strip():
            return []

        # ── 第一步：按自然段落边界预分割 ──────────────────────────
        paragraphs: list[str] = self._split_paragraphs(text)
        if not paragraphs:
            return []

        # ── 第二步：贪心合并 + 滑动窗口 ─────────────────────────
        chunks: list[str] = []
        current: str = ""

        for para in paragraphs:
            # 单段超过 chunk_size 时，强制按字符切割
            if len(para) > self.chunk_size:
                # 先把 current buffer 刷出
                if current:
                    chunks.append(current.strip())
                    current = ""
                chunks.extend(self._force_split(para))
                continue

            # 尝试追加段落到 current buffer
            separator = "\n\n" if current else ""
            candidate = current + separator + para

            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                # current buffer 已满，刷出
                if current:
                    chunks.append(current.strip())
                # 利用 overlap 回退：从 current 尾部取 overlap 字符
                if self.chunk_overlap > 0 and current:
                    overlap_text = current[-self.chunk_overlap:]
                    current = overlap_text + "\n\n" + para
                    # 如果加了 overlap 后就超了，丢弃 overlap
                    if len(current) > self.chunk_size:
                        current = para
                else:
                    current = para

        # 刷出最后的 buffer
        if current and current.strip():
            chunks.append(current.strip())

        return [c for c in chunks if c]

    def _split_paragraphs(self, text: str) -> list[str]:
        """按 ``\\n\\n`` 分割，再过滤空段。"""
        raw = text.split("\n\n")
        return [p.strip() for p in raw if p.strip()]

    def _force_split(self, text: str) -> list[str]:
        """将超长段按 chunk_size 强制切割，带 overlap。"""
        pieces: list[str] = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            piece = text[start:end].strip()
            if piece:
                pieces.append(piece)
            # 下一段起点回退 overlap
            start = end - self.chunk_overlap if end < len(text) else end
        return pieces
