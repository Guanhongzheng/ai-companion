"""会话差异化：AI 伴侣 / 好友单聊 / 群聊的行为必须真的不一样。"""

from fastapi.testclient import TestClient

from app.services.intent import (
    ACTION_CHAT,
    ACTION_POLISH,
    ACTION_SKIPPED,
    ACTION_SUGGEST,
    ACTION_SUMMARIZE,
    ACTION_TRANSLATE,
    infer_action,
    is_ai_mentioned,
    resolve_action,
    system_prompt_for,
)


def parse_events(raw: str) -> list[tuple[str, dict]]:
    import json

    events: list[tuple[str, dict]] = []
    name: str | None = None
    for block in raw.replace("\r\n", "\n").strip().split("\n\n"):
        lines = block.strip().splitlines()
        if not lines:
            continue
        data: list[str] = []
        for line in lines:
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data.append(line.split(":", 1)[1].strip())
        if name and data:
            events.append((name, json.loads("".join(data))))
    return events


# ---------------------------------------------------------------- @ 唤醒


def test_mention_detection() -> None:
    positives = ["@AI 帮我看看", "@小伴 在吗", "小伴，帮我总结", "小伴 看看这个", "助理：这个方案可行", "[@AI] 怎么修"]
    negatives = ["今天天气不错", "发给@张三 看一下", "小助手很重要", "小伴随说很好笑", "大家好呀"]
    assert all(is_ai_mentioned(t) for t in positives)
    assert not any(is_ai_mentioned(t) for t in negatives)


# ---------------------------------------------------------------- 动作推断


def test_action_inference() -> None:
    assert infer_action("这段话帮我润色一下") == ACTION_POLISH
    assert infer_action("翻译成英文") == ACTION_TRANSLATE
    assert infer_action("帮我总结一下聊天记录") == ACTION_SUMMARIZE
    assert infer_action("这条我该怎么回") == ACTION_SUGGEST
    # 弱信号不应误触发
    assert infer_action("帮我看看这段代码") == ACTION_CHAT
    assert infer_action("你好啊") == ACTION_CHAT


def test_resolve_action_by_session_type() -> None:
    # 群聊：只有被 @ 才说话
    assert resolve_action("group", "大家随便聊聊") == ACTION_SKIPPED
    assert resolve_action("group", "@AI 在吗") == ACTION_CHAT
    # 好友：显式传的 action 优先于猜测
    assert resolve_action("direct", "随便说点啥", ACTION_POLISH) == ACTION_POLISH
    # AI 伴侣：永远正常聊天，不搞辅助那套
    assert resolve_action("ai", "帮我润色一下") == ACTION_CHAT


def test_system_prompt_carries_action() -> None:
    polish = system_prompt_for("direct", ACTION_POLISH)
    assert "润色" in polish
    # 好友单聊的提示必须明确禁止冒充真人
    assert "不要冒充" in polish
    assert "润色" not in system_prompt_for("ai", ACTION_CHAT)


# ---------------------------------------------------------------- 端到端


def test_group_stays_silent_without_mention(client: TestClient, group_session_id: str) -> None:
    """群聊里没被 @ 时：消息落库，但 AI 不产生任何回复。"""
    resp = client.post(
        "/api/v1/chat",
        json={"session_id": group_session_id, "messages": [{"role": "user", "content": "今天谁去吃饭"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["waiting_for_mention"] is True
    assert body["action"] == ACTION_SKIPPED
    assert body["reply"] == ""

    history = client.get(f"/api/v1/sessions/{group_session_id}/messages").json()
    senders = [m["sender_type"] for m in history]
    assert "ai" not in senders, "没被 @ 时不该有 AI 消息"
    assert "user" in senders, "用户消息仍然要落库"


def test_group_responds_when_mentioned(client: TestClient, group_session_id: str) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={
            "session_id": group_session_id,
            "messages": [{"role": "user", "content": "@AI 帮我看下这个方案"}],
        },
    )
    body = resp.json()
    assert body["waiting_for_mention"] is False
    assert body["reply"], "被 @ 时应该正常回复"


def test_direct_action_is_reported(client: TestClient, direct_session_id: str) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={
            "session_id": direct_session_id,
            "messages": [{"role": "user", "content": "帮我润色一下这段话"}],
            "action": "polish",
        },
    )
    body = resp.json()
    assert body["action"] == ACTION_POLISH
    assert body["waiting_for_mention"] is False


def test_ai_session_ignores_actions(client: TestClient, session_id: str) -> None:
    """AI 伴侣会话即使传了 action 也应按正常聊天处理。"""
    resp = client.post(
        "/api/v1/chat",
        json={
            "session_id": session_id,
            "messages": [{"role": "user", "content": "今天有点累"}],
            "action": "polish",
        },
    )
    assert resp.json()["action"] == ACTION_CHAT


def test_stream_emits_action_event(client: TestClient, group_session_id: str) -> None:
    resp = client.post(
        "/api/v1/chat/stream",
        json={
            "session_id": group_session_id,
            "messages": [{"role": "user", "content": "随便聊聊"}],
        },
    )
    events = parse_events(resp.text)
    names = [n for n, _ in events]
    assert names[0] == "meta"
    assert "action" in names
    assert names[-1] == "done"
    # 未被 @ 时不应该有 token
    assert "token" not in names
    assert events[-1][1]["finish_reason"] == "skipped"
    action = next(d for n, d in events if n == "action")
    assert action["waiting_for_mention"] is True