"""Klien HTTP untuk berkomunikasi dengan MCP Server DARSI."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class MCPClient:
    """Klien untuk semua endpoint MCP Server."""

    def __init__(self, base_url: str | None = None, timeout: float = 15.0) -> None:
        self.base_url = (base_url or settings.mcp_server_url).rstrip("/")
        self.timeout = timeout

    # ── Health ────────────────────────────────────────────────────────────────

    def health(self) -> dict[str, str]:
        """Periksa liveness MCP server."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return {"status": "down"}

    def health_downstream(self) -> dict[str, object]:
        """Periksa status semua downstream via MCP (SurrealDB, Ollama)."""
        try:
            resp = httpx.get(
                f"{self.base_url}/mcp/health/downstream", timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {"overall": "down", "error": str(error)}

    # ── Domains & Data ────────────────────────────────────────────────────────

    def list_domains(self) -> dict[str, Any]:
        """Daftar domain operasional dari MCP server."""
        try:
            resp = httpx.get(f"{self.base_url}/mcp/domains", timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return {"domains": []}

    def fetch_domain_records(self, domain: str, limit: int = 50) -> dict[str, Any]:
        """Data clean satu domain dari MCP server."""
        try:
            resp = httpx.get(
                f"{self.base_url}/mcp/data/{domain}",
                params={"limit": limit},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {"domain": domain, "count": 0, "records": [], "error": str(error)}

    # ── Context ───────────────────────────────────────────────────────────────

    def fetch_context(
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
            resp = httpx.post(
                f"{self.base_url}/mcp/context",
                json=payload,
                timeout=self.timeout,
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

    def generate(
        self,
        query: str,
        n_results: int = 5,
        use_rag: bool = True,
    ) -> dict[str, Any]:
        """RAG retrieval + LLM generation via MCP server (LangChain + Ollama)."""
        payload: dict[str, Any] = {
            "query": query,
            "n_results": n_results,
            "use_rag": use_rag,
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/mcp/generate",
                json=payload,
                timeout=180.0,
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

    # ── Analytics ─────────────────────────────────────────────────────────────

    def fetch_analytics(self, endpoint: str) -> dict[str, Any]:
        """Ambil data analytics dari MCP server (overview, cost-by-category, dll.)."""
        try:
            resp = httpx.get(
                f"{self.base_url}/mcp/analytics/{endpoint}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {"error": str(error)}

    # ── Summary ───────────────────────────────────────────────────────────────

    def fetch_summary(self, endpoint: str) -> dict[str, Any]:
        """Ambil data summary dari MCP server (resource, cost)."""
        try:
            resp = httpx.get(
                f"{self.base_url}/mcp/summary/{endpoint}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as error:
            return {"error": str(error)}


mcp_client = MCPClient()
