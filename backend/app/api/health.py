"""Endpoint health & readiness untuk monitoring service backend DARSI."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.mcp_client import mcp_client

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
    """Periksa konektivitas: MCP server (liveness) + semua downstream via MCP."""
    status: dict[str, object] = {}

    mcp_live = mcp_client.health()
    status["mcp_server"] = "ok" if mcp_live.get("status") == "ok" else f"down: {mcp_live}"

    if status["mcp_server"] == "ok":
        downstream = mcp_client.health_downstream()
        status["surrealdb"] = downstream.get("surrealdb", "unknown")
        status["ollama"] = downstream.get("ollama", "unknown")
    else:
        status["surrealdb"] = "unreachable (mcp down)"
        status["ollama"] = "unreachable (mcp down)"

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    status["overall"] = overall
    return status
