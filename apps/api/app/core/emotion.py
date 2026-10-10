"""情绪识别。

当前实现是**轻量中文关键词打分**：零依赖、毫秒级、无需任何模型 Key，
保证演示链路随时能跑。

后续要升级成情感分析模型时，只需替换 :func:`detect` 内部实现，
或实现同样的 `detect(text) -> EmotionResult` 接口在 :data:`PROVIDER` 里注册，
上层（chat_service / SSE 协议）完全不用改。

标签集合必须与 packages/shared 的 EmotionTag 保持一致：
joy / calm / neutral / sad / anxious / angry / excited / tired
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

NEUTRAL = "neutral"

#: 情绪 -> 关键词。顺序无关，按出现次数累加。
KEYWORDS: dict[str, tuple[str, ...]] = {
    "joy": (
        "开心", "高兴", "快乐", "哈哈", "嘿嘿", "太好了", "不错", "喜欢", "满意",
        "舒服", "顺利", "搞定", "完成", "通过", "治愈", "开心死", "棒",
    ),
    "calm": (
        "平静", "放松", "安静", "踏实", "安心", "还行", "挺好", "稳了", "慢慢来",
        "不急", "放松点",
    ),
    "sad": (
        "难过", "伤心", "想哭", "哭了", "失落", "遗憾", "委屈", "孤单", "孤独",
        "难受", "低落", "emo", "郁闷", "想念",
    ),
    "anxious": (
        "焦虑", "紧张", "慌", "害怕", "担心", "焦虑症", "忐忑", "不安", "压力好大",
        "睡不着", "紧张得",
    ),
    "angry": (
        "生气", "愤怒", "火大", "气死", "恼火", "烦死", "讨厌", "离谱", "凭什么",
        "忍不了", "炸了", "气炸",
    ),
    "excited": (
        "激动", "兴奋", "好期待", "迫不及待", "太期待了", "冲鸭", "终于等到",
        "期待", "振奋",
    ),
    "tired": (
        "累", "疲惫", "好困", "困死", "没精神", "熬夜", "加班", "撑不住", "不想动",
        "起不来", "浑身无力",
    ),
}

#: 程度副词，命中时整体加权，让情绪强度更贴近真实语气
INTENSIFIERS = ("非常", "特别", "超级", "极其", "太", "真的", "好", "巨", "贼")

_WORD_RE = re.compile(r"[^\w一-鿿]+")


@dataclass(slots=True)
class EmotionResult:
    """情绪识别结果。"""

    tag: str
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)


def _boost(text: str) -> float:
    """根据程度副词给整体分数加权。"""
    level = 1.0
    for word in INTENSIFIERS:
        if word in text:
            level += 0.15
    return min(level, 1.9)


def detect(text: str) -> EmotionResult:
    """识别文本情绪。

    >>> detect("今天太累了好想躺着").tag
    'tired'
    >>> detect("测试通过啦，太好了！").tag
    'joy'
    >>> detect("随便看看文档").tag
    'neutral'
    """
    if not text or not text.strip():
        return EmotionResult(tag=NEUTRAL, confidence=0.3)

    scores: dict[str, float] = {}
    boost = _boost(text)

    for tag, words in KEYWORDS.items():
        hits = sum(text.count(word) for word in words)
        if hits:
            scores[tag] = hits * boost

    if not scores:
        return EmotionResult(tag=NEUTRAL, confidence=0.35, scores={})

    best_tag = max(scores, key=lambda k: scores[k])
    best_score = scores[best_tag]
    total = sum(scores.values())

    # 领先幅度越大越自信；绝对分越高也越自信
    margin = best_score / total
    confidence = min(0.95, 0.5 + best_score * 0.1 + (margin - 1 / len(scores)) * 0.3)

    return EmotionResult(tag=best_tag, confidence=round(confidence, 2), scores=scores)


#: 情绪识别提供方。M2 接入情感分析模型时在这里换实现。
PROVIDER: Callable[[str], EmotionResult] = detect