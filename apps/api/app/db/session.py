"""数据库引擎与会话工厂。

- 默认 SQLite（零配置，文件落在 data/sqlite/）
- 改 DATABASE_URL 即可切 PostgreSQL，业务代码无感知
- 启动时调 init_db() 建表；正式项目建议后续接 Alembic 迁移
"""

import logging
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)


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


#: 后期新增的列。``create_all`` 只建新表，**不会给已存在的表补列** ——
#: 开发者本地的 app.db 早就在了，光改模型定义会直接报 no such column。
#: 正式项目该上 Alembic，这里用最小改动覆盖 SQLite 这个单一场景。
_LATE_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("messages", "sender_label", "VARCHAR(64) DEFAULT '我'"),
)


def _migrate_sqlite() -> None:
    """给已存在的 SQLite 库补上后期新增的列。"""
    if not _is_sqlite or ":memory:" in settings.database_url:
        return

    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, column, ddl in _LATE_COLUMNS:
            if table not in existing_tables:
                continue
            if column in {c["name"] for c in inspector.get_columns(table)}:
                continue
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            except Exception as exc:
                logger.warning("补列失败 %s.%s：%s", table, column, exc)


def init_db() -> None:
    """建表 + 补列。会先 import app.models 确保所有模型都注册到 metadata。"""
    from app import models  # noqa: F401  (导入即注册)

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()