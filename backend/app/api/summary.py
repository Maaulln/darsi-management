"""Endpoint ringkasan manajerial untuk resource optimization dan cost efficiency."""

from typing import Any

from fastapi import APIRouter

from app.db.surrealdb import SurrealDBClient

router = APIRouter(prefix="/summary", tags=["summary"])
surreal_client = SurrealDBClient()


@router.get("/resource", response_model=dict[str, Any])
async def get_resource_summary() -> dict[str, Any]:
    """Mengambil ringkasan utilitas resource (listrik, air, okupansi).

    Returns:
        Dictionary berisi aggregat per unit:
        - listrik_kwh: Total konsumsi listrik per unit (kWh).
        - air_m3: Total konsumsi air per unit (m³).
        - bed_occupied: Jumlah tempat tidur terisi.
        - bed_capacity: Kapasitas tempat tidur total.
    """

    return surreal_client.get_resource_summary()


@router.get("/cost", response_model=dict[str, Any])
async def get_cost_summary() -> dict[str, Any]:
    """Mengambil ringkasan biaya operasional per unit dan kategori.

    Returns:
        Dictionary berisi:
        - total_cost_idr: Total pengeluaran per unit (Rp).
        - total_budget_idr: Total budget per unit (Rp).
        - categories: Breakdown per kategori biaya (listrik, air, consumables, dll).
    """

    return surreal_client.get_cost_summary()
