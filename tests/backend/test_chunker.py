"""分块测试：边界、重叠、章节/页码元数据。"""
from app.services.chunker import Chunk, chunk_document, chunk_text
from app.services.parsers import ParsedDocument, ParsedSection


def test_chunk_text_short():
    chunks = chunk_text("短文本", 800, 100)
    assert len(chunks) == 1
    assert chunks[0] == "短文本"


def test_chunk_text_multi_with_overlap():
    text = "\n\n".join(f"第{i}段，内容足够长。" * 30 for i in range(20))
    chunks = chunk_text(text, 300, 60)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)
    # 第二块应以第一块尾部开头（重叠生效）
    assert chunks[1].startswith(chunks[0][-60:].strip()[:20])


def test_chunk_text_no_empty():
    chunks = chunk_text("\n\n  \n\n", 800, 100)
    assert chunks == []


def test_chunk_document_keeps_metadata():
    doc = ParsedDocument(
        file_type="md",
        page_count=0,
        sections=[
            ParsedSection(title="第1章", level=1, path="第1章", page=0, text="A" * 2000),
            ParsedSection(title="第2章", level=1, path="第2章", page=0, text="B" * 2000),
        ],
    )
    chunks = chunk_document(doc, 500, 50)
    assert len(chunks) > 2
    for c in chunks:
        assert isinstance(c, Chunk)
        assert c.chapter in ("第1章", "第2章")
    assert all(c.index == i for i, c in enumerate(chunks))


def test_chunk_document_pdf_page():
    doc = ParsedDocument(
        file_type="pdf",
        page_count=3,
        sections=[ParsedSection(title="第1章", level=1, path="第1章", page=2, text="C" * 500)],
    )
    chunks = chunk_document(doc, 300, 50)
    assert chunks and all(c.page == 2 for c in chunks)
