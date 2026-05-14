"""Pengujian sederhana endpoint health pada API DARSI."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    """Memastikan endpoint health mengembalikan status sehat.

    Returns:
        None.
    """

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
