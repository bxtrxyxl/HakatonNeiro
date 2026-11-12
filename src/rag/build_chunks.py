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

from src.config import (
    ADMISSION_PATH,
    CHUNKS_PATH,
    PAGES_PATH,
    PROGRAMS_PATH,
    UNIVERSITIES_PATH,
)
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


LEVEL_RU = {
    "bachelor": "бакалавриат",
    "specialist": "специалитет",
    "master": "магистратура",
    "postgraduate": "аспирантура",
    "secondary": "среднее профессиональное",
}

FORM_RU = {
    "full_time": "очная",
    "part_time": "заочная",
    "evening": "очно-заочная",
    "remote": "заочная с применением ДОТ",
}


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _years_label(value: float | None) -> str:
    if value is None:
        return "не указан"
    if abs(value - 4.83) < 0.01:
        return "4 года 10 месяцев"
    if abs(value - 5.5) < 0.01:
        return "5 лет 6 месяцев"
    if abs(value - 2.5) < 0.01:
        return "2 года 6 месяцев"
    whole = int(round(value))
    if whole % 10 == 1 and whole % 100 != 11:
        return f"{whole} год"
    if whole % 10 in (2, 3, 4) and whole % 100 not in (12, 13, 14):
        return f"{whole} года"
    return f"{whole} лет"


def _money(value: int | None) -> str:
    if value is None:
        return "нет данных"
    return f"{value:,}".replace(",", " ")


def _date(value: str | None) -> str:
    if not value:
        return "нет данных"
    year, month, day = value.split("-")
    return f"{day}.{month}.{year}"


def _places(value: int | None, group: str | None) -> str:
    if value is None:
        if group:
            return f"нет отдельных данных (конкурсная группа {group})"
        return "нет данных"
    return str(value)


def _score(value: int | None, places: int | None) -> str:
    if value is not None:
        return str(value)
    if places == 0:
        return "нет мест"
    return "нет данных"


def _deadline(value: str | None, places: int | None) -> str:
    if value:
        return _date(value)
    if places == 0:
        return "нет мест"
    return "нет данных"


def build_fact_chunks(
    universities: list[dict],
    programs: list[dict],
    admissions: list[dict],
) -> list[dict]:
    """Превращает структурные факты в текстовые чанки для поиска."""
    universities_by_slug = {item["slug"]: item for item in universities}
    admissions_by_program = {item["program_id"]: item for item in admissions}
    result: list[dict] = []

    for university in universities:
        text = (
            f"{university.get('short_name')} ({university.get('name')}), "
            f"город {university.get('city', 'Новосибирск')}. "
            f"Официальный сайт: {university.get('site')}. "
            f"Адрес: {university.get('address') or 'нет данных'}. "
            f"Телефон: {university.get('phone') or 'нет данных'}. "
            f"Email: {university.get('email') or 'нет данных'}."
        )
        result.append(
            {
                "id": f"fact-university-{university['slug']}",
                "text": text,
                "url": university.get("site", ""),
                "title": f"{university.get('short_name')} — общая информация",
                "university": university["slug"],
                "raw_path": None,
            }
        )

    for program in programs:
        university = universities_by_slug.get(program["university_slug"], {})
        admission = admissions_by_program.get(program["id"], {})
        group = admission.get("competitive_group")
        required = admission.get("subjects_required", [])
        optional = admission.get("subjects_optional", [])
        min_scores = admission.get("min_scores", {})
        sources = admission.get("sources") or program.get("sources") or []
        url = sources[0]["url"] if sources else university.get("site", "")

        lines = [
            f"{university.get('short_name', program['university_slug'])} "
            f"({university.get('name', '')}).",
            f"Направление {program.get('code') or 'без кода'} «{program['name']}», "
            f"{LEVEL_RU.get(program['level'], program['level'])}, "
            f"{FORM_RU.get(program['form'], program['form'])} форма обучения, "
            f"срок обучения — {_years_label(program.get('duration_years'))}.",
            f"Бюджетных мест: {_places(program.get('budget_places'), group)}. "
            f"Платных мест: {_places(program.get('paid_places'), group)}. "
            f"Стоимость: {_money(program.get('tuition_rub'))} руб./год.",
            f"Проходной балл 2026: бюджет — "
            f"{_score(admission.get('passing_score_budget'), program.get('budget_places'))}, "
            f"платно — {_score(admission.get('passing_score_paid'), program.get('paid_places'))}.",
            f"Предметы: {', '.join(required) if required else 'нет данных'}. "
            f"По выбору: {', '.join(optional) if optional else 'нет'}.",
            f"Минимальные баллы: "
            f"{', '.join(f'{key} — {value}' for key, value in min_scores.items()) if min_scores else 'нет данных'}.",
            f"Сроки подачи: бюджет — "
            f"{_deadline(admission.get('application_deadline_budget'), program.get('budget_places'))}, "
            f"платно — "
            f"{_deadline(admission.get('application_deadline_paid'), program.get('paid_places'))}.",
        ]
        if admission.get("notes"):
            lines.append(admission["notes"])

        result.append(
            {
                "id": f"fact-program-{program['id']}",
                "text": " ".join(lines),
                "url": url,
                "title": (
                    f"{university.get('short_name', program['university_slug'])} — "
                    f"{program.get('code') or ''} {program['name']}"
                ).strip(),
                "university": program["university_slug"],
                "raw_path": None,
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

    universities = _load_json(UNIVERSITIES_PATH)
    programs = _load_json(PROGRAMS_PATH)
    admissions = _load_json(ADMISSION_PATH)
    fact_chunks = build_fact_chunks(universities, programs, admissions)
    chunks.extend(fact_chunks)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as out:
        for chunk in chunks:
            out.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(
        f"Готово: {len(chunks)} чанков "
        f"(страниц: {len(pages)}, фактов: {len(fact_chunks)}) -> {args.out}"
    )


if __name__ == "__main__":
    main()
