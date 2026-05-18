"""Endpoint analitik agregat operasional DARSI — semua data via MCP Server."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.mcp_client import mcp_client

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=dict[str, Any])
async def get_overview() -> dict[str, Any]:
    """KPI ringkasan tingkat tinggi untuk dashboard utama."""
    result = mcp_client.fetch_analytics("overview")
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/cost-by-category", response_model=dict[str, Any])
async def cost_by_category() -> dict[str, Any]:
    """Total biaya operasional dibreakdown per kategori biaya."""
    result = mcp_client.fetch_analytics("cost-by-category")
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/occupancy-by-unit", response_model=dict[str, Any])
async def occupancy_by_unit() -> dict[str, Any]:
    """Okupansi bed per unit untuk visualisasi bar chart."""
    result = mcp_client.fetch_analytics("occupancy-by-unit")
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/utility-trend", response_model=dict[str, Any])
async def utility_trend() -> dict[str, Any]:
    """Tren konsumsi utilitas (listrik & air) per unit."""
    result = mcp_client.fetch_analytics("utility-trend")
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/efficiency", response_model=dict[str, Any])
async def efficiency() -> dict[str, Any]:
    """Cost efficiency per unit: cost-per-service dan cost-to-revenue ratio."""
    result = mcp_client.fetch_analytics("efficiency")
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/staffing", response_model=dict[str, Any])
async def staffing() -> dict[str, Any]:
    """Staffing optimization: shift coverage vs overtime per unit."""
    result = mcp_client.fetch_analytics("staffing")
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/mcp-status", response_model=dict[str, Any])
async def mcp_status() -> dict[str, Any]:
    """Periksa status MCP server dan daftar domain yang dikenal."""
    return mcp_client.list_domains()
