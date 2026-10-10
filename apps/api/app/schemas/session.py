"""会话与消息的响应模型。字段与 packages/shared 的前端类型一一对应。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    created_at: datetime


class SessionCreate(BaseModel):
    type: str = "ai"
    title: str = "新会话"
    member_count: int = 2


class SessionRename(BaseModel):
    title: str