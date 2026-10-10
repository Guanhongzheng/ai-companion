"""多媒体接口：上传图片与音频、语音转写、图片理解、读取已上传的文件。"""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.core.overrides import ModelOverrideDep
from app.schemas.media import (
    MediaUploadOut,
    TranscribeOut,
    VisionOut,
)
from app.services import asr_service, media_service, vision_service

router = APIRouter()


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


@router.get("/{filename}", summary="读取已上传的文件")
def read_media(filename: str) -> FileResponse:
    path = media_service.resolve_media_path(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path)