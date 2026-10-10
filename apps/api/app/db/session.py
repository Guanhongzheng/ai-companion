"""数据库引擎与会话工厂。

- 默认 SQLite（零配置，文件落在 data/sqlite/）
- 改 DATABASE_URL 即可切 PostgreSQL，业务代码无感知
- 启动时调 init_db() 建表；正式项目建议后续接 Alembic 迁移
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base


def _ensure_sqlite_dir(url: str) -> None:
    """SQLite 文件所在目录不存在时自动创建。

    DATABASE_URL 默认是相对路径 `./data/sqlite/app.db`，而不同启动方式的
    CWD 不一样（uvicorn 在 apps/api，pytest 在别处），不自动建目录就会
    报 `unable to open database file`。
    """
    if not url.startswith("sqlite"):
        return
    remainder = url.removeprefix("sqlite:///")
    if not remainder or remainder.startswith(":") or ":memory:" in url:
        return
    parent = Path(remainder).expanduser().parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # SQLite 默认禁止跨线程，FastAPI 的线程池会踩到
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每个请求一个 Session，用完即关。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表。会先 import app.models 确保所有模型都注册到 metadata。"""
    from app import models  # noqa: F401  (导入即注册)

    Base.metadata.create_all(bind=engine)