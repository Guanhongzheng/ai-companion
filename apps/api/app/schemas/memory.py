"""记忆相关的出入参。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemoryOut(BaseModel):
    """对外输出一律是解密后的明文。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    content: str
    source: str
    confidence: float
    hit_count: int
    pinned: bool
    encrypted: bool
    created_at: datetime
    updated_at: datetime


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    type: str = "fact"
    session_id: str | None = None


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, max_length=500)
    type: str | None = None
    pinned: bool | None = None


class MemoryIngest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class MemorySearchHit(BaseModel):
    memory: MemoryOut
    score: float
    vector_score: float
    lexical_score: float
    reranker: str


class MemoryStats(BaseModel):
    total: int
    by_type: dict[str, int]
    encrypted: bool
    vector_store: str
    embedder: str
    #: 仍含敏感信息、需要清洗的记忆条数
    sensitive: int
    #: 脱敏总开关是否打开（关掉时前端要如实提示「当前不做脱敏」）
    safety_filter: bool


class ScrubOut(BaseModel):
    """隐私清洗结果。"""

    #: 命中的记忆条数
    scanned: int
    #: 实际脱敏的条数
    cleaned: int
    #: 涉及的敏感类型，如 ["id_card", "phone"]
    kinds: list[str] = Field(default_factory=list)
    #: 被清洗的记忆 id，前端据此高亮刷新
    ids: list[str] = Field(default_factory=list)