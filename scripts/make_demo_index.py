"""Демо-индекс из встроенной страницы — чтобы проверить UI и API без сети.

Запуск:
    python scripts/make_demo_index.py
    uvicorn src.api.main:app --reload

Файл data/chunks/chunks.jsonl в git не попадает. Это только для локальной
проверки: реальные данные собираются через src.ingestion.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import CHUNKS_PATH  # noqa: E402
from src.console import setup_console  # noqa: E402
from src.ingestion.parse import extract  # noqa: E402
from src.rag.build_chunks import build_chunks  # noqa: E402


def main() -> None:
    setup_console()

    fixture = ROOT / "tests" / "fixtures" / "nsu_demo.html"
    page = extract(fixture.read_bytes(), "https://www.nsu.ru/demo")
    page["university"] = "nsu"

    chunks = build_chunks([page])
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CHUNKS_PATH.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Демо-индекс: {len(chunks)} чанков -> {CHUNKS_PATH}")
    print("Запустите: uvicorn src.api.main:app --reload")


if __name__ == "__main__":
    main()
