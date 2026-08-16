"""本地 Embedding：fastembed + BAAI/bge-small-zh-v1.5（中文优化，512 维）。

无需任何 API Key，模型首次使用自动下载（约 100MB，可用 HF_ENDPOINT 镜像加速）。
"""
from __future__ import annotations

import threading

_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

_lock = threading.Lock()
_model = None


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding

                _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """批量本地向量化，返回 list[list[float]]。"""
    if not texts:
        return []
    model = _get_model()
    return [v.tolist() for v in model.embed(list(texts))]
