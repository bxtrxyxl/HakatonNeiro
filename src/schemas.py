"""Pydantic-модели данных о вузах, программах и приёме.

Единица доверия — Source: URL + дата парсинга. Любая запись без источника
считается черновой.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class StudyLevel(str, Enum):
    BACHELOR = "bachelor"
    SPECIALIST = "specialist"
    MASTER = "master"
    POSTGRADUATE = "postgraduate"
    SECONDARY = "secondary"


class StudyForm(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    EVENING = "evening"
    REMOTE = "remote"


class Source(BaseModel):
    url: str
    title: str | None = None
    parsed_at: datetime
    valid_from: date | None = None
    valid_to: date | None = None
    checksum: str | None = None


class University(BaseModel):
    slug: str = Field(description="Короткий идентификатор, например nsu")
    name: str
    short_name: str
    site: str
    city: str = "Новосибирск"
    founded: int | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str = "active"
    confirmed: bool = Field(
        default=False,
        description="Подтверждён ли вуз в финальном списке команды",
    )
    sources: list[Source] = Field(default_factory=list)


class Program(BaseModel):
    id: str
    university_slug: str
    faculty: str | None = None
    code: str | None = Field(default=None, description="Код направления, например 01.03.02")
    name: str
    level: StudyLevel
    form: StudyForm = StudyForm.FULL_TIME
    duration_years: float | None = None
    budget_places: int | None = None
    paid_places: int | None = None
    tuition_rub: int | None = None
    sources: list[Source] = Field(default_factory=list)


class Admission(BaseModel):
    id: str
    program_id: str
    year: int = Field(description="Год приёмной кампании")
    subjects_required: list[str] = Field(default_factory=list)
    subjects_optional: list[str] = Field(default_factory=list)
    exams_extra: list[str] = Field(default_factory=list)
    min_scores: dict[str, int] = Field(
        default_factory=dict,
        description="Минимальные баллы по предметам (порог участия)",
    )
    passing_score_budget: int | None = Field(
        default=None,
        description="Проходной балл на бюджет прошлого года (фактический cutoff)",
    )
    passing_score_paid: int | None = None
    application_deadline_budget: date | None = None
    application_deadline_paid: date | None = None
    competitive_group: str | None = Field(
        default=None,
        description="Код конкурсной группы, если конкурс общий для нескольких направлений",
    )
    notes: str | None = None
    sources: list[Source] = Field(default_factory=list)
