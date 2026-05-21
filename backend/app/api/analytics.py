"""Endpoint analitik agregat operasional DARSI — semua data via MCP Server."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.mcp_client import mcp_client

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _date_params(date_from: str | None, date_to: str | None) -> dict:
    return {"date_from": date_from, "date_to": date_to}


@router.get("/dashboard", response_model=dict[str, Any])
async def get_dashboard(
    date_from: str | None = Query(None, description="Filter dari tanggal (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Filter sampai tanggal (YYYY-MM-DD)"),
) -> dict[str, Any]:
    """Ambil semua data dashboard dalam satu request — 6 analytics secara paralel."""
    params = _date_params(date_from, date_to)
    results = await asyncio.gather(
        mcp_client.fetch_analytics("overview", params),
        mcp_client.fetch_analytics("cost-by-category", params),
        mcp_client.fetch_analytics("occupancy-by-unit", params),
        mcp_client.fetch_analytics("utility-trend", params),
        mcp_client.fetch_analytics("efficiency", params),
        mcp_client.fetch_analytics("staffing", params),
        return_exceptions=True,
    )
    keys = ["overview", "cost_by_category", "occupancy_by_unit", "utility_trend", "efficiency", "staffing"]
    return {
        k: (v if not isinstance(v, Exception) else {"error": str(v)})
        for k, v in zip(keys, results)
    }


@router.get("/overview", response_model=dict[str, Any])
async def get_overview(
    date_from: str | None = Query(None, description="Filter dari tanggal (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Filter sampai tanggal (YYYY-MM-DD)"),
) -> dict[str, Any]:
    result = await mcp_client.fetch_analytics("overview", _date_params(date_from, date_to))
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/cost-by-category", response_model=dict[str, Any])
async def cost_by_category(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict[str, Any]:
    result = await mcp_client.fetch_analytics("cost-by-category", _date_params(date_from, date_to))
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/occupancy-by-unit", response_model=dict[str, Any])
async def occupancy_by_unit(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict[str, Any]:
    result = await mcp_client.fetch_analytics("occupancy-by-unit", _date_params(date_from, date_to))
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/utility-trend", response_model=dict[str, Any])
async def utility_trend(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict[str, Any]:
    result = await mcp_client.fetch_analytics("utility-trend", _date_params(date_from, date_to))
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/efficiency", response_model=dict[str, Any])
async def efficiency(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict[str, Any]:
    result = await mcp_client.fetch_analytics("efficiency", _date_params(date_from, date_to))
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/staffing", response_model=dict[str, Any])
async def staffing(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
) -> dict[str, Any]:
    result = await mcp_client.fetch_analytics("staffing", _date_params(date_from, date_to))
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/daily-trend", response_model=dict[str, Any])
async def daily_trend(
    year: int = Query(..., description="Tahun (misal: 2024)"),
    month: int = Query(..., ge=1, le=12, description="Bulan 1-12"),
) -> dict[str, Any]:
    """Agregat per hari dalam satu bulan — digunakan untuk kalender heatmap."""
    result = await mcp_client.fetch_analytics("daily-trend", {"year": year, "month": month})
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/mcp-status", response_model=dict[str, Any])
async def mcp_status() -> dict[str, Any]:
    """Periksa status MCP server dan daftar domain yang dikenal."""
    return await mcp_client.list_domains()
