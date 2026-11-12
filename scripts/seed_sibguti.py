"""Заполнение базы по СибГУТИ (sibsutis) из официальных документов приёма-2026.

Источники:
- Итоги приёма 2026 (места и проходные баллы)
- Приложение 1 (перечень специальностей и сроки обучения)
- Приложение 2 (вступительные испытания)
- Минимальные баллы 2026
- Приложение 5 (сроки приёма)
- Стоимость обучения 2026/2027

Запуск:
    python scripts/seed_sibguti.py

Скрипт перезаписывает data/processed/programs.json и admission.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import ADMISSION_PATH, PROGRAMS_PATH  # noqa: E402
from src.console import setup_console  # noqa: E402

PARSED_AT = "2026-11-12T12:00:00"
UNIVERSITY = "sibsutis"

URL_RESULTS = "https://sibsutis.ru/applicants/documents/Прием%202026/Итоги%20приема%202026.pdf"
URL_EXAMS = (
    "https://sibsutis.ru/upload/iblock/710/"
    "Пр 2 Вступительные испытания и минимальные баллы в СибГУТИ и филиалы.pdf"
)
URL_MIN = (
    "https://sibsutis.ru/applicants/documents/Прием%202026/"
    "Правила%20приёма/Минимальные%20баллы%202026%20на%20сайт.pdf"
)
URL_DATES = (
    "https://sibsutis.ru/upload/iblock/147/"
    "Приложение 5 Сроки проведения приема и процедуры зачисления.pdf"
)
URL_TUITION = "https://sibsutis.ru/abitur/platnoe-obuchenie/"
URL_DURATION = (
    "https://sibsutis.ru/upload/iblock/211/"
    "Приложение 1 Перечень специальностей для поступления в СибГУТИ и филиалы.pdf"
)

BACHELOR_BUDGET_DEADLINE = "2026-07-25"
PAID_DEADLINE = "2026-08-20"
MASTER_DEADLINE = "2026-08-10"


def source(url: str, title: str, valid_from: str | None = None) -> dict:
    return {
        "url": url,
        "title": title,
        "parsed_at": PARSED_AT,
        "valid_from": valid_from,
        "valid_to": None,
        "checksum": None,
    }


SRC_RESULTS = source(URL_RESULTS, "Итоги приёма 2026: места и проходные баллы", "2026-08-07")
SRC_EXAMS = source(URL_EXAMS, "Приложение 2: вступительные испытания", "2026-01-19")
SRC_MIN = source(URL_MIN, "Минимальные баллы 2026", "2026-01-19")
SRC_DATES = source(URL_DATES, "Приложение 5: сроки приёма", "2026-01-19")
SRC_TUITION = source(URL_TUITION, "Стоимость обучения 2026/2027")
SRC_DURATION = source(
    URL_DURATION,
    "Приложение 1: перечень специальностей и сроки обучения",
    "2026-01-19",
)

PROGRAM_SOURCES = [SRC_RESULTS, SRC_EXAMS, SRC_DURATION, SRC_TUITION]
ADMISSION_SOURCES = [SRC_RESULTS, SRC_EXAMS, SRC_MIN, SRC_DATES]

SUBJECT_SETS = {
    "math_inf_phys": (
        ["Математика", "Русский язык"],
        ["Информатика", "Физика"],
    ),
    "phys_inf_math": (
        ["Физика", "Русский язык"],
        ["Информатика", "Математика"],
    ),
    "social": (
        ["Обществознание", "Русский язык"],
        ["История", "Информатика", "Иностранный язык (английский)"],
    ),
    "master_math": (["Математика и информационные технологии"], []),
    "master_security": (["Безопасность информационных и телекоммуникационных систем"], []),
    "master_infocom": (["Инфокоммуникационные технологии и системы связи"], []),
    "master_marketing": (["Маркетинг, реклама и связи с общественностью"], []),
    "master_security_infocom": (["Безопасность инфокоммуникационных систем и сетей"], []),
}

MIN_SCORES = {
    "Математика": 27,
    "Русский язык": 36,
    "Информатика": 40,
    "Физика": 36,
    "Обществознание": 44,
    "История": 34,
    "Иностранный язык (английский)": 34,
    "Математика и информационные технологии": 35,
    "Безопасность информационных и телекоммуникационных систем": 35,
    "Инфокоммуникационные технологии и системы связи": 35,
    "Маркетинг, реклама и связи с общественностью": 35,
    "Безопасность инфокоммуникационных систем и сетей": 35,
}

GROUP_NOTE = (
    "Входит в многопрофильный конкурс 11.03.00: общие бюджетные (112) и платные (8) "
    "места, проходной балл 171."
)
GROUP_HEAD_NOTE = "Многопрофильный конкурс объединяет направления 11.03.01, 11.03.03 и 11.03.04."

PROGRAMS = [
    # Бакалавриат, очная форма
    dict(
        id="sibguti-02.03.02-bachelor-full",
        code="02.03.02",
        name="Фундаментальная информатика и информационные технологии",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=50,
        paid=10,
        tuition=200_000,
        subjects="math_inf_phys",
        pass_b=233,
        pass_p=128,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    dict(
        id="sibguti-09.03.01-bachelor-full",
        code="09.03.01",
        name="Информатика и вычислительная техника",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=258,
        paid=101,
        tuition=200_000,
        subjects="math_inf_phys",
        pass_b=214,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    dict(
        id="sibguti-09.03.02-bachelor-full",
        code="09.03.02",
        name="Информационные системы и технологии",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=65,
        paid=85,
        tuition=200_000,
        subjects="math_inf_phys",
        pass_b=251,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    dict(
        id="sibguti-09.03.03-bachelor-full",
        code="09.03.03",
        name="Прикладная информатика",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=50,
        paid=25,
        tuition=200_000,
        subjects="math_inf_phys",
        pass_b=229,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    dict(
        id="sibguti-10.03.01-bachelor-full",
        code="10.03.01",
        name="Информационная безопасность",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=38,
        paid=52,
        tuition=200_000,
        subjects="math_inf_phys",
        pass_b=235,
        pass_p=141,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    dict(
        id="sibguti-11.03.01-bachelor-full",
        code="11.03.01",
        name="Радиотехника",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=None,
        paid=None,
        tuition=200_000,
        subjects="phys_inf_math",
        pass_b=171,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
        group="11.03.00",
        notes=GROUP_NOTE,
    ),
    dict(
        id="sibguti-11.03.02-bachelor-full",
        code="11.03.02",
        name="Инфокоммуникационные технологии и системы связи",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=196,
        paid=44,
        tuition=200_000,
        subjects="math_inf_phys",
        pass_b=185,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    dict(
        id="sibguti-11.03.03-bachelor-full",
        code="11.03.03",
        name="Конструирование и технология электронных средств",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=None,
        paid=None,
        tuition=200_000,
        subjects="phys_inf_math",
        pass_b=171,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
        group="11.03.00",
        notes=GROUP_NOTE,
    ),
    dict(
        id="sibguti-11.03.04-bachelor-full",
        code="11.03.04",
        name="Электроника и наноэлектроника",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=None,
        paid=None,
        tuition=200_000,
        subjects="phys_inf_math",
        pass_b=171,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
        group="11.03.00",
        notes=GROUP_NOTE,
    ),
    dict(
        id="sibguti-11.03.00-group-bachelor-full",
        code="11.03.00",
        name="Электроника, радиотехника и системы связи (многопрофильный конкурс)",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=112,
        paid=8,
        tuition=200_000,
        subjects="phys_inf_math",
        pass_b=171,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
        group="11.03.00",
        notes=GROUP_HEAD_NOTE,
    ),
    dict(
        id="sibguti-42.03.01-bachelor-full",
        code="42.03.01",
        name="Реклама и связи с общественностью",
        level="bachelor",
        form="full_time",
        duration=4,
        budget=0,
        paid=50,
        tuition=200_000,
        subjects="social",
        pass_b=None,
        pass_p=145,
        deadline_b=None,
        deadline_p=PAID_DEADLINE,
        notes="Бюджетных мест нет.",
    ),
    # Специалитет, очная форма
    dict(
        id="sibguti-10.05.02-specialist-full",
        code="10.05.02",
        name="Информационная безопасность телекоммуникационных систем",
        level="specialist",
        form="full_time",
        duration=5.5,
        budget=83,
        paid=47,
        tuition=200_000,
        subjects="math_inf_phys",
        pass_b=207,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    dict(
        id="sibguti-11.05.01-specialist-full",
        code="11.05.01",
        name="Радиоэлектронные системы и комплексы",
        level="specialist",
        form="full_time",
        duration=5.5,
        budget=10,
        paid=10,
        tuition=200_000,
        subjects="phys_inf_math",
        pass_b=171,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    dict(
        id="sibguti-11.05.04-specialist-full",
        code="11.05.04",
        name="Инфокоммуникационные технологии и системы специальной связи",
        level="specialist",
        form="full_time",
        duration=5.0,
        budget=24,
        paid=5,
        tuition=200_000,
        subjects="math_inf_phys",
        pass_b=189,
        pass_p=None,
        deadline_b=BACHELOR_BUDGET_DEADLINE,
        deadline_p=PAID_DEADLINE,
    ),
    # Бакалавриат, заочная форма (бюджетных мест нет)
    dict(
        id="sibguti-09.03.01-bachelor-part",
        code="09.03.01",
        name="Информатика и вычислительная техника",
        level="bachelor",
        form="part_time",
        duration=4.83,
        budget=0,
        paid=210,
        tuition=80_000,
        subjects="math_inf_phys",
        pass_b=None,
        pass_p=None,
        deadline_b=None,
        deadline_p=PAID_DEADLINE,
        notes="Заочная форма; бюджетных мест нет.",
    ),
    dict(
        id="sibguti-09.03.02-bachelor-part",
        code="09.03.02",
        name="Информационные системы и технологии",
        level="bachelor",
        form="part_time",
        duration=4.83,
        budget=0,
        paid=90,
        tuition=80_000,
        subjects="math_inf_phys",
        pass_b=None,
        pass_p=138,
        deadline_b=None,
        deadline_p=PAID_DEADLINE,
        notes="Заочная форма; бюджетных мест нет.",
    ),
    dict(
        id="sibguti-11.03.02-bachelor-part",
        code="11.03.02",
        name="Инфокоммуникационные технологии и системы связи",
        level="bachelor",
        form="part_time",
        duration=4.83,
        budget=0,
        paid=300,
        tuition=80_000,
        subjects="math_inf_phys",
        pass_b=None,
        pass_p=None,
        deadline_b=None,
        deadline_p=PAID_DEADLINE,
        notes="Заочная форма; бюджетных мест нет.",
    ),
    dict(
        id="sibguti-09.03.03-bachelor-remote",
        code="09.03.03",
        name="Прикладная информатика",
        level="bachelor",
        form="remote",
        duration=4.83,
        budget=0,
        paid=60,
        tuition=80_000,
        subjects="math_inf_phys",
        pass_b=None,
        pass_p=None,
        deadline_b=None,
        deadline_p=PAID_DEADLINE,
        notes="Заочная форма с применением ДОТ; бюджетных мест нет.",
    ),
    dict(
        id="sibguti-20.03.01-bachelor-remote",
        code="20.03.01",
        name="Техносферная безопасность",
        level="bachelor",
        form="remote",
        duration=4.83,
        budget=0,
        paid=30,
        tuition=80_000,
        subjects="math_inf_phys",
        pass_b=None,
        pass_p=142,
        deadline_b=None,
        deadline_p=PAID_DEADLINE,
        notes="Заочная форма с применением ДОТ; бюджетных мест нет.",
    ),
    dict(
        id="sibguti-42.03.01-bachelor-remote",
        code="42.03.01",
        name="Реклама и связи с общественностью",
        level="bachelor",
        form="remote",
        duration=4.83,
        budget=0,
        paid=30,
        tuition=80_000,
        subjects="social",
        pass_b=None,
        pass_p=173,
        deadline_b=None,
        deadline_p=PAID_DEADLINE,
        notes="Заочная форма с применением ДОТ; бюджетных мест нет.",
    ),
    # Магистратура, очная форма
    dict(
        id="sibguti-09.04.01-master-full",
        code="09.04.01",
        name="Информатика и вычислительная техника",
        level="master",
        form="full_time",
        duration=2,
        budget=11,
        paid=21,
        tuition=215_000,
        subjects="master_math",
        pass_b=97,
        pass_p=81,
        deadline_b=MASTER_DEADLINE,
        deadline_p=MASTER_DEADLINE,
        notes="Внутреннее вступительное испытание; минимальный балл 35.",
    ),
    dict(
        id="sibguti-09.04.02-master-full",
        code="09.04.02",
        name="Информационные системы и технологии",
        level="master",
        form="full_time",
        duration=2,
        budget=5,
        paid=20,
        tuition=210_000,
        subjects="master_math",
        pass_b=91,
        pass_p=None,
        deadline_b=MASTER_DEADLINE,
        deadline_p=MASTER_DEADLINE,
        notes="Внутреннее вступительное испытание; минимальный балл 35.",
    ),
    dict(
        id="sibguti-09.04.03-master-full",
        code="09.04.03",
        name="Прикладная информатика",
        level="master",
        form="full_time",
        duration=2,
        budget=5,
        paid=20,
        tuition=210_000,
        subjects="master_math",
        pass_b=95,
        pass_p=None,
        deadline_b=MASTER_DEADLINE,
        deadline_p=MASTER_DEADLINE,
        notes="Внутреннее вступительное испытание; минимальный балл 35.",
    ),
    dict(
        id="sibguti-10.04.01-master-full",
        code="10.04.01",
        name="Информационная безопасность",
        level="master",
        form="full_time",
        duration=2,
        budget=0,
        paid=20,
        tuition=210_000,
        subjects="master_security",
        pass_b=None,
        pass_p=None,
        deadline_b=None,
        deadline_p=MASTER_DEADLINE,
        notes="Не имеет государственной аккредитации; бюджетных мест нет.",
    ),
    dict(
        id="sibguti-11.04.02-networks-master-full",
        code="11.04.02",
        name="Инфокоммуникационные технологии и системы связи (Сети, системы и устройства телекоммуникаций)",
        level="master",
        form="full_time",
        duration=2,
        budget=21,
        paid=9,
        tuition=215_000,
        subjects="master_infocom",
        pass_b=86,
        pass_p=73,
        deadline_b=MASTER_DEADLINE,
        deadline_p=MASTER_DEADLINE,
        notes="Внутреннее вступительное испытание; минимальный балл 35.",
    ),
    dict(
        id="sibguti-11.04.02-mobile-master-full",
        code="11.04.02",
        name="Инфокоммуникационные технологии и системы связи (Архитектура и алгоритмы систем наземной и спутниковой мобильной связи)",
        level="master",
        form="full_time",
        duration=2,
        budget=12,
        paid=10,
        tuition=215_000,
        subjects="master_infocom",
        pass_b=71,
        pass_p=None,
        deadline_b=MASTER_DEADLINE,
        deadline_p=MASTER_DEADLINE,
        notes="Внутреннее вступительное испытание; минимальный балл 35.",
    ),
    dict(
        id="sibguti-42.04.01-master-full",
        code="42.04.01",
        name="Реклама и связи с общественностью",
        level="master",
        form="full_time",
        duration=2,
        budget=0,
        paid=20,
        tuition=190_000,
        subjects="master_marketing",
        pass_b=None,
        pass_p=None,
        deadline_b=None,
        deadline_p=MASTER_DEADLINE,
        notes="Не имеет государственной аккредитации; бюджетных мест нет.",
    ),
    # Магистратура, заочная форма
    dict(
        id="sibguti-09.04.01-master-part",
        code="09.04.01",
        name="Информатика и вычислительная техника",
        level="master",
        form="part_time",
        duration=2.5,
        budget=0,
        paid=30,
        tuition=85_000,
        subjects="master_math",
        pass_b=None,
        pass_p=None,
        deadline_b=None,
        deadline_p=MASTER_DEADLINE,
        notes="Заочная форма; бюджетных мест нет. Внутреннее испытание, минимальный балл 35.",
    ),
    dict(
        id="sibguti-11.04.02-networks-master-part",
        code="11.04.02",
        name="Инфокоммуникационные технологии и системы связи (Сети, системы и устройства телекоммуникаций)",
        level="master",
        form="part_time",
        duration=2.5,
        budget=0,
        paid=20,
        tuition=85_000,
        subjects="master_infocom",
        pass_b=None,
        pass_p=68,
        deadline_b=None,
        deadline_p=MASTER_DEADLINE,
        notes="Заочная форма; бюджетных мест нет. Внутреннее испытание, минимальный балл 35.",
    ),
    dict(
        id="sibguti-11.04.02-security-master-part",
        code="11.04.02",
        name="Инфокоммуникационные технологии и системы связи (Безопасность в инфокоммуникационных технологиях и системах связи)",
        level="master",
        form="part_time",
        duration=2.5,
        budget=0,
        paid=20,
        tuition=85_000,
        subjects="master_security_infocom",
        pass_b=None,
        pass_p=None,
        deadline_b=None,
        deadline_p=MASTER_DEADLINE,
        notes="Заочная форма; бюджетных мест нет. Внутреннее испытание, минимальный балл 35.",
    ),
]


def build_program(item: dict) -> dict:
    return {
        "id": item["id"],
        "university_slug": UNIVERSITY,
        "faculty": None,
        "code": item["code"],
        "name": item["name"],
        "level": item["level"],
        "form": item["form"],
        "duration_years": item["duration"],
        "budget_places": item["budget"],
        "paid_places": item["paid"],
        "tuition_rub": item["tuition"],
        "sources": PROGRAM_SOURCES,
    }


def build_admission(item: dict) -> dict:
    required, optional = SUBJECT_SETS[item["subjects"]]
    min_scores = {subject: MIN_SCORES[subject] for subject in required + optional}
    return {
        "id": f"{item['id']}-2026",
        "program_id": item["id"],
        "year": 2026,
        "subjects_required": required,
        "subjects_optional": optional,
        "exams_extra": [],
        "min_scores": min_scores,
        "passing_score_budget": item["pass_b"],
        "passing_score_paid": item["pass_p"],
        "application_deadline_budget": item["deadline_b"],
        "application_deadline_paid": item["deadline_p"],
        "competitive_group": item.get("group"),
        "notes": item.get("notes"),
        "sources": ADMISSION_SOURCES,
    }


def main() -> None:
    setup_console()

    programs = [build_program(item) for item in PROGRAMS]
    admissions = [build_admission(item) for item in PROGRAMS]

    PROGRAMS_PATH.write_text(
        json.dumps(programs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    ADMISSION_PATH.write_text(
        json.dumps(admissions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"СибГУТИ: {len(programs)} программ -> {PROGRAMS_PATH}")
    print(f"СибГУТИ: {len(admissions)} записей приёма -> {ADMISSION_PATH}")


if __name__ == "__main__":
    main()
