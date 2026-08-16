"""ChromaDB 向量库封装：持久化、按文档增删、相似检索（带溯源元数据）。"""
from __future__ import annotations

from pathlib import Path

import chromadb

from ..config import settings
from ..providers import AIProvider
from .chunker import Chunk

COLLECTION_NAME = "learning_docs"

# 按路径缓存 Chroma 客户端（避免每次请求重复初始化）
_client_cache: dict[str, chromadb.ClientAPI] = {}


def _get_client(path: str) -> chromadb.ClientAPI:
    if path not in _client_cache:
        Path(path).mkdir(parents=True, exist_ok=True)
        _client_cache[path] = chromadb.PersistentClient(path=path)
    return _client_cache[path]


class VectorStore:
    def __init__(self, path: str | None = None, provider: AIProvider | None = None):
        self._provider = provider
        self._path = path or settings.chroma_path
        self._client = _get_client(self._path)
        self._col = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def provider(self) -> AIProvider:
        if self._provider is None:
            from ..providers import get_provider

            self._provider = get_provider()
        return self._provider

    def add_chunks(
        self,
        document_id: int,
        document_name: str,
        chunks: list[Chunk],
        subject: str = "",
    ) -> int:
        """写入分块并向量化，返回写入块数。"""
        if not chunks:
            return 0
        ids = [f"{document_id}:{c.index}" for c in chunks]
        embeddings = self.provider.embed([c.text for c in chunks])
        self._col.add(
            ids=ids,
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "document_id": document_id,
                    "document_name": document_name,
                    "chapter": c.chapter,
                    "page": c.page,
                    "chunk_index": c.index,
                    "subject": subject,
                }
                for c in chunks
            ],
        )
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int | None = None,
        document_id: int | None = None,
        subject: str = "",
    ) -> list[dict]:
        """相似检索，返回 [{document_id, document_name, chapter, page, text, distance}]。"""
        top_k = top_k or settings.retrieval_top_k
        q = self.provider.embed_one(query)
        conds: list[dict] = []
        if document_id is not None:
            conds.append({"document_id": document_id})
        if subject:
            conds.append({"subject": subject})
        where = {"$and": conds} if len(conds) > 1 else (conds[0] if conds else None)
        res = self._col.query(
            query_embeddings=[q],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        out: list[dict] = []
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            if not doc or not str(doc).strip():
                continue
            out.append(
                {
                    "document_id": meta.get("document_id"),
                    "document_name": meta.get("document_name", ""),
                    "chapter": meta.get("chapter", ""),
                    "page": meta.get("page", 0),
                    "text": doc,
                    "distance": dist,
                }
            )
        return out

    def delete_document(self, document_id: int) -> None:
        """删除某文档的全部向量。"""
        self._col.delete(where={"document_id": document_id})

    def update_document_subject(self, document_id: int, subject: str) -> None:
        """更新某文档全部向量的 subject 元数据。"""
        res = self._col.get(where={"document_id": document_id})
        ids = res.get("ids") or []
        if ids:
            self._col.update(
                ids=ids,
                metadatas=[{"subject": subject}] * len(ids),
            )

    def get_document_chunks(self, document_id: int) -> list[dict]:
        """取某文档的全部分块（按 chunk_index 排序），用于总结/出题，避免重复解析原文件。"""
        res = self._col.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
        out = []
        for doc, meta in zip(res.get("documents") or [], res.get("metadatas") or []):
            out.append(
                {
                    "text": doc,
                    "chapter": meta.get("chapter", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "page": meta.get("page", 0),
                }
            )
        out.sort(key=lambda c: c["chunk_index"])
        return out

    def count(self) -> int:
        return self._col.count()