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

    assert names[0] == "meta"
    assert names[1] == "emotion"
    assert names[-1] == "done"
    assert "token" in names
    assert names.index("emotion") < names.index("token")

    meta = events[0][1]
    assert meta["session_id"] == session_id
    assert meta["mocked"] is True
    assert "/" in meta["model"], "模型名应带 LiteLLM provider 前缀"

    emotion = events[1][1]
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