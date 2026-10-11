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

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as OrmSession

from app.core import emotion as emotion_mod
from app.core.config import settings
from app.core.errors import friendly_model_error
from app.core.overrides import ModelOverride
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    StreamAction,
    StreamDone,
    StreamEmotion,
    StreamError,
    StreamMemory,
    StreamMeta,
    StreamToken,
)
from app.services import intent as intent_mod
from app.services import media_service, memory_service, session_service, vision_service

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

#: 真正的系统提示与动作指令都在 intent 模块，这里只做转发
SYSTEM_PROMPTS = intent_mod.SYSTEM_PROMPTS

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


def has_credentials(model: str | None = None, override: ModelOverride | None = None) -> bool:
    """是否具备调用真实模型的条件。

    用户自带 Key 时优先用用户的 —— 这样即使服务端 .env 一个 Key 都没配，
    用户自己填了就能用真实模型。
    """
    if override is not None and override.has_model:
        return True
    return bool(_credential_for(normalize_model(model)))


def resolve_model_and_key(
    model: str | None, override: ModelOverride | None = None
) -> tuple[str, str | None]:
    """决定这次请求实际用哪个模型、用谁的 Key。

    返回 ``(模型名, api_key)``；``api_key`` 为 None 表示交给 LiteLLM 自己解析
    （对应服务端 .env 里已配好的场景）。
    """
    if override is not None and override.has_model:
        return normalize_model(override.model_name), override.model_key
    return normalize_model(model), None


async def _stream_tokens(
    messages: list[dict[str, str]], model: str, api_key: str | None = None
) -> AsyncIterator[str]:
    """经 LiteLLM 流式调用真实模型。"""
    from litellm import acompletion

    response = await acompletion(
        model=model,
        messages=messages,
        stream=True,
        temperature=0.8,
        max_tokens=1024,
        **({"api_key": api_key} if api_key else {}),
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
    action: str = intent_mod.ACTION_CHAT,
    attachment_note: str = "",
) -> list[dict[str, str]]:
    """组装发给模型的消息数组：系统提示 + 动作指令 + 记忆 + 附件描述 + 历史。"""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": intent_mod.system_prompt_for(session_type, action)}
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
    if attachment_note:
        # 附件描述以 system 身份注入，避免污染用户原话
        messages.append({"role": "system", "content": attachment_note})
    messages.extend(history)
    return messages


async def _describe_attachments(
    attachments: list[dict[str, object]], override: ModelOverride | None = None
) -> str:
    """把消息里的图片与语音转写整理成一段上下文。

    没有可用的视觉模型时返回空串 —— 图片照样存、照样显示，只是 AI 看不见，
    这时界面应提示「当前模型无法理解图片」，而不是静默当作已理解。
    """
    if not attachments:
        return ""

    parts: list[str] = []

    # 语音：优先用前端已转好的文字，没有再试服务端 ASR
    for audio in media_service.audio_of(attachments):
        transcript = audio.get("transcript")
        if transcript:
            parts.append(f"（用户发来一段语音，内容是：{transcript}）")

    images = media_service.images_of(attachments)
    if images:
        data_urls = [
            url
            for url in (vision_service.load_as_data_url(str(i.get("url", ""))) for i in images)
            if url
        ]
        description = await vision_service.describe_images(
            data_urls, vision_service.DEFAULT_VISION_PROMPT, override
        )
        if description:
            parts.append(f"（用户发来了 {len(images)} 张图片，图片内容是：{description}）")
        else:
            parts.append(
                f"（用户发来了 {len(images)} 张图片，但当前模型无法理解图片内容）"
            )

    return "\n".join(parts)


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
    db: OrmSession, req: ChatRequest, override: ModelOverride | None = None
) -> AsyncIterator[tuple[str, object]]:
    """产出完整的 SSE 事件序列。

    副作用：会把用户消息与 AI 回复落库，并更新会话时间。
    """
    session = session_service.get_or_404(db, req.session_id)
    model, api_key = resolve_model_and_key(req.model, override)
    real = has_credentials(req.model, override)

    yield "meta", StreamMeta(session_id=session.id, model=model, mocked=not real)

    # 1) 落库用户消息
    latest_user = ""
    latest_attachments: list[dict[str, object]] = []
    for msg in req.messages:
        session_service.append_message(
            db,
            session,
            sender_type=msg.role,
            content=msg.content,
            attachments=msg.attachments,
        )
        if msg.role == "user":
            latest_user = msg.content
            latest_attachments = msg.attachments

    # 2) 意图判定：群聊里没被 @ 就安静旁听，不产生任何 AI 回复
    action = intent_mod.resolve_action(session.type, latest_user, req.action)
    waiting = action == intent_mod.ACTION_SKIPPED
    yield "action", StreamAction(action=action, waiting_for_mention=waiting)
    if waiting:
        logger.info("群聊未被 @，本轮不生成回复")
        yield "done", StreamDone(finish_reason="skipped")
        return

    # 2.5) 抽取长期记忆。放在这里而不是生成之前，是**故意的**：
    # 本轮回复不该用刚抽出来的记忆（那等于让 AI 自问自答地引用自己的笔记），
    # 而且抽取可能是一次 LLM 请求，压在 SSE 流前面会拖慢首字响应。
    # 所以丢后台，下一轮的 memory 事件里就能用上。
    memory_service.schedule_auto_ingest(latest_user, session.id)

    # 3) 情绪分析先发，前端可以立刻切主题，比等文字更快
    result = emotion_mod.PROVIDER(latest_user)
    yield "emotion", StreamEmotion(tag=result.tag, confidence=result.confidence)

    # 3.5) 召回长期记忆。放在情绪之后、生成之前，让界面能先展示「AI 想起了什么」
    memories = await _recall_memories(db, latest_user)
    if memories:
        yield "memory", StreamMemory(items=memories)

    # 3.7) 图片理解 / 语音转写，转成文本上下文
    attachment_note = await _describe_attachments(latest_attachments, override)

    # 3) 组装上下文并流式生成
    history = session_service.to_model_messages(db, session)
    messages = build_messages(session.type, history, memories, action, attachment_note)

    chunks: list[str] = []
    try:
        mock_text = _mock_action_reply(action) or _mock_reply(result.tag, latest_user)
        source = _stream_tokens(messages, model, api_key) if real else _mock_tokens(mock_text)
        async for text in source:
            chunks.append(text)
            yield "token", StreamToken(text=text)
    except Exception as exc:
        logger.exception("模型调用失败")
        yield "error", StreamError(message=friendly_model_error(exc))
        yield "done", StreamDone(finish_reason="error")
        return

    # 4) 落库 AI 回复
    reply = "".join(chunks)
    session_service.append_message(
        db, session, sender_type="ai", content=reply, emotion=result.tag
    )

    yield "done", StreamDone(finish_reason="stop")


#: 无 Key 时，按动作给出各自的模拟结果，让演示也能看出行为差异
MOCK_ACTION_REPLIES = {
    intent_mod.ACTION_POLISH: "润色后的版本：「明天下午三点，方便的话把方案发我，我看一下再回复你。」",
    intent_mod.ACTION_TRANSLATE: "Translation: Let's meet at three tomorrow afternoon. I'll send over the proposal later.",
    intent_mod.ACTION_SUMMARIZE: "- 明天三点开会\n- 需要提前准备方案\n- 会后由我方跟进",
    intent_mod.ACTION_SUGGEST: (
        "1. 「可以，我三点准时到。」\n2. 「时间我这边没问题，方案我提前发群里。」"
    ),
}


def _mock_action_reply(action: str) -> str | None:
    """辅助动作的模拟回复；普通聊天返回 None。"""
    return MOCK_ACTION_REPLIES.get(action)


def _mock_reply(tag: str, user_text: str) -> str:
    if tag in MOCK_REPLIES and user_text:
        return MOCK_REPLIES[tag]
    return NO_KEY_HINT


async def complete_chat(
    db: OrmSession, req: ChatRequest, override: ModelOverride | None = None
) -> ChatResponse:
    """非流式对话：内部复用同一套编排，只是把 token 收集起来。"""
    session = session_service.get_or_404(db, req.session_id)
    model, api_key = resolve_model_and_key(req.model, override)
    real = has_credentials(req.model, override)

    for msg in req.messages:
        session_service.append_message(
            db, session, sender_type=msg.role, content=msg.content, attachments=msg.attachments
        )

    latest = req.messages[-1].content if req.messages else ""
    attachments = req.messages[-1].attachments if req.messages else []
    action = intent_mod.resolve_action(session.type, latest, req.action)
    if action == intent_mod.ACTION_SKIPPED:
        # 群聊里没被 @ ：用户消息已落库，但 AI 不应该说话
        return ChatResponse(
            session_id=session.id,
            reply="",
            model=model,
            mocked=False,
            action=action,
            waiting_for_mention=True,
        )

    result = emotion_mod.PROVIDER(latest)
    # 与流式路径同一个位置：抽取丢后台，不拖慢本轮回复
    memory_service.schedule_auto_ingest(latest, session.id)
    memories = await _recall_memories(db, latest)
    history = session_service.to_model_messages(db, session)
    attachment_note = await _describe_attachments(attachments, override)
    messages = build_messages(session.type, history, memories, action, attachment_note)

    if real:
        from litellm import acompletion

        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=0.8,
                **({"api_key": api_key} if api_key else {}),
            )
            reply = response.choices[0].message.content or ""
        except Exception as exc:
            # 用户填错 Key / 网络不通都会走到这里，必须给能看懂的中文提示，
            # 而不是把厂商的原始堆栈甩出去
            logger.warning("模型调用失败：%s", friendly_model_error(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=friendly_model_error(exc),
            ) from exc
    else:
        reply = _mock_action_reply(action) or _mock_reply(
            result.tag, req.messages[-1].content if req.messages else ""
        )

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
        action=action,
    )


def dump(payload: object) -> str:
    """SSE data 字段序列化。"""
    if hasattr(payload, "model_dump"):
        return json.dumps(payload.model_dump(), ensure_ascii=False)
    return json.dumps(payload, ensure_ascii=False)