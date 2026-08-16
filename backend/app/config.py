"""应用配置：统一从项目根 .env 读取，全部可覆盖。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- AI Provider ----------
    ai_provider: str = "openai_compatible"  # openai_compatible | fake
    ai_base_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""
    ai_chat_model: str = "deepseek-chat"
    ai_timeout_seconds: int = 180

    # ---------- Embedding（独立可配）----------
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 16

    # ---------- 存储 ----------
    database_path: str = "backend/data/app.db"
    chroma_path: str = "backend/data/chroma"
    upload_dir: str = "backend/data/uploads"

    # ---------- 分块与检索 ----------
    chunk_size: int = 800
    chunk_overlap: int = 100
    retrieval_top_k: int = 6


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
