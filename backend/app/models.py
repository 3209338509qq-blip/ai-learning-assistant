"""SQLAlchemy ORM 模型。"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    """上传的学习资料。"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    original_name = Column(String(512), nullable=False)
    stored_name = Column(String(512), nullable=False)
    file_type = Column(String(16), nullable=False)  # pdf/docx/md/txt
    size_bytes = Column(Integer, default=0)
    subject = Column(String(64), default="")  # 学科分类，空=未分类
    status = Column(String(16), default="pending")  # pending/processing/ready/failed
    error = Column(Text, default="")
    chunk_count = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    chapters = relationship(
        "Chapter", back_populates="document", cascade="all, delete-orphan",
        order_by="Chapter.order_index",
    )
    summaries = relationship("Summary", back_populates="document", cascade="all, delete-orphan")
    quiz_sets = relationship("QuizSet", back_populates="document", cascade="all, delete-orphan")


class Chapter(Base):
    """文档章节信息（文件名/章节路径/页码溯源）。"""
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(512), nullable=False)
    level = Column(Integer, default=1)
    path = Column(String(1024), default="")  # 如 "第1章 Python基础 / 1.2 语法"
    page = Column(Integer, default=0)
    order_index = Column(Integer, default=0)

    document = relationship("Document", back_populates="chapters")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    title = Column(String(512), default="新对话")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    sources = Column(Text, default="[]")  # JSON：引用来源 [{document, chapter, page, excerpt}]
    created_at = Column(DateTime, default=utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document = relationship("Document", back_populates="summaries")
    chapter_path = Column(String(1024), default="")  # 空字符串 = 整篇文档
    title = Column(String(512), default="")
    core_points = Column(Text, default="")    # 核心知识点
    key_concepts = Column(Text, default="")   # 重点概念
    pitfalls = Column(Text, default="")       # 易错点
    memory_items = Column(Text, default="")   # 需要记忆的内容
    short_summary = Column(Text, default="")  # 简短总结
    created_at = Column(DateTime, default=utcnow)


class QuizSet(Base):
    __tablename__ = "quiz_sets"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    document = relationship("Document", back_populates="quiz_sets")
    attempts = relationship("QuizAttempt", back_populates="quiz_set", cascade="all, delete-orphan")
    chapter_path = Column(String(1024), default="")
    title = Column(String(512), default="")
    created_at = Column(DateTime, default=utcnow)

    questions = relationship(
        "Question", back_populates="quiz_set", cascade="all, delete-orphan",
        order_by="Question.order_index",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    quiz_set_id = Column(Integer, ForeignKey("quiz_sets.id", ondelete="CASCADE"), nullable=False)
    qtype = Column(String(16), nullable=False)  # choice / true_false / short_answer
    question = Column(Text, nullable=False)
    options = Column(Text, default="[]")  # JSON 数组
    answer = Column(Text, nullable=False)
    explanation = Column(Text, default="")
    difficulty = Column(String(16), default="medium")  # easy / medium / hard
    knowledge_point = Column(Text, default="")
    chapter = Column(String(1024), default="")
    order_index = Column(Integer, default=0)

    quiz_set = relationship("QuizSet", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True)
    quiz_set_id = Column(Integer, ForeignKey("quiz_sets.id", ondelete="CASCADE"), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    correct_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

    answers = relationship(
        "AnswerRecord", back_populates="attempt", cascade="all, delete-orphan",
    )
    quiz_set = relationship("QuizSet", back_populates="attempts")


class AnswerRecord(Base):
    __tablename__ = "answer_records"

    id = Column(Integer, primary_key=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    user_answer = Column(Text, default="")
    is_correct = Column(Boolean, nullable=True)  # None=未判（简答未自评）
    self_evaluated = Column(Boolean, default=False)  # 简答题自评标记
    answered_at = Column(DateTime, default=utcnow)

    attempt = relationship("QuizAttempt", back_populates="answers")


class WrongQuestion(Base):
    """错题本：冗余保存题目快照，独立于题组生命周期。"""
    __tablename__ = "wrong_questions"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, nullable=True)
    source_quiz_set_id = Column(Integer, nullable=True)
    source_question_id = Column(Integer, nullable=True)
    qtype = Column(String(16), nullable=False)
    question = Column(Text, nullable=False)
    options = Column(Text, default="[]")
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, default="")
    difficulty = Column(String(16), default="medium")
    knowledge_point = Column(Text, default="")
    chapter = Column(String(1024), default="")
    my_answer = Column(Text, default="")
    wrong_count = Column(Integer, default=1)
    last_wrong_at = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)