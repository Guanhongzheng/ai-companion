"""健康检查与对话接口的冒烟测试。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_chat_stub() -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"session_id": "s1", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "s1"
