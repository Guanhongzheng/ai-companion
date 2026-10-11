"""多媒体接口：上传图片与音频、语音转写、图片理解、读取与清理已上传的文件。"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as OrmSession

from app.core.overrides import ModelOverrideDep
from app.db.session import get_db
from app.schemas.media import (
    CleanupOut,
    MediaStatsOut,
    MediaUploadOut,
    TranscribeOut,
    VisionOut,
)
from app.services import asr_service, media_service, vision_service

router = APIRouter()

DbSession = Annotated[OrmSession, Depends(get_db)]


def _bad(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def _payload_of(stored: media_service.StoredAttachment) -> bytes:
    # 必须用服务端生成的 filename，stored.name 是用户原始文件名
    path = media_service.resolve_media_path(stored.filename)
    if path is None:
        raise HTTPException(status_code=400, detail="文件读取失败")
    return path.read_bytes()


@router.post("/image", response_model=MediaUploadOut, summary="上传图片")
async def upload_image(file: Annotated[UploadFile, File()]) -> MediaUploadOut:
    try:
        stored = await media_service.store_upload(file, "image")
    except ValueError as exc:
        raise _bad(str(exc)) from exc
    return MediaUploadOut(**stored.to_dict())


@router.post("/audio", response_model=MediaUploadOut, summary="上传音频")
async def upload_audio(file: Annotated[UploadFile, File()]) -> MediaUploadOut:
    try:
        stored = await media_service.store_upload(file, "audio")
    except ValueError as exc:
        raise _bad(str(exc)) from exc
    return MediaUploadOut(**stored.to_dict())


@router.post("/transcribe", response_model=TranscribeOut, summary="音频转文字")
async def transcribe(
    file: Annotated[UploadFile, File()], override: ModelOverrideDep
) -> TranscribeOut:
    """服务端 ASR 兜底。

    浏览器能用 Web Speech API 时前端不走这里（省一次调用也省一次上传），
    这个接口是给 Firefox / Safari 这类不支持的浏览器准备的。
    """
    try:
        stored = await media_service.store_upload(file, "audio")
    except ValueError as exc:
        raise _bad(str(exc)) from exc

    text = await asr_service.transcribe(_payload_of(stored), stored.mime, override)
    return TranscribeOut(
        url=stored.url,
        name=stored.name,
        transcript=text,
        available=text is not None,
        hint=(
            None
            if text is not None
            else "未配置语音识别服务（需要支持 ASR 的 Key）。音频已保存，可以先手动输入文字。"
        ),
    )


@router.post("/vision", response_model=VisionOut, summary="图片理解")
async def describe(
    file: Annotated[UploadFile, File()], override: ModelOverrideDep
) -> VisionOut:
    """单独调一次看图能力。聊天接口内部也会自动看图，这里主要给调试和手动预览用。"""
    try:
        stored = await media_service.store_upload(file, "image")
    except ValueError as exc:
        raise _bad(str(exc)) from exc

    data_url = vision_service.load_as_data_url(stored.url)
    if data_url is None:
        raise HTTPException(status_code=400, detail="图片读取失败")

    text = await vision_service.describe_images(
        [data_url], vision_service.DEFAULT_VISION_PROMPT, override
    )
    return VisionOut(
        url=stored.url,
        name=stored.name,
        description=text,
        available=text is not None,
        hint=(
            None
            if text is not None
            else "未配置支持视觉的模型。图片已保存，可以补充一句文字描述让 AI 理解。"
        ),
    )


@router.get("/stats", response_model=MediaStatsOut, summary="上传目录占用统计")
def stats(db: DbSession) -> MediaStatsOut:
    """给「存储与缓存」面板用：存了多少、其中多少是可以清的。"""
    return MediaStatsOut(**media_service.usage_stats(db))  # type: ignore[arg-type]


@router.post("/cleanup", response_model=CleanupOut, summary="清理无引用的上传文件")
def cleanup(
    db: DbSession,
    grace_hours: Annotated[float, Query(ge=0, le=24 * 365, description="宽限期（小时）")] = 1.0,
) -> CleanupOut:
    """删除没有任何消息引用、且已超过宽限期的文件。

    默认留 1 小时宽限期：用户此刻可能正在编辑一条带图消息，
    那张图还没有被任何消息引用，但绝不该被删掉。
    后端启动时的自动清理用更长的宽限期（见 ``MEDIA_CLEANUP_GRACE_HOURS``）。
    """
    result = media_service.cleanup_orphans(db, grace_seconds=grace_hours * 3600)
    return CleanupOut(**result.to_dict())


@router.delete(
    "/{filename}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除一个上传文件",
)
def delete_media(filename: str, db: DbSession) -> None:
    """删除单个文件（用户在输入框里移除附件时调用）。

    已被消息引用的文件拒绝删除 —— 否则历史消息里的图片会变成裂图，
    那种「坏得很安静」的失败比占点磁盘空间糟糕得多。
    """
    if media_service.resolve_media_path(filename) is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    if filename in media_service.referenced_filenames(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该文件已被消息引用，删除会影响历史记录",
        )
    if not media_service.delete_file(filename):
        raise HTTPException(status_code=404, detail="文件不存在")


@router.get("/{filename}", summary="读取已上传的文件")
def read_media(filename: str) -> FileResponse:
    path = media_service.resolve_media_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path)