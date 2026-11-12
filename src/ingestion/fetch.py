"""Загрузка страниц вузов с кэшированием в data/raw.

Пример:
    python -m src.ingestion.fetch https://www.nsu.ru/ru/ https://www.nstu.ru/

Каждая страница сохраняется как файл + рядом .meta с исходным URL и sha256.
Повторный запуск не перекачивает уже сохранённые страницы (--force чтобы обновить).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from src.config import RAW_DIR, USER_AGENT
from src.console import setup_console

TIMEOUT = httpx.Timeout(30.0)
DELAY_SECONDS = 1.0
MAX_CONCURRENCY = 3


def url_to_path(url: str, root: Path) -> Path:
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "_") or "unknown"
    path = parsed.path.strip("/") or "index"
    path = re.sub(r"[^\w\-./]+", "_", path)
    if not Path(path).suffix:
        path += ".html"
    return root / host / path


async def allowed_by_robots(client: httpx.AsyncClient, url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        response = await client.get(robots_url)
        if response.status_code >= 400:
            return True
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, url)
    except httpx.HTTPError:
        # robots.txt недоступен — не блокируем, но действуем вежливо (пауза ниже)
        return True


async def fetch_one(
    client: httpx.AsyncClient,
    url: str,
    root: Path = RAW_DIR,
    force: bool = False,
) -> Path:
    target = url_to_path(url, root)
    if target.exists() and not force:
        return target

    if not await allowed_by_robots(client, url):
        raise PermissionError(f"robots.txt запрещает загрузку: {url}")

    response = await client.get(url)
    response.raise_for_status()

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)

    meta = target.parent / f"{target.name}.meta"
    meta.write_text(
        f"url: {url}\n"
        f"status: {response.status_code}\n"
        f"content_type: {response.headers.get('content-type', '')}\n"
        f"sha256: {hashlib.sha256(response.content).hexdigest()}\n",
        encoding="utf-8",
    )
    return target


async def fetch_many(urls: list[str], force: bool = False) -> list[Path]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        },
    ) as client:

        async def worker(url: str) -> Path | None:
            async with semaphore:
                try:
                    path = await fetch_one(client, url, force=force)
                    print(f"[ok]   {url} -> {path}")
                    return path
                except Exception as exc:  # noqa: BLE001 — CLI должен продолжать работу
                    print(f"[fail] {url}: {exc}")
                    return None
                finally:
                    await asyncio.sleep(DELAY_SECONDS)

        results = await asyncio.gather(*(worker(url) for url in urls))

    return [path for path in results if path is not None]


def main() -> None:
    setup_console()
    parser = argparse.ArgumentParser(description="Загрузка страниц вузов")
    parser.add_argument("urls", nargs="+", help="URL страниц")
    parser.add_argument("--force", action="store_true", help="Перекачать существующие")
    args = parser.parse_args()

    saved = asyncio.run(fetch_many(args.urls, force=args.force))
    print(f"\nСохранено страниц: {len(saved)}")


if __name__ == "__main__":
    main()
