"""应用入口：创建 FastAPI 实例、挂中间件、注册路由。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.services.session_service import ensure_seed


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """启动/关闭钩子：建表、灌示例数据、初始化模型与向量库客户端。"""
    init_db()
    with SessionLocal() as db:
        ensure_seed(db)
    # TODO(M2): 初始化 Chroma 向量库客户端
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

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"], summary="健康检查")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "env": settings.app_env}
