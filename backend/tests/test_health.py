"""Smoke tests endpoint dasar backend DARSI."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """`/health` mengembalikan status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_health_alias() -> None:
    """`/api/health` mengembalikan status ok (alias untuk gateway Nginx)."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_overall_status() -> None:
    """Endpoint readiness selalu memuat field overall (ok/degraded)."""
    response = client.get("/api/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert "overall" in payload
    assert payload["overall"] in {"ok", "degraded"}
