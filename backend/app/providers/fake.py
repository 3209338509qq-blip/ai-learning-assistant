"""FakeProvider：无 API Key 时的测试/演示实现。

- chat：返回模板回答（可模拟"无依据"提示）
- embed：基于字符 n-gram 的确定性哈希向量（相似文本距离近，检索可演示）
"""
from __future__ import annotations

import hashlib
import math
import re

from ..config import settings
from .base import AIProvider, ChatMessage


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
        user_msgs = [m.content for m in messages if m.role == "user"]
        last = user_msgs[-1] if user_msgs else ""
        return (
            "【演示模式】当前未配置真实 AI 服务（AI_PROVIDER=fake）。\n\n"
            f"你刚才的问题是：「{last[:100]}」\n\n"
            "配置 .env 中的 AI_API_KEY 后将返回真实 AI 回答。"
        )

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
