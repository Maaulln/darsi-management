"""Tests endpoint analytics — selalu mengembalikan struktur valid meski SurrealDB offline."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_overview_structure() -> None:
    response = client.get("/api/analytics/overview")
    assert response.status_code == 200
    body = response.json()
    assert "kpi" in body
    for key in (
        "pasien_aktif",
        "bed_capacity",
        "bed_occupied",
        "bor_pct",
        "total_cost_idr",
    ):
        assert key in body["kpi"]


def test_cost_by_category_returns_list() -> None:
    response = client.get("/api/analytics/cost-by-category")
    assert response.status_code == 200
    assert isinstance(response.json()["categories"], list)


def test_occupancy_by_unit_returns_list() -> None:
    response = client.get("/api/analytics/occupancy-by-unit")
    assert response.status_code == 200
    assert isinstance(response.json()["units"], list)


def test_utility_trend_returns_dual_series() -> None:
    response = client.get("/api/analytics/utility-trend")
    assert response.status_code == 200
    body = response.json()
    assert "listrik" in body and "air" in body
