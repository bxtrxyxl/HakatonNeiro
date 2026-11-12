"""Структурные ответы по programs.json / admission.json.

Точные вопросы («сколько мест», «какой проходной балл», «какие предметы»,
«сколько стоит», «до какого числа») лучше не отдавать векторному поиску:
там легко перепутать похожие направления. Здесь мы находим программу по коду
или названию и отвечаем строго из базы.

Если вопрос не про факт или программу найти не удалось — возвращаем None,
и вызывающий код идёт в обычный RAG.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from src.config import ADMISSION_PATH, PROGRAMS_PATH, UNIVERSITIES_PATH
from src.rag.retrieve import content_terms, stem

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

CODE_RE = re.compile(r"\b\d{2}\.\d{2}\.\d{2}\b")

GENERIC_TERMS = {
    stem(word)
    for word in [
        "направление",
        "специальность",
        "форма",
        "обучение",
        "вуз",
        "университет",
        "сибгути",
        "сколько",
        "какой",
        "какие",
        "нужный",
        "есть",
        "можно",
        "расскажи",
        "подскажи",
        "место",
        "балл",
        "предмет",
        "стоимость",
        "срок",
    ]
}


def _load_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _data() -> tuple[list[dict], list[dict], list[dict]]:
    return (
        _load_json(PROGRAMS_PATH),
        _load_json(ADMISSION_PATH),
        _load_json(UNIVERSITIES_PATH),
    )


def _university(slug: str | None) -> dict | None:
    _, _, universities = _data()
    for item in universities:
        if item["slug"] == slug:
            return item
    return None


def _find_university(question: str) -> dict | None:
    _, _, universities = _data()
    q = question.lower()
    for item in universities:
        names = [item.get("short_name", ""), item.get("name", ""), item.get("slug", "")]
        if any(name and name.lower() in q for name in names):
            return item
    return None


def _admission_for(program_id: str) -> dict | None:
    _, admissions, _ = _data()
    for item in admissions:
        if item["program_id"] == program_id:
            return item
    return None


def _group_program(code: str | None) -> dict | None:
    if not code:
        return None
    programs, _, _ = _data()
    for item in programs:
        if item.get("code") == code and item.get("id", "").endswith("-group-bachelor-full"):
            return item
    for item in programs:
        if item.get("code") == code:
            return item
    return None


def _hint_bonus(program: dict, question: str) -> float:
    q = question.lower()
    bonus = 0.0

    if "магистрат" in q:
        bonus += 3 if program["level"] == "master" else -3
    elif "специалитет" in q:
        bonus += 3 if program["level"] == "specialist" else -3
    elif "бакалавриат" in q:
        bonus += 3 if program["level"] == "bachelor" else -3
    else:
        bonus += 1 if program["level"] == "bachelor" else 0

    if "заочн" in q:
        bonus += 2 if program["form"] in {"part_time", "remote"} else -2
    elif "очн" in q:
        bonus += 2 if program["form"] == "full_time" else -2
    else:
        bonus += 1 if program["form"] == "full_time" else 0

    return bonus


def _pick_best(matches: list[dict], question: str) -> dict:
    return max(matches, key=lambda program: _hint_bonus(program, question))


def find_program(question: str, university: str | None = None) -> dict | None:
    programs, _, _ = _data()
    candidates = [
        program
        for program in programs
        if not university or program["university_slug"] == university
    ]
    if not candidates:
        return None

    codes = CODE_RE.findall(question)
    if codes:
        matches = [program for program in candidates if program.get("code") in codes]
        if matches:
            return _pick_best(matches, question)

    query_terms = content_terms(question) - GENERIC_TERMS
    best: tuple[float, dict] | None = None
    for program in candidates:
        name_terms = content_terms(program["name"]) - GENERIC_TERMS
        overlap = query_terms & name_terms
        if not overlap:
            continue
        score = len(overlap) + _hint_bonus(program, question)
        if best is None or score > best[0]:
            best = (score, program)
    return best[1] if best else None


def _intent(question: str) -> str | None:
    q = question.lower()

    if any(
        word in q
        for word in [
            "контакт",
            "адрес",
            "телефон",
            "email",
            "почт",
            "приёмная комиссия",
            "приемная комиссия",
            "где находится",
        ]
    ):
        return "contacts"
    if "проходн" in q and "балл" in q:
        return "passing"
    if any(word in q for word in ["предмет", "егэ", "сдавать", "вступительн", "экзамен"]):
        return "subjects"
    if any(word in q for word in ["стоимост", "стоит", "цена", "оплат"]):
        return "tuition"
    if any(
        phrase in q
        for phrase in [
            "до какого числа",
            "дедлайн",
            "сроки подачи",
            "срок подачи",
            "когда подавать",
            "приём документов",
            "прием документов",
        ]
    ):
        return "deadlines"
    if "срок обучения" in q or "сколько лет" in q or "учиться" in q:
        return "duration"
    if "мест" in q and any(word in q for word in ["сколько", "количество", "бюджет", "платн"]):
        return "places"
    return None


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


def _date(value: str | None) -> str:
    if not value:
        return "нет данных"
    year, month, day = value.split("-")
    return f"{day}.{month}.{year}"


def _money(value: int | None) -> str:
    if value is None:
        return "нет данных"
    return f"{value:,}".replace(",", " ")


def _source(url: str, title: str | None) -> dict:
    return {"url": url, "title": title, "score": 0.0}


def _sources_for(record: dict, keywords: list[str]) -> list[dict]:
    result = []
    for source in record.get("sources", []):
        title = (source.get("title") or "").lower()
        if any(keyword in title for keyword in keywords):
            result.append(_source(source["url"], source.get("title")))
    if not result and record.get("sources"):
        first = record["sources"][0]
        result.append(_source(first["url"], first.get("title")))
    return result


def _program_label(program: dict, university: dict | None) -> str:
    short = (university or {}).get("short_name", program["university_slug"])
    return (
        f"{short}: {program.get('code') or 'без кода'} «{program['name']}», "
        f"{LEVEL_RU.get(program['level'], program['level'])}, "
        f"{FORM_RU.get(program['form'], program['form'])} форма."
    )


def _result(answer: str, sources: list[dict]) -> dict:
    return {
        "answer": answer,
        "sources": sources,
        "grounded": True,
        "mode": "facts",
    }


def _places_answer(program: dict, admission: dict, university: dict | None) -> dict:
    budget = program.get("budget_places")
    paid = program.get("paid_places")
    group = admission.get("competitive_group")
    lines = [_program_label(program, university)]

    if (budget is None or paid is None) and group:
        group_program = _group_program(group)
        if group_program:
            budget = budget if budget is not None else group_program.get("budget_places")
            paid = paid if paid is not None else group_program.get("paid_places")
            lines.append(f"Конкурс общий в группе {group}; места указаны суммарно по группе.")

    lines.append(f"Бюджетных мест: {budget if budget is not None else 'нет данных'}.")
    lines.append(f"Платных мест: {paid if paid is not None else 'нет данных'}.")
    if admission.get("notes"):
        lines.append(admission["notes"])

    return _result(" ".join(lines), _sources_for(admission, ["итоги"]))


def _passing_answer(program: dict, admission: dict, university: dict | None) -> dict:
    budget = admission.get("passing_score_budget")
    paid = admission.get("passing_score_paid")
    group = admission.get("competitive_group")

    if budget is None and group:
        group_program = _group_program(group)
        if group_program:
            group_admission = _admission_for(group_program["id"])
            if group_admission:
                budget = group_admission.get("passing_score_budget")

    lines = [
        _program_label(program, university),
        f"Проходной балл 2026: бюджет — {budget if budget is not None else 'нет данных'}, "
        f"платно — {paid if paid is not None else 'нет данных'}.",
    ]
    if admission.get("notes"):
        lines.append(admission["notes"])
    return _result(" ".join(lines), _sources_for(admission, ["итоги"]))


def _subjects_answer(program: dict, admission: dict, university: dict | None) -> dict:
    required = admission.get("subjects_required", [])
    optional = admission.get("subjects_optional", [])
    min_scores = admission.get("min_scores", {})

    lines = [_program_label(program, university)]
    lines.append(f"Предметы: {', '.join(required) if required else 'нет данных'}.")
    if optional:
        lines.append(f"По выбору: {', '.join(optional)}.")
    if min_scores:
        lines.append(
            "Минимальные баллы: "
            + ", ".join(f"{subject} — {score}" for subject, score in min_scores.items())
            + "."
        )
    return _result(
        " ".join(lines),
        _sources_for(admission, ["вступительн", "минимальн"]),
    )


def _tuition_answer(program: dict, admission: dict, university: dict | None) -> dict:
    lines = [
        _program_label(program, university),
        f"Стоимость обучения: {_money(program.get('tuition_rub'))} руб./год.",
    ]
    return _result(" ".join(lines), _sources_for(program, ["стоимост"]))


def _tuition_summary(question: str, university_slug: str | None) -> dict | None:
    programs, _, _ = _data()
    items = [
        program
        for program in programs
        if not university_slug or program["university_slug"] == university_slug
    ]
    if not items:
        return None

    q = question.lower()
    filtered = items
    if "магистрат" in q:
        filtered = [program for program in filtered if program["level"] == "master"]
    elif "специалитет" in q:
        filtered = [program for program in filtered if program["level"] == "specialist"]
    elif "бакалавриат" in q:
        filtered = [program for program in filtered if program["level"] == "bachelor"]

    if "заочн" in q:
        filtered = [program for program in filtered if program["form"] in {"part_time", "remote"}]
    elif "очн" in q:
        filtered = [program for program in filtered if program["form"] == "full_time"]

    if filtered:
        items = filtered

    university = _university(items[0]["university_slug"])
    groups: dict[tuple[str, str], set[int]] = {}
    for program in items:
        tuition = program.get("tuition_rub")
        if tuition is None:
            continue
        key = (
            LEVEL_RU.get(program["level"], program["level"]),
            FORM_RU.get(program["form"], program["form"]),
        )
        groups.setdefault(key, set()).add(tuition)

    lines = [f"{(university or {}).get('short_name', items[0]['university_slug'])} — стоимость обучения 2026/2027:"]
    for (level, form), values in sorted(groups.items()):
        prices = sorted(values)
        price = _money(prices[0]) if len(prices) == 1 else f"{_money(prices[0])}–{_money(prices[-1])}"
        lines.append(f"— {level}, {form} форма: {price} руб./год.")

    sources = _sources_for(items[0], ["стоимост"])
    return _result(" ".join(lines), sources)


def _deadlines_answer(program: dict, admission: dict, university: dict | None) -> dict:
    lines = [_program_label(program, university)]
    budget = admission.get("application_deadline_budget")
    paid = admission.get("application_deadline_paid")
    if budget:
        lines.append(f"Бюджетные места: документы принимают до {_date(budget)}.")
    elif program.get("budget_places") == 0:
        lines.append("Бюджетных мест нет.")
    if paid:
        lines.append(f"Платные места: документы принимают до {_date(paid)}.")
    return _result(" ".join(lines), _sources_for(admission, ["сроки"]))


def _deadlines_summary(question: str, university_slug: str | None) -> dict | None:
    programs, admissions, _ = _data()
    programs_by_id = {program["id"]: program for program in programs}
    program_ids = {
        program["id"]
        for program in programs
        if not university_slug or program["university_slug"] == university_slug
    }
    items = [item for item in admissions if item["program_id"] in program_ids]
    if not items:
        return None

    q = question.lower()
    filtered = items
    if "магистрат" in q:
        filtered = [
            item for item in filtered
            if programs_by_id[item["program_id"]]["level"] == "master"
        ]
    elif "специалитет" in q:
        filtered = [
            item for item in filtered
            if programs_by_id[item["program_id"]]["level"] == "specialist"
        ]
    elif "бакалавриат" in q:
        filtered = [
            item for item in filtered
            if programs_by_id[item["program_id"]]["level"] == "bachelor"
        ]

    if "заочн" in q:
        filtered = [
            item for item in filtered
            if programs_by_id[item["program_id"]]["form"] in {"part_time", "remote"}
        ]
    elif "очн" in q:
        filtered = [
            item for item in filtered
            if programs_by_id[item["program_id"]]["form"] == "full_time"
        ]

    if filtered:
        items = filtered

    by_level: dict[str, list[dict]] = {}
    for item in items:
        program = programs_by_id.get(item["program_id"])
        if program:
            by_level.setdefault(program["level"], []).append(item)

    if university_slug is None:
        university_slug = next(
            (program["university_slug"] for program in programs if program["id"] in program_ids),
            None,
        )
    university = _university(university_slug) if university_slug else None

    lines = [f"{(university or {}).get('short_name', 'Вуз')} — сроки подачи документов в 2026 году:"]
    for level in ["bachelor", "specialist", "master", "postgraduate", "secondary"]:
        level_items = by_level.get(level)
        if not level_items:
            continue
        budget_dates = sorted(
            {
                item["application_deadline_budget"]
                for item in level_items
                if item.get("application_deadline_budget")
            }
        )
        paid_dates = sorted(
            {
                item["application_deadline_paid"]
                for item in level_items
                if item.get("application_deadline_paid")
            }
        )
        parts = []
        if budget_dates:
            parts.append("бюджет — до " + ", ".join(_date(value) for value in budget_dates))
        else:
            parts.append("бюджетных мест нет")
        if paid_dates:
            parts.append("платно — до " + ", ".join(_date(value) for value in paid_dates))
        else:
            parts.append("платных мест нет")
        lines.append(f"{LEVEL_RU.get(level, level)}: " + "; ".join(parts) + ".")

    sources = _sources_for(items[0], ["сроки"])
    return _result(" ".join(lines), sources)


def _duration_answer(program: dict, admission: dict, university: dict | None) -> dict:
    lines = [
        _program_label(program, university),
        f"Срок обучения: {_years_label(program.get('duration_years'))}.",
    ]
    return _result(" ".join(lines), _sources_for(program, ["приложение 1", "перечень"]))


def _contacts_result(university: dict) -> dict:
    lines = [f"{university.get('short_name')} ({university.get('name')})."]
    if university.get("address"):
        lines.append(f"Адрес: {university['address']}.")
    if university.get("phone"):
        lines.append(f"Телефон: {university['phone']}.")
    if university.get("email"):
        lines.append(f"Email: {university['email']}.")
    if university.get("site"):
        lines.append(f"Сайт: {university['site']}.")

    sources = []
    if university.get("site"):
        sources.append(_source(university["site"], f"{university.get('short_name')} — официальный сайт"))
    for item in university.get("sources", []):
        sources.append(_source(item["url"], item.get("title")))
    return _result(" ".join(lines), sources)


def answer_from_facts(question: str, university: str | None = None) -> dict | None:
    programs, _, _ = _data()
    if not programs:
        return None

    q = question.lower()
    intent = _intent(q)
    if intent is None:
        return None

    if university is None:
        found = _find_university(q)
        if found:
            university = found["slug"]

    if intent == "contacts":
        target = _university(university) if university else _find_university(q)
        if target:
            return _contacts_result(target)
        return None

    if intent == "tuition" and find_program(question, university) is None:
        return _tuition_summary(question, university)
    if intent == "deadlines" and find_program(question, university) is None:
        return _deadlines_summary(question, university)

    program = find_program(question, university)
    if program is None:
        return None

    admission = _admission_for(program["id"])
    if admission is None:
        return None

    university_data = _university(program["university_slug"])

    if intent == "places":
        return _places_answer(program, admission, university_data)
    if intent == "passing":
        return _passing_answer(program, admission, university_data)
    if intent == "subjects":
        return _subjects_answer(program, admission, university_data)
    if intent == "tuition":
        return _tuition_answer(program, admission, university_data)
    if intent == "deadlines":
        return _deadlines_answer(program, admission, university_data)
    if intent == "duration":
        return _duration_answer(program, admission, university_data)
    return None
