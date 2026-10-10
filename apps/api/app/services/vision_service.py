"""图像理解（Vision）。

把图片构造成多模态 messages 交给视觉模型。关键点：

* 视觉模型和对话模型**常常不是同一个**（Qwen-VL、gpt-4o、claude 都行），
  所以要能单独指定 ``VISION_MODEL``
* 没配 Key、或模型不支持视觉时，返回 ``None`` 而不是报错 ——
  界面据此提示「图片已发送，但当前模型无法理解图片」，而不是让消息发不出去
"""

from __future__ import annotations

import base64
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.errors import friendly_model_error
from app.core.overrides import ModelOverride

logger = logging.getLogger(__name__)

#: 明确支持视觉的 provider（用于判断「用户填的模型能不能看图」）
VISION_PROVIDERS = ("dashscope", "openai", "anthropic", "siliconflow", "gemini", "zhipu")

#: 各家推荐的视觉模型
VISION_MODELS = {
    "dashscope": "dashscope/qwen-vl-plus",
    "openai": "openai/gpt-4o-mini",
    "anthropic": "anthropic/claude-3-5-sonnet-latest",
    "siliconflow": "siliconflow/Qwen/Qwen2-VL-7B-Instruct",
    "gemini": "gemini/gemini-2.0-flash",
    "zhipu": "zhipuai/glm-4v-plus",
}


@dataclass(slots=True)
class VisionTarget:
    model: str
    api_key: str | None


def _provider_of(model_name: str) -> str:
    return model_name.split("/", 1)[0] if "/" in model_name else ""


def pick_vision_model(override: ModelOverride | None = None) -> VisionTarget | None:
    """决定用哪个视觉模型和 Key；不可用时返回 None。"""
    # 1) 单独配了视觉模型就用它
    if settings.vision_model.strip():
        return VisionTarget(model=settings.vision_model.strip(), api_key=None)

    # 2) 用户在设置页填的对话模型，自己就支持视觉
    if override is not None and override.has_model:
        provider = _provider_of(override.model_name or "")
        if provider in VISION_PROVIDERS:
            return VisionTarget(
                model=override.model_name,
                api_key=override.model_key,
            )

    # 3) 退回到服务端已配的、支持视觉的 provider
    env_keys = {
        "dashscope": settings.dashscope_api_key,
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
    }
    for provider, key in env_keys.items():
        if key:
            return VisionTarget(model=VISION_MODELS[provider], api_key=key)

    return None


def load_as_data_url(url_path: str) -> str | None:
    """把已上传的图片读成 data URL。

    只接受 ``{api_prefix}/media/xxx`` 这种自家上传接口的路径，
    不接受任意外链 —— 否则等于让服务端替用户去请求任意地址。
    """
    prefix = f"{settings.api_prefix}/media/"
    if not url_path.startswith(prefix):
        return None
    filename = url_path[len(prefix) :]
    if "/" in filename or "\\" in filename or not filename:
        return None

    root = Path(settings.local_storage_dir).resolve()
    candidate = (root / filename).resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None

    mime = mimetypes.guess_type(filename)[0] or "image/png"
    encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_vision_message(prompt: str, data_urls: list[str]) -> list[dict[str, object]]:
    """构造多模态 content。图片排在文字后面，多数模型对这种顺序更稳。"""
    content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
    for url in data_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    return [{"role": "user", "content": content}]


async def describe_images(
    data_urls: list[str], prompt: str, override: ModelOverride | None = None
) -> str | None:
    """让模型描述这��图片。不可用或失败都返回 None。"""
    target = pick_vision_model(override)
    if target is None or not data_urls:
        return None

    try:
        from litellm import acompletion

        response = await acompletion(
            model=target.model,
            messages=build_vision_message(prompt, data_urls),
            max_tokens=400,
            **({"api_key": target.api_key} if target.api_key else {}),
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception as exc:
        logger.warning("图像理解失败：%s", friendly_model_error(exc))
        return None


#: 看图时给模型的指令，要求客观描述、不要脑补
DEFAULT_VISION_PROMPT = (
    "请客观描述这些图片的内容：主体是什么、有什么文字、有哪些值得注意的细节。"
    "不确定的地方直接说不确定，不要编造。"
)