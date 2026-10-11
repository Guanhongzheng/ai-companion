"""应用入口：创建 FastAPI 实例、挂中间件、注册路由。"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as OrmSession

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.services import media_service, memory_service
from app.services.memory_service import ensure_seed_memories
from app.services.session_service import ensure_seed

logger = logging.getLogger(__name__)


def _auto_cleanup_media(db: OrmSession) -> None:
    """启动时回收没有被任何消息引用的上传文件。

    「上传即落盘」决定了孤儿文件一定会产生（用户传了图又没发），
    所以不能只靠手动清理。宽限期取得比较长，一次只清掉明显陈旧的。

    这里刻意把异常吞掉：清理失败绝不该让服务起不来。
    """
    if not settings.media_auto_cleanup:
        return
    try:
        result = media_service.cleanup_orphans(
            db, grace_seconds=settings.media_cleanup_grace_hours * 3600
        )
    except Exception:  # 启动路径上任何清理问题都不该中断服务
        logger.exception("上传文件自动清理失败（不影响启动）")
        return

    if result.deleted:
        logger.info(
            "自动清理上传文件：删除 %d 个，释放 %.1f MB（保留 %d 个引用中 / %d 个宽限期内）",
            result.deleted,
            result.freed_bytes / 1024 / 1024,
            result.kept_referenced,
            result.kept_recent,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """启动/关闭钩子：建表、灌示例数据、初始化模型与向量库客户端。"""
    init_db()
    with SessionLocal() as db:
        ensure_seed(db)
        ensure_seed_memories(db)
        memory_service.sync_vector_store(db)
        _auto_cleanup_media(db)
    # TODO(M2): 按需预热 Chroma 连接与重排模型
    yield
    # TODO: 释放 HTTP / 向量库连接池


app = FastAPI(
    title="ai-companion API",
    description="个性化多模态 AI 伴侣与社交对话平台 · 后端服务",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"], summary="健康检查")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "env": settings.app_env}
