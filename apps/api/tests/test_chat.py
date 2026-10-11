"""对话接口：非流式、SSE 事件序列、情绪识别、消息落库。"""

import json

from fastapi.testclient import TestClient

from app.core.emotion import detect


def parse_sse(raw: str) -> list[tuple[str, dict]]:
    """把 SSE 文本流解析成 [(event, data), ...]。

    SSE 规范用 \\r\\n 分隔事件块，先统一成 \\n 再切。
    """
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    events: list[tuple[str, dict]] = []
    name: str | None = None
    for block in normalized.strip().split("\n\n"):
        lines = block.strip().splitlines()
        if not lines:
            continue
        data_lines: list[str] = []
        for line in lines:
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        if name and data_lines:
            events.append((name, json.loads("".join(data_lines))))
    return events


def test_emotion_detector() -> None:
    assert detect("测试通过啦，太好了！").tag == "joy"
    assert detect("今天太累了好想躺着").tag == "tired"
    assert detect("我有点焦虑，压力大到睡不着").tag == "anxious"
    assert detect("随便看看文档").tag == "neutral"
    assert detect("").tag == "neutral"


def test_chat_non_stream_persists_messages(client: TestClient, session_id: str) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "messages": [{"role": "user", "content": "你好呀"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert body["reply"]
    # 无 Key 时必须走降级路径
    assert body["mocked"] is True

    history = client.get(f"/api/v1/sessions/{session_id}/messages").json()
    assert [m["sender_type"] for m in history[-2:]] == ["user", "ai"]
    assert history[-1]["emotion"] == body["emotion"]


def test_chat_stream_event_order(client: TestClient, session_id: str) -> None:
    resp = client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "messages": [{"role": "user", "content": "今天好累啊"}]},
    )
    assert resp.status_code == 200

    events = parse_sse(resp.text)
    names = [name for name, _ in events]

    # 事件顺序：意图判定 → 情绪 → 增量文本 → 结束
    assert names[0] == "meta"
    assert names[1] == "action"
    assert names[2] == "emotion"
    assert names[-1] == "done"
    assert "token" in names
    assert names.index("action") < names.index("emotion") < names.index("token")

    meta = events[0][1]
    assert meta["session_id"] == session_id
    assert meta["mocked"] is True
    assert "/" in meta["model"], "模型名应带 LiteLLM provider 前缀"

    action = events[1][1]
    assert action["action"] == "chat"
    assert action["waiting_for_mention"] is False

    emotion = next(d for n, d in events if n == "emotion")
    assert emotion["tag"] == "tired"
    assert 0 < emotion["confidence"] <= 1

    reply = "".join(d["text"] for n, d in events if n == "token")
    assert reply, "token 事件应拼出非空回复"
    assert events[-1][1]["finish_reason"] == "stop"


def test_chat_unknown_session_is_404(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"session_id": "nope", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 404


def test_normalize_model_adds_provider_prefix() -> None:
    from app.services.chat_service import normalize_model

    assert normalize_model("deepseek-chat") == "deepseek/deepseek-chat"
    assert normalize_model("qwen-plus") == "dashscope/qwen-plus"
    assert normalize_model("gpt-4o") == "openai/gpt-4o"
    assert normalize_model("openai/gpt-4o") == "openai/gpt-4o"
    assert normalize_model("claude-3-5-sonnet") == "anthropic/claude-3-5-sonnet"

# ---------------------------------------------------------------- 记忆可见性


def test_stream_emits_learned_event(client: TestClient, session_id: str, clean_memory_db: None) -> None:
    """🔴 后台抽取到的记忆必须发成事件，否则等于没发生。

    抽取是异步的、结果在 SSE 流末尾才产生，但用户必须看得见「我刚记住了什么」。
    少了这个事件，AI 悄悄学会了东西而界面毫无变化，
    抽取失败也同样静悄悄 —— 这正是「静默失效」。
    """
    resp = client.post(
        "/api/v1/chat/stream",
        json={
            "session_id": session_id,
            "messages": [{"role": "user", "content": "我是一名海洋生物学家，常年在厦门"}],
        },
    )
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    names = [name for name, _ in events]

    assert "learned" in names, f"应发出 learned 事件，实际事件：{names}"
    # learned 必须在 done 之前 —— 流一旦结束就推不出去了
    assert names.index("learned") < names.index("done")

    payload = next(d for n, d in events if n == "learned")
    assert payload["attempted"] is True
    assert payload["items"], "learned 事件里应该有内容"
    assert any("海洋生物学家" in i["content"] for i in payload["items"])


def test_learned_event_never_leaks_secrets(client: TestClient, session_id: str, clean_memory_db: None) -> None:
    """🔴 「记住了」会把记忆内容直接渲染在界面上，脱敏漏了就是当众曝光。"""
    resp = client.post(
        "/api/v1/chat/stream",
        json={
            "session_id": session_id,
            "messages": [
                {"role": "user", "content": "我在北京做建筑设计。我的手机号是13812345678"}
            ],
        },
    )
    events = parse_sse(resp.text)
    names = [name for name, _ in events]
    assert "learned" in names, f"应发出 learned 事件，实际：{names}"

    payload = next(d for n, d in events if n == "learned")
    joined = " ".join(item["content"] for item in payload["items"])
    assert "13812345678" not in joined, f"learned 事件里泄漏了完整手机号：{joined}"
    # 整条响应都不能出现原文 —— 这条比只看 learned 更严格，
    # 因为「记住了」的载荷一旦变了字段名，只看 joined 就漏了
    assert "13812345678" not in resp.text, "SSE 响应里不能出现完整手机号"


def test_no_learned_event_for_small_talk(client: TestClient, session_id: str) -> None:
    """寒暄不该触发抽取，也就不该出现空的「记住了」提示。"""
    resp = client.post(
        "/api/v1/chat/stream",
        json={"session_id": session_id, "messages": [{"role": "user", "content": "嗯"}]},
    )
    names = [name for name, _ in parse_sse(resp.text)]
    assert "learned" not in names
