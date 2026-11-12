"""Нарезка pages.jsonl на чанки для поиска.

Пример:
    python -m src.rag.build_chunks
    python -m src.rag.build_chunks --max-chars 1000 --overlap 150

Каждый чанк — самостоятельный фрагмент с метаданными источника. Именно эти
метаданные потом превращаются в цитаты в ответе.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

from src.config import CHUNKS_PATH, PAGES_PATH
from src.console import setup_console


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> list[str]:
    """Режет текст по абзацам, длинные абзацы — жёстко, с перекрытием."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 1 <= max_chars:
            buffer = f"{buffer}\n{paragraph}".strip()
            continue

        if buffer:
            chunks.append(buffer)
            buffer = ""

        if len(paragraph) <= max_chars:
            buffer = paragraph
            continue

        start = 0
        step = max(max_chars - overlap, 1)
        while start < len(paragraph):
            chunks.append(paragraph[start : start + max_chars])
            start += step

    if buffer:
        chunks.append(buffer)

    return chunks


def make_chunk_id(url: str, index: int, text: str) -> str:
    digest = hashlib.sha1(f"{url}:{index}:{text[:80]}".encode("utf-8")).hexdigest()[:10]
    return f"{digest}-{index:04d}"


def build_chunks(
    pages: Iterable[dict],
    max_chars: int = 1200,
    overlap: int = 200,
) -> list[dict]:
    result: list[dict] = []
    for page in pages:
        text = (page.get("text") or "").strip()
        if not text:
            continue
        for index, piece in enumerate(chunk_text(text, max_chars, overlap)):
            result.append(
                {
                    "id": make_chunk_id(page.get("url", ""), index, piece),
                    "text": piece,
                    "url": page.get("url", ""),
                    "title": page.get("title", ""),
                    "university": page.get("university"),
                    "raw_path": page.get("raw_path"),
                }
            )
    return result


def main() -> None:
    setup_console()
    parser = argparse.ArgumentParser(description="pages.jsonl -> chunks.jsonl")
    parser.add_argument("--pages", type=Path, default=PAGES_PATH)
    parser.add_argument("--out", type=Path, default=CHUNKS_PATH)
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=200)
    args = parser.parse_args()

    if not args.pages.exists():
        raise SystemExit(
            f"Нет файла {args.pages}. Сначала: python -m src.ingestion.parse"
        )

    pages = [
        json.loads(line)
        for line in args.pages.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chunks = build_chunks(pages, args.max_chars, args.overlap)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as out:
        for chunk in chunks:
            out.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Готово: {len(chunks)} чанков из {len(pages)} страниц -> {args.out}")


if __name__ == "__main__":
    main()
