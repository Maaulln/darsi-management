"""Endpoint ringkasan manajerial untuk resource & cost optimization DARSI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.db.surrealdb import SurrealDBClient

router = APIRouter(prefix="/api/summary", tags=["summary"])
surreal_client = SurrealDBClient()


@router.get("/resource", response_model=dict[str, Any])
async def get_resource_summary() -> dict[str, Any]:
    """Ringkasan utilitas resource (listrik, air, okupansi) per unit."""
    return surreal_client.get_resource_summary()


@router.get("/cost", response_model=dict[str, Any])
async def get_cost_summary() -> dict[str, Any]:
    """Ringkasan biaya operasional per unit & kategori."""
    return surreal_client.get_cost_summary()
