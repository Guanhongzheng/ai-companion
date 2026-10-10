"""v1 路由汇总：新增模块时在这里注册。"""

from fastapi import APIRouter

from app.api.v1 import chat, memory, sessions

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(memory.router, prefix="/memory", tags=["memory"])

# 后续按域补充：
# api_router.include_router(companion.router, prefix="/companion", tags=["companion"])
# api_router.include_router(social.router, prefix="/social", tags=["social"])
# api_router.include_router(media.router, prefix="/media", tags=["media"])
