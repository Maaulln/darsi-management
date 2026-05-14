"""Endpoint data operasional DARSI — daftar domain, sample data, dan record detail."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.mcp_client import mcp_client

router = APIRouter(prefix="/api/data", tags=["data"])

DUMMY_RECORDS: list[dict[str, str]] = [
    {
        "id": "SIMRS-001",
        "unit": "Rawat Inap",
        "indikator": "Bed Occupancy Rate",
        "nilai": "72%",
    },
    {
        "id": "SIMRS-002",
        "unit": "IGD",
        "indikator": "Waktu Tunggu",
        "nilai": "18 menit",
    },
]


@router.get("/list")
async def list_data() -> dict[str, list[dict[str, str]]]:
    """Daftar contoh indikator operasional MVP."""
    return {"items": DUMMY_RECORDS}


@router.get("/domains")
async def list_domains() -> dict[str, Any]:
    """Daftar domain clean yang tersedia di MCP server."""
    return mcp_client.list_domains()


@router.get("/domain/{domain}")
async def get_domain_data(domain: str, limit: int = 50) -> dict[str, Any]:
    """Ambil data clean dari satu domain via MCP server.

    Args:
        domain: Nama domain (mis. okupansi_kamar, biaya_operasional).
        limit: Jumlah record maksimal.
    """
    payload = mcp_client.fetch_domain_records(domain, limit=limit)
    if payload.get("error"):
        raise HTTPException(status_code=502, detail=payload["error"])
    return payload


@router.get("/{record_id}")
async def get_data(record_id: str) -> dict[str, str]:
    """Ambil detail satu record dummy berdasarkan ID."""
    for record in DUMMY_RECORDS:
        if record["id"] == record_id:
            return record
    raise HTTPException(status_code=404, detail="Record tidak ditemukan")
