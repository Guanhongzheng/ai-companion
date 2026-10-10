"""对话接口：非流式 + SSE 流式。

当前为**骨架实现**：流式接口用假数据演示事件协议，
接入 LiteLLM 后把 `_fake_token_stream` 换掉即可。
"""

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(description="user | assistant | system")
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(description="会话 ID")
    messages: list[ChatMessage] = Field(default_factory=list)
    model: str | None = Field(default=None, description="不传则用 DEFAULT_CHAT_MODEL")
    stream: bool = True


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    emotion: str | None = None


@router.post("", response_model=ChatResponse, summary="对话（非流式）")
async def chat(req: ChatRequest) -> ChatResponse:
    # TODO: 调 services/chat_service.py，走 LangGraph + LiteLLM
    return ChatResponse(session_id=req.session_id, reply="[stub] 后端已收到消息", emotion="neutral")


async def _fake_token_stream(text: str) -> AsyncIterator[str]:
    """占位实现：把一句话按字吐出，用于验证 SSE 链路。"""
    for ch in text:
        yield ch
        await asyncio.sleep(0.03)


@router.post("/stream", summary="对话（SSE 流式）")
async def chat_stream(req: ChatRequest) -> EventSourceResponse:
    """SSE 事件协议（前端按 event 名分发）：

    - `meta`    : 会话元信息
    - `token`   : 增量文本
    - `emotion` : 情绪标签，驱动前端主题/壁纸/音乐
    - `done`    : 结束
    """

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        yield {"event": "meta", "data": json.dumps({"session_id": req.session_id})}

        # TODO: 替换为真实的情感分析结果
        yield {
            "event": "emotion",
            "data": json.dumps({"tag": "calm", "confidence": 0.82}),
        }

        reply = "[stub] 这是一段占位回复，用来验证前后端 SSE 是否连通。"
        async for token in _fake_token_stream(reply):
            yield {"event": "token", "data": json.dumps({"text": token})}

        yield {"event": "done", "data": json.dumps({"finish_reason": "stop"})}

    return EventSourceResponse(event_generator())
