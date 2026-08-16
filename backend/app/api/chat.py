"""AI 对话 API：RAG 问答，保留会话与消息历史。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Conversation, Message, utcnow
from ..schemas import ChatHistoryOut, ChatRequest, ChatResponse, ConversationOut, MessageOut
from ..services.ai_service import AIService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    return db.query(Conversation).order_by(Conversation.updated_at.desc()).all()


@router.get("/conversations/{conv_id}", response_model=ChatHistoryOut)
def get_conversation(conv_id: int, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"conversation": conv, "messages": conv.messages}


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    service = AIService()
    conv: Conversation | None = None
    if req.conversation_id:
        conv = db.get(Conversation, req.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="会话不存在")

    history = []
    if conv is not None:
        for m in conv.messages[-10:]:
            history.append({"role": m.role, "content": m.content})

    answer, sources, has_evidence = service.chat_with_rag(req.message, history)

    if conv is None:
        title = req.message.strip()[:30]
        conv = Conversation(title=title)
        db.add(conv)
        db.flush()

    user_msg = Message(conversation_id=conv.id, role="user", content=req.message)
    ai_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources, ensure_ascii=False),
    )
    db.add(user_msg)
    db.add(ai_msg)
    conv.updated_at = utcnow()
    db.commit()
    db.refresh(ai_msg)
    return ChatResponse(
        conversation_id=conv.id,
        message_id=ai_msg.id,
        answer=answer,
        sources=sources,
        has_evidence=has_evidence,
    )


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(conv)
    db.commit()
    return {"ok": True}
