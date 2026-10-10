"""用户自带 Key（BYOK）的请求级覆盖。

设计原则（与项目「密钥永不入库」约定一致）：

* 用户在浏览器里填 Key → 存在浏览器 localStorage → 每次请求用 ``X-Model-Key`` 头带上
* **后端不落盘、不入库、不打日志**，只在这次请求的生命周期内存在于内存
* 没带这个头时，一切走 ``.env`` 里的默认配置，行为与从前完全一致

日志脱敏：所有涉及 Key 的地方只打是否存在与前后 4 位，不打全值。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header

logger = logging.getLogger(__name__)

# 请求头名称
HEADER_MODEL_KEY = "x-model-key"
HEADER_MODEL_NAME = "x-model-name"
HEADER_EMBEDDING_KEY = "x-embedding-key"
HEADER_EMBEDDING_MODEL = "x-embedding-model"


def mask(value: str | None) -> str:
    """脱敏：只保留前后 4 位。日志里永远不要出现完整 Key。"""
    if not value:
        return "<空>"
    if len(value) <= 10:
        return f"{value[:2]}***{value[-2:]}"
    return f"{value[:4]}***{value[-4:]}"


@dataclass(frozen=True, slots=True)
class ModelOverride:
    """本次请求携带的用户配置。"""

    model_key: str | None = None
    model_name: str | None = None
    embedding_key: str | None = None
    embedding_model: str | None = None

    @property
    def has_model(self) -> bool:
        return bool(self.model_key and self.model_name)

    @property
    def has_embedding(self) -> bool:
        """Embedding 优先用独立的 Key，没填就复用对话的 Key。"""
        return bool((self.embedding_key or self.model_key) and self.embedding_model)

    @property
    def resolved_embedding_key(self) -> str | None:
        return self.embedding_key or self.model_key


async def read_override(
    x_model_key: Annotated[str | None, Header(alias=HEADER_MODEL_KEY)] = None,
    x_model_name: Annotated[str | None, Header(alias=HEADER_MODEL_NAME)] = None,
    x_embedding_key: Annotated[str | None, Header(alias=HEADER_EMBEDDING_KEY)] = None,
    x_embedding_model: Annotated[str | None, Header(alias=HEADER_EMBEDDING_MODEL)] = None,
) -> ModelOverride:
    """FastAPI 依赖：把请求头解析成覆盖配置。"""
    override = ModelOverride(
        model_key=(x_model_key or "").strip() or None,
        model_name=(x_model_name or "").strip() or None,
        embedding_key=(x_embedding_key or "").strip() or None,
        embedding_model=(x_embedding_model or "").strip() or None,
    )
    if override.has_model:
        logger.debug("本次请求使用用户自带 Key：%s", mask(override.model_key))
    return override


ModelOverrideDep = Annotated[ModelOverride, Depends(read_override)]