"""HTTP API чат-помощника.

Запуск:
    uvicorn src.api.main:app --reload

Эндпоинты:
    GET  /                  — минимальный чат (web/index.html)
    GET  /health            — статус индекса
    GET  /api/universities  — справочник вузов
    POST /api/chat          — вопрос -> ответ + цитаты
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.config import CHUNKS_PATH, UNIVERSITIES_PATH, WEB_DIR
from src.rag.answer import answer_question
from src.rag.retrieve import Retriever

app = FastAPI(
    title="Абитуриент-бот: вузы Новосибирска",
    version="0.1.0",
    description="RAG-чат по официальным источникам вузов. Ответы сопровождаются ссылками.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    university: str | None = Field(default=None, description="slug вуза, например nsu")


class SourceOut(BaseModel):
    url: str
    title: str | None = None
    score: float = 0.0


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    grounded: bool
    mode: str


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    if not CHUNKS_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Индекс не собран. Выполните: python -m src.ingestion.parse && "
                "python -m src.rag.build_chunks"
            ),
        )
    return Retriever.from_jsonl(CHUNKS_PATH)


def load_universities() -> list[dict]:
    if not UNIVERSITIES_PATH.exists():
        return []
    return json.loads(UNIVERSITIES_PATH.read_text(encoding="utf-8"))


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    page = WEB_DIR / "index.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="web/index.html не найден")
    return FileResponse(page)


@app.get("/health")
def health() -> dict:
    chunks = 0
    if CHUNKS_PATH.exists():
        with CHUNKS_PATH.open(encoding="utf-8") as handle:
            chunks = sum(1 for line in handle if line.strip())
    return {
        "status": "ok",
        "chunks": chunks,
        "index_ready": chunks > 0,
        "universities": len(load_universities()),
    }


@app.get("/api/universities")
def universities() -> list[dict]:
    return load_universities()


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    retriever = get_retriever()
    result = answer_question(
        question=request.question,
        retriever=retriever,
        top_k=request.top_k,
        university=request.university,
    )
    return ChatResponse(**result)
