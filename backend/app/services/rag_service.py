"""Service RAG DARSI: retrieve konteks (MCP/Chroma) lalu generate jawaban via Ollama."""

from __future__ import annotations

from typing import Any

import chromadb
import httpx

from app.core.config import settings
from app.services.mcp_client import mcp_client

COLLECTION_NAMES = [
    "darsi_pasien_aktif",
    "darsi_okupansi_kamar",
    "darsi_biaya_operasional",
    "darsi_konsumsi_obat_alkes",
    "darsi_lembur_staf",
    "darsi_meter_listrik",
    "darsi_konsumsi_air",
    "darsi_jadwal_alat_berat",
]


PROMPT_TEMPLATE = (
    "Anda adalah asisten analitik operasional rumah sakit DARSI Surabaya.\n"
    "Gunakan KONTEKS DATA OPERASIONAL berikut untuk menjawab pertanyaan dengan ringkas,\n"
    "akurat, dan dalam Bahasa Indonesia. Jika data tidak cukup, jelaskan terbatas pada\n"
    "fakta yang tersedia dan sarankan data tambahan yang dibutuhkan.\n\n"
    "KONTEKS DATA OPERASIONAL:\n"
    "{context}\n\n"
    "PERTANYAAN: {query}\n\n"
    "JAWABAN:"
)


def _get_chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def retrieve_context_chroma_only(query: str, n_results: int = 5) -> str:
    """Retrieval fallback langsung ke ChromaDB tanpa MCP server."""
    try:
        client = _get_chroma_client()
    except Exception as error:
        return f"[ChromaDB tidak tersedia: {error}]"

    all_docs: list[str] = []
    for col_name in COLLECTION_NAMES:
        try:
            collection = client.get_collection(col_name)
            results = collection.query(query_texts=[query], n_results=n_results)
            docs = results.get("documents", [[]])[0]
            if docs:
                all_docs.append(f"[{col_name}]")
                all_docs.extend(f"  • {doc}" for doc in docs)
        except Exception:
            continue

    if not all_docs:
        return "Tidak ada data operasional yang relevan ditemukan."
    return "\n".join(all_docs[:40])


def retrieve_context(query: str, n_results: int = 5) -> tuple[str, str, dict[str, Any]]:
    """Ambil konteks via MCP server bila tersedia, fallback ke ChromaDB direct.

    Args:
        query: Pertanyaan pengguna.
        n_results: Top-k per domain.

    Returns:
        Tuple (context_text, source, mcp_metadata).
    """
    mcp_payload = mcp_client.fetch_context(query, n_results=n_results)
    context = mcp_payload.get("context", "").strip()
    source = mcp_payload.get("source", "unavailable")

    if source in {"unavailable", "empty"} or not context:
        fallback = retrieve_context_chroma_only(query, n_results=n_results)
        return fallback, "chromadb_direct", mcp_payload

    return context, source, mcp_payload


def generate_with_ollama(query: str, context: str) -> str:
    """Kirim prompt RAG ke Ollama dan kembalikan jawaban.

    Args:
        query: Pertanyaan pengguna.
        context: Konteks yang dipakai sebagai grounding.

    Returns:
        Jawaban LLM (string).
    """
    prompt = PROMPT_TEMPLATE.format(context=context, query=query)
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }
    try:
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        return f"[Model tidak dapat dihubungi: {error}]"

    return response.json().get("response", "Model tidak memberikan jawaban.")


def rag_query(query: str, n_results: int = 5) -> dict[str, Any]:
    """Pipeline RAG lengkap: retrieve via MCP/Chroma → generate via Ollama."""
    context, source, mcp_payload = retrieve_context(query, n_results=n_results)
    answer = generate_with_ollama(query, context)
    return {
        "query": query,
        "context_used": context,
        "answer": answer,
        "source": source,
        "chroma_hits": mcp_payload.get("chroma_hits", 0),
        "surreal_hits": mcp_payload.get("surreal_hits", 0),
        "matched_domains": mcp_payload.get("matched_domains", []),
    }
