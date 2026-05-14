"""Endpoint health & readiness untuk monitoring service backend DARSI."""

from __future__ import annotations

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.postgres import create_postgres_engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Liveness probe sederhana."""
    return {"status": "ok"}


@router.get("/api/health")
async def api_health_check() -> dict[str, str]:
    """Alias liveness probe di bawah prefix `/api/` untuk gateway Nginx."""
    return {"status": "ok"}


@router.get("/api/readiness")
async def readiness() -> dict[str, object]:
    """Periksa konektivitas downstream: Postgres, MCP server, dan Ollama."""

    status: dict[str, object] = {}

    try:
        engine = create_postgres_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception as error:  # noqa: BLE001
        status["postgres"] = f"down: {error}"

    try:
        response = httpx.get(f"{settings.mcp_server_url}/health", timeout=5.0)
        response.raise_for_status()
        status["mcp_server"] = "ok"
    except Exception as error:  # noqa: BLE001
        status["mcp_server"] = f"down: {error}"

    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
        response.raise_for_status()
        status["ollama"] = "ok"
    except Exception as error:  # noqa: BLE001
        status["ollama"] = f"down: {error}"

    overall = "ok" if all(value == "ok" for value in status.values()) else "degraded"
    status["overall"] = overall
    return status
