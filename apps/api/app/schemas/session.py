"""会话与消息的响应模型。字段与 packages/shared 的前端类型一一对应。"""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str = "ai"
    title: str
    avatar_url: str | None = None
    member_count: int = 2
    unread_count: int = 0
    pinned: bool = False
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    sender_type: str
    sender_id: str
    content: str
    content_type: str = "text"
    emotion: str | None = None
    #: 结构化附件。库里存的是 JSON 文本，这里自动解析成列表
    attachments: list[dict[str, Any]] = []
    created_at: datetime

    @field_validator("attachments", mode="before")
    @classmethod
    def _parse_attachments(cls, value: object) -> object:
        """DB 里存的是 JSON 字符串，出参要结构化列表。

        解析失败就当没有附件 —— 坏数据不该让整个消息列表 500。
        """
        if not isinstance(value, str):
            return value
        try:
            data = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
        return data if isinstance(data, list) else []


class SessionCreate(BaseModel):
    type: str = "ai"
    title: str = "新会话"
    member_count: int = 2


class SessionRename(BaseModel):
    title: str