"""pytest 全局配置：隔离数据目录 + FakeProvider 注入。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def app_env(tmp_path, monkeypatch):
    """将数据库/向量库/上传目录重定向到临时目录，并启用可注入的 FakeProvider。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.database as database
    from app.config import settings as cfg
    from app.database import Base
    from app.providers.fake import FakeProvider
    from app.services import ai_service

    cfg.database_path = str(tmp_path / "test.db")
    cfg.chroma_path = str(tmp_path / "chroma")
    cfg.upload_dir = str(tmp_path / "uploads")
    cfg.ai_provider = "fake"
    (tmp_path / "uploads").mkdir(exist_ok=True)

    engine = create_engine(
        f"sqlite:///{cfg.database_path}", connect_args={"check_same_thread": False}
    )
    database.engine = engine
    database.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    provider = FakeProvider()
    # 替换各模块引用的 get_provider（get_provider 有 lru_cache，测试内直接覆写）
    monkeypatch.setattr(ai_service, "get_provider", lambda: provider)
    import app.providers as providers

    monkeypatch.setattr(providers, "get_provider", lambda: provider)

    def set_reply(text: str):
        provider._reply_fn = lambda messages: text

    yield {"tmp_path": tmp_path, "set_reply": set_reply, "provider": provider}


@pytest.fixture()
def client(app_env):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
