"""pytest 全局配置。

必须在导入 app 之前改好 DATABASE_URL —— config 是模块级 lru_cache，
等 app 被导入就晚了。
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "ai_companion_test.db"
_TEST_DB.unlink(missing_ok=True)
_TEST_CHROMA = Path(tempfile.gettempdir()) / "ai_companion_test_chroma"
_TEST_UPLOADS = Path(tempfile.gettempdir()) / "ai_companion_test_uploads"

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
# Chroma 默认落在项目 data/ 下，测试时改到临时目录，别污染开发环境
os.environ["CHROMA_PERSIST_DIR"] = _TEST_CHROMA.as_posix()
os.environ["LOCAL_STORAGE_DIR"] = _TEST_UPLOADS.as_posix()

# 测试必须可重复：**清空所有模型 Key 与 Ollama 地址**，强制走 mock 分支。
# 否则开发者本机配了真 .env 时，测试会真的去调模型并因 mocked=False 而挂掉。
#
# ⚠️ 必须设为空字符串而不是 pop：pop 掉环境变量后，pydantic-settings 会
# 转而从 .env 文件里读，反而拿到了真 Key。空字符串才能真正覆盖 .env。
for _key in (
    "DEEPSEEK_API_KEY",
    "DASHSCOPE_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "SILICONFLOW_API_KEY",
    "MOONSHOT_API_KEY",
    "ZHIPUAI_API_KEY",
    "VOLCENGINE_ACCESS_KEY",
    "OLLAMA_BASE_URL",
):
    os.environ[_key] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_db() -> Iterator[None]:
    init_db()
    yield
    engine.dispose()


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    # with 上下文才会触发 lifespan（建表 + 灌示例会话）
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session_id(client: TestClient) -> str:
    """AI 伴侣会话的 ID。

    必须显式挑ai 类型：群聊会话在没有 @ 提及时**不会**产生 AI 回复，
    拿列表第一个（正好是群聊）会让对话相关的测试全部失真。
    """
    sessions = client.get("/api/v1/sessions").json()
    return next(s["id"] for s in sessions if s["type"] == "ai")


@pytest.fixture
def group_session_id(client: TestClient) -> str:
    """群聊会话的 ID，用于测试 @ 唤醒逻辑。"""
    sessions = client.get("/api/v1/sessions").json()
    return next(s["id"] for s in sessions if s["type"] == "group")


@pytest.fixture
def direct_session_id(client: TestClient) -> str:
    """好友单聊会话的 ID，用于测试辅助动作。"""
    sessions = client.get("/api/v1/sessions").json()
    return next(s["id"] for s in sessions if s["type"] == "direct")