"""会话相关路由：列表、创建、改名、删除、消息历史。"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as OrmSession

from app.db.session import get_db
from app.schemas.session import (
    MessageOut,
    SessionCreate,
    SessionOut,
    SessionRename,
)
from app.services import session_service

router = APIRouter()

DbSession = Annotated[OrmSession, Depends(get_db)]


@router.get("", response_model=list[SessionOut], summary="会话列表")
def list_sessions(db: DbSession) -> list[SessionOut]:
    return [SessionOut.model_validate(s) for s in session_service.list_sessions(db)]


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED, summary="创建会话")
def create_session(payload: SessionCreate, db: DbSession) -> SessionOut:
    return SessionOut.model_validate(
        session_service.create_session(
            db, type=payload.type, title=payload.title, member_count=payload.member_count
        )
    )


@router.get(
    "/{session_id}/messages",
    response_model=list[MessageOut],
    summary="会话消息历史",
)
def list_messages(session_id: str, db: DbSession) -> list[MessageOut]:
    session_service.get_or_404(db, session_id)
    return [MessageOut.model_validate(m) for m in session_service.list_messages(db, session_id)]


@router.patch("/{session_id}", response_model=SessionOut, summary="重命名会话")
def rename_session(session_id: str, payload: SessionRename, db: DbSession) -> SessionOut:
    return SessionOut.model_validate(
        session_service.rename_session(db, session_id, payload.title)
    )


@router.delete(
    "/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除会话"
)
def delete_session(session_id: str, db: DbSession) -> None:
    session_service.delete_session(db, session_id)