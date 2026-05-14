"""Tests untuk endpoint data operasional & MCP proxy."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_dummy_data() -> None:
    response = client.get("/api/data/list")
    assert response.status_code == 200
    items = response.json()["items"]
    assert isinstance(items, list)
    assert items, "dummy records harus tersedia"


def test_get_data_by_id_found() -> None:
    response = client.get("/api/data/SIMRS-001")
    assert response.status_code == 200
    assert response.json()["id"] == "SIMRS-001"


def test_get_data_by_id_not_found() -> None:
    response = client.get("/api/data/NOT-EXIST")
    assert response.status_code == 404


def test_domains_endpoint_returns_list() -> None:
    """MCP server biasanya offline saat unit test → expect struktur valid."""
    response = client.get("/api/data/domains")
    assert response.status_code == 200
    assert "domains" in response.json()
