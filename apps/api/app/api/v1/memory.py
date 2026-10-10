"""记忆接口：列表、搜索、增删改、导出、清空、摄入、统计。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session as OrmSession

from app.core import crypto
from app.db.session import get_db
from app.memory.extractor import MEMORY_TYPES
from app.memory.retriever import retrieve
from app.schemas.memory import (
    MemoryCreate,
    MemoryIngest,
    MemoryOut,
    MemorySearchHit,
    MemoryStats,
    MemoryUpdate,
)
from app.services import memory_service

router = APIRouter()

DbSession = Annotated[OrmSession, Depends(get_db)]


def _to_out(memory) -> MemoryOut:
    """ORM -> 出参，顺带把正文解密。"""
    out = MemoryOut.model_validate(memory)
    return out.model_copy(update={"content": crypto.decrypt(memory.content)})


@router.get("", response_model=list[MemoryOut], summary="记忆列表")
def list_memories(db: DbSession, type: str | None = None, limit: int = 200) -> list[MemoryOut]:
    if type and type not in MEMORY_TYPES:
        raise HTTPException(status_code=400, detail=f"未知的记忆类型：{type}")
    return [_to_out(m) for m in memory_service.list_memories(db, type=type, limit=limit)]


@router.get("/stats", response_model=MemoryStats, summary="记忆统计")
def stats(db: DbSession) -> MemoryStats:
    return MemoryStats(**memory_service.stats(db))  # type: ignore[arg-type]


@router.get("/search", response_model=list[MemorySearchHit], summary="语义搜索记忆")
async def search_memories(db: DbSession, q: str, top_n: int = 10) -> list[MemorySearchHit]:
    if not q.strip():
        raise HTTPException(status_code=400, detail="q 不能为空")

    hits = await retrieve(q, top_n=top_n)
    by_id = {m.id: m for m in memory_service.list_memories(db, limit=1000)}
    out: list[MemorySearchHit] = []
    for hit in hits:
        row = by_id.get(hit.id)
        if row is None:
            continue
        row.hit_count += 1
        out.append(
            MemorySearchHit(
                memory=_to_out(row),
                score=hit.score,
                vector_score=hit.vector_score,
                lexical_score=hit.lexical_score,
                reranker=hit.reranker,
            )
        )
    db.commit()
    return out


@router.post("", response_model=MemoryOut, status_code=status.HTTP_201_CREATED, summary="新增记忆")
async def create_memory(payload: MemoryCreate, db: DbSession) -> MemoryOut:
    if payload.type not in MEMORY_TYPES:
        raise HTTPException(status_code=400, detail=f"未知的记忆类型：{payload.type}")
    try:
        memory = await memory_service.add_memory(
            db,
            payload.content,
            type=payload.type,
            session_id=payload.session_id,
            source="manual",
            confidence=1.0,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(memory)


@router.post(
    "/ingest",
    response_model=list[MemoryOut],
    status_code=status.HTTP_201_CREATED,
    summary="从一段文本抽取记忆",
)
async def ingest(payload: MemoryIngest, db: DbSession) -> list[MemoryOut]:
    saved_ids = await memory_service.ingest_text(db, payload.text, payload.session_id)
    rows = [m for m in memory_service.list_memories(db, limit=1000) if m.id in set(saved_ids)]
    return [_to_out(m) for m in rows]


@router.patch("/{memory_id}", response_model=MemoryOut, summary="编辑记忆")
async def update_memory(memory_id: str, payload: MemoryUpdate, db: DbSession) -> MemoryOut:
    if payload.type and payload.type not in MEMORY_TYPES:
        raise HTTPException(status_code=400, detail=f"未知的记忆类型：{payload.type}")
    memory = await memory_service.update_memory(
        db,
        memory_id,
        content=payload.content,
        type=payload.type,
        pinned=payload.pinned,
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return _to_out(memory)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除单条")
def delete_memory(memory_id: str, db: DbSession) -> None:
    if not memory_service.delete_memory(db, memory_id):
        raise HTTPException(status_code=404, detail="记忆不存在")


@router.get("/export", summary="导出全部记忆")
def export_memories(db: DbSession) -> PlainTextResponse:
    return PlainTextResponse(
        memory_service.export_all(db),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="ai-companion-memories.json"'},
    )


@router.delete("", summary="一键清空全部记忆")
def clear_memories(db: DbSession) -> dict[str, int]:
    deleted = memory_service.clear_all(db)
    return {"deleted": deleted}