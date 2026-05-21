"""Endpoint ringkasan manajerial DARSI — semua data via MCP Server."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.mcp_client import mcp_client

router = APIRouter(prefix="/api/summary", tags=["summary"])


@router.get("/resource", response_model=dict[str, Any])
async def get_resource_summary() -> dict[str, Any]:
    """Ringkasan utilitas resource (listrik, air, okupansi) per unit."""
    result = await mcp_client.fetch_summary("resource")
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result


@router.get("/cost", response_model=dict[str, Any])
async def get_cost_summary() -> dict[str, Any]:
    """Ringkasan biaya operasional per unit & kategori."""
    result = await mcp_client.fetch_summary("cost")
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])
    return result
