"""向量化层：把文本转成定长向量。

**刻意做成可插拔的**，因为能不能装本地模型、能不能调云端 API，取决于部署环境：

===============  ==================================================
优先级实现        启用条件
===============  ==================================================
1. 本地 bge-m3     装了 ``requirements-ml.txt``（会带 PyTorch，2-3GB）
2. 云端 Embedding  配了任意模型 API Key，经 LiteLLM 路由
3. 哈希降级        都没有时的兜底，零依赖、毫秒级
===============  ==================================================

第3 种是**功能哈希（feature hashing）**：把中文的字符 unigram + bigram
用 blake2b 映射到固定维度上。它不是语义向量，但对字面相近的文本召回效果尚可，
足以让「抽取 → 去重 → 召回 → 重排」整条链路在任何环境下都跑得通、能演示。
换到 bge-m3 或云端模型时检索质量会有明显提升，**上层代码一行都不用改**。

⚠️ 哈希必须用 blake2b 而不是内置 ``hash()``：内置哈希对字符串是按进程加盐的，
跨进程不稳定，会导致「入库时算出的向量」和「检索时算出的向量」对不上，
向量库直接失效。
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_DIM = 1024


# ---------------------------------------------------------------- 接口


@runtime_checkable
class Embedder(Protocol):
    """所有向量化实现的统一契约。"""

    name: str
    dim: int

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


# ---------------------------------------------------------------- 哈希兜底

_CLEAN_RE = re.compile(r"[^\w一-鿿]+")
_STOP = frozenset("的了是在和与也就都而及或吗呢啊吧呀哦嗯我你他她它们这那有没不很")


class HashingEmbedder:
    """字符 n-gram 特征哈希 + L2 归一化。零依赖，纯 CPU。"""

    name = "hashing"
    dim = DEFAULT_DIM

    def _grams(self, text: str) -> list[str]:
        cleaned = _CLEAN_RE.sub(" ", text.lower()).strip()
        if not cleaned:
            return []
        grams: list[str] = []
        for token in cleaned.split():
            # 中文按字 bigram，英文数字按整词
            chars = list(token)
            grams.extend(chars)
            grams.extend(chars[i] + chars[i + 1] for i in range(len(chars) - 1))
        return [g for g in grams if g not in _STOP]

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for gram in self._grams(text):
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=4).digest()
            vec[int.from_bytes(digest, "big") % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


# ---------------------------------------------------------------- 本地 bge-m3


class SentenceTransformerEmbedder:
    """本地 bge-m3。需要先装 requirements-ml.txt。"""

    name = "bge-m3"
    #: bge-m3 是稠密向量，1024 维
    dim = 1024

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(settings.default_embedding_model, trust_remote_code=True)
        self.dim = self._model.get_sentence_embedding_dimension() or self.dim

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]


# ---------------------------------------------------------------- 云端


class CloudEmbedder:
    """经 LiteLLM 调用云端 Embedding（DashScope / OpenAI / 硅基流动等）。"""

    name = "cloud"

    def __init__(self, model: str | None = None) -> None:
        self.model = _with_provider(model or settings.default_embedding_model)

    @property
    def dim(self) -> int:
        # 常见维度：bge-m3=1024, text-embedding-v3=1024/2048, text-embedding-3=1536
        lowered = self.model.lower()
        if "bge" in lowered:
            return 1024
        if "text-embedding-v3" in lowered:
            return 1024
        return 1536

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        from litellm import aembedding

        resp = await aembedding(model=self.model, input=list(texts))
        # 保证返回顺序与输入一致
        ordered = sorted(resp.data, key=lambda d: d.index)
        return [item["embedding"] for item in ordered]

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_documents([text]))[0]


def _with_provider(name: str) -> str:
    """给云端 embedding 模型名补上 LiteLLM provider 前缀。"""
    if "/" in name:
        return name
    lowered = name.lower()
    rules = (
        ("bge", "siliconflow"),
        ("text-embedding-v3", "dashscope"),
        ("text-embedding", "dashscope"),
        ("qwen", "dashscope"),
    )
    for prefix, provider in rules:
        if lowered.startswith(prefix):
            return f"{provider}/{name}"
    return name


# ---------------------------------------------------------------- 选择


_cached: Embedder | None = None


def _has_any_model_key() -> bool:
    return bool(
        settings.openai_api_key
        or settings.dashscope_api_key
        or settings.deepseek_api_key
        or settings.anthropic_api_key
        or settings.gemini_api_key
    )


def get_embedder() -> Embedder:
    """按优先级挑选向量化实现，结果缓存。

    想强制指定时设环境变量 ``MEMORY_EMBEDDING_PROVIDER``：
    ``hashing`` / ``sentence-transformers`` / ``cloud``
    """
    global _cached
    if _cached is not None:
        return _cached

    forced = (settings.memory_embedding_provider or "").strip().lower()
    # 默认按「本地模型 → 云端 → 哈希」依次尝试
    candidates = [forced] if forced else ["sentence-transformers", "cloud", "hashing"]

    for kind in candidates:
        try:
            if kind == "sentence-transformers":
                embedder: Embedder = SentenceTransformerEmbedder()
            elif kind == "cloud":
                if not _has_any_model_key():
                    continue
                embedder = CloudEmbedder()
            else:
                embedder = HashingEmbedder()
        except Exception as exc:
            logger.warning("向量化实现 %s 不可用（%s），尝试下一个", kind, exc)
            continue
        else:
            logger.info("记忆向量化使用：%s（dim=%d）", embedder.name, embedder.dim)
            _cached = embedder
            return _cached

    fallback = HashingEmbedder()
    logger.warning("所有向量化实现都不可用，降级为哈希实现")
    _cached = fallback
    return fallback


def reset_embedder() -> None:
    """测试用：清掉缓存，重新探测。"""
    global _cached
    _cached = None


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """余弦相似度。两个向量都已 L2 归一化，点积即可。"""
    return sum(x * y for x, y in zip(a, b, strict=False))