"""会话相关路由：列表、创建、改名、删除、消息历史。"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as OrmSession

from app.db.session import get_db
from app.schemas.session import (
    GroupSummaryOut,
    MessageOut,
    SessionCreate,
    SessionOut,
    SessionRename,
)
from app.services import media_service, session_service

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
    out: list[MessageOut] = []
    for m in session_service.list_messages(db, session_id):
        dto = MessageOut.model_validate(m)
        # attachments 在库里是 JSON 文本，出参要的是结构化列表
        out.append(dto.model_copy(update={"attachments": media_service.parse_attachments(m.attachments)}))
    return out


@router.patch("/{session_id}", response_model=SessionOut, summary="重命名会话")
def rename_session(session_id: str, payload: SessionRename, db: DbSession) -> SessionOut:
    return SessionOut.model_validate(
        session_service.rename_session(db, session_id, payload.title)
    )


@router.delete(
    "/{session_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除单条消息",
)
def delete_message(session_id: str, message_id: str, db: DbSession) -> None:
    """删一条消息。

    「重新生成」要用它：用户对回复不满意时，得先把旧回复删掉才能重新问一遍，
    否则两条回复会一起留在上下文里，模型看到自己说过两次。

    删 AI 的回复时连带删掉它引用的上传文件 —— 不然文件会变成孤儿，
    只能等启动时的自动清理（默认 24h 宽限期）。
    """
    session_service.get_or_404(db, session_id)
    session_service.delete_message(db, session_id, message_id)


@router.delete(
    "/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除会话"
)
def delete_session(session_id: str, db: DbSession) -> None:
    session_service.delete_session(db, session_id)


@router.post(
    "/{session_id}/summarize",
    response_model=GroupSummaryOut,
    summary="总结群聊",
)
async def summarize_session(session_id: str, db: DbSession) -> GroupSummaryOut:
    """把群聊里的讨论收拢成结构化摘要：议题 / 结论 / 待办 / 参与者。

    仅对群聊会话开放 —— AI 伴侣和好友单聊是两个人的对话，
    「总结谁说了什么」这个问题不存在。

    模型不可用时**照样返回结果**（规则版），断网、Key 填错都不会让这个功能消失。
    """
    from app.services import summary_service

    session = session_service.get_or_404(db, session_id)
    if session.type != "group":
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="只有群聊会话需要总结")

    summary = await summary_service.summarize(db, session_id)
    return GroupSummaryOut(**summary.to_dict(), text=summary_service.render_text(summary))