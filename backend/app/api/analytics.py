"""Endpoint analitik agregat operasional DARSI untuk dashboard."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.db.surrealdb import SurrealDBClient
from app.services.mcp_client import mcp_client

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
surreal_client = SurrealDBClient()


@router.get("/overview", response_model=dict[str, Any])
async def get_overview() -> dict[str, Any]:
    """Ringkasan tingkat tinggi untuk dashboard utama.

    Returns:
        Dictionary berisi total pasien aktif, total kapasitas/tempat tidur terisi,
        total kWh listrik, dan total biaya operasional bulanan.
    """
    queries = {
        "pasien_total": "SELECT count() AS total FROM clean_pasien_aktif GROUP ALL",
        "okupansi": "SELECT math::sum(bed_capacity) AS capacity, math::sum(bed_occupied) AS occupied FROM clean_okupansi_kamar GROUP ALL",
        "listrik": "SELECT math::sum(kwh_total) AS kwh FROM clean_meter_listrik GROUP ALL",
        "air": "SELECT math::sum(volume_m3_total) AS volume FROM clean_konsumsi_air GROUP ALL",
        "biaya": "SELECT math::sum(amount_idr) AS total_cost, math::sum(budget_idr) AS total_budget FROM clean_biaya_operasional GROUP ALL",
        "lembur": "SELECT math::sum(overtime_hours) AS hours, math::sum(overtime_cost_idr) AS cost FROM clean_lembur_staf GROUP ALL",
    }

    result: dict[str, Any] = {}
    for key, sql in queries.items():
        records = surreal_client.query(sql)
        result[key] = records[0] if records else {}

    capacity = result.get("okupansi", {}).get("capacity") or 0
    occupied = result.get("okupansi", {}).get("occupied") or 0
    bor_pct = round(100 * occupied / capacity, 2) if capacity else 0.0

    total_cost = result.get("biaya", {}).get("total_cost") or 0
    total_budget = result.get("biaya", {}).get("total_budget") or 0
    budget_usage_pct = round(100 * total_cost / total_budget, 2) if total_budget else 0.0

    return {
        "kpi": {
            "pasien_aktif": result.get("pasien_total", {}).get("total", 0),
            "bed_capacity": capacity,
            "bed_occupied": occupied,
            "bor_pct": bor_pct,
            "kwh_total": result.get("listrik", {}).get("kwh", 0),
            "air_m3_total": result.get("air", {}).get("volume", 0),
            "total_cost_idr": total_cost,
            "total_budget_idr": total_budget,
            "budget_usage_pct": budget_usage_pct,
            "overtime_hours": result.get("lembur", {}).get("hours", 0),
            "overtime_cost_idr": result.get("lembur", {}).get("cost", 0),
        },
        "raw": result,
    }


@router.get("/cost-by-category", response_model=dict[str, Any])
async def cost_by_category() -> dict[str, Any]:
    """Total biaya operasional dibreakdown per kategori biaya."""
    sql = (
        "SELECT cost_category, math::sum(amount_idr) AS total_cost,"
        " math::sum(budget_idr) AS total_budget"
        " FROM clean_biaya_operasional GROUP BY cost_category"
    )
    records = surreal_client.query(sql)
    return {"categories": records}


@router.get("/occupancy-by-unit", response_model=dict[str, Any])
async def occupancy_by_unit() -> dict[str, Any]:
    """Okupansi bed per unit untuk visualisasi bar chart."""
    sql = (
        "SELECT unit_code, math::sum(bed_capacity) AS capacity,"
        " math::sum(bed_occupied) AS occupied"
        " FROM clean_okupansi_kamar GROUP BY unit_code"
    )
    records = surreal_client.query(sql)
    return {"units": records}


@router.get("/utility-trend", response_model=dict[str, Any])
async def utility_trend() -> dict[str, Any]:
    """Tren konsumsi utilitas (listrik & air) per unit."""
    listrik = surreal_client.query(
        "SELECT unit_code, math::sum(kwh_total) AS kwh FROM clean_meter_listrik GROUP BY unit_code"
    )
    air = surreal_client.query(
        "SELECT unit_code, math::sum(volume_m3_total) AS volume FROM clean_konsumsi_air GROUP BY unit_code"
    )
    return {"listrik": listrik, "air": air}


@router.get("/mcp-status", response_model=dict[str, Any])
async def mcp_status() -> dict[str, Any]:
    """Periksa status MCP server dan daftar domain yang dikenal."""
    return mcp_client.list_domains()
