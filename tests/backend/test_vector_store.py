"""向量库测试：写入、检索、过滤、删除。"""
import pytest

from app.providers.fake import FakeProvider
from app.services.chunker import Chunk
from app.services.vector_store import VectorStore


@pytest.fixture()
def store(tmp_path):
    return VectorStore(path=str(tmp_path / "chroma"), provider=FakeProvider())


def test_add_and_search(store):
    chunks = [
        Chunk(0, "Python 装饰器用于扩展函数功能。", "第1章", 1),
        Chunk(1, "生成器使用 yield 关键字。", "第2章", 3),
        Chunk(2, "列表推导式创建列表。", "第1章", 2),
    ]
    store.add_chunks(1, "python_notes.md", chunks)

    hits = store.search("什么是装饰器？", top_k=2)
    assert len(hits) == 2
    assert "装饰器" in hits[0]["text"]
    assert hits[0]["document_name"] == "python_notes.md"
    assert hits[0]["chapter"] == "第1章"
    assert hits[0]["page"] == 1


def test_search_with_document_filter(store):
    store.add_chunks(1, "a.md", [Chunk(0, "装饰器内容。", "第1章", 1)])
    store.add_chunks(2, "b.md", [Chunk(0, "装饰器内容。", "第1章", 1)])
    hits = store.search("装饰器", top_k=5, document_id=2)
    assert len(hits) == 1
    assert hits[0]["document_id"] == 2


def test_delete_document(store):
    store.add_chunks(1, "a.md", [Chunk(0, "内容A。", "第1章", 1)])
    store.add_chunks(2, "b.md", [Chunk(0, "内容B。", "第2章", 2)])
    store.delete_document(1)
    hits = store.search("内容", top_k=5)
    assert len(hits) == 1
    assert hits[0]["document_id"] == 2


def test_count(store):
    store.add_chunks(1, "a.md", [Chunk(0, "甲。", "第1章", 1), Chunk(1, "乙。", "第1章", 1)])
    assert store.count() == 2
