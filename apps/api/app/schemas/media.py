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