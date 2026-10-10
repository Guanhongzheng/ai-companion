"""对话相关的出入参。

SSE 事件协议（前端按 event 名分发）：
    meta -> emotion -> token*N -> done
出错时发 error 后关闭连接。
"""

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    role: str = Field(default="user", description="user | assistant | system")
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, description="会话 ID")
    messages: list[ChatMessageIn] = Field(default_factory=list)
    model: str | None = Field(default=None, description="不传则用 DEFAULT_CHAT_MODEL")
    stream: bool = True
    #: 好友单聊里的辅助动作。不传则由后端按关键词推断
    action: str | None = Field(default=None, description="polish / translate / summarize / suggest")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    emotion: str | None = None
    model: str | None = None
    mocked: bool = Field(default=False, description="是否走了本地降级，未调用真实模型")
    memories: list[dict[str, object]] = Field(default_factory=list)
    #: 本轮实际执行的意图：chat（正常对话）/ polish / translate / summarize / suggest
    action: str = "chat"
    #: 群聊里没被 @ 时为 True，此时不产生 AI 回复
    waiting_for_mention: bool = False


# ---- SSE 事件负载 ----


class StreamMeta(BaseModel):
    session_id: str
    model: str
    mocked: bool = False


class StreamEmotion(BaseModel):
    tag: str
    confidence: float


class StreamToken(BaseModel):
    text: str


class StreamDone(BaseModel):
    finish_reason: str = "stop"


class StreamAction(BaseModel):
    """本轮意图判定结果，前端据此切换提示文案与后续可选项。"""

    #: chat / polish / translate / summarize / suggest / skipped
    action: str
    #: 群聊里没被 @ 时为 True
    waiting_for_mention: bool = False


class StreamMemory(BaseModel):
    """本次回复召回到的记忆，用来在界面上展示「AI 想起了什么」。"""

    items: list[dict[str, object]] = []


class StreamError(BaseModel):
    message: str