# Модель данных

Три файла в `data/processed/` — «источник правды» для структурных фактов.
Тексты страниц и чанки — отдельно, для RAG.

## University

```json
{
  "slug": "nsu",
  "name": "Новосибирский государственный университет",
  "short_name": "НГУ",
  "site": "https://www.nsu.ru",
  "city": "Новосибирск",
  "founded": 1958,
  "address": "ул. Пирогова, 1",
  "phone": "+7 ...",
  "email": "...",
  "status": "active",
  "confirmed": true,
  "sources": [
    {
      "url": "https://www.nsu.ru/ru/about",
      "title": "Об университете",
      "parsed_at": "2026-11-12T12:00:00",
      "valid_from": "2026-11-01",
      "valid_to": null,
      "checksum": "sha256:..."
    }
  ]
}
```

`slug` — стабильный идентификатор. Он же используется в поле `university`
у чанков и в фильтре `/api/chat`.

## Program

```json
{
  "id": "nsu-01.03.02-bachelor",
  "university_slug": "nsu",
  "faculty": "Факультет информационных технологий",
  "code": "01.03.02",
  "name": "Прикладная математика и информатика",
  "level": "bachelor",
  "form": "full_time",
  "duration_years": 4,
  "budget_places": 100,
  "paid_places": 25,
  "tuition_rub": 250000,
  "sources": []
}
```

`level`: `bachelor`, `specialist`, `master`, `postgraduate`, `secondary`.
`form`: `full_time`, `part_time`, `evening`, `remote`.

## Admission

```json
{
  "id": "nsu-01.03.02-2026",
  "program_id": "nsu-01.03.02-bachelor",
  "year": 2026,
  "subjects_required": ["Математика", "Русский язык"],
  "subjects_optional": ["Информатика", "Физика"],
  "exams_extra": [],
  "min_scores": { "Математика": 60, "Русский язык": 40, "Информатика": 60 },
  "passing_score_budget": 245,
  "passing_score_paid": 180,
  "application_deadline_budget": "2026-07-25",
  "application_deadline_paid": "2026-08-20",
  "competitive_group": null,
  "notes": null,
  "sources": []
}
```

### Что важно не перепутать

- `min_scores` — **минимальные** баллы (порог участия в конкурсе).
- `passing_score_budget` — **проходной** балл (фактический cutoff, обычно за прошлый год).
- `year` — год приёмной кампании. Все баллы и сроки привязаны к нему.
- `subjects_optional` — предметы по выбору; в разных вузах набор и правила выбора отличаются.
- `application_deadline_budget` / `application_deadline_paid` — разные дедлайны
  для бюджета и платных мест; не смешивайте их.
- `competitive_group` — код общего конкурса (например, 11.03.00), если места
  и проходной балл считаются на группу направлений.
- `notes` — оговорки: нет аккредитации, нет бюджетных мест, заочная форма и т. п.
- `tuition_rub` — стоимость **за год**, не за семестр.
- `budget_places` / `paid_places`: `0` — мест нет, `null` — нет данных.

## Как пополнять

1. Скачать страницы: `python -m src.ingestion.fetch <url>`.
2. Разобрать: `python -m src.ingestion.parse`.
3. Извлечь факты в `programs.json` / `admission.json` (вручную или LLM-ассистентом).
   Пример готового заполнения — `scripts/seed_sibguti.py`.
4. Проверить: `python scripts/check_data.py`.
5. Пересобрать чанки: `python -m src.rag.build_chunks`.
6. Прогнать оценку: `python -m src.eval.run_eval`.

Правило: **любая запись без `sources` — черновик**, её нельзя показывать пользователю
как факт.
