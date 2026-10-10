"""记忆业务编排：抽取 → 去重 → 入库 → 召回 → 增删改导出。

路由层只做参数校验，所有记忆逻辑都在这里。
向量写入 Chroma、元数据写入 SQLite，两边用同一个 id，任何删除都要同时清两边。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session as OrmSession

from app.core import crypto
from app.core.config import settings
from app.memory.embedding import embed_query_with_fallback, get_embedder
from app.memory.extractor import MEMORY_TYPES, extract
from app.memory.retriever import format_for_prompt, retrieve
from app.memory.store import get_store
from app.models.memory import MemoryModel

logger = logging.getLogger(__name__)

#: 首次启动时灌入的示例记忆，方便一打开就有东西看
SEED_MEMORIES = (
    ("profile", "我是一名后端工程师，主要用 Python"),
    ("profile", "我住在深圳南山"),
    ("preference", "我喜欢吃潮汕牛肉火锅"),
    ("preference", "我讨厌下雨天"),
    ("profile", "我养了一只叫豆豆的猫"),
)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------- 写入


async def add_memory(
    db: OrmSession,
    content: str,
    *,
    type: str = "fact",
    session_id: str | None = None,
    source: str = "manual",
    confidence: float = 0.9,
) -> MemoryModel:
    """写入一条记忆（SQL + 向量），已存在高度相似的内容则跳过。"""
    content = content.strip()
    if not content:
        raise ValueError("记忆内容不能为空")

    # 去重：新记忆若与已有记忆高度相似就不再重复存
    existing = await retrieve(content, recall_k=3, top_n=1)
    if existing and existing[0].score >= settings.memory_dedup_threshold:
        logger.info("记忆重复，跳过：%s", content[:30])
        hit = db.get(MemoryModel, existing[0].id)
        if hit is not None:
            hit.hit_count += 1
            db.commit()
        return hit  # type: ignore[return-value]

    vector = await embed_query_with_fallback(content)

    memory = MemoryModel(
        id=_new_id(),
        type=type if type in MEMORY_TYPES else "fact",
        content=crypto.encrypt(content),
        session_id=session_id,
        source=source,
        confidence=confidence,
        encrypted=crypto.is_enabled(),
        created_at=_now(),
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    get_store().upsert([memory.id], [vector], [content])
    return memory


async def ingest_text(db: OrmSession, text: str, session_id: str | None = None) -> list[str]:
    """从一段对话文本里抽取并写入记忆，返回新增的记忆 id。"""
    candidates = await extract(text)
    saved: list[str] = []
    for candidate in candidates:
        try:
            memory = await add_memory(
                db,
                candidate.content,
                type=candidate.type,
                session_id=session_id,
                source="llm" if settings.openai_api_key or settings.dashscope_api_key else "rules",
                confidence=candidate.weight,
            )
        except ValueError:
            continue
        if memory is not None:
            saved.append(memory.id)
    return saved


def _log_task_failure(name: str):
    """后台任务的失败回调。

    ⚠️ ``add_done_callback`` 在任务**成功**时也会触发，所以不能无条件打 error ——
    之前这么写导致每次启动都误报「种子索引失败」，而索引其实一直是好的。
    """

    def _callback(task) -> None:
        if task.cancelled():
            logger.warning("%s 被取消（通常是进程退出）", name)
            return
        exc = task.exception()
        if exc is not None:
            logger.error("%s：%s", name, exc)

    return _callback


def ensure_seed_memories(db: OrmSession) -> None:
    """首次启动灌几条示例记忆。"""
    if db.execute(select(MemoryModel.id).limit(1)).first():
        return

    for kind, content in SEED_MEMORIES:
        db.add(
            MemoryModel(
                id=_new_id(),
                type=kind,
                content=crypto.encrypt(content),
                source="seed",
                confidence=0.8,
                encrypted=crypto.is_enabled(),
                created_at=_now(),
            )
        )
    db.commit()
    _schedule_seed_index()
    logger.info("已初始化 %d 条示例记忆", len(SEED_MEMORIES))


def _schedule_seed_index() -> None:
    """给种子记忆补向量索引。

    服务启动时已经在事件循环里，不能再调 asyncio.run（会抛 RuntimeError），
    这时挂成后台任务；同步场景（如测试）则直接跑完。
    任务内部**自己开 session**，不复用调用方的 —— 调用方的 session 可能已经关闭。
    """
    import asyncio

    async def _index() -> None:
        from app.db.session import SessionLocal

        with SessionLocal() as s:
            rows = s.execute(select(MemoryModel).where(MemoryModel.source == "seed")).scalars().all()
            if not rows:
                return
            embedder = get_embedder()
            plains = [crypto.decrypt(m.content) for m in rows]
            vectors = await embedder.embed_documents(plains)
            get_store().upsert([m.id for m in rows], vectors, plains)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_index())
        return

    task = loop.create_task(_index())
    task.add_done_callback(_log_task_failure("种子索引"))


# ---------------------------------------------------------------- 读取


def list_memories(
    db: OrmSession, *, type: str | None = None, limit: int = 200
) -> list[MemoryModel]:
    stmt = select(MemoryModel).order_by(desc(MemoryModel.pinned), desc(MemoryModel.updated_at))
    if type:
        stmt = stmt.where(MemoryModel.type == type)
    return list(db.execute(stmt.limit(limit)).scalars().all())


async def search_memories(db: OrmSession, query: str, top_n: int = 10) -> list[MemoryModel]:
    """向量召回 + 重排，按 id 回表取元数据。被命中的记忆 hit_count +1。"""
    hits = await retrieve(query, top_n=top_n)
    found: list[MemoryModel] = []
    for hit in hits:
        row = db.get(MemoryModel, hit.id)
        if row is None:
            continue
        row.hit_count += 1
        found.append(row)
    db.commit()
    return found


async def build_context(query: str, top_n: int | None = None) -> str:
    """召回并拼成注入 prompt 的上下文片段。"""
    memories = await retrieve(query, top_n=top_n)
    return format_for_prompt(memories)


def get_memory(db: OrmSession, memory_id: str) -> MemoryModel | None:
    return db.get(MemoryModel, memory_id)


# ---------------------------------------------------------------- 改删


async def update_memory(
    db: OrmSession,
    memory_id: str,
    *,
    content: str | None = None,
    type: str | None = None,
    pinned: bool | None = None,
) -> MemoryModel | None:
    memory = db.get(MemoryModel, memory_id)
    if memory is None:
        return None

    if content is not None and content.strip() != crypto.decrypt(memory.content):
        plain = content.strip()
        memory.content = crypto.encrypt(plain)
        memory.encrypted = crypto.is_enabled()
        vector = await embed_query_with_fallback(plain)
        get_store().upsert([memory.id], [vector], [plain])

    if type is not None and type in MEMORY_TYPES:
        memory.type = type
    if pinned is not None:
        memory.pinned = pinned
    memory.updated_at = _now()

    db.commit()
    db.refresh(memory)
    return memory


def delete_memory(db: OrmSession, memory_id: str) -> bool:
    memory = db.get(MemoryModel, memory_id)
    if memory is None:
        return False
    db.delete(memory)
    db.commit()
    get_store().delete([memory_id])
    return True


def clear_all(db: OrmSession) -> int:
    """一键清空：SQL 与向量库同时清空。"""
    rows = db.execute(select(MemoryModel.id)).scalars().all()
    db.query(MemoryModel).delete()
    db.commit()
    get_store().delete_all()
    return len(rows)


def export_all(db: OrmSession) -> str:
    """导出为 JSON 字符串（正文一律解密，方便用户自行备份）。"""
    rows = db.execute(select(MemoryModel).order_by(MemoryModel.created_at)).scalars().all()
    payload = [
        {
            "id": r.id,
            "type": r.type,
            "content": crypto.decrypt(r.content),
            "source": r.source,
            "confidence": r.confidence,
            "hit_count": r.hit_count,
            "pinned": r.pinned,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]
    return json.dumps({"version": 1, "count": len(payload), "memories": payload}, ensure_ascii=False, indent=2)


def sync_vector_store(db: OrmSession) -> dict[str, int]:
    """把向量库和 SQL 对齐，启动时调用。

    两侧是独立存储，手工删库、换数据库文件、异常退出等都可能让它们不一致：

    * 向量库里有、SQL 里没有 → 孤儿向量，检索时会召回到「不存在的记忆」（且会重复出现）
    * SQL 里有、向量库里没有 → 这条记忆永远召不到

    这里双向修复，保证「删了就真删干净」。
    """
    store = get_store()
    # 注意：select(MemoryModel.id) 返回的是字符串列本身，不是 ORM 对象
    sql_ids = set(db.execute(select(MemoryModel.id)).scalars().all())
    vector_ids = store.all_ids()

    orphans = vector_ids - sql_ids
    if orphans:
        store.delete(orphans)

    missing = sql_ids - vector_ids
    if missing:
        rows = (
            db.execute(select(MemoryModel).where(MemoryModel.id.in_(missing))).scalars().all()
        )
        plains = [crypto.decrypt(m.content) for m in rows]
        if plains:
            _schedule_index(rows, plains)

    if orphans or missing:
        logger.info("记忆向量对账：清理孤儿 %d 条，补建索引 %d 条", len(orphans), len(missing))
    return {"removed": len(orphans), "reindexed": len(missing)}


def _schedule_index(rows: list[MemoryModel], plains: list[str]) -> None:
    """异步补建向量索引。"""
    import asyncio

    ids = [m.id for m in rows]

    async def _run() -> None:
        embedder = get_embedder()
        vectors = await embedder.embed_documents(plains)
        get_store().upsert(ids, vectors, plains)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_run())
        return
    task = loop.create_task(_run())
    task.add_done_callback(_log_task_failure("记忆索引补建"))


def stats(db: OrmSession) -> dict[str, object]:
    rows = list(db.execute(select(MemoryModel)).scalars().all())
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r.type] = by_type.get(r.type, 0) + 1
    return {
        "total": len(rows),
        "by_type": by_type,
        "encrypted": crypto.is_enabled(),
        "vector_store": get_store().name,
        "embedder": get_embedder().name,
    }