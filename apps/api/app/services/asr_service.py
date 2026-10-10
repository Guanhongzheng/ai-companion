"""语音转写（ASR）。

两条路，优先级从高到低：

1. **浏览器已经转好了** —— 前端用 Web Speech API 拿到文字，连音频一起传上来，
   这里直接用文字，省一次调用也省一次上传
2. **云端 ASR** —— 用户录了音但浏览器不支持识别时（Firefox / Safari），把音频
   发上来，经 LiteLLM 调 Whisper 或通义的语音识别

没配 Key 时返回 ``None`` 而不是报错：调用方据此在界面上说明「语音识别需要配置 Key」，
而不是让整个发送流程失败。
"""

from __future__ import annotations

import base64
import logging

from app.core.config import settings
from app.core.errors import friendly_model_error
from app.core.overrides import ModelOverride

logger = logging.getLogger(__name__)

#: 各provider 的 ASR 模型名
_ASR_MODELS = {
    "openai": "openai/whisper-1",
    "dashscope": "dashscope/paraformer-realtime-v2",
    "deepseek": None,  # DeepSeek 没有 ASR
}

#: 支持 ASR 的 provider（按优先级）
_ASR_PROVIDERS = ("dashscope", "openai")


def pick_asr_model(override: ModelOverride | None = None) -> tuple[str, str | None] | None:
    """决定用哪个 ASR 模型和 Key。

    返回 ``None`` 表示没有可用的 ASR 能力（调用方应给出友好提示）。
    """
    if override is not None and override.has_model:
        provider = override.model_name.split("/", 1)[0] if "/" in override.model_name else ""
        if _ASR_MODELS.get(provider):
            return _ASR_MODELS[provider], override.model_key

    env_keys = {
        "dashscope": settings.dashscope_api_key,
        "openai": settings.openai_api_key,
    }
    for provider in _ASR_PROVIDERS:
        if env_keys.get(provider):
            return _ASR_MODELS[provider], env_keys[provider]

    if settings.volcengine_access_key:
        return "volcengine/volcengine-asr", None
    return None


async def transcribe(
    audio: bytes, mime: str, override: ModelOverride | None = None
) -> str | None:
    """把音频转成文字。

    返回识别结果；不可用或失败时返回 ``None``，**不抛异常** —— 语音识别失败
    不应该让用户发不出消息。
    """
    target = pick_asr_model(override)
    if target is None:
        return None
    model, api_key = target

    try:
        from litellm import atranscription

        response = await atranscription(
            model=model,
            file=base64.b64encode(audio),
            **({"api_key": api_key} if api_key else {}),
        )
        text = getattr(response, "text", None)
        if text is None and isinstance(response, dict):
            text = response.get("text")
        return (text or "").strip() or None
    except Exception as exc:
        logger.warning("语音转写失败：%s", friendly_model_error(exc))
        return None