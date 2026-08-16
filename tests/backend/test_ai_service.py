"""AI 服务测试：RAG 问答 / 总结 / 出题（FakeProvider + 注入回复）。"""
import json

from app.providers.fake import FakeProvider
from app.services.ai_service import AIService
from app.services.chunker import Chunk
from app.services.parsers import ParsedDocument, ParsedSection
from app.services.vector_store import VectorStore


def make_service(tmp_path, reply_fn):
    provider = FakeProvider(reply_fn=reply_fn)
    store = VectorStore(path=str(tmp_path / "chroma"), provider=provider)
    store.add_chunks(
        1,
        "python_notes.md",
        [
            Chunk(0, "装饰器是一个接收函数并返回新函数的可调用对象。", "第1章 Python基础", 1),
            Chunk(1, "生成器用 yield 惰性生成值。", "第2章 进阶", 2),
        ],
    )
    return AIService(store=store)


def test_chat_with_evidence_returns_sources(tmp_path):
    service = make_service(tmp_path, lambda msgs: "装饰器本质是函数[1]。")
    answer, sources, has_evidence = service.chat_with_rag("什么是装饰器？")
    assert has_evidence is True
    assert len(sources) >= 1
    assert sources[0]["document_name"] == "python_notes.md"
    assert sources[0]["chapter"] == "第1章 Python基础"
    assert sources[0]["page"] == 1
    assert "[1]" in answer


def test_chat_no_evidence_when_kb_empty(tmp_path):
    # 空知识库
    provider = FakeProvider(reply_fn=lambda msgs: "当前知识库没有找到足够依据。")
    store = VectorStore(path=str(tmp_path / "chroma"), provider=provider)
    service = AIService(store=store)
    answer, sources, has_evidence = service.chat_with_rag("量子力学是什么？")
    assert has_evidence is False
    assert sources == []


def test_generate_summary_parses_json(tmp_path):
    def reply(msgs):
        return json.dumps(
            {
                "core_points": "装饰器核心",
                "key_concepts": "闭包",
                "pitfalls": "注意顺序",
                "memory_items": "记忆内容",
                "short_summary": "简短总结",
            },
            ensure_ascii=False,
        )

    service = make_service(tmp_path, reply)
    doc = ParsedDocument(
        file_type="md",
        page_count=0,
        sections=[ParsedSection("第1章", 1, "第1章", 0, "装饰器内容" * 50)],
    )
    out = service.generate_summary(doc, "notes.md")
    assert out["core_points"] == "装饰器核心"
    assert out["short_summary"] == "简短总结"


def test_generate_quiz_parses_json_array(tmp_path):
    def reply(msgs):
        return json.dumps(
            [
                {
                    "type": "choice",
                    "question": "装饰器的作用？",
                    "options": ["A. 扩展函数功能", "B. 删除函数"],
                    "answer": "A",
                    "explanation": "装饰器在不修改原函数代码的情况下扩展功能。",
                    "difficulty": "easy",
                    "knowledge_point": "装饰器",
                }
            ],
            ensure_ascii=False,
        )

    service = make_service(tmp_path, reply)
    doc = ParsedDocument(
        file_type="md",
        page_count=0,
        sections=[ParsedSection("第1章", 1, "第1章", 0, "装饰器内容" * 50)],
    )
    questions = service.generate_quiz(doc, "notes.md", count=1, types=["choice"])
    assert len(questions) == 1
    q = questions[0]
    assert q["qtype"] == "choice"
    assert q["answer"] == "A"
    assert q["options"] == ["A. 扩展函数功能", "B. 删除函数"]


def test_extract_json_tolerates_code_fence(tmp_path):
    service = make_service(tmp_path, lambda msgs: "x")
    raw = '\x60\x60\x60json\n{"a": 1}\n\x60\x60\x60'
    assert service._extract_json(raw) == {"a": 1}


def test_extract_json_plain_dict(tmp_path):
    service = make_service(tmp_path, lambda msgs: "x")
    assert service._extract_json('{"a": 1}') == {"a": 1}
