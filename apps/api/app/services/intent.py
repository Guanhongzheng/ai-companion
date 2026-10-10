"""会话意图：辅助动作与 @ 唤醒判定。

三种会话的行为必须真的不一样，否则「个性化对话中枢」就只是换了个列表项：

* ``ai``     AI 伴侣 —— 全量 Agent 能力，正常聊天
* ``direct`` 好友单聊 —— AI **不冒充真人**，只做辅助：润色 / 翻译 / 总结 / 建议回复
* ``group``  群聊 —— AI 只在被 @ 时才说话，不抢话、不刷屏

这里把判定逻辑单独拆出来，好测也好复用。
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------- 群聊 @ 唤醒

#: AI 在群里的名字
BOT_NAMES = ("AI", "小伴", "助理")

#: 触发词：显式 @ 、直接喊名字
#: 名字后面用前瞻要求是标点/空格/结尾，避免「小助手很重要」这种被误判
_MENTION_RE = re.compile(
    r"(?:@\s*(?:AI|ai|小伴|助理)"
    r"|\[@\s*(?:AI|ai|小伴|助理)[^\]]*\]"
    r"|(?:^|\s)(?:小伴|助理)(?=[,，:：。!！?？\s]|$))",
    re.IGNORECASE,
)


def is_ai_mentioned(text: str) -> bool:
    """群里这条消息是不是在对 AI 说话。

    除了显式 ``@AI``，还认直接喊名字（"小伴，帮我看看"），
    因为很多 IM 里 @ 会带上各种不可见的格式片段，纯字符串匹配不可靠。
    """
    return bool(_MENTION_RE.search(text or ""))


# ---------------------------------------------------------------- 辅助动作

ACTION_CHAT = "chat"
ACTION_POLISH = "polish"
ACTION_TRANSLATE = "translate"
ACTION_SUMMARIZE = "summarize"
ACTION_SUGGEST = "suggest"
ACTION_SKIPPED = "skipped"

ACTIONS = (
    ACTION_CHAT,
    ACTION_POLISH,
    ACTION_TRANSLATE,
    ACTION_SUMMARIZE,
    ACTION_SUGGEST,
    ACTION_SKIPPED,
)

ACTION_LABELS = {
    ACTION_POLISH: "润色",
    ACTION_TRANSLATE: "翻译",
    ACTION_SUMMARIZE: "总结",
    ACTION_SUGGEST: "建议回复",
}

#: 动作关键词。命中即判定，按顺序匹配，先匹配到的优先。
_ACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        ACTION_POLISH,
        re.compile(r"润色|改写|改一下|帮我改|优化一下|换个说法|通顺点|书面一点|更正式|更口语"),
    ),
    (
        ACTION_TRANSLATE,
        re.compile(r"翻译|译成|translate|英文怎么说|用英语|中文意思"),
    ),
    (
        ACTION_SUMMARIZE,
        re.compile(r"总结|概括|摘要|梳理|提炼|tl;?dr|重点是什么"),
    ),
    (
        ACTION_SUGGEST,
        re.compile(r"我该怎么回|怎么回复|怎么回|建议回|帮我回|替我想|该怎么说"),
    ),
)


def infer_action(text: str) -> str:
    """按关键词猜用户想要哪种辅助。猜不到就当正常聊天。

    注意：这里刻意只做「强信号」匹配 ——「帮我看看这段代码」里的「帮我」
    不足以判定成某个动作，宁可当成聊天，也不要误触发润色。
    """
    for action, pattern in _ACTION_PATTERNS:
        if pattern.search(text or ""):
            return action
    return ACTION_CHAT


def resolve_action(session_type: str, text: str, requested: str | None = None) -> str:
    """决定这一轮实际要做什么。

    * 群聊：没被 @ → ``skipped``（不产生回复）
    * 好友单聊：显式传了 action 就用它，否则猜
    * AI 伴侣：始终是正常聊天，不搞辅助那一套
    """
    if session_type == "group":
        return ACTION_CHAT if is_ai_mentioned(text) else ACTION_SKIPPED

    if session_type == "direct":
        if requested and requested in ACTIONS and requested != ACTION_CHAT:
            return requested
        return infer_action(text)

    return ACTION_CHAT


# ---------------------------------------------------------------- 提示词

SYSTEM_PROMPTS = {
    "ai": (
        "你是一个贴心的中文 AI 伴侣。说话自然、口语化，像真人一样有温度，"
        "不要客套话和多余的排版。用户情绪低落时先接住情绪再谈事。"
    ),
    "direct": (
        "你是一个中文写作助手。你在用户的私人聊天里帮忙，**不要冒充对方的朋友**。"
        "按用户要求做润色、翻译、总结或拟回复，只输出结果本身，"
        "不要加解释、不要加「好的」之类的开场白。给出可直接复制使用的内容。"
    ),
    "group": (
        "你参与一个群聊。被 @ 时才回答，回答简短自然，"
        "不要抢话，不要刷屏，不要一次说太多。"
    ),
}

#: 各动作对应的指令，拼到系统提示后面
ACTION_INSTRUCTIONS = {
    ACTION_POLISH: (
        "任务：把用户最后一条消息润色成更通顺、得体的版本。"
        "保持原意和语气，只输出润色后的文字，用引号包起来。"
    ),
    ACTION_TRANSLATE: (
        "任务：把用户最后一条消息翻译成英文（若是英文则译成中文）。"
        "只输出译文。"
    ),
    ACTION_SUMMARIZE: (
        "任务：总结用户提供的内容。用不超过 3 条要点列出关键信息，"
        "每条一行，用「- 」开头。"
    ),
    ACTION_SUGGEST: (
        "任务：用户不知道该怎么回复。给出 2 个不同风格的回复建议"
        "（比如一个友好、一个直接），每个建议单独一行并用「1. 」「2. 」标注，"
        "不要解释为什么。"
    ),
}


def system_prompt_for(session_type: str, action: str) -> str:
    """拼出这一轮真正要用的系统提示。"""
    base = SYSTEM_PROMPTS.get(session_type, SYSTEM_PROMPTS["ai"])
    instruction = ACTION_INSTRUCTIONS.get(action)
    return f"{base}\n\n{instruction}" if instruction else base