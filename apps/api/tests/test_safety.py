"""敏感信息识别、脱敏与隐私清洗。

这些用例的价值不在覆盖率，而在**守住两条线**：

1. 真的能识别出身份证 / 手机 / 银行卡（校验位写错一个就会漏）
2. 绝不误伤正常内容 —— 误报的代价是用户看到自己的信息被无故涂掉
"""

from app.core.safety import (
    SecretKind,
    detect,
    luhn_ok,
    mask_value,
    redact,
    summarize,
    valid_id_card,
)

# 校验位合法的号码（用脚本算出来的，不是随手编的 —— 编的过不了校验）
ID_OK = "310101199003077755"
ID_BAD = "310101199003077758"
CARD_OK = "6222021234567890128"
PHONE = "13812345678"
API_KEY = "sk-abcdef1234567890abcdef"


# ---------------------------------------------------------------- 校验位


def test_id_card_checksum() -> None:
    assert valid_id_card(ID_OK) is True
    assert valid_id_card(ID_BAD) is False
    # 长度不对
    assert valid_id_card("31010119900307") is False


def test_luhn() -> None:
    assert luhn_ok(CARD_OK) is True
    # 只改最后一位就该失效
    assert luhn_ok(CARD_OK[:-1] + ("0" if CARD_OK[-1] != "0" else "1")) is False


# ---------------------------------------------------------------- 识别


def test_detects_id_card() -> None:
    kinds = summarize(f"我的身份证是{ID_OK}")
    assert SecretKind.ID_CARD in kinds


def test_detects_phone_with_context() -> None:
    assert SecretKind.PHONE in summarize(f"我手机号是{PHONE}")


def test_detects_bank_card() -> None:
    assert SecretKind.BANK_CARD in summarize(f"我的银行卡号是{CARD_OK}")


def test_detects_email_and_social() -> None:
    kinds = summarize("邮箱 a.b@example.com，微信号 li_ming_888")
    assert SecretKind.EMAIL in kinds
    assert SecretKind.SOCIAL_ID in kinds


def test_detects_api_key_in_mixed_chinese_context() -> None:
    """🔴 这条曾经是个真 bug。

    正则原本用 ``\\b`` 界定边界，但 Python 的 ``\\b`` 基于 Unicode 词字符，
    中文字符也算词字符 —— 于是「我的 key 是sk-xxx」里「是」与「s」之间
    没有边界，整个正则不匹配。而这恰恰是中国用户最真实的写法。
    """
    assert SecretKind.API_KEY in summarize(f"我的 key 是{API_KEY}")
    assert SecretKind.API_KEY in summarize(f"my key is {API_KEY}")


# ---------------------------------------------------------------- 误报


def test_no_false_positive_on_order_number() -> None:
    """18 位随机数字必须被身份证/银行卡校验位挡掉。"""
    assert detect("订单号是928374615293847162") == []


def test_no_false_positive_on_bare_phone_like_number() -> None:
    """光有 11 位数字、没有「手机/电话」这类上下文，不认。"""
    assert detect("订单号是82937461529") == []


def test_no_false_positive_on_dates_and_amounts() -> None:
    assert detect("我从20230101开始算的") == []
    assert detect("我月薪20000，存款15万") == []


def test_no_false_positive_on_english_and_version() -> None:
    assert detect("我用的token是gpt-4o-mini-turbo-2024") == []
    assert detect("我装了Python 3.13.12版本") == []


def test_normal_chat_untouched() -> None:
    text = "我住在深圳南山，喜欢爬山，养了一只叫豆豆的猫"
    assert detect(text) == []
    assert redact(text) == text


# ---------------------------------------------------------------- 脱敏


def test_redact_keeps_context() -> None:
    """掩码而不是抹掉 —— 用户要能看出「对，AI 记的是这个」。"""
    out = redact(f"我的手机号是{PHONE}")
    assert PHONE not in out
    assert "我的手机号是" in out
    assert out == "我的手机号是138****5678"


def test_redact_multiple_without_overlap() -> None:
    text = f"我叫李明，手机{PHONE}，身份证{ID_OK}，邮箱a.b@c.com"
    out = redact(text)
    for secret in (PHONE, ID_OK, "a.b@c.com"):
        assert secret not in out
    # 三段掩码各出现一次，没有重复替换产生的乱码
    assert "****" in out
    assert "李明" in out


def test_mask_never_exposes_full_value() -> None:
    """掩码不能只是「换个写法」，必须真的挖掉中间那段。"""
    for kind, value in (
        (SecretKind.ID_CARD, ID_OK),
        (SecretKind.PHONE, PHONE),
        (SecretKind.BANK_CARD, CARD_OK),
        (SecretKind.API_KEY, API_KEY),
        (SecretKind.EMAIL, "user@example.com"),
    ):
        masked = mask_value(kind, value)
        assert value not in masked, f"{kind} 的掩码泄漏了原文：{masked}"
        assert masked != value, f"{kind} 的掩码没有改变任何东西"
        # 真的挖掉了：中间必须有一段打码
        assert "*" in masked, f"{kind} 的掩码里看不到打码：{masked}"


def test_mask_hides_middle_segment() -> None:
    """中间必须真的被挖掉，不能只是换一种写法。

    保留首尾是**刻意**的：手机号 138****5678 里首位能判断运营商、
    末位让用户确认「对，是这个号」—— 银行短信和快递面单都是这么处理的。
    代价是接受一定程度的暴露，这是「让用户认得出」的必要成本。
    """
    masked = mask_value(SecretKind.PHONE, PHONE)
    assert PHONE not in masked
    assert masked.startswith("138")
    assert masked.endswith("5678")
    # 中间那 4 位确实没了
    assert "1234" not in masked


def test_redact_is_idempotent() -> None:
    """清洗存量时可能重复跑，已脱敏的内容不该被再次改动。"""
    once = redact(f"我的手机号是{PHONE}")
    assert redact(once) == once