"""全局配置：从环境变量 / .env 读取，禁止在代码里硬编码密钥。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根（apps/api）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 运行环境 ----
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # ---- 模型 Provider ----
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    dashscope_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    allow_user_provided_keys: bool = True

    default_chat_model: str = "deepseek-chat"
    default_agent_model: str = "deepseek-chat"
    default_embedding_model: str = "bge-m3"
    default_rerank_model: str = "bge-reranker-v2-m3"
    default_asr_model: str = "whisper-1"

    # ---- 存储 ----
    vector_store: str = "chroma"
    chroma_persist_dir: str = "./data/chroma"
    database_url: str = "sqlite:///./data/sqlite/app.db"
    storage_backend: str = "local"
    local_storage_dir: str = "./data/uploads"

    # ---- 实时 / MCP ----
    realtime_backend: str = "sse"

    # ---- 音乐 ----
    music_api_base_url: str = "http://localhost:3001"

    # ---- 安全 ----
    enable_safety_filter: bool = True
    memory_encryption_key: str = ""

    # ---- RAG 记忆 ----
    #: 向量化实现：hashing / sentence-transformers / cloud，留空则自动按优先级探测
    memory_embedding_provider: str = ""
    #: 记忆召回数量（送入重排前的候选数）
    memory_recall_k: int = 8
    #: 重排后最终注入对话的记忆条数
    memory_top_n: int = 3
    #: 去重阈值：新记忆与已有记忆相似度超过它则视为重复
    memory_dedup_threshold: float = 0.86
    #: 是否加密记忆正文
    memory_encrypt: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
