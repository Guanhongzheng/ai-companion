"""把各家模型厂商五花八门的报错翻译成用户能看懂的话。

模型调用失败时，原始异常往往包含一堆 provider 特定的堆栈，甚至可能带上
Key 的片段。**对外一律只给中文短句，不给原文。**
"""

from __future__ import annotations

#: 命中即返回的规则，按优先级从上到下
_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("401", "unauthorized", "authentication", "invalid api key", "invalid_api_key"),
     "API Key 无效或已过期，请检查是否复制完整、是否已吊销"),
    (("403", "forbidden", "permission denied", "access denied"),
     "API Key 有效，但没有该模型的权限，可能需要开通服务或换模型"),
    (("404", "not found", "does not exist", "model_not_found"),
     "模型不存在，请从下拉列表里选一个，或检查拼写"),
    (("insufficient balance", "insufficient", "quota", "arrearage", "余额"),
     "余额不足或额度已用完，请到控制台充值"),
    (("429", "rate limit", "too many requests", "rate_limit"),
     "触发限流，等一会儿再试"),
    (("timeout", "timed out"), "连接超时，可能是网络问题，或需要为后端配置代理"),
    (("connection", "network", "dns", "econnrefused", "getaddrinfo"),
     "连不上模型服务商，可能是网络问题，或需要为后端配置代理"),
    (("ssl", "certificate"), "SSL 证书校验失败，如果你开着代理，试试关掉它"),
)


def friendly_model_error(exc: BaseException) -> str:
    """返回一个可以直接展示给用户的中文短句。"""
    text = str(exc)
    lowered = text.lower()

    for needles, message in _RULES:
        if any(n in lowered or n in text for n in needles):
            return message

    # 兜底：截断原文，避免把整段堆栈塞给界面
    return f"模型调用失败：{text[:150]}"