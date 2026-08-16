"""FakeProvider：无 API Key 时的测试/演示实现。

- chat：普通问答返回模板回答；
  检测到总结/出题请求时，返回基于资料原文的演示 JSON（保证全流程可体验）
- embed：基于字符 n-gram 的确定性哈希向量（相似文本距离近，检索可演示）
"""
from __future__ import annotations

import hashlib
import json
import math
import re

from ..config import settings
from .base import AIProvider, ChatMessage

_DEMO_NOTE = "（演示内容，配置 AI_API_KEY 后生成真实结果）"


class FakeProvider(AIProvider):
    name = "fake"

    def __init__(self, reply_fn=None):
        """reply_fn: 可选，测试时注入自定义回答（接收 messages，返回 str）。"""
        self._reply_fn = reply_fn

    def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> str:
        if self._reply_fn is not None:
            return self._reply_fn(messages)
        all_text = "\n".join(m.content for m in messages)
        if '"core_points"' in all_text:
            return json.dumps(self._demo_summary(all_text), ensure_ascii=False)
        if "每道题包含" in all_text or "knowledge_point" in all_text:
            return json.dumps(self._demo_questions(all_text), ensure_ascii=False)
        user_msgs = [m.content for m in messages if m.role == "user"]
        last = user_msgs[-1] if user_msgs else ""
        return (
            "【演示模式】当前未配置真实 AI 服务（AI_PROVIDER=fake）。\n\n"
            f"你刚才的问题是：「{last[:100]}」\n\n"
            "配置 .env 中的 AI_API_KEY 后将返回真实 AI 回答。"
        )

    def stream_chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ):
        """模拟流式：按小块产出回复，制造打字机效果。"""
        text = self.chat(messages, temperature)
        step = 8
        for i in range(0, len(text), step):
            yield text[i : i + step]

    # ---------- 演示内容生成 ----------

    def _extract_content(self, all_text: str, max_len: int = 3000) -> str:
        for marker in ("资料内容：", "【参考资料】"):
            idx = all_text.find(marker)
            if idx != -1:
                return all_text[idx + len(marker) :][:max_len]
        return all_text[:max_len]

    def _sentences(self, content: str) -> list[str]:
        parts = re.split(r"[。！？!?；;\n]", content)
        out = []
        for p in parts:
            p = p.strip().strip("-").strip()
            if 6 <= len(p) <= 60:
                out.append(p)
        return out[:8]

    def _demo_summary(self, all_text: str) -> dict:
        content = self._extract_content(all_text)
        sentences = self._sentences(content)
        lines = "\n".join(f"- {s}" for s in sentences[:5]) or "- （资料内容过短）"
        note = _DEMO_NOTE
        return {
            "core_points": f"{note}\n{lines}",
            "key_concepts": f"{note}\n- 来自资料的关键概念，配置真实 AI 后由模型提炼",
            "pitfalls": f"{note}\n- 常见易错点，配置真实 AI 后由模型分析",
            "memory_items": f"{note}\n- 需要记忆的内容，配置真实 AI 后由模型整理",
            "short_summary": f"演示总结：资料共 {len(content)} 字。{sentences[0] if sentences else ''}",
        }

    def _demo_questions(self, all_text: str) -> list[dict]:
        content = self._extract_content(all_text)
        sentences = self._sentences(content)
        questions: list[dict] = []
        for s in sentences[:3]:
            questions.append(
                {
                    "type": "true_false",
                    "question": f"（演示题）根据资料判断：「{s}」",
                    "options": [],
                    "answer": "正确",
                    "explanation": f"演示模式：该句摘自资料原文。{_DEMO_NOTE}",
                    "difficulty": "easy",
                    "knowledge_point": "演示",
                    "chapter": "",
                }
            )
        return questions

    # ---------- Embedding ----------

    def embed(self, texts: list[str]) -> list[list[float]]:
        dim = max(settings.embedding_dimensions, 8)
        vecs = []
        for t in texts:
            v = [0.0] * dim
            for tok in self._tokenize(t):
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                v[h % dim] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vecs.append([x / norm for x in v])
        return vecs

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """中文按双字切分、英文按单词切分，保证相似文本向量相近。"""
        tokens: list[str] = []
        for seg in re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z0-9_]+", text.lower()):
            if seg and seg[0] >= "\u4e00":
                if len(seg) <= 2:
                    tokens.append(seg)
                else:
                    tokens.extend(seg[i : i + 2] for i in range(len(seg) - 1))
            else:
                tokens.append(seg)
        return tokens

    def chat_configured(self) -> bool:
        return True

    def embedding_configured(self) -> bool:
        return True