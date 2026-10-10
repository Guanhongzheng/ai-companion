"""设置接口：查看模型来源、校验用户填的 Key 是否可用。

**这些接口自己不带 Key**，Key 由请求头 ``X-Model-Key`` 传入（同对话接口），
服务端不落盘、不入库、不打日志。
"""

from typing import Any

from fastapi import APIRouter

from app.core.errors import friendly_model_error
from app.core.overrides import ModelOverrideDep, mask
from app.services.chat_service import normalize_model

router = APIRouter()


@router.get("/status", summary="查看当前生效的模型来源")
async def status(override: ModelOverrideDep) -> dict[str, Any]:
    from app.core.config import settings as app_settings

    server_has_key = bool(
        app_settings.openai_api_key
        or app_settings.dashscope_api_key
        or app_settings.deepseek_api_key
        or app_settings.anthropic_api_key
        or app_settings.gemini_api_key
    )

    return {
        "using_user_key": override.has_model,
        "model": normalize_model(override.model_name) if override.has_model else app_settings.default_chat_model,
        # 只回传脱敏后的提示，界面用它显示「当前使用 sk-a***mnop」
        "key_hint": mask(override.model_key),
        "server_default_model": app_settings.default_chat_model,
        "server_has_any_key": server_has_key,
        "memory_encrypted": app_settings.memory_encrypt,
    }


@router.post("/validate", summary="校验 Key 与模型可用性")
async def validate(override: ModelOverrideDep) -> dict[str, Any]:
    """用最小 token 发一次真实请求，确认 Key 与模型名可用。

    失败时只返回错误摘要，绝不把 Key 或完整堆栈带回来。
    """
    if not override.has_model:
        return {"ok": False, "message": "没有收到 API Key"}

    model = normalize_model(override.model_name)
    key = override.model_key
    assert key is not None  # has_model 已保证非空

    try:
        from litellm import acompletion

        resp = await acompletion(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=4,
            api_key=key,
        )
        _ = resp.choices[0].message.content
    except Exception as exc:
        return {"ok": False, "model": model, "message": friendly_model_error(exc)}

    return {"ok": True, "model": model, "message": "连接成功"}
