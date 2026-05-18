"""Tests untuk endpoint /api/chat & /api/rag (offline-friendly via monkeypatch)."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import rag_service

client = TestClient(app)


def test_chat_empty_message_rejected() -> None:
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 400


def test_chat_rag_path(monkeypatch) -> None:
    """Override `rag_query` agar test tidak bergantung ke Ollama/SurrealDB."""

    def fake_rag_query(query: str, n_results: int = 5) -> dict:
        return {
            "query": query,
            "context_used": "[Vector Search · biaya_operasional]\n  • dummy doc",
            "answer": "Jawaban dummy untuk testing.",
            "source": "surrealdb_vector+structured+ollama",
            "vector_hits": 1,
            "surreal_hits": 0,
            "matched_domains": ["biaya_operasional"],
        }

    monkeypatch.setattr(rag_service, "rag_query", fake_rag_query)
    monkeypatch.setattr("app.api.chat.rag_query", fake_rag_query)

    response = client.post("/api/chat", json={"message": "biaya listrik?"})
    assert response.status_code == 200
    body = response.json()
    assert "Jawaban dummy" in body["response"]
    assert body["matched_domains"] == ["biaya_operasional"]


def test_rag_query_endpoint(monkeypatch) -> None:
    def fake_rag_query(query: str, n_results: int = 5) -> dict:
        return {
            "query": query,
            "context_used": "ctx",
            "answer": "jawaban",
            "source": "surrealdb_vector+structured+ollama",
            "vector_hits": 2,
            "surreal_hits": 1,
            "matched_domains": ["okupansi_kamar"],
        }

    monkeypatch.setattr("app.api.rag.rag_query", fake_rag_query)
    response = client.post("/api/rag/query", json={"query": "bor icu?"})
    assert response.status_code == 200
    body = response.json()
    assert body["matched_domains"] == ["okupansi_kamar"]


def test_rag_query_empty_rejected() -> None:
    response = client.post("/api/rag/query", json={"query": "   "})
    assert response.status_code == 400
