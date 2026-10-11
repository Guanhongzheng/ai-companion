"""会话与消息的 ORM 模型。

三层会话（ai / direct / group）共用同一张 sessions 表，
靠 type 字段区分能力差异，避免为每种会话建一套表。
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SessionModel(Base):
    """一次会话（AI 伴侣 / 好友单聊 / 群聊）。"""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    #: ai=AI 伴侣单聊 / direct=好友单聊 / group=群聊
    type: Mapped[str] = mapped_column(String(16), index=True, default="ai")
    title: Mapped[str] = mapped_column(String(120), default="新会话")
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=2)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, index=True
    )

    messages: Mapped[list["MessageModel"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MessageModel(Base):
    """一条消息。用户与 AI 共用同一张表，靠 sender_type 区分。"""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    #: user / ai / system
    sender_type: Mapped[str] = mapped_column(String(16), default="user")
    sender_id: Mapped[str] = mapped_column(String(64), default="local-user")
    #: 群聊里这条消息是谁说的。写入时定好（优先取请求里的显示名），
    #: 不在读的时候从 sender_id 猜 —— 否则历史数据改了 id 名字就跟着变。
    sender_label: Mapped[str] = mapped_column(String(64), default="我")
    content: Mapped[str] = mapped_column(Text, default="")
    #: text / image / audio / file
    content_type: Mapped[str] = mapped_column(String(16), default="text")
    #: 结构化附件，JSON 数组。元素形如
    #: {"kind": "image", "url": "/api/v1/media/xxx.png", "name": "截图.png"}
    #: {"kind": "audio", "url": "...", "transcript": "识别出的文字"}
    attachments: Mapped[str] = mapped_column(Text, default="[]")
    #: 情绪标签，驱动前端主题 / 壁纸 / 音乐联动
    emotion: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    session: Mapped[SessionModel] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_session_created", "session_id", "created_at"),)