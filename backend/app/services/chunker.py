"""文本分块：按段落/句子边界切分，保留章节与页码元数据。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .parsers import ParsedDocument


@dataclass
class Chunk:
    index: int          # 文档内全局序号
    text: str
    chapter: str        # 章节路径（溯源用）
    page: int           # 页码（溯源用）


_SENTENCE_END = re.compile(r"(?<=[。！？!?；;])\s*")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


def _split_long(text: str, max_len: int) -> list[str]:
    """把超长段落按句子切成 <= max_len 的单元。"""
    if len(text) <= max_len:
        return [text]
    parts = [p for p in _SENTENCE_END.split(text) if p.strip()]
    out: list[str] = []
    cur = ""
    for part in parts:
        if len(cur) + len(part) <= max_len:
            cur += part
        else:
            if cur:
                out.append(cur.strip())
            # 单个句子仍超长则硬切
            while len(part) > max_len:
                out.append(part[:max_len])
                part = part[max_len:]
            cur = part
    if cur.strip():
        out.append(cur.strip())
    return [o for o in out if o]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """通用文本分块：段落优先，句子其次，最后硬切；相邻块带重叠。"""
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]
    units: list[str] = []
    for p in paragraphs:
        units.extend(_split_long(p, chunk_size))

    chunks: list[str] = []
    cur = ""
    for u in units:
        if len(cur) + len(u) + 1 <= chunk_size:
            cur = f"{cur}\n{u}".strip() if cur else u
        else:
            if cur:
                chunks.append(cur)
            cur = u
    if cur:
        chunks.append(cur)

    # 相邻块重叠（首块不动，后续块前缀拼接上一块尾部）
    if overlap > 0 and len(chunks) > 1:
        merged = [chunks[0]]
        for c in chunks[1:]:
            prev = merged[-1]
            tail = prev[-overlap:] if len(prev) > overlap else prev
            merged.append(f"{tail}\n{c}" if tail else c)
        chunks = merged
    return chunks


def chunk_document(doc: ParsedDocument, chunk_size: int = 800, overlap: int = 100) -> list[Chunk]:
    """按章节分块，每块携带章节路径与页码。"""
    out: list[Chunk] = []
    idx = 0
    for section in doc.sections:
        for text in chunk_text(section.text, chunk_size, overlap):
            out.append(Chunk(index=idx, text=text, chapter=section.path, page=section.page))
            idx += 1
    if not out:
        out.append(Chunk(index=0, text=doc.full_text, chapter="全文", page=1))
    return out
