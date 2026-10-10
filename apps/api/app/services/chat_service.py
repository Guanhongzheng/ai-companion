"""对话服务：消息编排 + 流式生成。

设计要点
--------
1. **所有模型调用统一走 LiteLLM**，业务代码不直连任何厂商 SDK。
2. **未配置任何模型 Key 时自动降级为本地模拟流**，保证在没有网、没有 Key、
   演示现场断网的情况下，整条 SSE 链路依然完整可跑通。
3. 本模块产出的是 `(事件名, 负载)` 序列，路由层只负责序列化成 SSE，
   协议细节集中在这里，不散落。

事件顺序： meta -> emotion -> token*N -> done   （出错时 error）
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session as OrmSession

from app.core import emotion as emotion_mod
from app.core.config import settings
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    StreamDone,
    StreamEmotion,
    StreamError,
    StreamMemory,
    StreamMeta,
    StreamToken,
)
from app.services import session_service

logger = logging.getLogger(__name__)

AI_COMPANION_SYSTEM = (
    "你是「小伴」，用户的长期 AI 伴侣。说话自然、简短、有温度，像真人聊天而不是客服。"
    "不要用列表和 Markdown 标题，不要重复用户的话。"
    "当用户情绪低落时先接住情绪，再 gentle 地给建议。"
)

ASSISTANT_SYSTEM = (
    "你是一个中文助手。回答直接、简洁，用口语，不要客套话和多余的排版。"
)

GROUP_SYSTEM = (
    "你参与一个群聊。被 @ 时才回答，回答简短自然，不要抢话，不要刷屏。"
)

SYSTEM_PROMPTS = {
    "ai": AI_COMPANION_SYSTEM,
    "direct": ASSISTANT_SYSTEM,
    "group": GROUP_SYSTEM,
}

#: 无 Key 时使用的模拟回复，会根据情绪挑一句，让演示有辨识度
MOCK_REPLIES = {
    "sad": "我在这儿呢。想说的话我都会认真听，你慢慢说，不着急。",
    "anxious": "听起来你有点绷着。要不先深呼吸一下？最让你不安的是哪件事？",
    "angry": "确实够呛的。换我我也炸。先骂完，然后我们一起看看怎么收拾。",
    "tired": "辛苦了。要不先歇会儿？水喝了没，今天别再硬扛了。",
    "excited": "哇，听着就很带劲！快跟我说说详情，我准备好兴奋了。",
    "joy": "不错啊！看得出来你挺开心的，我也跟着高兴。",
    "calm": "这样挺好的，安安稳稳的。继续保持。",
    "neutral": "收到。你想从哪儿开始聊？",
}

NO_KEY_HINT = (
    "【当前为本地模拟回复】检测到还没有配置任何模型 API Key，"
    "所以没有真正调用大模型。在 apps/api/.env 里填上 DEEPSEEK_API_KEY / "
    "DASHSCOPE_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY "
    "中的任意一个（或设置 OLLAMA_BASE_URL 走本地模型），重启后即可获得真实回复。"
)


def normalize_model(model: str | None) -> str:
    """给模型名补上 LiteLLM 需要的 provider 前缀。"""
    name = model or settings.default_chat_model
    if "/" in name:
        return name
    lowered = name.lower()
    rules = (
        ("deepseek", "deepseek"),
        ("qwen", "dashscope"),
        ("claude", "anthropic"),
        ("gemini", "gemini"),
        ("gpt", "openai"),
        ("o1", "openai"),
        ("o3", "openai"),
        ("llama", "ollama"),
        ("mistral", "ollama"),
    )
    for prefix, provider in rules:
        if lowered.startswith(prefix):
            return f"{provider}/{name}"
    return name


def _credential_for(model: str) -> str:
    """返回该模型对应的 API Key（本地模型返回非空标记）。"""
    provider = model.split("/", 1)[0] if "/" in model else ""
    mapping = {
        "openai": settings.openai_api_key,
        "deepseek": settings.deepseek_api_key,
        "dashscope": settings.dashscope_api_key,
        "anthropic": settings.anthropic_api_key,
        "gemini": settings.gemini_api_key,
    }
    if provider in mapping:
        return mapping[provider]
    if provider == "ollama" or settings.ollama_base_url:
        return "local"
    # 前缀不认识时，只要配了任意一个 Key 就允许尝试
    return any(
        (
            settings.openai_api_key,
            settings.deepseek_api_key,
            settings.dashscope_api_key,
            settings.anthropic_api_key,
            settings.gemini_api_key,
        )
    )


def has_credentials(model: str | None = None) -> bool:
    """是否具备调用真实模型的条件。"""
    return bool(_credential_for(normalize_model(model)))


async def _stream_tokens(messages: list[dict[str, str]], model: str) -> AsyncIterator[str]:
    """经 LiteLLM 流式调用真实模型。"""
    from litellm import acompletion

    response = await acompletion(
        model=model,
        messages=messages,
        stream=True,
        temperature=0.8,
        max_tokens=1024,
    )
    async for chunk in response:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None)
        content = getattr(delta, "content", None)
        if content:
            yield content


async def _mock_tokens(text: str, delay: float = 0.02) -> AsyncIterator[str]:
    """本地模拟流：逐字吐出，行为与真实模型一致，便于前端无差别处理。"""
    for chunk in _chunk_cn(text):
        yield chunk
        await asyncio.sleep(delay)


def _chunk_cn(text: str) -> list[str]:
    """中文按 1-2 字切块，比逐字更接近真实模型的吐字节奏。"""
    return [text[i : i + 2] for i in range(0, len(text), 2)] or [""]


def build_messages(
    session_type: str,
    history: list[dict[str, str]],
    memories: list[dict[str, object]] | None = None,
) -> list[dict[str, str]]:
    """组装发给模型的消息数组：系统提示 + 记忆 + 历史。"""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPTS.get(session_type, ASSISTANT_SYSTEM)}
    ]
    if memories:
        lines = "\n".join(f"- {m.get('content', '')}" for m in memories)
        messages.append(
            {
                "role": "system",
                "content": (
                    "以下是关于用户的已知信息，可以自然地利用它们来回应，"
                    "不要生硬罗列，也不要提「根据我的记录」这类说法：\n" + lines
                ),
            }
        )
    messages.extend(history)
    return messages


async def _recall_memories(db: OrmSession, query: str) -> list[dict[str, object]]:
    """召回与本轮相关的记忆，供注入 prompt 与界面展示。"""
    from app.memory.retriever import retrieve

    if not query.strip():
        return []
    try:
        hits = await retrieve(query)
    except Exception as exc:
        logger.warning("记忆召回失败：%s", exc)
        return []

    if not hits:
        return []

    # 命中的记忆 hit_count +1（借数据库 session 更新）
    from app.models.memory import MemoryModel

    for hit in hits:
        row = db.get(MemoryModel, hit.id)
        if row is not None:
            row.hit_count += 1
    try:
        db.commit()
    except Exception:
        db.rollback()

    return [hit.to_dict() for hit in hits]


async def stream_chat_events(
    db: OrmSession, req: ChatRequest
) -> AsyncIterator[tuple[str, object]]:
    """产出完整的 SSE 事件序列。

    副作用：会把用户消息与 AI 回复落库，并更新会话时间。
    """
    session = session_service.get_or_404(db, req.session_id)
    model = normalize_model(req.model)
    real = has_credentials(model)

    yield "meta", StreamMeta(session_id=session.id, model=model, mocked=not real)

    # 1) 落库用户消息
    latest_user = ""
    for msg in req.messages:
        session_service.append_message(
            db, session, sender_type=msg.role, content=msg.content
        )
        if msg.role == "user":
            latest_user = msg.content

    # 2) 情绪分析先发，前端可以立刻切主题，比等文字更快
    result = emotion_mod.PROVIDER(latest_user)
    yield "emotion", StreamEmotion(tag=result.tag, confidence=result.confidence)

    # 2.5) 召回长期记忆。放在情绪之后、生成之前，让界面能先展示「AI 想起了什么」
    memories = await _recall_memories(db, latest_user)
    if memories:
        yield "memory", StreamMemory(items=memories)

    # 3) 组装上下文并流式生成
    history = session_service.to_model_messages(db, session)
    messages = build_messages(session.type, history, memories)

    chunks: list[str] = []
    try:
        source = _stream_tokens(messages, model) if real else _mock_tokens(
            _mock_reply(result.tag, latest_user)
        )
        async for text in source:
            chunks.append(text)
            yield "token", StreamToken(text=text)
    except Exception as exc:
        logger.exception("模型调用失败")
        yield "error", StreamError(message=f"模型调用失败：{exc}")
        yield "done", StreamDone(finish_reason="error")
        return

    # 4) 落库 AI 回复
    reply = "".join(chunks)
    session_service.append_message(
        db, session, sender_type="ai", content=reply, emotion=result.tag
    )

    yield "done", StreamDone(finish_reason="stop")


def _mock_reply(tag: str, user_text: str) -> str:
    if tag in MOCK_REPLIES and user_text:
        return MOCK_REPLIES[tag]
    return NO_KEY_HINT


async def complete_chat(db: OrmSession, req: ChatRequest) -> ChatResponse:
    """非流式对话：内部复用同一套编排，只是把 token 收集起来。"""
    session = session_service.get_or_404(db, req.session_id)
    model = normalize_model(req.model)
    real = has_credentials(model)

    for msg in req.messages:
        session_service.append_message(db, session, sender_type=msg.role, content=msg.content)

    result = emotion_mod.PROVIDER(req.messages[-1].content if req.messages else "")
    memories = await _recall_memories(db, req.messages[-1].content if req.messages else "")
    history = session_service.to_model_messages(db, session)
    messages = build_messages(session.type, history, memories)

    if real:
        from litellm import acompletion

        response = await acompletion(model=model, messages=messages, temperature=0.8)
        reply = response.choices[0].message.content or ""
    else:
        reply = _mock_reply(result.tag, req.messages[-1].content if req.messages else "")

    session_service.append_message(
        db, session, sender_type="ai", content=reply, emotion=result.tag
    )

    return ChatResponse(
        session_id=session.id,
        reply=reply,
        emotion=result.tag,
        model=model,
        mocked=not real,
        memories=memories,
    )


def dump(payload: object) -> str:
    """SSE data 字段序列化。"""
    if hasattr(payload, "model_dump"):
        return json.dumps(payload.model_dump(), ensure_ascii=False)
    return json.dumps(payload, ensure_ascii=False)