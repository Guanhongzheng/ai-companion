"""记忆召回与重排。

流程：**向量召回 Top-K → 混合打分重排 → 取 Top-N 注入对话**

重排策略分两档：

* 装了 ``requirements-ml.txt``（bge-reranker 一起装上了）→ 用 CrossEncoder 重排
* 没装 → 退化成「向量分 + 字符 bigram 重叠度」的混合分

第二档不是摆设：当向量化退化成哈希实现时，召回质量本就有限，
叠一层词面重叠度能明显改善排序 —— 例如问「我住在哪里」时，
向量分可能把三条都压得很平，但「住」这个字的命中是决定性的。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.core.config import settings
from app.memory.embedding import get_embedder
from app.memory.store import get_store

logger = logging.getLogger(__name__)

_OVERLAP_RE = re.compile(r"[^\w一-鿿]+")
_STOP = frozenset("的了吗呢啊吧呀哦嗯我你他她它们这那在是")

#: 混合打分权重：向量分 vs 词面重叠度
_VECTOR_WEIGHT = 0.65


@dataclass(slots=True)
class RetrievedMemory:
    id: str
    content: str
    score: float
    vector_score: float
    lexical_score: float
    reranker: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "content": self.content,
            "score": round(self.score, 4),
            "vector_score": round(self.vector_score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "reranker": self.reranker,
        }


def _grams(text: str) -> set[str]:
    cleaned = _OVERLAP_RE.sub(" ", text.lower()).strip()
    out: set[str] = set()
    for token in cleaned.split():
        chars = list(token)
        out.update(c for c in chars if c not in _STOP)
        out.update(chars[i] + chars[i + 1] for i in range(len(chars) - 1))
    return out


def lexical_overlap(query: str, document: str) -> float:
    """字符 bigram 的 Jaccard 相似度，取值 0~1。"""
    q, d = _grams(query), _grams(document)
    if not q or not d:
        return 0.0
    intersection = len(q & d)
    union = len(q | d)
    return intersection / union if union else 0.0


_cross_encoder = None
_cross_encoder_failed = False


def _get_cross_encoder():
    """懒加载 bge-reranker；没装或加载失败都返回 None。"""
    global _cross_encoder, _cross_encoder_failed
    if _cross_encoder is not None or _cross_encoder_failed:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder

        _cross_encoder = CrossEncoder(settings.default_rerank_model)
    except Exception as exc:
        logger.info("bge-reranker 不可用（%s），改用混合打分", exc)
        _cross_encoder_failed = True
        _cross_encoder = None
    return _cross_encoder


async def retrieve(
    query: str,
    *,
    recall_k: int | None = None,
    top_n: int | None = None,
) -> list[RetrievedMemory]:
    """召回 + 重排。

    >>> len(await retrieve("我住在哪里")) <= settings.memory_top_n
    True
    """
    text = query.strip()
    if not text:
        return []

    recall_k = recall_k or settings.memory_recall_k
    top_n = top_n if top_n is not None else settings.memory_top_n

    embedder = get_embedder()
    query_vec = await embedder.embed_query(text)
    candidates = get_store().query(query_vec, recall_k)
    if not candidates:
        return []

    lexical = [lexical_overlap(text, doc) for _mid, _score, doc in candidates]
    vector_scores = [max(0.0, score) for _mid, score, _doc in candidates]

    encoder = _get_cross_encoder()
    if encoder is not None:
        try:
            rerank_scores = [
                float(v) for v in encoder.predict([(text, doc) for _m, _s, doc in candidates])
            ]
            reranker = "bge-reranker"
            final = rerank_scores
        except Exception as exc:
            logger.warning("重排失败（%s），回退混合打分", exc)
            encoder = None
    if encoder is None:
        final = [
            _VECTOR_WEIGHT * v + (1 - _VECTOR_WEIGHT) * lex
            for v, lex in zip(vector_scores, lexical, strict=False)
        ]
        reranker = "hybrid"

    scored = [
        RetrievedMemory(
            id=mid,
            content=doc,
            score=score,
            vector_score=vec,
            lexical_score=lex,
            reranker=reranker,
        )
        for (mid, _s, doc), vec, lex, score in zip(
            candidates, vector_scores, lexical, final, strict=False
        )
    ]

    # 相似度过低的直接丢掉，避免把无关记忆塞进 prompt
    scored = [s for s in scored if s.score >= 0.08]
    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[:top_n]


def format_for_prompt(memories: list[RetrievedMemory]) -> str:
    """把召回结果拼成注入 prompt 的一段文本。"""
    if not memories:
        return ""
    lines = [f"{i}. {m.content}" for i, m in enumerate(memories, start=1)]
    return "以下是关于用户的已知信息，可自然地利用它们，不要生硬罗列：\n" + "\n".join(lines)