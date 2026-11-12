"""Проверка доступности сайтов вузов из справочника.

Запуск:
    python scripts/check_sites.py
    python scripts/check_sites.py --timeout 10

Делает по одному запросу на вуз (без обхода страниц) и показывает HTTP-статус.
Нужен, чтобы заранее понять, какие сайты доступны из текущей сети, а какие
отдают 403 и требуют запуска с российского IP или ручного сохранения страниц.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import UNIVERSITIES_PATH, USER_AGENT  # noqa: E402
from src.console import setup_console  # noqa: E402

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


def main() -> None:
    setup_console()
    parser = argparse.ArgumentParser(description="Проверка доступности сайтов вузов")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--only", help="проверить только один slug")
    args = parser.parse_args()

    items = json.loads(UNIVERSITIES_PATH.read_text(encoding="utf-8"))
    if args.only:
        items = [item for item in items if item["slug"] == args.only]
        if not items:
            raise SystemExit(f"Вуз с slug={args.only!r} не найден")

    reachable = 0
    with httpx.Client(
        timeout=args.timeout,
        follow_redirects=True,
        headers=HEADERS,
    ) as client:
        for item in items:
            started = time.perf_counter()
            try:
                with client.stream("GET", item["site"]) as response:
                    elapsed = time.perf_counter() - started
                    status = response.status_code
                    final_url = str(response.url)
                    print(
                        f"{status:>3}  {item['slug']:<10} "
                        f"{item['site']:<26} {elapsed:5.1f}s  {final_url}"
                    )
                    if status < 400:
                        reachable += 1
            except httpx.HTTPError as exc:
                print(f"ERR  {item['slug']:<10} {item['site']:<26} {exc}")

    print(f"\nДоступно: {reachable} из {len(items)}")


if __name__ == "__main__":
    main()
