"""Парсинг сохранённых страниц в data/processed/pages.jsonl.

Пример:
    python -m src.ingestion.parse
    python -m src.ingestion.parse --root data/raw --out data/processed/pages.jsonl

Формат строки pages.jsonl:
    {"url": "...", "university": "nsu", "title": "...", "text": "...", "tables": [[...]]}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.config import PAGES_PATH, RAW_DIR, UNIVERSITIES_PATH
from src.console import setup_console


def extract(html: str | bytes, url: str = "") -> dict:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines = [line.strip() for line in main.get_text("\n").splitlines()]
    text = "\n".join(line for line in lines if line)

    tables: list[list[list[str]]] = []
    for table in main.find_all("table"):
        rows: list[list[str]] = []
        for tr in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)

    return {"url": url, "title": title, "text": text, "tables": tables}


def load_university_hosts() -> dict[str, str]:
    if not UNIVERSITIES_PATH.exists():
        return {}
    items = json.loads(UNIVERSITIES_PATH.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for item in items:
        host = urlparse(item.get("site", "")).netloc.lower()
        if host:
            mapping[host.removeprefix("www.")] = item["slug"]
    return mapping


def university_for_url(url: str, hosts: dict[str, str]) -> str | None:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host in hosts:
        return hosts[host]
    for known, slug in hosts.items():
        if host.endswith("." + known):
            return slug
    return None


def iter_raw_pages(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.endswith(".meta"):
            continue
        meta = path.parent / f"{path.name}.meta"
        if not meta.exists():
            continue
        url = ""
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.startswith("url:"):
                url = line.split(":", 1)[1].strip()
                break
        yield path, url


def main() -> None:
    setup_console()
    parser = argparse.ArgumentParser(description="Парсинг HTML в pages.jsonl")
    parser.add_argument("--root", type=Path, default=RAW_DIR)
    parser.add_argument("--out", type=Path, default=PAGES_PATH)
    args = parser.parse_args()

    hosts = load_university_hosts()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with args.out.open("w", encoding="utf-8") as out:
        for path, url in iter_raw_pages(args.root):
            if path.suffix.lower() not in {".html", ".htm", ""}:
                print(f"[skip] не HTML: {path}")
                continue
            try:
                raw = path.read_bytes()
            except OSError as exc:
                print(f"[fail] {path}: {exc}")
                continue

            page = extract(raw, url)
            page["university"] = university_for_url(url, hosts)
            page["raw_path"] = str(path)
            out.write(json.dumps(page, ensure_ascii=False) + "\n")
            count += 1

    print(f"Готово: {count} страниц -> {args.out}")


if __name__ == "__main__":
    main()
