"""Оценка на golden-set.

Пример:
    python -m src.eval.run_eval
    python -m src.eval.run_eval --golden data/golden/qa.jsonl --top-k 5

Метрики намеренно простые и воспроизводимые:
- keyword_hit — все ожидаемые ключевые слова попали в ответ;
- source_hit  — среди цитат есть ожидаемый URL;
- no_answer   — система корректно отказалась отвечать (expect_no_answer).

Пустые списки ожиданий не считаются автоматическим попаданием: такие вопросы
пропускаются в соответствующей метрике (n/a), иначе оценка завышается.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from src.config import CHUNKS_PATH, GOLDEN_PATH
from src.console import setup_console
from src.rag.answer import answer_question
from src.rag.retrieve import Retriever

NORMALIZE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return NORMALIZE_RE.sub(" ", text.lower()).strip()


def keywords_found(answer: str, keywords: list[str]) -> bool | None:
    if not keywords:
        return None
    text = normalize(answer)
    return all(normalize(keyword) in text for keyword in keywords)


def normalize_url(url: str) -> str:
    value = url.strip().rstrip("/")
    return value.replace("https://www.", "https://").replace("http://www.", "http://")


def source_found(sources: list[dict], expected_urls: list[str]) -> bool | None:
    if not expected_urls:
        return None
    actual = {normalize_url(source.get("url", "")) for source in sources}
    return any(normalize_url(url) in actual for url in expected_urls)


def rate(values: list[bool | None]) -> float | None:
    defined = [value for value in values if value is not None]
    if not defined:
        return None
    return sum(defined) / len(defined)


def fmt(value: float | None) -> str:
    return f"{value:.1%}" if value is not None else "n/a"


def main() -> None:
    setup_console()
    parser = argparse.ArgumentParser(description="Оценка на golden-set")
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    parser.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if not args.golden.exists():
        raise SystemExit(f"Нет файла {args.golden}")
    if not args.chunks.exists():
        raise SystemExit(
            f"Нет индекса {args.chunks}. Сначала: python -m src.rag.build_chunks"
        )

    cases = [
        json.loads(line)
        for line in args.golden.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    retriever = Retriever.from_jsonl(args.chunks)

    rows = []
    for case in cases:
        result = answer_question(
            case["question"],
            retriever,
            top_k=args.top_k,
            university=case.get("university"),
        )
        rows.append(
            {
                "id": case.get("id", "?"),
                "keyword_hit": keywords_found(
                    result["answer"], case.get("expected_keywords", [])
                ),
                "source_hit": source_found(
                    result["sources"], case.get("expected_urls", [])
                ),
                "no_answer_hit": (
                    result["grounded"] is False
                    if case.get("expect_no_answer")
                    else None
                ),
                "mode": result["mode"],
            }
        )

    def cell(value: bool | None) -> str:
        return "n/a" if value is None else str(value)

    print(f"{'id':<8}{'keyword':<10}{'source':<10}{'no_answer':<12}mode")
    for row in rows:
        print(
            f"{row['id']:<8}{cell(row['keyword_hit']):<10}"
            f"{cell(row['source_hit']):<10}{cell(row['no_answer_hit']):<12}{row['mode']}"
        )

    print("\nИтого:")
    print(f"  вопросов:        {len(rows)}")
    print(f"  keyword_hit:     {fmt(rate([row['keyword_hit'] for row in rows]))}")
    print(f"  source_hit:      {fmt(rate([row['source_hit'] for row in rows]))}")
    print(f"  no_answer:       {fmt(rate([row['no_answer_hit'] for row in rows]))}")


if __name__ == "__main__":
    main()
