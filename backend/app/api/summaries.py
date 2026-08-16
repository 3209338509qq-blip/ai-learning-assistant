"""自动总结 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Document, Summary
from ..schemas import SummaryOut, SummaryRequest
from ..services.ai_service import AIService
from ..services.parsers import parse_document
from ..config import settings
from pathlib import Path

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


@router.post("/generate", response_model=SummaryOut)
def generate_summary(req: SummaryRequest, db: Session = Depends(get_db)):
    doc = db.get(Document, req.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    if doc.status != "ready":
        raise HTTPException(status_code=400, detail=f"资料未处理完成（当前状态: {doc.status}）")

    upload_path = Path(settings.upload_dir) / doc.stored_name
    parsed = parse_document(str(upload_path), doc.file_type)
    service = AIService()
    data = service.generate_summary(parsed, doc.original_name, req.chapter_path)

    title = req.chapter_path or "全文"
    summary = Summary(
        document_id=doc.id,
        chapter_path=req.chapter_path,
        title=f"{doc.original_name} · {title}",
        **data,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


@router.get("/document/{doc_id}", response_model=list[SummaryOut])
def list_summaries(doc_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Summary)
        .filter(Summary.document_id == doc_id)
        .order_by(Summary.created_at.desc())
        .all()
    )


@router.get("", response_model=list[SummaryOut])
def list_all_summaries(db: Session = Depends(get_db)):
    return db.query(Summary).order_by(Summary.created_at.desc()).all()


@router.delete("/{summary_id}")
def delete_summary(summary_id: int, db: Session = Depends(get_db)):
    s = db.get(Summary, summary_id)
    if s is None:
        raise HTTPException(status_code=404, detail="总结不存在")
    db.delete(s)
    db.commit()
    return {"ok": True}
