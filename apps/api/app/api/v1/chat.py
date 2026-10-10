"""对话接口：非流式 + SSE 流式。

路由层保持轻薄 —— 事件序列由 chat_service 产出，这里只负责序列化。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession
from sse_starlette.sse import EventSourceResponse

from app.core.overrides import ModelOverrideDep
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter()

DbSession = Annotated[OrmSession, Depends(get_db)]


@router.post("", response_model=ChatResponse, summary="对话（非流式）")
async def chat(req: ChatRequest, db: DbSession, override: ModelOverrideDep) -> ChatResponse:
    return await chat_service.complete_chat(db, req, override)


@router.post("/stream", summary="对话（SSE 流式）")
async def chat_stream(req: ChatRequest, db: DbSession, override: ModelOverrideDep) -> EventSourceResponse:
    """SSE 事件协议（前端按 event 名分发）：

    - `meta`    : 会话元信息（含实际使用的模型、是否降级）
    - `emotion` : 情绪标签，驱动前端主题 / 壁纸 / 音乐
    - `token`   : 增量文本
    - `done`    : 结束
    - `error`   : 出错，随后连接关闭
    """

    async def event_generator():
        async for name, payload in chat_service.stream_chat_events(db, req, override):
            yield {"event": name, "data": chat_service.dump(payload)}

    return EventSourceResponse(event_generator())