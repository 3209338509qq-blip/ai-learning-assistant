"""自动出题与做题判分 API。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import (
    AnswerRecord,
    Document,
    Question,
    QuizAttempt,
    QuizSet,
    WrongQuestion,
)
from ..schemas import QuizRequest, QuizResultOut, QuizSetOut, QuizSubmitRequest
from ..services.ai_service import AIService
from ..services.parsers import parse_document

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


def _normalize_answer(v: str) -> str:
    v = v.strip().upper()
    mapping = {"对": "正确", "√": "正确", "T": "正确", "TRUE": "正确", "错": "错误", "×": "错误", "F": "错误", "FALSE": "错误"}
    if v in mapping:
        return mapping[v]
    return v


@router.post("/generate", response_model=QuizSetOut)
def generate_quiz(req: QuizRequest, db: Session = Depends(get_db)):
    doc = db.get(Document, req.document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    if doc.status != "ready":
        raise HTTPException(status_code=400, detail=f"资料未处理完成（当前状态: {doc.status}）")

    upload_path = Path(settings.upload_dir) / doc.stored_name
    parsed = parse_document(str(upload_path), doc.file_type)
    service = AIService()
    items = service.generate_quiz(
        parsed, doc.original_name, req.chapter_path, req.count, req.types
    )
    if not items:
        raise HTTPException(status_code=502, detail="出题失败：AI 返回内容无法解析，请重试")

    scope = req.chapter_path or "全文"
    quiz_set = QuizSet(
        document_id=doc.id,
        chapter_path=req.chapter_path,
        title=f"{doc.original_name} · {scope}",
    )
    db.add(quiz_set)
    db.flush()
    for i, item in enumerate(items):
        db.add(
            Question(
                quiz_set_id=quiz_set.id,
                qtype=item["qtype"],
                question=item["question"],
                options=json.dumps(item["options"], ensure_ascii=False),
                answer=item["answer"],
                explanation=item["explanation"],
                difficulty=item["difficulty"],
                knowledge_point=item["knowledge_point"],
                chapter=item["chapter"],
                order_index=i,
            )
        )
    db.commit()
    db.refresh(quiz_set)
    return quiz_set


@router.get("", response_model=list[QuizSetOut])
def list_quiz_sets(db: Session = Depends(get_db)):
    return db.query(QuizSet).order_by(QuizSet.created_at.desc()).all()


@router.get("/{quiz_id}", response_model=QuizSetOut)
def get_quiz_set(quiz_id: int, db: Session = Depends(get_db)):
    qs = db.get(QuizSet, quiz_id)
    if qs is None:
        raise HTTPException(status_code=404, detail="题组不存在")
    return qs


@router.delete("/{quiz_id}")
def delete_quiz_set(quiz_id: int, db: Session = Depends(get_db)):
    qs = db.get(QuizSet, quiz_id)
    if qs is None:
        raise HTTPException(status_code=404, detail="题组不存在")
    db.delete(qs)
    db.commit()
    return {"ok": True}


@router.post("/{quiz_id}/submit", response_model=QuizResultOut)
def submit_quiz(quiz_id: int, req: QuizSubmitRequest, db: Session = Depends(get_db)):
    qs = db.get(QuizSet, quiz_id)
    if qs is None:
        raise HTTPException(status_code=404, detail="题组不存在")

    questions = {q.id: q for q in qs.questions}
    attempt = QuizAttempt(quiz_set_id=quiz_id, total_count=len(questions))
    db.add(attempt)
    db.flush()

    results = []
    wrong_count = 0
    for submit in req.answers:
        q = questions.get(submit.question_id)
        if q is None:
            continue
        if q.qtype == "short_answer":
            if submit.self_evaluated is None:
                is_correct = None
            else:
                is_correct = bool(submit.self_evaluated)
        else:
            is_correct = _normalize_answer(submit.user_answer) == _normalize_answer(q.answer)

        db.add(
            AnswerRecord(
                attempt_id=attempt.id,
                question_id=q.id,
                user_answer=submit.user_answer,
                is_correct=is_correct,
                self_evaluated=bool(submit.self_evaluated),
            )
        )
        results.append(
            {
                "question_id": q.id,
                "user_answer": submit.user_answer,
                "is_correct": bool(is_correct),
                "correct_answer": q.answer,
                "explanation": q.explanation,
            }
        )
        if is_correct is False:
            wrong_count += 1
            _save_wrong_question(db, q, submit.user_answer)

    attempt.correct_count = sum(1 for r in results if r["is_correct"])
    attempt.finished_at = datetime.now(timezone.utc)
    db.commit()

    score = round(attempt.correct_count / attempt.total_count * 100, 1) if attempt.total_count else 0
    return QuizResultOut(
        attempt_id=attempt.id,
        correct_count=attempt.correct_count,
        total_count=attempt.total_count,
        score=score,
        wrong_question_count=wrong_count,
        results=results,
    )


def _save_wrong_question(db: Session, q: Question, my_answer: str) -> None:
    """错题入库（重复错误则累加次数）。"""
    existing = (
        db.query(WrongQuestion)
        .filter(WrongQuestion.source_question_id == q.id)
        .first()
    )
    if existing is not None:
        existing.wrong_count += 1
        existing.my_answer = my_answer
        existing.last_wrong_at = datetime.now(timezone.utc)
        return
    reason = ""
    if q.qtype == "choice":
        reason = f"选择了「{my_answer}」，正确答案是「{q.answer}」"
    elif q.qtype == "true_false":
        reason = f"判断为「{my_answer}」，正确答案是「{q.answer}」"
    db.add(
        WrongQuestion(
            document_id=q.quiz_set.document_id if q.quiz_set else None,
            source_quiz_set_id=q.quiz_set_id,
            source_question_id=q.id,
            qtype=q.qtype,
            question=q.question,
            options=q.options,
            correct_answer=q.answer,
            explanation=q.explanation,
            difficulty=q.difficulty,
            knowledge_point=q.knowledge_point,
            chapter=q.chapter,
            my_answer=my_answer,
            wrong_count=1,
        )
    )
