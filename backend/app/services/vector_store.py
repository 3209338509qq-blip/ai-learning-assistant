"""ChromaDB 向量库封装：持久化、按文档增删、相似检索（带溯源元数据）。"""
from __future__ import annotations

from pathlib import Path

import chromadb

from ..config import settings
from ..providers import AIProvider
from .chunker import Chunk

COLLECTION_NAME = "learning_docs"


class VectorStore:
    def __init__(self, path: str | None = None, provider: AIProvider | None = None):
        self._provider = provider
        self._path = path or settings.chroma_path
        Path(self._path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self._path)
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

    def add_chunks(self, document_id: int, document_name: str, chunks: list[Chunk]) -> int:
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
    ) -> list[dict]:
        """相似检索，返回 [{document_id, document_name, chapter, page, text, distance}]。"""
        top_k = top_k or settings.retrieval_top_k
        q = self.provider.embed_one(query)
        where = {"document_id": document_id} if document_id is not None else None
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

    def count(self) -> int:
        return self._col.count()
