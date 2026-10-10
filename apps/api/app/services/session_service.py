"""会话与消息的业务逻辑。路由层只做参数校验，所有数据操作都走这里。"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session as OrmSession

from app.models.session import MessageModel, SessionModel
from app.services.media_service import dump_attachments

logger = logging.getLogger(__name__)

#: 送给模型的上下文条数上限，防止长会话把 token 撑爆
MODEL_CONTEXT_LIMIT = 20

_ROLE_MAP = {"user": "user", "ai": "assistant", "assistant": "assistant", "system": "system"}

SEED_SESSIONS = (
    {"type": "ai", "title": "小伴", "member_count": 2},
    {"type": "direct", "title": "林小满", "member_count": 2},
    {"type": "group", "title": "产品讨论组", "member_count": 6},
)


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------- 会话


def list_sessions(db: OrmSession) -> list[SessionModel]:
    """会话列表：置顶优先，其次按最近活跃排序。"""
    stmt = select(SessionModel).order_by(desc(SessionModel.pinned), desc(SessionModel.updated_at))
    return list(db.execute(stmt).scalars().all())


def get_or_404(db: OrmSession, session_id: str) -> SessionModel:
    session = db.get(SessionModel, session_id)
    if session is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"会话不存在：{session_id}")
    return session


def create_session(
    db: OrmSession, *, type: str = "ai", title: str = "新会话", member_count: int = 2
) -> SessionModel:
    session = SessionModel(
        id=_new_id(), type=type, title=title, member_count=member_count, updated_at=_now()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def rename_session(db: OrmSession, session_id: str, title: str) -> SessionModel:
    session = get_or_404(db, session_id)
    session.title = title
    session.updated_at = _now()
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: OrmSession, session_id: str) -> None:
    session = get_or_404(db, session_id)
    db.delete(session)  # cascade 会连带删掉 messages
    db.commit()


def ensure_seed(db: OrmSession) -> None:
    """首次启动时塞几条示例会话，让界面一打开就有东西可看。"""
    if db.execute(select(SessionModel.id).limit(1)).first():
        return
    for item in SEED_SESSIONS:
        db.add(SessionModel(id=_new_id(), updated_at=_now(), **item))
    db.commit()
    logger.info("已初始化示例会话")


# ---------------------------------------------------------------- 消息


def list_messages(db: OrmSession, session_id: str, limit: int = 200) -> list[MessageModel]:
    stmt = (
        select(MessageModel)
        .where(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def append_message(
    db: OrmSession,
    session: SessionModel,
    *,
    sender_type: str,
    content: str,
    content_type: str = "text",
    emotion: str | None = None,
    sender_id: str = "local-user",
    attachments: list[dict[str, object]] | None = None,
) -> MessageModel:
    """追加一条消息并立即提交。

    流式场景下刻意每条都提交：即使生成中途失败，用户说的话也不会丢。
    """
    message = MessageModel(
        id=_new_id(),
        session_id=session.id,
        sender_type=sender_type,
        sender_id=sender_id,
        content=content,
        content_type=content_type,
        emotion=emotion,
        attachments=dump_attachments(attachments or []),
        created_at=_now(),
    )
    db.add(message)
    session.updated_at = _now()
    db.commit()
    db.refresh(message)
    return message


def to_model_messages(db: OrmSession, session: SessionModel) -> list[dict[str, str]]:
    """取出最近的对话，转换成 LiteLLM 认识的消息数组。

    直接查库而不是读 relationship —— 流式过程中刚插入的消息可能还没同步进集合。
    """
    rows = (
        db.execute(
            select(MessageModel)
            .where(MessageModel.session_id == session.id)
            .order_by(desc(MessageModel.created_at))
            .limit(MODEL_CONTEXT_LIMIT)
        )
        .scalars()
        .all()
    )
    return [
        {"role": _ROLE_MAP.get(m.sender_type, "user"), "content": m.content}
        for m in reversed(rows)
        if m.content and m.content.strip()
    ]