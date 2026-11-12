from pathlib import Path

from src.rag.build_chunks import chunk_text
from src.rag.retrieve import Retriever
from src.schemas import University

ROOT = Path(__file__).resolve().parents[1]


def test_seed_universities_are_valid() -> None:
    import json

    items = json.loads((ROOT / "data/processed/universities.json").read_text(encoding="utf-8"))
    for item in items:
        University.model_validate(item)


def test_chunk_text_splits_long_text() -> None:
    chunks = chunk_text("а" * 3000, max_chars=1200, overlap=200)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 1200 for chunk in chunks)


def test_chunk_text_keeps_short_text_whole() -> None:
    assert chunk_text("короткий текст", max_chars=1200) == ["короткий текст"]


def test_retriever_ranks_relevant_chunk_first() -> None:
    retriever = Retriever(
        [
            {"text": "проходной балл на бюджет в прошлом году", "url": "u1"},
            {"text": "общежитие, столовая и спортивный комплекс", "url": "u2"},
        ]
    )
    hits = retriever.search("проходной балл", k=1)
    assert hits and hits[0]["url"] == "u1"


def test_retriever_filters_by_university() -> None:
    retriever = Retriever(
        [
            {"text": "факультет информационных технологий", "url": "u1", "university": "nstu"},
            {"text": "факультет информационных технологий", "url": "u2", "university": "nsu"},
        ]
    )
    hits = retriever.search("факультет", k=5, university="nsu")
    assert [hit["url"] for hit in hits] == ["u2"]


def test_answer_refuses_without_relevant_sources() -> None:
    from src.rag.answer import answer_question

    retriever = Retriever([{"text": "общежитие и столовая", "url": "u1"}])
    result = answer_question("есть ли военная кафедра", retriever)
    assert result["grounded"] is False
    assert result["mode"] == "no-data"
