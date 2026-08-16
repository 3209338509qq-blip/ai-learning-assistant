"""Pydantic 请求/响应模型。"""
import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------- 资料 ----------

class ChapterOut(BaseModel):
    id: int
    title: str
    level: int
    path: str
    page: int

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: int
    original_name: str
    file_type: str
    size_bytes: int
    status: str
    error: str
    chunk_count: int
    page_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentOut):
    chapters: list[ChapterOut] = []


# ---------- 对话 ----------

class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: list[dict[str, Any]] = []
    created_at: datetime

    @field_validator("sources", mode="before")
    @classmethod
    def parse_sources(cls, v):
        """数据库存 JSON 字符串，输出时解析为列表。"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v or []

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    sources: list[dict[str, Any]] = []
    has_evidence: bool


class ChatHistoryOut(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut] = []


# ---------- 总结 ----------

class SummaryRequest(BaseModel):
    document_id: int
    chapter_path: str = ""


class SummaryOut(BaseModel):
    id: int
    document_id: int
    chapter_path: str
    title: str
    core_points: str
    key_concepts: str
    pitfalls: str
    memory_items: str
    short_summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- 出题与做题 ----------

class QuizRequest(BaseModel):
    document_id: int
    chapter_path: str = ""
    count: int = Field(default=5, ge=1, le=30)
    types: list[str] = Field(default=["choice", "true_false", "short_answer"])

    @field_validator("types")
    @classmethod
    def validate_types(cls, v):
        allowed = {"choice", "true_false", "short_answer"}
        for t in v:
            if t not in allowed:
                raise ValueError(f"不支持的题型: {t}")
        return v or list(allowed)


class QuestionOut(BaseModel):
    id: int
    qtype: str
    question: str
    options: list[str] = []
    answer: str
    explanation: str
    difficulty: str
    knowledge_point: str
    chapter: str
    order_index: int

    @field_validator("options", mode="before")
    @classmethod
    def parse_options(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v or []

    model_config = {"from_attributes": True}


class QuizSetOut(BaseModel):
    id: int
    document_id: int
    chapter_path: str
    title: str
    created_at: datetime
    questions: list[QuestionOut] = []

    model_config = {"from_attributes": True}


class AnswerSubmit(BaseModel):
    question_id: int
    user_answer: str = ""
    self_evaluated: Optional[bool] = None  # 简答题：True=自评答对，False=答错，None=未自评


class QuizSubmitRequest(BaseModel):
    answers: list[AnswerSubmit]


class AnswerResultOut(BaseModel):
    question_id: int
    user_answer: str
    is_correct: bool
    correct_answer: str
    explanation: str


class QuizResultOut(BaseModel):
    attempt_id: int
    correct_count: int
    total_count: int
    score: float  # 0-100
    wrong_question_count: int
    results: list[AnswerResultOut]


# ---------- 错题本 ----------

class WrongQuestionOut(BaseModel):
    id: int
    qtype: str
    question: str
    options: list[str] = []
    correct_answer: str
    explanation: str
    difficulty: str
    knowledge_point: str
    chapter: str
    my_answer: str
    wrong_count: int
    last_wrong_at: datetime
    created_at: datetime

    @field_validator("options", mode="before")
    @classmethod
    def parse_options(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v or []

    model_config = {"from_attributes": True}


class WrongRedoRequest(BaseModel):
    is_correct: bool  # 重新练习时用户自评是否答对


# ---------- 设置 ----------

class SettingsOut(BaseModel):
    ai_provider: str
    chat_model: str
    embedding_model: str
    chat_configured: bool
    embedding_configured: bool
    document_count: int
    chunk_count: int
    wrong_question_count: int