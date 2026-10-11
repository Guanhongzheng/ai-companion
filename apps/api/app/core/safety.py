"""敏感信息识别与脱敏。

为什么需要它
------------
记忆是从对话里提炼的**长期**数据，而模型抽取的判断标准是「这是稳定事实」。
问题在于：手机号、身份证号恰恰就是最稳定的事实 —— 模型的判断没错，
但结果是一个 AI 伴侣把用户身份证存进了向量库，还会通过 SSE 的 memory 事件
直接渲染在聊天界面上。

所以在记忆写入前必须拦一道。

设计取舍
--------
1. **宁可漏，不可错杀。** 身份证和银行卡都带校验位，校验不过就不认；
   11 位数字只有「1 开头 + 手机号上下文词」才判为手机号，光一个 11 位数字
   更可能是订单号。误报的代价是用户看到自己的正常信息被涂掉，体验极差。
2. **掩码而不是删除。** 「我的手机号是138****5678」比整句消失更有用 ——
   用户能确认「对，是这个号」，AI 也知道这是个联系方式。
3. **原文永不落库。** 这是本模块存在的唯一理由。

这里的「脱敏」是**可逆的掩码**（保留首尾），不是加密。真正的保密靠
``crypto.py`` 的 Fernet 加密；两者解决的是不同的问题，不要混为一谈。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class SecretKind(StrEnum):
    """敏感信息类型。

    枚举值本身会出现在 API 响应里，**前端据此决定用哪种样式提示**。
    """

    ID_CARD = "id_card"
    PHONE = "phone"
    BANK_CARD = "bank_card"
    EMAIL = "email"
    #: 微信号 / QQ 号这类社交账号 —— 本身没有校验位，靠上下文词判定
    SOCIAL_ID = "social_id"
    #: 形如 sk-xxx 的 API Key
    API_KEY = "api_key"


#: 展示顺序：越危险的越靠前
KIND_LABELS: dict[SecretKind, str] = {
    SecretKind.ID_CARD: "身份证号",
    SecretKind.BANK_CARD: "银行卡号",
    SecretKind.PHONE: "手机号",
    SecretKind.EMAIL: "邮箱",
    SecretKind.SOCIAL_ID: "社交账号",
    SecretKind.API_KEY: "API Key",
}


@dataclass(frozen=True, slots=True)
class Secret:
    """一处敏感信息。``start``/``end`` 是原文中的位置，供精确替换。"""

    kind: SecretKind
    start: int
    end: int
    text: str


# ---------------------------------------------------------------- 校验位

#: 身份证前 17 位的加权因子（GB 11643-1999）
_ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_ID_CHECK_CHARS = "10X98765432"


def valid_id_card(value: str) -> bool:
    """校验 18 位身份证号的校验位。

    这是把误报压下去的关键：一串随机 18 位数字能通过校验的概率不到 1/11。
    """
    if len(value) != 18 or not value[:17].isdigit():
        return False
    if not (value[:17][:6].isdigit() and value[6:14].isdigit() and value[14:17].isdigit()):
        return False

    total = sum(int(ch) * w for ch, w in zip(value[:17], _ID_WEIGHTS, strict=True))
    return _ID_CHECK_CHARS[total % 11] == value[17].upper()


def luhn_ok(value: str) -> bool:
    """银行卡 Luhn 校验。同样是为了把误报压到极低。"""
    digits = [int(c) for c in value]
    checksum = 0
    # 从右往左，每隔一位翻倍
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


# ---------------------------------------------------------------- 正则

#: 18 位身份证（末位允许 X）或 15 位老身份证
_ID_RE = re.compile(r"(?<![0-9A-Za-z])(\d{17}[\dXx]|\d{15})(?![0-9A-Za-z])")
#: 银行卡：16~19 位，带 Luhn 校验
_BANK_RE = re.compile(r"(?<!\d)(\d{16,19})(?!\d)")
#: 手机号：1 开头 + 第二位 3-9，共 11 位
_PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
#: 邮箱。同样不用 ``\b``（理由见 ``_KEY_RE`` 的注释）
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9-])"
)
#: 常见 API Key 前缀
#:
#: ⚠️ 这里**不能用 ``\b``**。Python 的 ``\b`` 基于 Unicode 词字符判定，
#: 中文字符也算词字符，于是「我的key 是sk-xxx」里「是」与「s」之间没有边界，
#: 正则直接不匹配 —— 而这恰恰是中国用户最真实的写法。
#: 改用只考虑 ASCII 词字符的负向前后瞻。
_KEY_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:sk|pk|ghp|gho|xoxb|AKIA)[-_][A-Za-z0-9_-]{12,}(?![A-Za-z0-9_-])"
)

#: 社交账号的上下文词 —— 没有它们，数字串一律不认
_SOCIAL_CONTEXT = (
    "微信号", "微信", "vx", "v信", "wx", "qq", "QQ", "扣扣",
    "wechat", "WeChat", "公众号", "小红书", "抖音号", "快手",
)
_SOCIAL_RE = re.compile(
    r"(?:" + "|".join(re.escape(w) for w in _SOCIAL_CONTEXT) + r")\s*[:：是]?\s*"
    r"([A-Za-z0-9_\-]{5,24})"
)


def detect(text: str) -> list[Secret]:
    """找出文本里所有敏感片段，按位置排序、互不重叠。

    重叠时**先命中的优先**（按 :data:`KIND_LABELS` 的危险度排序），
    避免同一段字符被算两次、替换出乱码。
    """
    if not text:
        return []

    raw: list[Secret] = []

    # --- 带校验位的：先跑，命中就占住这段字符 ---
    reserved: list[tuple[int, int]] = []

    def _take(start: int, end: int) -> bool:
        """这段区间没被别人占走才返回 True。"""
        if any(s < end and start < e for s, e in reserved):
            return False
        reserved.append((start, end))
        return True

    for m in _ID_RE.finditer(text):
        value = m.group(1)
        if valid_id_card(value) and _take(m.start(1), m.end(1)):
            raw.append(Secret(SecretKind.ID_CARD, m.start(1), m.end(1), value))

    for m in _BANK_RE.finditer(text):
        value = m.group(1)
        if luhn_ok(value) and _take(m.start(1), m.end(1)):
            raw.append(Secret(SecretKind.BANK_CARD, m.start(1), m.end(1), value))

    for m in _KEY_RE.finditer(text):
        if _take(m.start(), m.end()):
            raw.append(Secret(SecretKind.API_KEY, m.start(), m.end(), m.group(0)))

    # --- 无校验位的：靠上下文词降低误报 ---
    for m in _PHONE_RE.finditer(text):
        # 前后 6 个字符里出现「手机/电话/联系」这类词才认。
        # 光凭「1 开头 11 位」就判定太激进 —— 订单号、用户 ID 也会中招。
        window = text[max(0, m.start() - 6) : m.end() + 6]
        has_context = any(w in window for w in ("手机", "电话", "联系", "号码", "phone", "tel"))
        if has_context and _take(m.start(1), m.end(1)):
            raw.append(Secret(SecretKind.PHONE, m.start(1), m.end(1), m.group(1)))

    for m in _SOCIAL_RE.finditer(text):
        value = m.group(1)
        if _take(m.start(1), m.end(1)):
            raw.append(Secret(SecretKind.SOCIAL_ID, m.start(1), m.end(1), value))

    for m in _EMAIL_RE.finditer(text):
        if _take(m.start(), m.end()):
            raw.append(Secret(SecretKind.EMAIL, m.start(), m.end(), m.group(0)))

    raw.sort(key=lambda s: s.start)
    return raw


def mask_value(kind: SecretKind, value: str) -> str:
    """单个敏感值的掩码形式。

    保留首尾是刻意的取舍：手机号 ``138****5678`` 里首位能判断运营商、
    末位让用户确认「对，是这个号」—— 银行短信和快递面单都是这么处理的。
    代价是接受一定程度的暴露，换取用户仍能认出这条记忆说的是自己的什么信息。
    完全抹掉会让用户困惑「我明明说过，AI 怎么突然想不起来了」。
    """
    if kind is SecretKind.EMAIL:
        # a***@example.com —— 保留域名，否则失去「哪个邮箱服务商」的信息
        name, _, domain = value.partition("@")
        head = name[0] if name else ""
        return f"{head}***@{domain}" if domain else "***"

    if kind in {SecretKind.SOCIAL_ID, SecretKind.API_KEY}:
        # 账号与密钥两头都不能露：开头会暴露平台/长度规则
        return f"{value[:2]}***{value[-2:]}" if len(value) > 6 else "***"

    # 身份证 / 手机 / 银行卡：保留前 3 后 4，中间打码
    if len(value) <= 7:
        return "***"
    return f"{value[:3]}****{value[-4:]}"


def redact(text: str) -> str:
    """把文本里的敏感信息替换成掩码。

    掩码而不是整段删除：「手机号138****5678」仍然是一条有意义的记忆
    （用户能看出「对，AI 记了这个」），而整段抹掉只会让人困惑
    「为什么我明明说过的事，AI 突然想不起来了」。
    """
    if not text:
        return text
    secrets = detect(text)
    if not secrets:
        return text

    out: list[str] = []
    cursor = 0
    for item in secrets:
        out.append(text[cursor : item.start])
        out.append(mask_value(item.kind, item.text))
        cursor = item.end
    out.append(text[cursor:])
    return "".join(out)


def summarize(text: str) -> list[SecretKind]:
    """只返回命中的类型（去重），用于统计与提示。"""
    seen: list[SecretKind] = []
    for item in detect(text):
        if item.kind not in seen:
            seen.append(item.kind)
    return seen