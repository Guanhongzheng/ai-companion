"""RAG 记忆：抽取、向量化、召回重排、CRUD、导出清空。"""

import json

from fastapi.testclient import TestClient

from app.core import crypto
from app.memory.embedding import cosine_similarity, get_embedder
from app.memory.extractor import extract_by_rules
from app.memory.retriever import lexical_overlap
from app.services.memory_service import worth_extracting

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


# ---------------------------------------------------------------- BYOK


def test_settings_status_without_key(client: TestClient) -> None:
    """没有带 Key 时，一切走服务端配置。"""
    resp = client.get("/api/v1/settings/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["using_user_key"] is False
    assert body["key_hint"] == "<空>"
    assert body["model"] == body["server_default_model"]


def test_settings_status_masks_key(client: TestClient) -> None:
    """带 Key 时只回传脱敏值，绝不回传完整 Key。"""
    secret = "sk-super-secret-key-1234567890"
    body = client.get(
        "/api/v1/settings/status",
        headers={"X-Model-Key": secret, "X-Model-Name": "deepseek-chat"},
    ).json()
    assert body["using_user_key"] is True
    assert body["model"] == "deepseek/deepseek-chat"
    assert secret not in json.dumps(body)
    assert body["key_hint"] == "sk-s***7890"


def test_validate_without_key(client: TestClient) -> None:
    body = client.post("/api/v1/settings/validate").json()
    assert body["ok"] is False
    assert "Key" in body["message"]


def test_chat_uses_user_key_model(client: TestClient, session_id: str) -> None:
    """带上自己的 Key 后应走真实模型分支；Key 无效时返回 502 + 中文提示而非堆栈。"""
    secret = "sk-not-a-real-key-abcdefghijklmnop"
    resp = client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "messages": [{"role": "user", "content": "你好"}]},
        headers={"X-Model-Key": secret, "X-Model-Name": "deepseek-chat"},
    )
    # 真实调用必然失败（Key 是假的），关键是要变成可读的 502 而不是 500 堆栈
    assert resp.status_code == 502
    detail = resp.json()["detail"]
    assert "Key" in detail or "失败" in detail
    # 原始异常里可能带 Key 片段，绝不能回显
    assert secret not in detail
    assert "Traceback" not in detail


def test_mask_helper() -> None:
    from app.core.overrides import mask

    assert mask(None) == "<空>"
    assert mask("sk-1234") == "sk***34"
    assert mask("sk-abcdefghijklmnop") == "sk-a***mnop"


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

# ---------------------------------------------------------------- 隐私清洗

#: 校验位合法的号码，编的号过不了校验会被当普通数字放过
_ID_OK = "310101199003077755"
_PHONE = "13812345678"


def _create_memory(client: TestClient, content: str, type_: str = "fact") -> str:
    resp = client.post("/api/v1/memory", json={"content": content, "type": type_})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_stats_reports_sensitive_count(client: TestClient) -> None:
    """有含敏感信息的记忆时，/stats 必须如实报出来，不能默认「一切安全」。"""
    _create_memory(client, f"用户的手机号是{_PHONE}")
    stats = client.get("/api/v1/memory/stats").json()
    assert stats["sensitive"] >= 1
    assert stats["safety_filter"] is True


def test_scrub_cleans_sensitive_memory(client: TestClient) -> None:
    mid = _create_memory(client, f"用户的身份证号是{_ID_OK}")

    before = client.get("/api/v1/memory/stats").json()
    assert before["sensitive"] >= 1

    resp = client.post("/api/v1/memory/scrub")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cleaned"] >= 1
    assert "id_card" in body["kinds"]
    assert mid in body["ids"]

    # 库里不能再有原文
    after = client.get("/api/v1/memory/stats").json()
    assert after["sensitive"] == 0
    content = next(m["content"] for m in client.get("/api/v1/memory").json() if m["id"] == mid)
    assert _ID_OK not in content
    assert "****" in content


def test_scrub_is_idempotent(client: TestClient) -> None:
    """清洗接口可能被反复点，不能把内容洗坏。"""
    _create_memory(client, f"用户的手机号是{_PHONE}")
    assert client.post("/api/v1/memory/scrub").json()["cleaned"] >= 1
    second = client.post("/api/v1/memory/scrub").json()
    assert second["cleaned"] == 0
    assert second["scanned"] == 0


def test_scrub_rebuilds_vector(client: TestClient) -> None:
    """🔴 改了正文却不同步向量库，检索命中的仍然是旧内容。

    这条用例守的就是「SQL 与向量库必须一致」这条老教训
    （和 sync_vector_store 双向对账同一个道理）。
    """
    mid = _create_memory(client, f"用户的手机号是{_PHONE}")
    client.post("/api/v1/memory/scrub")

    hits = client.get("/api/v1/memory/search", params={"q": _PHONE}).json()
    matched = [h for h in hits if h["memory"]["id"] == mid]
    for hit in matched:
        assert _PHONE not in hit["memory"]["content"]


def test_extract_redacts_before_persist(client: TestClient, session_id: str) -> None:
    """端到端：对话里说出手机号，落库的记忆里不该有原文。"""
    client.post(
        "/api/v1/chat",
        json={
            "session_id": session_id,
            "messages": [
                {"role": "user", "content": f"我叫林小满，我的手机号是{_PHONE}"}
            ],
        },
    )
    for m in client.get("/api/v1/memory").json():
        assert _PHONE not in m["content"], f"记忆里漏出了手机号：{m['content']}"


# ---------------------------------------------------------------- 自动抽取


def test_extract_keeps_multiple_same_type_facts() -> None:
    """🔴 曾经同类型只留权重最高的一条，结果职业被宠物顶掉了。

    两句都是 profile，但它们是两条独立的事实，谁也顶不掉谁。
    """
    text = "我是一名海洋生物学家，常年在厦门研究中华白海豚。我养了三只水母，都叫小透明"
    got = extract_by_rules(text)
    contents = " ".join(c.content for c in got)
    assert "海洋生物学家" in contents, f"职业信息丢了：{contents}"
    assert "水母" in contents, f"宠物信息丢了：{contents}"


def test_worth_extracting_gate() -> None:
    """前置门槛：寒暄不值得花一次模型调用去抽取。"""
    assert worth_extracting("我是一名海洋生物学家") is True
    assert worth_extracting("嗯") is False
    assert worth_extracting("好的") is False
    assert worth_extracting("在吗") is False
    assert worth_extracting("") is False


def test_chat_actually_ingests_memories(client: TestClient, session_id: str) -> None:
    """🔴 端到端闭环：说完话，记忆要真的多出来。

    这条曾经是个假象 —— 对话链路压根没调用抽取器，全靠种子数据撑着，
    演示时「AI 能记住我说过的话」看着成立，实际上换个话题就露馅。
    """
    before = client.get("/api/v1/memory/stats").json()["total"]

    client.post(
        "/api/v1/chat",
        json={
            "session_id": session_id,
            "messages": [
                {"role": "user", "content": "我是一名海洋生物学家，常年在厦门研究中华白海豚"}
            ],
        },
    )

    after = client.get("/api/v1/memory/stats").json()["total"]
    assert after > before, "对话后记忆条数应该增加"

    bodies = " ".join(m["content"] for m in client.get("/api/v1/memory").json())
    assert "海洋生物学家" in bodies


def test_chat_does_not_ingest_small_talk(client: TestClient, session_id: str) -> None:
    """寒暄不该产生记忆，更不该每次都去调一次模型。"""
    before = client.get("/api/v1/memory/stats").json()["total"]
    client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "messages": [{"role": "user", "content": "嗯"}]},
    )
    assert client.get("/api/v1/memory/stats").json()["total"] == before
