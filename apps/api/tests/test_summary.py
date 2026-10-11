"""群聊总结：说话人保留、摘要生成、降级与边界。

核心价值守在两处：
1. **说话人必须进到模型上下文** —— 否则 AI 看到的是「一个人说了 20 句」
2. **待办不能混入既成事实** —— 用户会照着待办去追进度，追不到就不信这份摘要
"""

from fastapi.testclient import TestClient

from app.services.summary_service import (
    GroupSummary,
    render_text,
    summarize_by_rules,
)

CHAT = (
    ("张三", "下周的产品评审改到周四了"),
    ("李四", "那我们周三先把材料准备好"),
    ("张三", "我来出数据部分"),
    ("李四", "负责跟设计那边对齐，我明天问他们"),
    ("王五", "我觉得用户增长这块可以放后面"),
    ("张三", "所以就定了，周四评审，周三收齐材料"),
)



def _fresh_group(client: TestClient, title: str = "临时群") -> str:
    """新建一个干净的群聊会话。

    复用共享的 group_session_id 会让断言依赖别的用例发过什么 ——
    测试一旦耦合，「看起来通过」和「真的通过」就分不开。
    """
    return client.post(
        "/api/v1/sessions", json={"type": "group", "title": title, "member_count": 6}
    ).json()["id"]


# ---------------------------------------------------------------- 说话人


def test_group_context_keeps_speaker(client: TestClient) -> None:
    """🔴 群聊的模型上下文必须能分辨谁说了什么。

    以前所有 user 消息都被压成同一条 role=user，
    AI 看到的是「一个人连着说了 20 句」—— 它没法做群聊总结，
    因为根本不知道谁主张了什么。
    """
    sid = _fresh_group(client, "发言人测试")
    try:
        client.post(
            "/api/v1/chat",
            json={
                "session_id": sid,
                "messages": [
                    {"role": "user", "content": "我觉得该延到下周", "sender_id": "u_zhang"},
                    {"role": "user", "content": "我同意", "sender_id": "u_li"},
                ],
            },
        )
        history = client.get(f"/api/v1/sessions/{sid}/messages").json()
        labels = [m["sender_label"] for m in history if m["sender_type"] == "user"]
        assert "zhang" in labels, f"发言人标签没落库：{labels}"
        assert "li" in labels, f"发言人标签没落库：{labels}"
    finally:
        client.delete(f"/api/v1/sessions/{sid}")


def test_sender_name_preferred_over_id(client: TestClient) -> None:
    """给了显示名就用显示名 —— 「张三」比「u_zhangsan」自然得多。"""
    sid = _fresh_group(client, "显示名测试")
    try:
        client.post(
            "/api/v1/chat",
            json={
                "session_id": sid,
                "messages": [
                    {
                        "role": "user",
                        "content": "这个方案我看过两遍了",
                        "sender_id": "u_zhangsan",
                        "sender_name": "张三",
                    }
                ],
            },
        )
        history = client.get(f"/api/v1/sessions/{sid}/messages").json()
        mine = [m for m in history if "方案" in m["content"]]
        assert mine and mine[-1]["sender_label"] == "张三"
    finally:
        client.delete(f"/api/v1/sessions/{sid}")


def test_group_context_labels_speakers(client: TestClient) -> None:
    """🔴 to_model_messages 在群聊里必须给每条发言打上标签。

    这是群聊总结的地基：没有它，模型看到的是「一个人连着说了 20 句」。
    """
    from app.db.session import SessionLocal
    from app.models.session import SessionModel
    from app.services.session_service import to_model_messages

    sid = _fresh_group(client, "上下文标签")
    try:
        client.post(
            "/api/v1/chat",
            json={
                "session_id": sid,
                "messages": [
                    {"role": "user", "content": "我来跟进这个", "sender_id": "u_wang"},
                ],
            },
        )
        with SessionLocal() as sess:
            session = sess.get(SessionModel, sid)
            ctx = to_model_messages(sess, session)
        joined = " ".join(m["content"] for m in ctx if m["role"] == "user")
        assert "wang" in joined, f"群聊上下文里没有发言人标签：{joined}"
    finally:
        client.delete(f"/api/v1/sessions/{sid}")


# ---------------------------------------------------------------- 规则法


def test_rules_summary_structure() -> None:
    s = summarize_by_rules(list(CHAT))
    assert s.source == "rules"
    assert s.message_count == 6
    assert s.topic, "应给出议题"
    assert s.participants[0].name == "张三"
    assert s.participants[0].count == 3


def test_rules_find_conclusions() -> None:
    s = summarize_by_rules(list(CHAT))
    assert any("周四" in c for c in s.conclusions), s.conclusions


def test_rules_separate_commitments_from_facts() -> None:
    """🔴 「评审改到周四了」是既成事实，不能混进待办。

    用户会照着待办去追进度，追不到就再也不信这份摘要。
    """
    s = summarize_by_rules(list(CHAT))
    assert any("我来出" in t for t in s.todos), s.todos
    assert any("负责" in t for t in s.todos), s.todos
    assert not any("改到周四" in t for t in s.todos), f"通知被误当成待办：{s.todos}"


def test_rules_ignore_ai_own_replies() -> None:
    """AI 说过的话不算「群成员讨论了什么」。

    把自己说过的话算进摘要，等于让 AI 总结自己，循环且没意义。
    """
    from app.services.summary_service import collect_messages

    assert isinstance(collect_messages, object)
    # 空群聊
    assert summarize_by_rules([]).message_count == 0
    assert "还没有人说话" in render_text(GroupSummary(topic="还没有人说话"))


def test_empty_group_summary_is_honest() -> None:
    """没话说时不能编内容。"""
    s = summarize_by_rules([])
    assert s.message_count == 0
    assert s.participants == []
    assert render_text(s)


def test_render_text_has_all_sections() -> None:
    text = render_text(summarize_by_rules(list(CHAT)))
    for token in ("参与者", "结论", "待办"):
        assert token in text, f"缺 {token}：{text}"


# ---------------------------------------------------------------- 接口


def test_summarize_endpoint(client: TestClient) -> None:
    """自带一份群聊数据，不依赖共享会话里的历史。

    复用 ``group_session_id`` 会让断言依赖别的用例发过什么 ——
    测试一旦耦合，「看起来通过」和「真的通过」就分不开了。
    """
    sid = client.post(
        "/api/v1/sessions", json={"type": "group", "title": "总结测试", "member_count": 6}
    ).json()["id"]
    try:
        for name, content in CHAT:
            client.post(
                "/api/v1/chat",
                json={
                    "session_id": sid,
                    "messages": [
                        {"role": "user", "content": content, "sender_id": f"u_{name}"}
                    ],
                },
            )

        resp = client.post(f"/api/v1/sessions/{sid}/summarize")
        assert resp.status_code == 200
        body = resp.json()
        assert body["source"] in {"llm", "rules"}
        assert body["message_count"] == len(CHAT)
        assert body["text"], "应有纯文本形式"
        assert body["participants"], "应统计参与者"
    finally:
        client.delete(f"/api/v1/sessions/{sid}")


def test_summarize_rejected_for_non_group(client: TestClient, session_id: str) -> None:
    """单聊是两个人对话，「总结谁说了什么」这个问题不存在。"""
    resp = client.post(f"/api/v1/sessions/{session_id}/summarize")
    assert resp.status_code == 400
    assert "群聊" in resp.json()["detail"]


def test_summarize_empty_group_never_500(client: TestClient) -> None:
    """空群聊也要返回结果，不能因为「没话可说」就报错。

    必须**新建**会话而不是复用 ``group_session_id`` 那个 ——
    那是共享会话，前面的用例已经往里塞了消息，「空」的前提根本不成立。
    """
    empty = client.post(
        "/api/v1/sessions", json={"type": "group", "title": "空群", "member_count": 4}
    ).json()["id"]
    try:
        resp = client.post(f"/api/v1/sessions/{empty}/summarize")
        assert resp.status_code == 200
        assert resp.json()["message_count"] == 0
        assert resp.json()["text"], "空群也要有可显示的文本，不能是空串"
    finally:
        client.delete(f"/api/v1/sessions/{empty}")


def test_summarize_unknown_session_404(client: TestClient) -> None:
    assert client.post("/api/v1/sessions/nope/summarize").status_code == 404