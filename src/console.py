"""Корректный вывод русского текста в консоль Windows."""

from __future__ import annotations

import sys


def setup_console() -> None:
    """Переключает stdout/stderr на UTF-8, чтобы print не падал с UnicodeEncodeError."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001 — не критично для работы
                pass
