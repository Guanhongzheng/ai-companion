"""多媒体附件的上传与读取。

只做「存」不做「看」—— 语音转写在``asr_service``，图像理解在 ``vision_service``。
两边都能独立降级：没配模型 Key 时图片照样能存、能显示，只是不会被理解。

安全约束：

* 白名单校验类型与大小，不接受任意扩展名
* 文件名完全由服务端生成（uuid），**不采用用户提交的原始文件名**，杜绝路径穿越
* 静态读取走 ``FileResponse``，并做路径合法性检查，确保不会读到 data/ 之外
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import UploadFile

from app.core.config import settings

AttachmentKind = Literal["image", "audio"]

#: 允许的图片类型（浏览器 mime → 扩展名）
IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

#: 允许的音频类型
AUDIO_TYPES = {
    "audio/webm": ".webm",  # Chrome/Edge 录音默认格式
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",  # Safari 录音格式
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/webm;codecs=opus": ".webm",
    "audio/webm;codecs=mp4a.40.2": ".m4a",
}

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25MB


def max_image_bytes() -> int:
    return settings.max_image_mb * 1024 * 1024


def max_audio_bytes() -> int:
    return settings.max_audio_mb * 1024 * 1024


@dataclass(slots=True)
class StoredAttachment:
    kind: AttachmentKind
    url: str
    #: 用户看到的原始文件名，仅用于展示
    name: str
    #: 服务端生成的磁盘文件名，读文件必须用这个
    filename: str
    size: int
    mime: str

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "url": self.url,
            "name": self.name,
            "size": self.size,
            "mime": self.mime,
        }


def _upload_dir() -> Path:
    # local_storage_dir 本身已经指向 data/uploads，这里不再重复套一层
    path = Path(settings.local_storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _strip_codec(mime: str) -> str:
    """audio/webm;codecs=opus -> audio/webm"""
    return mime.split(";")[0].strip().lower()


async def store_upload(
    file: UploadFile, kind: AttachmentKind
) -> StoredAttachment:
    """保存一个上传文件，返回可直接给前端用的附件信息。"""
    mime = _strip_codec(file.content_type or "")
    table = IMAGE_TYPES if kind == "image" else AUDIO_TYPES
    limit = MAX_IMAGE_BYTES if kind == "image" else MAX_AUDIO_BYTES

    ext = table.get(mime)
    if ext is None:
        allowed = "、".join(sorted({_strip_codec(m) for m in table}))
        raise ValueError(f"不支持的{kind}类型：{mime or '未知'}。支持：{allowed}")

    limit = max_image_bytes() if kind == "image" else max_audio_bytes()
    payload = await file.read()
    if not payload:
        raise ValueError("文件是空的")
    if len(payload) > limit:
        raise ValueError(
            f"文件太大（{len(payload) // 1024 // 1024}MB），上限 {limit // 1024 // 1024}MB"
        )

    # 文件名完全由服务端生成，不使用用户提交的原始名字
    filename = f"{uuid.uuid4().hex}{ext}"
    target = _upload_dir() / filename
    target.write_bytes(payload)

    return StoredAttachment(
        kind=kind,
        url=f"{settings.api_prefix}/media/{filename}",
        name=file.filename or filename,
        filename=filename,
        size=len(payload),
        mime=mime,
    )


def resolve_media_path(filename: str) -> Path | None:
    """把 URL 里的文件名解析成磁盘路径。

    返回 None 表示非法（越界或不存在）。这里必须严格：filename 一旦能穿出
    data/uploads，这个接口就变成了任意文件读取。
    """
    root = _upload_dir().resolve()
    candidate = (root / filename).resolve()
    if not candidate.is_file():
        return None
    # 防目录穿越：解析后的路径必须仍在 uploads 目录内
    if root not in candidate.parents:
        return None
    return candidate


# ---------------------------------------------------------------- 附件序列化


def parse_attachments(raw: str | None) -> list[dict[str, object]]:
    """把 DB 里的 JSON 文本还原成附件列表。数据坏了就当没有附件，不要让对话崩掉。"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return data if isinstance(data, list) else []


def dump_attachments(items: list[dict[str, object]]) -> str:
    return json.dumps(items, ensure_ascii=False)


def images_of(attachments: list[dict[str, object]]) -> list[dict[str, object]]:
    return [a for a in attachments if a.get("kind") == "image"]


def audio_of(attachments: list[dict[str, object]]) -> list[dict[str, object]]:
    return [a for a in attachments if a.get("kind") == "audio"]