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