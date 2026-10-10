"""应用入口：创建 FastAPI 实例、挂中间件、注册路由。"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """启动/关闭钩子：初始化数据库、向量库、模型客户端。"""
    # TODO: 初始化 SQLAlchemy engine、Chroma client、LiteLLM 配置
    yield
    # TODO: 释放资源


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
