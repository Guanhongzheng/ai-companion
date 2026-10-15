"""会话与消息的业务逻辑。路由层只做参数校验，所有数据操作都走这里。"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session as OrmSession

from app.models.session import MessageModel, SessionModel
from app.services import media_service
from app.services.media_service import dump_attachments, parse_attachments

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
    # 先把这批附件记下来，再删会话 —— 会话一旦删掉就再也查不到引用了，
    # 那些文件会永远留在 uploads 里，谁都找不到它们属于谁。
    filenames = media_service.referenced_filenames(db, session_id=session_id)
    db.delete(session)  # cascade 会连带删掉 messages
    db.commit()

    removed = sum(1 for name in filenames if media_service.delete_file(name))
    if removed:
        logger.info("删除会话 %s 时顺带清理了 %d 个附件文件", session_id, removed)


def delete_message(db: OrmSession, session_id: str, message_id: str) -> None:
    """删一条消息，顺带清掉它上传的文件。

    文件回收的逻辑和 ``delete_session`` 一样：**先记引用再删记录**，
    记录一删就再也查不到文件属于谁，那些文件会永远留在 uploads 里。
    """
    from fastapi import HTTPException

    message = db.execute(
        select(MessageModel).where(
            MessageModel.id == message_id, MessageModel.session_id == session_id
        )
    ).scalar_one_or_none()
    if message is None:
        raise HTTPException(status_code=404, detail="消息不存在")

    filenames = parse_attachments(message.attachments)
    names = [f.get("filename") for f in filenames if isinstance(f, dict) and f.get("filename")]
    db.delete(message)
    db.commit()

    removed = sum(1 for name in names if name and media_service.delete_file(name))
    if removed:
        logger.info("删除消息 %s 时顺带清理了 %d 个附件文件", message_id, removed)


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


def _label_of(sender_id: str) -> str:
    """从 sender_id 推导显示名：``u_alice`` -> ``Alice``。"""
    raw = (sender_id or "").strip()
    if not raw or raw == "local-user":
        return "我"
    return raw.removeprefix("u_").replace("_", " ")


def append_message(
    db: OrmSession,
    session: SessionModel,
    *,
    sender_type: str,
    content: str,
    content_type: str = "text",
    emotion: str | None = None,
    sender_id: str = "local-user",
    sender_name: str | None = None,
    attachments: list[dict[str, object]] | None = None,
) -> MessageModel:
    """追加一条消息并立即提交。

    流式场景下刻意每条都提交：即使生成中途失败，用户说的话也不会丢。

    ``sender_name`` 优先于 ``sender_id`` 推导出的名字 —— 群聊里
    显示「张三」比显示「u_zhangsan」自然得多。
    """
    label = (sender_name or "").strip() or _label_of(sender_id)
    message = MessageModel(
        id=_new_id(),
        session_id=session.id,
        sender_type=sender_type,
        sender_id=sender_id,
        sender_label=label,
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

    直接查库而不是走 relationship —— 流式过程中刚插入的消息可能还没同步进集合。

    🔴 **群聊必须携带说话人**，否则做不了群聊总结。
    群里有 6 个人，如果把所有 user 消息都压成同一条 role=user，
    模型看到的是「一个人连着说了 20 句」—— 它既不知道谁说了什么，
    也无从总结出「谁主张了什么」。这里按会话类型分流：
      * AI 伴侣 / 好友单聊 → 只有两个角色，传统 messages 格式即可
      * 群聊 → 用「发言人：内容」的文本形式带上标签
        （chat completions 协议不支持多个 user 角色交替出现）
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
    is_group = session.type == "group"
    out: list[dict[str, str]] = []
    for m in reversed(rows):
        if not m.content or not m.content.strip():
            continue
        role = _ROLE_MAP.get(m.sender_type, "user")
        if is_group and role == "user":
            out.append({"role": "user", "content": f"{speaker_label(m)}：{m.content}"})
        else:
            out.append({"role": role, "content": m.content})
    return out


def speaker_label(message: MessageModel) -> str:
    """这条消息在群聊里该显示成谁、该被总结成谁。

    优先用写入时存下的 ``sender_label``（那是用户给的显示名），
    旧数据没有这一列时才从 ``sender_id`` 推导。
    """
    stored = (message.sender_label or "").strip()
    if stored:
        return stored
    return _label_of(message.sender_id)
