"""从对话中抽取候选记忆。

两条路线，自动降级：

* 配了模型 Key → 让 LLM 输出结构化 JSON（质量最好）
* 没配Key → 走**规则抽取**：中文自述句式匹配（零依赖，毫秒级）

规则法覆盖的是个人助手场景里最高频的几类信息：身份、职业、居住、
喜好、厌恶、宠物、家人、习惯。抽取不准的地方宁可不抽 —— 宁缺毋滥。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

# 记忆类型
TYPE_PROFILE = "profile"  # 身份/职业/居住
TYPE_PREFERENCE = "preference"  # 喜好/厌恶
TYPE_FACT = "fact"  # 其他稳定事实
TYPE_EVENT = "event"  # 近期事件

MEMORY_TYPES = (TYPE_PROFILE, TYPE_PREFERENCE, TYPE_FACT, TYPE_EVENT)

# ---------------------------------------------------------------- 规则法

#: (正则, 类型, 权重)。权重越高越像「值得长期记住的陈述」
PATTERNS: tuple[tuple[re.Pattern[str], str, float], ...] = (
    (re.compile(r"我(?:叫|的名字叫|的名字是)\s*[\w一-鿿]{1,12}"), TYPE_PROFILE, 0.95),
    (re.compile(r"我(?:今年)?\s*\d{1,2}\s*岁"), TYPE_PROFILE, 0.9),
    (re.compile(r"我(?:是一名|是|当)\s*[\w一-鿿]{2,20}"), TYPE_PROFILE, 0.85),
    (re.compile(r"我在[\w一-鿿]{2,20}(?:工作|上班|读书|上学|做)"), TYPE_PROFILE, 0.9),
    (re.compile(r"我(?:住在|住在|来自|老家在)\s*[\w一-鿿]{2,20}"), TYPE_PROFILE, 0.9),
    (re.compile(r"我(?:的生日(?:是|在)|生于)\s*[\w一-鿿]{1,16}"), TYPE_PROFILE, 0.85),
    (re.compile(r"我(?:喜欢|爱|钟意|偏爱)\s*.{1,24}"), TYPE_PREFERENCE, 0.8),
    (re.compile(r"我(?:讨厌|不喜欢|受不了|最怕)\s*.{1,24}"), TYPE_PREFERENCE, 0.85),
    (re.compile(r"我(?:不吃|戒了|素食)\s*.{1,16}"), TYPE_PREFERENCE, 0.75),
    (re.compile(r"我(?:养了|养着|有一只|养了一只)\s*.{1,20}"), TYPE_PROFILE, 0.85),
    (re.compile(r"我(?:有|带着)(?:一个|一个)?\s*[\w一-鿿]{1,6}(?:孩子|女儿|儿子)"), TYPE_PROFILE, 0.85),
    (re.compile(r"我(?:的)?(?:工作|职业|岗位)(?:是|为)\s*.{1,16}"), TYPE_PROFILE, 0.85),
    (re.compile(r"我(?:每天|经常|习惯)(?:都)?\s*.{1,20}"), TYPE_PREFERENCE, 0.6),
    (re.compile(r"我(?:打算|计划|准备)\s*.{1,24}"), TYPE_EVENT, 0.7),
    (re.compile(r"我(?:下周|明天|最近|这周)\s*.{1,24}"), TYPE_EVENT, 0.65),
)

_SENT_SPLIT = re.compile(r"[。！？!?；;\n]+")
#: 这些句子基本没有记忆价值，直接丢掉
_NOISE = re.compile(r"^(?:你好|您好|哈+|嘿+|嗯+|哦+|谢谢|好的|在的|是的|不是|什么|为什么|怎么|吗|呢)[。！？!?]*$")


@dataclass(slots=True)
class Candidate:
    content: str
    type: str
    weight: float


def extract_by_rules(text: str, *, min_weight: float = 0.6) -> list[Candidate]:
    """规则抽取。同一段文本里同类型只保留权重最高的一条。"""
    if not text.strip():
        return []

    best: dict[str, Candidate] = {}
    for raw in _SENT_SPLIT.split(text):
        sentence = raw.strip()
        if not sentence or len(sentence) > 120 or _NOISE.match(sentence):
            continue
        if "我" not in sentence:
            continue
        for pattern, kind, weight in PATTERNS:
            if not pattern.search(sentence):
                continue
            # 句子过长时截到匹配处附近，避免把整段闲聊都存进去
            content = sentence if len(sentence) <= 60 else sentence[:60]
            current = best.get(kind)
            if current is None or weight > current.weight:
                best[kind] = Candidate(content=content, type=kind, weight=weight)
            break

    return sorted(
        (c for c in best.values() if c.weight >= min_weight),
        key=lambda c: c.weight,
        reverse=True,
    )


# ---------------------------------------------------------------- LLM 法

_LLM_PROMPT = """从下面的对话中，抽取关于「用户本人」的长期有效信息。

要求：
1. 只抽取稳定事实（身份、职业、居住地、喜好、厌恶、家人、宠物、长期习惯）
2. 不要抽取：情绪状态、寒暄、临时任务、你对他说的话
3. 每条独立成句，不超过 30 字
4. 没有值得记的就返回空数组

只输出 JSON 数组，元素形如 {{"content": "...", "type": "profile|preference|fact|event"}}

对话内容：
{text}
"""


def _has_model_key() -> bool:
    return bool(
        settings.openai_api_key
        or settings.dashscope_api_key
        or settings.deepseek_api_key
        or settings.anthropic_api_key
        or settings.gemini_api_key
    )


async def extract_by_llm(text: str) -> list[Candidate]:
    """让模型抽。失败一律返回空列表，由调用方回退到规则法。"""
    try:
        from litellm import acompletion

        from app.services.chat_service import normalize_model

        resp = await acompletion(
            model=normalize_model(None),
            messages=[{"role": "user", "content": _LLM_PROMPT.format(text=text)}],
            temperature=0.1,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content or ""
        match = re.search(r"\[.*]", raw, re.DOTALL)
        items = json.loads(match.group(0) if match else "[]")
    except Exception as exc:
        logger.warning("LLM 抽取失败，回退规则法：%s", exc)
        return []

    out: list[Candidate] = []
    for item in items if isinstance(items, list) else []:
        content = str(item.get("content", "")).strip()
        kind = str(item.get("type", TYPE_FACT))
        if content and kind in MEMORY_TYPES:
            out.append(Candidate(content=content, type=kind, weight=0.9))
    return out


async def extract(text: str) -> list[Candidate]:
    """统一入口：有Key 走 LLM，否则走规则。"""
    if _has_model_key():
        candidates = await extract_by_llm(text)
        if candidates:
            return candidates
        return []
    return extract_by_rules(text)