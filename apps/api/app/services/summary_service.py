"""群聊摘要。

群聊与单聊最大的差别：**信息来自多个人，且没人负责整理**。
六个人各说各的，结论散落在几十条消息里 —— 这正是「AI 辅助真实社交」
最该出手的地方：不参与讨论，只负责把散落的信息收拢成一份可读的东西。

产出不是一段话，而是**结构化**的四块：

* ``topic`` 议题 —— 这段讨论在聊什么
* ``conclusions`` 结论 —— 已经达成一致的部分
* ``todos`` 待办 —— 谁答应做什么
* ``participants`` 参与者及其发言量

为什么结构化：群聊里真正有用的信息是「谁说了什么」和「接下来谁要做」，
一段流水账式的总结反而更难用。

两条路线自动降级：配了模型 Key 走 LLM，否则走**规则抽取**（零依赖）。
规则法拿不到语义，但「谁说了多少」「有哪些句子像结论/待办」是能统计出来的。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field

from sqlalchemy import desc, select
from sqlalchemy.orm import Session as OrmSession

from app.core.config import settings
from app.models.session import MessageModel
from app.services.session_service import speaker_label

logger = logging.getLogger(__name__)

#: 参与总结的最大消息数。再多模型也读不完，且真正有效的信息在最近的部分
MAX_MESSAGES = 60

#: 少于这么多条消息不值得总结 —— 三句话总结不出什么
MIN_MESSAGES = 3


@dataclass(slots=True)
class SpeakerStat:
    """一个发言人的统计。"""

    name: str
    count: int


@dataclass(slots=True)
class GroupSummary:
    """一份群聊摘要。"""

    topic: str = ""
    conclusions: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    participants: list[SpeakerStat] = field(default_factory=list)
    #: 覆盖了多少条消息
    message_count: int = 0
    #: 走的是模型还是规则
    source: str = "rules"

    def to_dict(self) -> dict[str, object]:
        return {
            "topic": self.topic,
            "conclusions": self.conclusions,
            "todos": self.todos,
            "participants": [asdict(p) for p in self.participants],
            "message_count": self.message_count,
            "source": self.source,
        }


# ---------------------------------------------------------------- 取材


def collect_messages(db: OrmSession, session_id: str) -> list[tuple[str, str]]:
    """取出要总结的消息，返回 ``[(发言人, 内容)]``，已剔除 AI 自己的回复。

    AI 说过的话不算「群成员讨论了什么」—— 把自己的回复算进摘要里，
    等于让 AI 总结自己说过的话，既循环又没意义。
    """
    rows = (
        db.execute(
            select(MessageModel)
            .where(MessageModel.session_id == session_id)
            .order_by(desc(MessageModel.created_at))
            .limit(MAX_MESSAGES)
        )
        .scalars()
        .all()
    )
    items: list[tuple[str, str]] = []
    for m in reversed(rows):
        if m.sender_type != "user":
            continue
        if not m.content or not m.content.strip():
            continue
        items.append((speaker_label(m), m.content.strip()))
    return items


# ---------------------------------------------------------------- 规则法

#: 长得像「结论」的句子
_CONCLUSION_HINTS = ("所以", "因此", "就这样", "定了", "结论", "那就", "达成", "确认")
#: 长得像「待办」的句子
_TODO_HINTS = (
    "我来", "我去", "负责", "跟进", "明天", "下周", "截止", "deadline", "安排", "发一下",
)
#: **承诺性**动作词。只有「我来做」才是待办，光有时间词不算 ——
#: 「下周评审改到周四了」是一条已发生的事实，不是谁答应要做的事。
_COMMIT_HINTS = ("我来", "我去", "负责", "跟进", "我来出", "我跟进")
#: 「改到/定在/是/已经」这类**陈述/通知**句式。
#: 它常与时间词同时出现（「评审改到周四」），但说的是既成事实而非承诺，
#: 混进待办会让整份摘要的可信度下降 —— 用户会拿它去追进度。
_ANNOUNCE_HINTS = ("改到", "改在", "定在", "定在", "安排在", "已经", "通知", "定了在", "延到", "提前")
_TRAILING = "。！？!?，,；;、 \t\n"


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[。！？!?\n]+", text)
    return [p.strip(_TRAILING) for p in parts if p.strip(_TRAILING)]


def _stat_participants(items: list[tuple[str, str]]) -> list[SpeakerStat]:
    counter: dict[str, int] = {}
    for name, _ in items:
        counter[name] = counter.get(name, 0) + 1
    ordered = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)
    return [SpeakerStat(name=name, count=count) for name, count in ordered]


def _keywords(items: list[tuple[str, str]]) -> list[str]:
    """统计出现最多的双字词，粗略当作议题线索。

    中文没有空格分词，这里不做正经分词 ——
    规则法的定位是「没有 Key 也能给出个像样的结构」，
    真要理解议题得靠模型。
    """
    stop = {
        "我们", "你们", "他们", "这个", "那个", "什么", "怎么", "这样", "那样",
        "现在", "已经", "还是", "可以", "不是", "就是", "但是", "所以", "然后",
        "一个", "没有", "知道", "觉得", "应该", "这些", "那些", "大家",
    }
    counter: dict[str, int] = {}
    for _, content in items:
        for sent in _sentences(content):
            for i in range(len(sent) - 1):
                gram = sent[i : i + 2]
                if gram in stop or not re.fullmatch(r"[一-鿿]{2}", gram):
                    continue
                counter[gram] = counter.get(gram, 0) + 1
    return [w for w, _ in sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:4]]


def summarize_by_rules(items: list[tuple[str, str]]) -> GroupSummary:
    """规则法总结。拿不到语义，但统计与句式识别是可靠的。"""
    summary = GroupSummary(source="rules", message_count=len(items))
    if not items:
        summary.topic = "还没有人说话"
        return summary

    summary.participants = _stat_participants(items)

    words = _keywords(items)
    if words:
        summary.topic = f"讨论集中在「{'、'.join(words)}」"

    for name, content in items:
        for sent in _sentences(content):
            if len(sent) < 4 or len(sent) > 60:
                continue
            if len(summary.conclusions) >= 5 and len(summary.todos) >= 5:
                break
            # 结论优先：有「所以/定了/就这么定」这类收敛词的句子，
            # 说的是讨论结果而不是某个人要做的事
            if any(h in sent for h in _CONCLUSION_HINTS):
                if len(summary.conclusions) < 5:
                    summary.conclusions.append(f"{name}：{sent}")
            elif any(h in sent for h in _COMMIT_HINTS):
                # 「我来做 / 我负责」才是真正的待办承诺
                if len(summary.todos) < 5:
                    summary.todos.append(f"{name}：{sent}")
            elif (
                any(h in sent for h in _TODO_HINTS)
                and len(summary.todos) < 5
                # 「改到周四」「已经定在…」这类是通知不是承诺，别混进待办 ——
                # 用户会照着待办去追进度，追不到就再也不信这份摘要了。
                and not any(h in sent for h in _ANNOUNCE_HINTS)
            ):
                # 兜底：只有时间词/安排类词，弱信号，排在最后
                summary.todos.append(f"{name}：{sent}")

    # 一条都没捞到时别留空数组，界面上「有 0 条结论」比「没识别出来」更糟
    if not summary.conclusions:
        top = summary.participants[0].name if summary.participants else ""
        summary.conclusions = [f"共 {len(items)} 条发言，" + (f"其中 {top} 说得最多。" if top else "")]
    return summary


# ---------------------------------------------------------------- LLM 法

_LLM_PROMPT = """下面是群聊里的聊天记录，请总结成结构化的中文摘要。

要求：
1. **topic**：这段讨论的核心议题，一句话
2. **conclusions**：已经达成一致或明确表达的结论，最多 5 条
3. **todos**：有人承诺要做的事，最多 5 条，格式「名字：事情」
4. 只总结人类成员说过的话，**不要把 AI 的回复算进讨论内容**
5. 没有结论或待办就留空数组，不要编造
6. 用中文，语气中性，不要用「大家一致认为」这种你没依据的说法

只输出 JSON，形如：
{{"topic": "...", "conclusions": ["..."], "todos": ["..."]}}

聊天记录：
{transcript}
"""


def _has_model_key() -> bool:
    return bool(
        settings.openai_api_key
        or settings.dashscope_api_key
        or settings.deepseek_api_key
        or settings.anthropic_api_key
        or settings.gemini_api_key
    )


def _transcript(items: list[tuple[str, str]]) -> str:
    return "\n".join(f"{name}：{content}" for name, content in items)


async def summarize_by_llm(items: list[tuple[str, str]]) -> GroupSummary | None:
    """让模型总结。失败返回 None，由调用方回退规则法。"""
    try:
        from litellm import acompletion

        from app.services.chat_service import normalize_model

        resp = await acompletion(
            model=normalize_model(None),
            messages=[{"role": "user", "content": _LLM_PROMPT.format(transcript=_transcript(items))}],
            temperature=0.2,
            max_tokens=800,
        )
        raw = resp.choices[0].message.content or ""
        match = re.search(r"\{.*}", raw, re.DOTALL)
        data = json.loads(match.group(0) if match else "{}")
    except Exception as exc:
        logger.warning("群聊总结的模型调用失败，回退规则法：%s", exc)
        return None

    if not isinstance(data, dict):
        return None

    def _str_list(key: str) -> list[str]:
        value = data.get(key)
        if not isinstance(value, list):
            return []
        return [str(v).strip() for v in value if str(v).strip()]

    return GroupSummary(
        topic=str(data.get("topic", "")).strip(),
        conclusions=_str_list("conclusions"),
        todos=_str_list("todos"),
        participants=_stat_participants(items),
        message_count=len(items),
        source="llm",
    )


# ---------------------------------------------------------------- 入口


async def summarize(db: OrmSession, session_id: str) -> GroupSummary:
    """给一个群聊会话生成摘要。

    无论模型成不成功都**一定有结果** —— 演示现场断网、Key 填错、
    余额不足都不该让这个功能直接消失，退回规则版即可。
    """
    items = collect_messages(db, session_id)

    if _has_model_key() and len(items) >= MIN_MESSAGES:
        result = await summarize_by_llm(items)
        if result is not None:
            return result

    return summarize_by_rules(items)


def render_text(summary: GroupSummary) -> str:
    """摘要的纯文本形式。存进会话历史、或直接发到群里时用。"""
    lines: list[str] = []
    if summary.topic:
        lines.append(f"【{summary.topic}】")

    people = "、".join(f"{p.name}({p.count})" for p in summary.participants[:5])
    if people:
        lines.append(f"参与者：{people}")

    if summary.conclusions:
        lines.append("结论：")
        lines.extend(f"· {c}" for c in summary.conclusions)

    if summary.todos:
        lines.append("待办：")
        lines.extend(f"· {t}" for t in summary.todos)

    return "\n".join(lines) if lines else "暂时没什么可总结的"