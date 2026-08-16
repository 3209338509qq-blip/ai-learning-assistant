"""OpenAI 兼容 Provider。

适用于所有提供 /chat/completions 与 /embeddings 的 OpenAI 兼容服务：
DeepSeek、MiMo、OpenAI、硅基流动、Ollama(openai 模式) 等。
"""
from __future__ import annotations

import httpx

from ..config import settings
from .base import AIProvider, ChatMessage


class OpenAICompatibleProvider(AIProvider):
    name = "openai_compatible"

    def _headers(self, api_key: str) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _base_url(self, url: str) -> str:
        return url.rstrip("/")

    # ---------- 对话 ----------

    def chat(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> str:
        if not self.chat_configured():
            raise RuntimeError(
                "对话模型未配置：请设置 AI_API_KEY（或 AI_PROVIDER=fake 体验演示模式）"
            )
        payload = {
            "model": settings.ai_chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        url = f"{self._base_url(settings.ai_base_url)}/chat/completions"
        try:
            resp = httpx.post(
                url,
                json=payload,
                headers=self._headers(settings.ai_api_key),
                timeout=settings.ai_timeout_seconds,
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"调用对话模型失败（网络错误）: {e}") from e
        if resp.status_code != 200:
            raise RuntimeError(
                f"调用对话模型失败 HTTP {resp.status_code}: {resp.text[:300]}"
            )
        try:
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"对话模型返回格式异常: {resp.text[:300]}") from e

    # ---------- Embedding ----------

    def _embed_config(self) -> tuple[str, str]:
        base = settings.embedding_base_url or settings.ai_base_url
        key = settings.embedding_api_key or settings.ai_api_key
        return base, key

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.embedding_configured():
            raise RuntimeError(
                "Embedding 未配置：请设置 EMBEDDING_BASE_URL/EMBEDDING_API_KEY"
                "（DeepSeek 官方无 embedding 端点，可用硅基流动等兼容服务）"
            )
        base, key = self._embed_config()
        url = f"{self._base_url(base)}/embeddings"
        results: list[list[float]] = []
        for i in range(0, len(texts), settings.embedding_batch_size):
            batch = texts[i : i + settings.embedding_batch_size]
            try:
                resp = httpx.post(
                    url,
                    json={"model": settings.embedding_model, "input": batch},
                    headers=self._headers(key),
                    timeout=settings.ai_timeout_seconds,
                )
            except httpx.HTTPError as e:
                raise RuntimeError(f"调用 Embedding 失败（网络错误）: {e}") from e
            if resp.status_code != 200:
                raise RuntimeError(
                    f"调用 Embedding 失败 HTTP {resp.status_code}: {resp.text[:300]}"
                )
            try:
                data = resp.json()["data"]
                results.extend(item["embedding"] for item in data)
            except (KeyError, TypeError) as e:
                raise RuntimeError(f"Embedding 返回格式异常: {resp.text[:300]}") from e
        if len(results) != len(texts):
            raise RuntimeError(
                f"Embedding 返回数量不一致: 期望 {len(texts)} 实际 {len(results)}"
            )
        return results

    # ---------- 配置状态 ----------

    def chat_configured(self) -> bool:
        return bool(settings.ai_api_key and settings.ai_chat_model)

    def embedding_configured(self) -> bool:
        base = settings.embedding_base_url or settings.ai_base_url
        key = settings.embedding_api_key or settings.ai_api_key
        return bool(base and key and settings.embedding_model)
