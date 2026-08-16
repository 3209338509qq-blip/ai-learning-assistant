"""设置与状态 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings as cfg
from ..database import get_db
from ..models import Document, WrongQuestion
from ..providers import get_provider
from ..schemas import SettingsOut
from ..services.vector_store import VectorStore

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    provider = get_provider()
    chunk_total = 0
    try:
        chunk_total = VectorStore().count()
    except Exception:  # noqa: BLE001
        chunk_total = 0
    return SettingsOut(
        ai_provider=provider.name,
        chat_model=cfg.ai_chat_model,
        embedding_model=cfg.embedding_model,
        chat_configured=provider.chat_configured(),
        embedding_configured=provider.embedding_configured(),
        document_count=db.query(func.count(Document.id)).scalar() or 0,
        chunk_count=chunk_total,
        wrong_question_count=db.query(func.count(WrongQuestion.id)).scalar() or 0,
    )
