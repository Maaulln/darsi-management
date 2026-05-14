"""Endpoint health check untuk memantau status layanan backend."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Mengembalikan status layanan backend.

    Returns:
        Dictionary status sederhana untuk kebutuhan readiness probe.
    """

    return {"status": "ok"}
