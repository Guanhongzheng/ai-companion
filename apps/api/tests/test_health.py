"""健康检查与会话 CRUD。"""

from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_seed_sessions_created(client: TestClient) -> None:
    """首次启动应自动灌入 AI / 好友 / 群聊三类示例会话。"""
    resp = client.get("/api/v1/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) == 3
    assert {s["type"] for s in sessions} == {"ai", "direct", "group"}


def test_create_rename_delete_session(client: TestClient) -> None:
    created = client.post(
        "/api/v1/sessions", json={"type": "direct", "title": "临时会话", "member_count": 2}
    )
    assert created.status_code == 201
    sid = created.json()["id"]

    renamed = client.patch(f"/api/v1/sessions/{sid}", json={"title": "改过的名字"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "改过的名字"

    assert client.delete(f"/api/v1/sessions/{sid}").status_code == 204
    assert client.get(f"/api/v1/sessions/{sid}/messages").status_code == 404


def test_messages_of_unknown_session_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/sessions/does-not-exist/messages").status_code == 404