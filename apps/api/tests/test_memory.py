"""RAG 记忆：抽取、向量化、召回重排、CRUD、导出清空。"""

from fastapi.testclient import TestClient

from app.core import crypto
from app.memory.embedding import cosine_similarity, get_embedder
from app.memory.extractor import extract_by_rules
from app.memory.retriever import lexical_overlap

# ---------------------------------------------------------------- 抽取


def test_extract_profile_sentences() -> None:
    text = "你好呀！我叫林小满，今年28岁，是一名后端工程师。我住在深圳南山。"
    got = extract_by_rules(text)
    assert got, "应该能抽到身份类记忆"
    assert any("林小满" in c.content for c in got)


def test_extract_ignores_small_talk() -> None:
    """情绪化闲聊不该被记成长期记忆。"""
    got = extract_by_rules("哈哈今天真的太累了，好想躺着什么都不做")
    assert got == []


def test_extract_preference_and_event() -> None:
    assert any(c.type == "preference" for c in extract_by_rules("我喜欢吃潮汕牛肉火锅"))
    assert any(c.type == "event" for c in extract_by_rules("我打算下周开始学法语"))


# ---------------------------------------------------------------- 向量化


def test_embedder_is_deterministic() -> None:
    """哈希实现必须跨调用一致，否则向量库会失效。"""
    import asyncio

    embedder = get_embedder()

    async def run() -> tuple[list[float], list[float]]:
        return (
            await embedder.embed_query("我住在深圳南山"),
            await embedder.embed_query("我住在深圳南山"),
        )

    a, b = asyncio.run(run())
    assert a == b
    assert len(a) == embedder.dim


def test_vectors_are_normalized() -> None:
    import asyncio

    embedder = get_embedder()
    vec = asyncio.run(embedder.embed_query("测试向量化"))
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-6


def test_similarity_ordering() -> None:
    import asyncio

    embedder = get_embedder()

    async def run() -> list[float]:
        docs = await embedder.embed_documents(["我住在深圳南山", "我养了一只叫豆豆的猫"])
        query = await embedder.embed_query("我住在哪里")
        return [cosine_similarity(query, d) for d in docs]

    sims = asyncio.run(run())
    assert sims[0] > sims[1], "居住相关的句子应该比猫更匹配"


def test_lexical_overlap() -> None:
    assert lexical_overlap("我住在哪里", "我住在深圳南山") > 0
    assert lexical_overlap("完全无关", "我住在深圳南山") == 0


# ---------------------------------------------------------------- 接口


def test_seed_memories_created(client: TestClient) -> None:
    resp = client.get("/api/v1/memory")
    assert resp.status_code == 200
    assert len(resp.json()) == 5
    # 出参必须是解密后的明文
    assert all(not m["content"].startswith("enc::") for m in resp.json())


def test_stats(client: TestClient) -> None:
    body = client.get("/api/v1/memory/stats").json()
    assert body["total"] == 5
    assert "by_type" in body
    assert body["embedder"] in {"hashing", "cloud", "bge-m3"}


def test_create_search_update_delete(client: TestClient) -> None:
    created = client.post(
        "/api/v1/memory", json={"content": "我用的编辑器是 VS Code", "type": "preference"}
    )
    assert created.status_code == 201
    mid = created.json()["id"]

    hits = client.get("/api/v1/memory/search", params={"q": "编辑器"}).json()
    assert hits, "应该能搜到刚建的记忆"
    assert hits[0]["memory"]["id"] == mid

    updated = client.patch(f"/api/v1/memory/{mid}", json={"pinned": True})
    assert updated.status_code == 200
    assert updated.json()["pinned"] is True

    assert client.delete(f"/api/v1/memory/{mid}").status_code == 204
    assert client.patch(f"/api/v1/memory/{mid}", json={"pinned": False}).status_code == 404


def test_dedup_prevents_duplicate(client: TestClient) -> None:
    """完全一样的内容不该被存两次。"""
    payload = {"content": "我每周三都会去健身房", "type": "preference"}
    first = client.post("/api/v1/memory", json=payload)
    second = client.post("/api/v1/memory", json=payload)
    assert first.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_ingest_from_text(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/memory/ingest",
        json={"text": "我养了一只叫旺财的狗，我住在广州天河区"},
    )
    assert resp.status_code == 201
    contents = [m["content"] for m in resp.json()]
    assert any("旺财" in c for c in contents)


def test_search_empty_query_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/memory/search", params={"q": "  "}).status_code == 400


def test_unknown_type_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/memory", params={"type": "nope"}).status_code == 400
    assert client.post("/api/v1/memory", json={"content": "x", "type": "nope"}).status_code == 400


def test_export_and_clear(client: TestClient) -> None:
    exported = client.get("/api/v1/memory/export")
    assert exported.status_code == 200
    assert "memories" in exported.json()
    assert exported.json()["count"] >= 5

    cleared = client.delete("/api/v1/memory")
    assert cleared.status_code == 200
    assert cleared.json()["deleted"] >= 5
    assert client.get("/api/v1/memory").json() == []


# ---------------------------------------------------------------- 加密


def test_crypto_roundtrip() -> None:
    crypto.reset()
    plain = "这是私密内容"
    token = crypto.encrypt(plain)
    # 未启用加密时原样返回
    assert token == plain
    assert crypto.decrypt(token) == plain
    crypto.reset()


def test_crypto_with_key(monkeypatch: object) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "memory_encrypt", True, raising=False)  # type: ignore[attr-defined]
    monkeypatch.setattr(
        config.settings, "memory_encryption_key", "unit-test-key-32-chars-long!!!!", raising=False  # type: ignore[attr-defined]
    )
    crypto.reset()
    try:
        assert crypto.is_enabled()
        token = crypto.encrypt("我的秘密")
        assert token.startswith("enc::")
        assert crypto.decrypt(token) == "我的秘密"
    finally:
        crypto.reset()