"""Настройки проекта: пути и параметры LLM из окружения."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent


def _path(env_name: str, default: str) -> Path:
    value = Path(os.getenv(env_name, default))
    return value if value.is_absolute() else ROOT_DIR / value


DATA_DIR = _path("DATA_DIR", "data")
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHUNKS_DIR = DATA_DIR / "chunks"
GOLDEN_DIR = DATA_DIR / "golden"

UNIVERSITIES_PATH = PROCESSED_DIR / "universities.json"
PROGRAMS_PATH = PROCESSED_DIR / "programs.json"
ADMISSION_PATH = PROCESSED_DIR / "admission.json"
PAGES_PATH = PROCESSED_DIR / "pages.jsonl"
CHUNKS_PATH = CHUNKS_DIR / "chunks.jsonl"
GOLDEN_PATH = GOLDEN_DIR / "qa.jsonl"

WEB_DIR = ROOT_DIR / "web"

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")

USER_AGENT = "HakatonNeiroBot/0.1 (student hackathon; educational use)"
