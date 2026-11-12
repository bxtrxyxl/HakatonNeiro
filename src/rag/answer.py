"""Генерация ответа по найденным фрагментам.

Два режима:
- llm — если задан LLM_API_KEY, вызываем OpenAI-совместимый /chat/completions;
- extractive — если ключа нет или LLM недоступна, отдаём наиболее релевантный
  фрагмент дословно. Это позволяет демонстрировать систему без внешних сервисов.

Главное правило: нет данных в контексте — нет ответа. Лучше честно отказаться,
чем выдумать проходной балл.
"""

from __future__ import annotations

import re

import httpx

from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE
from src.rag.retrieve import Retriever, content_terms

SYSTEM_PROMPT = """Ты — помощник абитуриента по вузам Новосибирска.

Правила:
1. Отвечай ТОЛЬКО по фрагментам контекста ниже. Не используй внешние знания о вузах.
2. Если в контексте нет ответа, прямо скажи: «В доступных источниках нет этой информации».
3. Не выдумывай числа, баллы, сроки и названия. Каждое число должно быть в контексте.
4. Указывай источники в виде [1], [2] — номера фрагментов.
5. Отвечай кратко и по делу, на русском языке.
6. Если вопрос про год приёма, а в контексте другой год — уточни это в ответе.
"""

NO_DATA_ANSWER = (
    "В доступных источниках нет информации, чтобы ответить на этот вопрос. "
    "Попробуйте переформулировать или уточнить вуз и направление."
)

# Минимальная доля значимых слов запроса, найденных в чанке. Если ниже —
# считаем, что релевантных источников нет. Порог нужно настраивать на golden-set.
MIN_COVERAGE = 0.34


def build_context(hits: list[dict]) -> str:
    blocks = []
    for index, hit in enumerate(hits, start=1):
        title = hit.get("title") or "Без названия"
        blocks.append(
            f"[{index}] {title}\nURL: {hit.get('url', '')}\n{hit.get('text', '')}"
        )
    return "\n\n".join(blocks)


MAX_EXCERPT = 400


def _excerpts(text: str) -> list[str]:
    """Режет текст на предложения, а слишком длинные — на окна по 400 символов."""
    pieces: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= MAX_EXCERPT:
            pieces.append(sentence)
            continue
        step = 100
        for start in range(0, len(sentence), step):
            piece = sentence[start : start + MAX_EXCERPT].strip()
            if piece:
                pieces.append(piece)
    return pieces


def _extractive_answer(question: str, hits: list[dict]) -> str:
    """Без LLM: по одному лучшему окну из каждого источника, максимум два."""
    terms = content_terms(question)
    per_hit: list[tuple[int, int, str]] = []

    for index, hit in enumerate(hits, start=1):
        text = " ".join(hit.get("text", "").split())
        best_for_hit: tuple[int, str] | None = None
        for piece in _excerpts(text):
            overlap = len(terms & content_terms(piece))
            if overlap and (best_for_hit is None or overlap > best_for_hit[0]):
                best_for_hit = (overlap, piece)
        if best_for_hit is not None:
            per_hit.append((best_for_hit[0], index, best_for_hit[1]))

    if not per_hit:
        fallback = " ".join(hits[0].get("text", "").split())
        if len(fallback) > MAX_EXCERPT:
            fallback = fallback[:MAX_EXCERPT].rsplit(" ", 1)[0] + "…"
        return f"По доступному источнику: {fallback}\n\nИсточник: [1]"

    per_hit.sort(key=lambda item: (-item[0], item[1]))
    lines = [f"— …{piece}… [{index}]" for _, index, piece in per_hit[:2]]
    return "По доступным источникам:\n" + "\n".join(lines)


def _call_llm(question: str, context: str) -> str:
    payload = {
        "model": LLM_MODEL,
        "temperature": LLM_TEMPERATURE,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Контекст:\n{context}\n\nВопрос: {question}",
            },
        ],
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def answer_question(
    question: str,
    retriever: Retriever,
    top_k: int = 5,
    university: str | None = None,
) -> dict:
    hits = retriever.search(question, k=top_k, university=university)
    hits = [hit for hit in hits if retriever.coverage(question, hit) >= MIN_COVERAGE]

    if not hits:
        return {
            "answer": NO_DATA_ANSWER,
            "sources": [],
            "grounded": False,
            "mode": "no-data",
        }

    sources = [
        {
            "url": hit.get("url", ""),
            "title": hit.get("title") or None,
            "score": hit.get("score", 0.0),
        }
        for hit in hits
    ]

    if LLM_API_KEY:
        try:
            answer = _call_llm(question, build_context(hits))
            return {
                "answer": answer,
                "sources": sources,
                "grounded": True,
                "mode": "llm",
            }
        except Exception as exc:  # noqa: BLE001 — демо не должно падать из-за LLM
            print(f"[warn] LLM недоступна ({exc}), использую extractive-режим")

    return {
        "answer": _extractive_answer(question, hits),
        "sources": sources,
        "grounded": True,
        "mode": "extractive",
    }
