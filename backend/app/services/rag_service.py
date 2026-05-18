"""Service RAG DARSI — thin wrapper ke MCP Server (retrieval + generation via LangChain)."""

from __future__ import annotations

from typing import Any

from app.services.mcp_client import mcp_client


def rag_query(query: str, n_results: int = 5) -> dict[str, Any]:
    """Pipeline RAG lengkap: delegasikan ke MCP Server (SurrealDB vector + structured + Ollama)."""
    return mcp_client.generate(query, n_results=n_results, use_rag=True)


def direct_query(query: str) -> dict[str, Any]:
    """Query langsung ke LLM tanpa RAG — delegasikan ke MCP Server."""
    return mcp_client.generate(query, use_rag=False)
