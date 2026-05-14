"""Endpoint data operasional awal untuk MVP DARSI."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/data", tags=["data"])

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
    """Mengambil daftar data operasional contoh.

    Returns:
        Dictionary berisi list record operasional untuk kebutuhan UI awal.
    """

    return {"items": DUMMY_RECORDS}


@router.get("/{record_id}")
async def get_data(record_id: str) -> dict[str, str]:
    """Mengambil detail data berdasarkan ID.

    Args:
        record_id: ID record operasional.

    Returns:
        Satu record data operasional.

    Raises:
        HTTPException: Jika data dengan ID terkait tidak ditemukan.
    """

    for record in DUMMY_RECORDS:
        if record["id"] == record_id:
            return record

    raise HTTPException(status_code=404, detail="Record tidak ditemukan")
