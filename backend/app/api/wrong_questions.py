"""错题本 API。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import WrongQuestion
from ..schemas import WrongQuestionOut, WrongRedoRequest

router = APIRouter(prefix="/api/wrong-questions", tags=["wrong-questions"])


@router.get("", response_model=list[WrongQuestionOut])
def list_wrong_questions(db: Session = Depends(get_db)):
    return db.query(WrongQuestion).order_by(WrongQuestion.last_wrong_at.desc()).all()


@router.delete("/{wq_id}")
def delete_wrong_question(wq_id: int, db: Session = Depends(get_db)):
    wq = db.get(WrongQuestion, wq_id)
    if wq is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    db.delete(wq)
    db.commit()
    return {"ok": True}


@router.post("/{wq_id}/redo", response_model=WrongQuestionOut)
def redo_wrong_question(wq_id: int, req: WrongRedoRequest, db: Session = Depends(get_db)):
    """重新练习：答对则移除，答错则错误次数 +1。"""
    wq = db.get(WrongQuestion, wq_id)
    if wq is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    if req.is_correct:
        db.delete(wq)
        db.commit()
        raise HTTPException(status_code=200, detail="")
    wq.wrong_count += 1
    wq.last_wrong_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(wq)
    return wq
