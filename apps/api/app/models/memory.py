"""记忆的 ORM 模型。

向量存在 Chroma，元数据与正文存在这里，两边用同一个 id 关联。
正文是否加密由 ``app.core.crypto`` 决定，这里只负责存取。
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class MemoryModel(Base):
    """一条长期记忆。"""

    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    #: profile / preference / fact / event
    type: Mapped[str] = mapped_column(String(16), default="fact", index=True)
    #: 记忆正文（开启加密时存的是密文）
    content: Mapped[str] = mapped_column(Text, default="")
    #: 抽取这段记忆的来源会话
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    #: 抽取时的抽取器：rules / llm / manual
    source: Mapped[str] = mapped_column(String(16), default="rules")
    #: 抽取置信度
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    #: 被召回过多少次，用于后续做记忆衰减
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    #: 正文是否处于加密态，列表接口据此决定要不要返回明文
    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (Index("ix_memories_type_created", "type", "created_at"),)