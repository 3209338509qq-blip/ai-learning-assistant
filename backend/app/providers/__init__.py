"""Provider 工厂：根据配置返回具体实现，业务代码不直接实例化具体 Provider。"""
from functools import lru_cache

from ..config import settings
from .base import AIProvider, ChatMessage
from .fake import FakeProvider
from .openai_compat import OpenAICompatibleProvider

__all__ = ["AIProvider", "ChatMessage", "get_provider"]


@lru_cache
def get_provider() -> AIProvider:
    if settings.ai_provider == "fake":
        return FakeProvider()
    if settings.ai_provider == "openai_compatible":
        return OpenAICompatibleProvider()
    raise ValueError(f"未知的 AI_PROVIDER: {settings.ai_provider}，可选: openai_compatible / fake")
