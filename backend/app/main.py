"""FastAPI 应用入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, documents, quizzes, settings as settings_api, summaries, wrong_questions
from .database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Learning Assistant API",
    description="个人 AI 学习助手：资料解析、RAG 问答、自动总结、自动出题、错题本",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    documents.router,
    chat.router,
    summaries.router,
    quizzes.router,
    wrong_questions.router,
    settings_api.router,
):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}
