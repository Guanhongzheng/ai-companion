"""向量存储。

优先用 Chroma（持久化到 data/chroma/），不可用时降级为进程内存储，
保证在任何环境下记忆功能都能跑通 —— 降级时会在日志里明确提示「重启后需要重建」。

**注意**：向量库里只放 embedding 和原文，元数据（类型、来源会话、是否置顶等）
存在 SQL 里。两边用同一个 memory id 关联，删除时两边一起清。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterable, Sequence
from typing import Any, Protocol

from app.core.config import settings
from app.memory.embedding import cosine_similarity

logger = logging.getLogger(__name__)

COLLECTION_NAME = "memories"


class VectorStore(Protocol):
    name: str

    def upsert(
        self,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Sequence[str],
    ) -> None: ...

    def query(self, embedding: Sequence[float], top_k: int) -> list[tuple[str, float, str]]: ...

    def delete(self, ids: Iterable[str]) -> None: ...

    def delete_all(self) -> None: ...

    def all_ids(self) -> set[str]:
        """库里现有的全部 id，用于和 SQL 侧对账。"""
        ...

    def count(self) -> int: ...


# ---------------------------------------------------------------- Chroma


class ChromaStore:
    """基于 ChromaDB 的持久化存储。"""

    name = "chroma"

    def __init__(self) -> None:
        import chromadb

        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

    def upsert(
        self,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Sequence[str],
    ) -> None:
        if not ids:
            return
        self._collection.upsert(
            ids=list(ids),
            embeddings=[list(v) for v in embeddings],
            documents=list(documents),
        )

    def query(self, embedding: Sequence[float], top_k: int) -> list[tuple[str, float, str]]:
        total = self._collection.count()
        if total == 0:
            return []
        result = self._collection.query(
            query_embeddings=[list(embedding)],
            n_results=min(top_k, total),
            include=["documents", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        # Chroma 用「距离」表示，cosine 空间下距离 = 1 - 余弦相似度
        dists = (result.get("distances") or [[]])[0]
        return [
            (str(mid), 1.0 - float(dist), str(doc or ""))
            for mid, doc, dist in zip(ids, docs, dists, strict=False)
        ]

    def delete(self, ids: Iterable[str]) -> None:
        id_list = list(ids)
        if id_list:
            self._collection.delete(ids=id_list)

    def delete_all(self) -> None:
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

    def all_ids(self) -> set[str]:
        return {str(x) for x in (self._collection.get(include=[]) or {}).get("ids", [])}

    def count(self) -> int:
        return self._collection.count()


# ---------------------------------------------------------------- 内存兜底


class InMemoryStore:
    """Chroma 不可用时的进程内兜底。

    ⚠️ 数据不落盘，进程重启即丢失。仅用于保证演示链路不断。
    """

    name = "memory"

    def __init__(self) -> None:
        self._data: dict[str, tuple[list[float], str]] = {}
        self._lock = threading.Lock()

    def upsert(
        self,
        ids: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        documents: Sequence[str],
    ) -> None:
        with self._lock:
            for mid, vec, doc in zip(ids, embeddings, documents, strict=False):
                self._data[mid] = (list(vec), doc)

    def query(self, embedding: Sequence[float], top_k: int) -> list[tuple[str, float, str]]:
        with self._lock:
            scored = [
                (mid, cosine_similarity(embedding, vec), doc)
                for mid, (vec, doc) in self._data.items()
            ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def delete(self, ids: Iterable[str]) -> None:
        with self._lock:
            for mid in ids:
                self._data.pop(mid, None)

    def delete_all(self) -> None:
        with self._lock:
            self._data.clear()

    def all_ids(self) -> set[str]:
        with self._lock:
            return set(self._data)

    def count(self) -> int:
        return len(self._data)


# ---------------------------------------------------------------- 获取

_cached: VectorStore | None = None
_lock = threading.Lock()


def get_store() -> VectorStore:
    global _cached
    if _cached is not None:
        return _cached
    with _lock:
        if _cached is not None:
            return _cached
        try:
            store: VectorStore = ChromaStore()
            logger.info("记忆向量库：Chroma（%s）", settings.chroma_persist_dir)
        except Exception as exc:
            logger.warning("Chroma 不可用（%s），降级为进程内存存储（重启后记忆丢失）", exc)
            store = InMemoryStore()
        _cached = store
        return store


def reset_store() -> None:
    """测试用。"""
    global _cached
    with _lock:
        _cached = None


def store_info() -> dict[str, Any]:
    return {"backend": get_store().name, "count": get_store().count()}