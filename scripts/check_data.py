"""Проверка целостности данных.

Запуск:
    python scripts/check_data.py

Проверяет:
- соответствие JSON Pydantic-схемам;
- уникальность slug вузов и id программ;
- ссылочную целостность program -> university, admission -> program;
- адекватность года приёмной кампании.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import ADMISSION_PATH, PROGRAMS_PATH, UNIVERSITIES_PATH  # noqa: E402
from src.console import setup_console  # noqa: E402
from src.schemas import Admission, Program, University  # noqa: E402


def load(path: Path) -> list[dict]:
    if not path.exists():
        print(f"[warn] нет файла {path}")
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    setup_console()
    errors: list[str] = []

    universities = load(UNIVERSITIES_PATH)
    programs = load(PROGRAMS_PATH)
    admissions = load(ADMISSION_PATH)

    parsed_universities: list[University] = []
    for item in universities:
        try:
            parsed_universities.append(University.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"universities: {item.get('slug', '?')}: {exc}")

    parsed_programs: list[Program] = []
    for item in programs:
        try:
            parsed_programs.append(Program.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"programs: {item.get('id', '?')}: {exc}")

    parsed_admissions: list[Admission] = []
    for item in admissions:
        try:
            parsed_admissions.append(Admission.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"admission: {item.get('id', '?')}: {exc}")

    slugs = [item.slug for item in parsed_universities]
    if len(slugs) != len(set(slugs)):
        errors.append("universities: повторяющиеся slug")

    program_ids = [item.id for item in parsed_programs]
    if len(program_ids) != len(set(program_ids)):
        errors.append("programs: повторяющиеся id")

    slug_set = set(slugs)
    for program in parsed_programs:
        if program.university_slug not in slug_set:
            errors.append(
                f"programs: {program.id} ссылается на неизвестный вуз {program.university_slug}"
            )

    program_id_set = set(program_ids)
    for admission in parsed_admissions:
        if admission.program_id not in program_id_set:
            errors.append(
                f"admission: {admission.id} ссылается на неизвестную программу {admission.program_id}"
            )
        if not 2020 <= admission.year <= 2035:
            errors.append(f"admission: {admission.id}: подозрительный год {admission.year}")

    current_year = datetime.now().year
    confirmed = sum(1 for item in parsed_universities if item.confirmed)

    print("Данные:")
    print(f"  вузов:      {len(parsed_universities)} (подтверждено: {confirmed})")
    print(f"  программ:   {len(parsed_programs)}")
    print(f"  приёмов:    {len(parsed_admissions)}")
    print(f"  текущий год: {current_year}")

    if errors:
        print("\nОшибки:")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)

    print("\nOK: ошибок не найдено")


if __name__ == "__main__":
    main()
