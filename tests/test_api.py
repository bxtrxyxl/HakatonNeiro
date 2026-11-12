import json

from fastapi.testclient import TestClient

import src.api.main as api


def test_health() -> None:
    client = TestClient(api.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "chunks" in response.json()


def test_chat_without_index_returns_503(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(api, "CHUNKS_PATH", tmp_path / "missing.jsonl")
    api.get_retriever.cache_clear()

    client = TestClient(api.app)
    response = client.post("/api/chat", json={"question": "тест"})

    assert response.status_code == 503
    api.get_retriever.cache_clear()


def test_chat_with_index_returns_sources(tmp_path, monkeypatch) -> None:
    chunks = tmp_path / "chunks.jsonl"
    chunks.write_text(
        json.dumps(
            {
                "id": "1",
                "text": "проходной балл на бюджет в 2026 году — 245",
                "url": "https://example.org",
                "title": "Пример",
                "university": "nsu",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(api, "CHUNKS_PATH", chunks)
    monkeypatch.setattr("src.rag.answer.LLM_API_KEY", "")
    api.get_retriever.cache_clear()

    client = TestClient(api.app)
    response = client.post(
        "/api/chat",
        json={"question": "какой проходной балл", "university": "nsu"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert data["sources"][0]["url"] == "https://example.org"
    assert data["mode"] == "extractive"

    api.get_retriever.cache_clear()
