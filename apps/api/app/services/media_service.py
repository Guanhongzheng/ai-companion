"""多媒体附件的上传、读取与清理。

只做「存」不做「看」—— 语音转写在``asr_service``，图像理解在 ``vision_service``。
两边都能独立降级：没配模型 Key 时图片照样能存、能显示，只是不会被理解。

安全约束：

* 白名单校验类型与大小，不接受任意扩展名
* 文件名完全由服务端生成（uuid），**不采用用户提交的原始文件名**，杜绝路径穿越
* 静态读取走 ``FileResponse``，并做路径合法性检查，确保不会读到 data/ 之外
* 删除同样只接受纯文件名，越界一律拒绝

清理是怎么设计的
----------------
上传接口是「先落盘再挂到消息上」的两步流程，中间必然产生两类孤儿文件：

1. 传了但没发出去（用户移除了附件、切了会话、直接关页面）
2. 发过，但消息随会话被删掉了

本模块把「谁还被引用」算准（扫 ``messages.attachments``），
再由 ``cleanup_orphans`` 按宽限期回收未引用的文件。
宽限期是为了保护**正在编辑、还没发送**的附件 —— 它们此刻同样是未引用状态。
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session as OrmSession

from app.core.config import settings
from app.models.session import MessageModel

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


def _safe_child_path(filename: str) -> Path | None:
    """把文件名解析成 uploads 目录内的路径；越界返回 None。

    与 ``resolve_media_path`` 的区别：**不要求文件已存在** ——
    删除场景也要用它，先算安全路径再决定动不动手。
    """
    if not filename:
        return None
    root = _upload_dir().resolve()
    candidate = (root / filename).resolve()
    # candidate == root 说明文件名被构造成了 "."，也要挡掉
    if candidate == root or root not in candidate.parents:
        return None
    return candidate


def resolve_media_path(filename: str) -> Path | None:
    """把 URL 里的文件名解析成磁盘路径。

    返回 None 表示非法（越界或不存在）。这里必须严格：filename 一旦能穿出
    data/uploads，这个接口就变成了任意文件读取。
    """
    candidate = _safe_child_path(filename)
    if candidate is None or not candidate.is_file():
        return None
    return candidate


def delete_file(filename: str) -> bool:
    """删除一个上传文件。越界或不存在都返回 False，不抛异常。"""
    path = _safe_child_path(filename)
    if path is None or not path.is_file():
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return True


def filename_of_attachment(attachment: Mapping[str, object]) -> str | None:
    """从附件的 ``url`` 里取出磁盘文件名。

    只认「纯文件名」：带路径分隔符或 ``..`` 的一律丢弃，
    防止历史脏数据把删除操作引到 uploads 之外。
    """
    url = attachment.get("url")
    if not isinstance(url, str) or not url:
        return None
    name = url.rstrip("/").rsplit("/", 1)[-1]
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        return None
    return name


def list_upload_files() -> list[Path]:
    """列出 uploads 目录下的所有文件（不含子目录）。"""
    try:
        return [p for p in _upload_dir().iterdir() if p.is_file()]
    except OSError:
        return []


def referenced_filenames(db: OrmSession, *, session_id: str | None = None) -> set[str]:
    """收集当前仍被消息附件引用的磁盘文件名。

    直接查 messages 表而不是走 relationship：清理是独立触发的，
    不该依赖某个会话对象是否被加载。
    """
    stmt = select(MessageModel.attachments).where(MessageModel.attachments.is_not(None))
    if session_id is not None:
        stmt = stmt.where(MessageModel.session_id == session_id)

    names: set[str] = set()
    for (raw,) in db.execute(stmt).all():
        for attachment in parse_attachments(raw):
            if isinstance(attachment, dict):
                name = filename_of_attachment(attachment)
                if name:
                    names.add(name)
    return names


@dataclass(slots=True)
class CleanupResult:
    """一次清理的账目。分开记比只报一个总数有用得多。"""

    scanned: int = 0
    deleted: int = 0
    freed_bytes: int = 0
    #: 仍被消息引用，保留
    kept_referenced: int = 0
    #: 未超宽限期（多半是用户正在编辑的附件），保留
    kept_recent: int = 0
    #: 删除失败（文件被占用等）
    failed: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "scanned": self.scanned,
            "deleted": self.deleted,
            "freed_bytes": self.freed_bytes,
            "kept_referenced": self.kept_referenced,
            "kept_recent": self.kept_recent,
            "failed": self.failed,
        }


def cleanup_orphans(db: OrmSession, *, grace_seconds: float = 0.0) -> CleanupResult:
    """删除「没有被任何消息引用」且「已超过宽限期」的上传文件。

    宽限期不是可选项 —— 用户刚上传、还没点发送的图片此刻就是未引用状态，
    没有宽限期就会把人家正在写的消息配图删掉。
    """
    referenced = referenced_filenames(db)
    now = time.time()
    result = CleanupResult()

    for path in list_upload_files():
        result.scanned += 1

        if path.name in referenced:
            result.kept_referenced += 1
            continue

        try:
            stat = path.stat()
        except OSError:
            result.failed += 1
            continue

        if now - stat.st_mtime < grace_seconds:
            result.kept_recent += 1
            continue

        try:
            path.unlink()
        except OSError:
            result.failed += 1
            continue

        result.deleted += 1
        result.freed_bytes += stat.st_size

    return result


def usage_stats(db: OrmSession) -> dict[str, object]:
    """上传目录的占用情况，给「存了多少、有多少能清」一个准数。"""
    referenced = referenced_filenames(db)
    files = list_upload_files()

    total = 0
    orphan_count = 0
    orphan_bytes = 0
    for path in files:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        total += size
        if path.name not in referenced:
            orphan_count += 1
            orphan_bytes += size

    return {
        "file_count": len(files),
        "total_bytes": total,
        "referenced_count": len(files) - orphan_count,
        "orphan_count": orphan_count,
        "orphan_bytes": orphan_bytes,
        "directory": str(_upload_dir()),
    }


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