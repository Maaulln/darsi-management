"""Klien HTTP ringan untuk berkomunikasi dengan MCP server DARSI."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class MCPClient:
    """Klien sederhana untuk endpoint MCP server."""

    def __init__(self, base_url: str | None = None, timeout: float = 15.0) -> None:
        self.base_url = (base_url or settings.mcp_server_url).rstrip("/")
        self.timeout = timeout

    def fetch_context(
        self,
        query: str,
        n_results: int = 5,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Mengambil konteks RAG (ChromaDB + SurrealDB) dari MCP server.

        Args:
            query: Pertanyaan pengguna.
            n_results: Jumlah dokumen top-k per domain.
            domains: Override pemilihan domain (opsional).

        Returns:
            Dictionary `ContextResponse` dari MCP server. Jika MCP server tidak
            tersedia, kembalikan struktur kosong dengan source `unavailable`.
        """
        payload: dict[str, Any] = {"query": query, "n_results": n_results}
        if domains:
            payload["domains"] = domains
        try:
            response = httpx.post(
                f"{self.base_url}/mcp/context",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as error:
            return {
                "source": "unavailable",
                "context": f"[MCP server tidak tersedia: {error}]",
                "chroma_hits": 0,
                "surreal_hits": 0,
                "matched_domains": [],
            }

    def list_domains(self) -> dict[str, Any]:
        """Mengambil daftar domain dari MCP server."""
        try:
            response = httpx.get(f"{self.base_url}/mcp/domains", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return {"domains": []}

    def fetch_domain_records(self, domain: str, limit: int = 50) -> dict[str, Any]:
        """Mengambil data clean dari satu domain via MCP server."""
        try:
            response = httpx.get(
                f"{self.base_url}/mcp/data/{domain}",
                params={"limit": limit},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as error:
            return {
                "domain": domain,
                "count": 0,
                "records": [],
                "error": str(error),
            }


mcp_client = MCPClient()
