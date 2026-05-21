"""Klien HTTP untuk berkomunikasi dengan MCP Server DARSI."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.config import settings


async def _get_db_ai_config() -> tuple[str, str]:
    def _sync_fetch() -> tuple[str, str]:
        try:
            from sqlalchemy import text
            from app.services.postgres import engine
            with engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT key, value FROM darsi_settings"
                        " WHERE key IN ('ai_url', 'ai_model')"
                    )
                ).fetchall()
                data = {row[0]: row[1] for row in rows}
                return data.get("ai_url") or "", data.get("ai_model") or ""
        except Exception:
            return "", ""

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sync_fetch)


class MCPClient:
    """Klien untuk semua endpoint MCP Server."""

    def __init__(self, base_url: str | None = None, timeout: float = 15.0) -> None:
        self.base_url = (base_url or settings.mcp_server_url).rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    # ── Health ────────────────────────────────────────────────────────────────

    async def health(self) -> dict[str, str]:
        """Periksa liveness MCP server."""
        try:
            resp = await self._http.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return {"status": "down"}

    async def health_downstream(self) -> dict[str, object]:
        """Periksa status semua downstream via MCP (SurrealDB, Ollama)."""
        try:
            resp = await self._http.get(
                f"{self.base_url}/mcp/health/downstream"
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {"overall": "down", "error": str(error)}

    # ── Domains & Data ────────────────────────────────────────────────────────

    async def list_domains(self) -> dict[str, Any]:
        """Daftar domain operasional dari MCP server."""
        try:
            resp = await self._http.get(f"{self.base_url}/mcp/domains")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return {"domains": []}

    async def fetch_domain_records(self, domain: str, limit: int = 50) -> dict[str, Any]:
        """Data clean satu domain dari MCP server."""
        try:
            resp = await self._http.get(
                f"{self.base_url}/mcp/data/{domain}",
                params={"limit": limit},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {"domain": domain, "count": 0, "records": [], "error": str(error)}

    # ── Context ───────────────────────────────────────────────────────────────

    async def fetch_context(
        self,
        query: str,
        n_results: int = 5,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Konteks RAG (SurrealDB vector + structured) dari MCP server."""
        payload: dict[str, Any] = {"query": query, "n_results": n_results}
        if domains:
            payload["domains"] = domains
        try:
            resp = await self._http.post(
                f"{self.base_url}/mcp/context",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {
                "source": "unavailable",
                "context": f"[MCP server tidak tersedia: {error}]",
                "vector_hits": 0,
                "surreal_hits": 0,
                "matched_domains": [],
            }

    # ── Generate (RAG + LLM) ──────────────────────────────────────────────────

    async def generate(
        self,
        query: str,
        n_results: int = 5,
        use_rag: bool = True,
    ) -> dict[str, Any]:
        """RAG retrieval + LLM generation via MCP server (LangChain + Ollama)."""
        url, model = await _get_db_ai_config()
        payload: dict[str, Any] = {
            "query": query,
            "n_results": n_results,
            "use_rag": use_rag,
            "ai_url": url,
            "ai_model": model,
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    f"{self.base_url}/mcp/generate",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as error:
            return {
                "query": query,
                "answer": f"[Gagal menghubungi MCP server: {error}]",
                "context_used": "",
                "source": "error",
                "vector_hits": 0,
                "surreal_hits": 0,
                "matched_domains": [],
            }

    async def generate_stream(
        self,
        query: str,
        n_results: int = 5,
        use_rag: bool = True,
    ):
        """RAG + LLM streaming via MCP server — yield token chunks secara async."""
        url, model = await _get_db_ai_config()
        payload: dict[str, Any] = {
            "query": query,
            "n_results": n_results,
            "use_rag": use_rag,
            "ai_url": url,
            "ai_model": model,
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST", f"{self.base_url}/mcp/generate/stream", json=payload
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_text():
                    yield chunk

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def fetch_analytics(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Ambil data analytics dari MCP server (overview, cost-by-category, dll.)."""
        try:
            resp = await self._http.get(
                f"{self.base_url}/mcp/analytics/{endpoint}",
                params={k: v for k, v in (params or {}).items() if v is not None},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {"error": str(error)}

    # ── Summary ───────────────────────────────────────────────────────────────

    async def fetch_summary(self, endpoint: str) -> dict[str, Any]:
        """Ambil data summary dari MCP server (resource, cost)."""
        try:
            resp = await self._http.get(
                f"{self.base_url}/mcp/summary/{endpoint}",
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {"error": str(error)}


mcp_client = MCPClient()
