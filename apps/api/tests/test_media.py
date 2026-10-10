"""多媒体：上传校验、路径安全、附件持久化。"""

import io

from fastapi.testclient import TestClient

# 1x1 PNG
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)

# 文件头故意用错类型，测白名单是否拦住
FAKE = b"<?php echo 'evil'; ?>"


def _upload(client: TestClient, path: str, data: bytes, mime: str):
    return client.post(path, files={"file": ("probe", io.BytesIO(data), mime)})


# ---------------------------------------------------------------- 上传


def test_upload_image(client: TestClient) -> None:
    resp = _upload(client, "/api/v1/media/image", PNG, "image/png")
    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "image"
    assert body["url"].startswith("/api/v1/media/")
    assert body["size"] == len(PNG)
    # 服务端生成文件名，不该保留用户提交的原始名
    assert "probe" not in body["url"]


def test_upload_audio_accepts_codec_params(client: TestClient) -> None:
    """Chrome 录音的 mime 带 codecs 参数，必须能识别。"""
    resp = _upload(client, "/api/v1/media/audio", b"fake-webm", "audio/webm;codecs=opus")
    assert resp.status_code == 200
    assert resp.json()["mime"] == "audio/webm"


def test_reject_unknown_type(client: TestClient) -> None:
    """白名单之外的类型一律拒绝，扩展名不能由客户端决定。"""
    resp = _upload(client, "/api/v1/media/image", FAKE, "application/x-php")
    assert resp.status_code == 400
    assert "不支持" in resp.json()["detail"]


def test_disk_extension_comes_from_whitelist(client: TestClient) -> None:
    """把脚本伪装成 image/png 上传，落到磁盘仍是 .png，永不按脚本执行。

    这里验证的是**扩展名来自白名单而非用户文件名** —— 这是上传接口
    最重要的安全属性之一。
    """
    resp = _upload(client, "/api/v1/media/image", FAKE, "image/png")
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.endswith(".png")
    assert ".php" not in url
    # 原始文件名只作为展示信息保留，不进 URL
    assert resp.json()["name"] == "probe"

    # 取回来时 Content-Type 由磁盘上的扩展名决定
    fetched = client.get(url)
    assert fetched.status_code == 200
    assert fetched.headers["content-type"].startswith("image/")


def test_reject_empty_file(client: TestClient) -> None:
    resp = _upload(client, "/api/v1/media/image", b"", "image/png")
    assert resp.status_code == 400


def test_reject_oversize_image(client: TestClient, monkeypatch: object) -> None:
    from app.services import media_service

    monkeypatch.setattr(media_service, "max_image_bytes", lambda: 1024)  # type: ignore[attr-defined]
    resp = _upload(client, "/api/v1/media/image", PNG + b"x" * 4096, "image/png")
    assert resp.status_code == 400
    assert "太大" in resp.json()["detail"]


# ---------------------------------------------------------------- 读取安全


def test_read_uploaded_file(client: TestClient) -> None:
    url = _upload(client, "/api/v1/media/image", PNG, "image/png").json()["url"]
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.content == PNG


def test_path_traversal_rejected(client: TestClient) -> None:
    """目录穿越必须挡住 —— 这个接口等于任意文件读取。"""
    for evil in ["..%2F..%2F.env", "..", "%2e%2e%2fconfig.py"]:
        assert client.get(f"/api/v1/media/{evil}").status_code == 404


def test_resolve_media_path_rejects_outside() -> None:
    from app.services.media_service import resolve_media_path

    assert resolve_media_path("..\\..\\.env") is None
    assert resolve_media_path("不存在的文件.png") is None


# ---------------------------------------------------------------- 附件持久化


def test_message_with_attachment_roundtrip(client: TestClient, session_id: str) -> None:
    """带图片的消息要能发出去，并在历史里原样返回附件。"""
    url = _upload(client, "/api/v1/media/image", PNG, "image/png").json()["url"]
    attachment = {"kind": "image", "url": url, "name": "shot.png", "mime": "image/png"}

    sent = client.post(
        "/api/v1/chat",
        json={
            "session_id": session_id,
            "messages": [
                {"role": "user", "content": "这张图里是什么？", "attachments": [attachment]}
            ],
        },
    )
    assert sent.status_code == 200

    history = client.get(f"/api/v1/sessions/{session_id}/messages").json()
    mine = [m for m in history if m["sender_type"] == "user"]
    assert mine, "用户消息应已落库"
    assert mine[-1]["attachments"], "附件应被持久化"
    assert mine[-1]["attachments"][0]["url"] == url


def test_messages_without_attachment_have_empty_list(client: TestClient, session_id: str) -> None:
    client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "messages": [{"role": "user", "content": "纯文字标记"}]},
    )
    history = client.get(f"/api/v1/sessions/{session_id}/messages").json()
    # 只校验自己刚发的那条：测试共用同一个会话，不能断言全部为空
    mine = [m for m in history if m["content"] == "纯文字标记"]
    assert mine, "消息应已落库"
    assert mine[-1]["attachments"] == []


def test_audio_transcript_note_injected(client: TestClient, session_id: str) -> None:
    """语音转写结果应作为上下文参与对话。"""
    resp = client.post(
        "/api/v1/chat",
        json={
            "session_id": session_id,
            "messages": [
                {
                    "role": "user",
                    "content": "",
                    "attachments": [
                        {"kind": "audio", "url": "/api/v1/media/x.webm", "transcript": "明天要开会"}
                    ],
                }
            ],
        },
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------- 降级


def test_vision_without_model_degrades(client: TestClient) -> None:
    """没配视觉模型时应明确告知，而不是报错。"""
    resp = _upload(client, "/api/v1/media/vision", PNG, "image/png")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["description"] is None
    assert "未配置" in (body["hint"] or "")


def test_transcribe_without_asr_degrades(client: TestClient) -> None:
    resp = _upload(client, "/api/v1/media/transcribe", b"fake", "audio/webm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert "未配置" in (body["hint"] or "")