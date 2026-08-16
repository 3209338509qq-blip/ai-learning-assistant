"""AI Provider 统一接口。

业务代码只依赖本接口（AIService → AIProvider → 具体模型），
切换模型/厂商只需改环境变量，不改业务代码。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # system / user / assistant
    content: str


class AIProvider(ABC):
    """统一 AI 能力接口：对话 + Embedding。"""

    name: str = "base"

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> str:
        """调用对话模型，返回回复文本。"""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化，返回与输入等长的向量列表。"""

    @abstractmethod
    def chat_configured(self) -> bool:
        """对话模型是否已配置可用。"""

    @abstractmethod
    def embedding_configured(self) -> bool:
        """Embedding 模型是否已配置可用。"""

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
