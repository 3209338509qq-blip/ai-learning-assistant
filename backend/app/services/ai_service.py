"""AI 业务服务：RAG 问答 / 自动总结 / 自动出题。

所有业务只依赖 AIProvider 接口，不接触具体模型。
"""
from __future__ import annotations

import json
import re
from typing import Any

from ..config import settings
from ..providers import ChatMessage, get_provider
from .parsers import ParsedDocument
from .vector_store import VectorStore

SYSTEM_PROMPT = """你是一名严谨的个人学习助手。回答规则：
1. 优先依据下方【参考资料】回答用户问题。
2. 引用资料内容时，在句末标注来源编号 [1][2]（编号对应参考资料列表）。
3. 如果参考资料中没有足够依据回答，必须明确回答：「当前知识库没有找到足够依据。」
4. 不要编造资料中不存在的内容，回答使用中文。
"""

NO_EVIDENCE_ANSWER = "当前知识库没有找到足够依据。"


def _format_context(sources: list[dict]) -> str:
    lines = []
    for i, s in enumerate(sources, 1):
        page = f"（第 {s['page']} 页）" if s.get("page") else ""
        lines.append(
            f"[{i}] 来源：{s['document_name']}，章节：{s['chapter']}{page}\n{s['text']}"
        )
    return "\n\n".join(lines)


class AIService:
    def __init__(self, store: VectorStore | None = None):
        self.store = store or VectorStore()
        # provider 统一取自向量库（同一 AI 能力来源，便于测试注入）
        self.provider = self.store.provider

    # ---------------- RAG 问答 ----------------

    def chat_with_rag(
        self,
        query: str,
        history: list[dict] | None = None,
        document_id: int | None = None,
    ) -> tuple[str, list[dict], bool]:
        sources = self.store.search(query, document_id=document_id)
        has_evidence = bool(sources)
        messages = [ChatMessage("system", SYSTEM_PROMPT)]
        for h in history or []:
            messages.append(ChatMessage(h.get("role", "user"), h.get("content", "")))
        if has_evidence:
            messages.append(
                ChatMessage(
                    "system",
                    f"【参考资料】\n{_format_context(sources)}\n"
                    "请依据以上资料回答，并按要求标注来源编号。",
                )
            )
        messages.append(ChatMessage("user", query))
        answer = self.provider.chat(messages)
        source_out = []
        for s in sources:
            excerpt = s["text"][:200]
            source_out.append(
                {
                    "document_id": s["document_id"],
                    "document_name": s["document_name"],
                    "chapter": s["chapter"],
                    "page": s["page"],
                    "excerpt": excerpt,
                }
            )
        return answer, source_out, has_evidence

    # ---------------- 自动总结 ----------------

    def generate_summary(
        self,
        doc: ParsedDocument,
        filename: str,
        chapter_path: str = "",
    ) -> dict[str, str]:
        text, scope = self._scope_text(doc, chapter_path)
        prompt = (
            f"请为以下学习资料生成结构化总结。\n"
            f"资料：{filename}，范围：{scope}\n\n"
            f"资料内容：\n{text[:12000]}\n\n"
            "严格输出 JSON 对象，字段如下：\n"
            '{"core_points": "核心知识点（分条列出）", "key_concepts": "重点概念（含解释）", '
            '"pitfalls": "易错点", "memory_items": "需要记忆的内容", "short_summary": "简短总结（100字内）"}'
        )
        raw = self.provider.chat(
            [ChatMessage("system", SYSTEM_PROMPT), ChatMessage("user", prompt)],
            temperature=0.3,
        )
        return self._parse_json_dict(
            raw,
            fallback_keys=["core_points", "key_concepts", "pitfalls", "memory_items", "short_summary"],
        )

    # ---------------- 自动出题 ----------------

    def generate_quiz(
        self,
        doc: ParsedDocument,
        filename: str,
        chapter_path: str = "",
        count: int = 5,
        types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        types = types or ["choice", "true_false", "short_answer"]
        text, scope = self._scope_text(doc, chapter_path)
        prompt = (
            f"请根据以下学习资料出练习题。\n"
            f"资料：{filename}，范围：{scope}\n\n"
            f"资料内容：\n{text[:12000]}\n\n"
            f"要求：共 {count} 道题，题型分配尽量均匀（可选题型：choice 选择题 / true_false 判断题 / short_answer 简答题）。\n"
            "每道题包含：question 题干、options 选项数组（仅选择题，选项形如 'A. xxx'）、"
            "answer 答案（选择题填选项字母；判断题填 '正确'/'错误'；简答题填完整答案）、"
            "explanation 解析、difficulty（easy/medium/hard）、knowledge_point 对应知识点。\n"
            "严格输出 JSON 数组，不要输出其他内容。"
        )
        raw = self.provider.chat(
            [ChatMessage("system", SYSTEM_PROMPT), ChatMessage("user", prompt)],
            temperature=0.5,
        )
        return self._parse_quiz(raw, chapter_path)

    # ---------------- 内部工具 ----------------

    def _scope_text(self, doc: ParsedDocument, chapter_path: str) -> tuple[str, str]:
        if not chapter_path:
            return doc.full_text[:24000], "全文"
        for s in doc.sections:
            if s.path == chapter_path:
                return s.text[:12000], chapter_path
        return doc.full_text[:12000], "全文"

    def _parse_json_dict(self, raw: str, fallback_keys: list[str]) -> dict[str, str]:
        data = self._extract_json(raw)
        if isinstance(data, dict):
            return {k: str(data.get(k, "")).strip() for k in fallback_keys}
        return {k: "" for k in fallback_keys}

    def _parse_quiz(self, raw: str, chapter_path: str) -> list[dict[str, Any]]:
        data = self._extract_json(raw)
        if not isinstance(data, list):
            return []
        out = []
        for item in data:
            if not isinstance(item, dict) or not str(item.get("question", "")).strip():
                continue
            qtype = str(item.get("type", "choice")).strip()
            if qtype not in ("choice", "true_false", "short_answer"):
                qtype = "choice"
            q: dict[str, Any] = {
                "qtype": qtype,
                "question": str(item.get("question", "")).strip(),
                "options": (
                    [str(o) for o in item.get("options", []) if str(o).strip()]
                    if isinstance(item.get("options"), list)
                    else []
                ),
                "answer": str(item.get("answer", "")).strip(),
                "explanation": str(item.get("explanation", "")).strip(),
                "difficulty": (
                    str(item.get("difficulty", "")).strip()
                    if str(item.get("difficulty", "")).strip() in ("easy", "medium", "hard")
                    else "medium"
                ),
                "knowledge_point": str(item.get("knowledge_point", "")).strip(),
                "chapter": str(item.get("chapter", "")).strip() or chapter_path,
            }
            if q["answer"]:
                out.append(q)
        return out

    def _extract_json(self, raw: str) -> Any:
        """从模型输出中提取 JSON（容忍 markdown 代码围栏）。"""
        text = raw.strip()
        fence = re.search(r"\x60\x60\x60(?:json)?\s*([\s\S]*?)\x60\x60\x60", text)
        if fence:
            text = fence.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return None
