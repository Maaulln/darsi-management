"""Smoke tests untuk MCP server DARSI."""

from fastapi.testclient import TestClient

from app.main import app, detect_intent


def test_mcp_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_mcp_domains_listed() -> None:
    client = TestClient(app)
    response = client.get("/mcp/domains")
    assert response.status_code == 200
    payload = response.json()
    assert "domains" in payload
    assert len(payload["domains"]) >= 6


def test_mcp_context_responds() -> None:
    """Konteks selalu berstruktur valid meski Chroma/Surreal kosong."""
    client = TestClient(app)
    response = client.post("/mcp/context", json={"query": "okupansi kamar ICU"})
    assert response.status_code == 200
    body = response.json()
    assert "source" in body
    assert "context" in body
    assert "matched_domains" in body
    assert "okupansi_kamar" in body["matched_domains"]


def test_detect_intent_finds_biaya() -> None:
    assert "biaya_operasional" in detect_intent("Berapa total biaya listrik bulan ini?")


def test_detect_intent_defaults_when_unknown() -> None:
    assert detect_intent("apa kabar") != []
