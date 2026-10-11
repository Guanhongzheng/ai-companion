"""多媒体相关的出入参。"""

from pydantic import BaseModel, Field


class MediaUploadOut(BaseModel):
    kind: str = Field(description="image / audio")
    url: str = Field(description="可直接访问的相对路径")
    name: str
    size: int
    mime: str


class TranscribeOut(BaseModel):
    url: str
    name: str
    #: 识别出的文字；不可用时为 None
    transcript: str | None = None
    #: 是否具备识别能力
    available: bool
    #: 不可用时给用户看的中文提示
    hint: str | None = None


class VisionOut(BaseModel):
    url: str
    name: str
    #: 图片描述；不可用时为 None
    description: str | None = None
    available: bool
    hint: str | None = None


class MediaStatsOut(BaseModel):
    """上传目录的占用情况。"""

    #: 磁盘上的文件总数
    file_count: int
    #: 占用字节数
    total_bytes: int
    #: 仍被消息引用的文件数
    referenced_count: int
    #: 没有任何消息引用、可被清理的文件数
    orphan_count: int
    #: 可清理的字节数
    orphan_bytes: int
    #: uploads 目录的绝对路径，便于排查
    directory: str


class CleanupOut(BaseModel):
    """一次清理的结果。分开记账，便于判断到底是「没得清」还是「被保护了」。"""

    #: 扫描到的文件数
    scanned: int
    #: 实际删除数
    deleted: int
    #: 释放的字节数
    freed_bytes: int
    #: 仍被消息引用而保留
    kept_referenced: int
    #: 未超过宽限期而保留（多半是正在编辑、尚未发送的附件）
    kept_recent: int
    #: 删除失败数（文件被占用等）
    failed: int


class Attachment(BaseModel):
    """消息附件。存在 messages.attachments 这个 JSON 列里。"""

    kind: str = Field(description="image / audio")
    url: str
    name: str = ""
    #: 语音转写结果
    transcript: str | None = None
    #: 图片理解结果
    description: str | None = None
    mime: str = ""
    size: int = 0