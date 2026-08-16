"""AI 对话 API：RAG 问答，保留会话与消息历史。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Conversation, Message, utcnow
from ..schemas import ChatHistoryOut, ChatRequest, ChatResponse, ConversationOut, MessageOut
from ..services.ai_service import AIService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/stream")
def chat_stream(req: ChatRequest, db: Session = Depends(get_db)):
    """SSE 流式对话：data: {"type":"delta"|"done"|"error", ...}"""
    service = AIService()
    conv: Conversation | None = None
    if req.conversation_id:
        conv = db.get(Conversation, req.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="会话不存在")

    # 先持久化用户消息
    if conv is None:
        conv = Conversation(title=req.message.strip()[:30])
        db.add(conv)
        db.flush()
    user_msg = Message(conversation_id=conv.id, role="user", content=req.message)
    db.add(user_msg)
    conv.updated_at = utcnow()
    db.commit()

    history = []
    if conv is not None:
        recent = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id.desc())
            .limit(10)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in reversed(recent)]

    def event_gen():
        full = ""
        try:
            stream, sources, has_evidence = service.stream_chat_with_rag(req.message, history)
            for piece in stream:
                full += piece
                yield f"data: {json.dumps({'type': 'delta', 'content': piece}, ensure_ascii=False)}\n\n"
            # 流结束后持久化完整回答
            ai_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=full,
                sources=json.dumps(sources, ensure_ascii=False),
            )
            db.add(ai_msg)
            conv.updated_at = utcnow()
            db.commit()
            yield f"data: {json.dumps({'type': 'done', 'sources': sources, 'has_evidence': has_evidence}, ensure_ascii=False)}\n\n"
        except Exception as e:  # noqa: BLE001 - 流式异常通知前端
            db.rollback()
            if full:
                db.add(
                    Message(
                        conversation_id=conv.id,
                        role="assistant",
                        content=full + "\n\n（生成中断）",
                        sources="[]",
                    )
                )
                db.commit()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)[:300]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


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

    # 先持久化用户消息：即使 AI 调用失败，用户输入也不丢失
    if conv is None:
        title = req.message.strip()[:30]
        conv = Conversation(title=title)
        db.add(conv)
        db.flush()
    user_msg = Message(conversation_id=conv.id, role="user", content=req.message)
    db.add(user_msg)
    conv.updated_at = utcnow()
    db.commit()

    history = []
    if conv is not None:
        recent = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.id.desc())
            .limit(10)
            .all()
        )
        history = [{"role": m.role, "content": m.content} for m in reversed(recent)]

    try:
        answer, sources, has_evidence = service.chat_with_rag(req.message, history)
    except Exception as e:  # noqa: BLE001 - AI 故障返回 502，消息已保存
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {str(e)[:300]}") from e

    ai_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        sources=json.dumps(sources, ensure_ascii=False),
    )
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