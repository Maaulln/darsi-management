"""Entrypoint MCP server DARSI — konektor SurrealDB + ChromaDB RAG retrieval."""

from __future__ import annotations

import os
import httpx
import chromadb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="DARSI MCP Server")

CHROMA_HOST = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

SURREALDB_URL = os.getenv("SURREALDB_URL", "http://surrealdb:8000")
SURREALDB_USER = os.getenv("SURREALDB_USER", "root")
SURREALDB_PASSWORD = os.getenv("SURREALDB_PASSWORD", "root")
SURREALDB_NS = os.getenv("SURREALDB_NS", "darsi")
SURREALDB_DB = os.getenv("SURREALDB_DB", "operasional")

CHROMA_COLLECTIONS = [
    "darsi_pasien_aktif",
    "darsi_okupansi_kamar",
    "darsi_biaya_operasional",
    "darsi_konsumsi_obat_alkes",
    "darsi_lembur_staf",
    "darsi_meter_listrik",
]


class ContextRequest(BaseModel):
    query: str
    n_results: int = 5


class ContextResponse(BaseModel):
    source: str
    context: str
    surreal_hits: int = 0
    chroma_hits: int = 0


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "mcp-server"}


@app.post("/mcp/context", response_model=ContextResponse)
async def build_context(payload: ContextRequest) -> ContextResponse:
    """Mengambil konteks operasional dari ChromaDB dan/atau SurrealDB.

    Strategi:
    1. Query ChromaDB (vector similarity) untuk konteks semantik.
    2. Query SurrealDB untuk data agregat terstruktur.
    3. Gabungkan hasil sebagai konteks RAG.

    Args:
        payload: Query dan jumlah hasil yang diinginkan.

    Returns:
        Konteks terstruktur siap pakai untuk prompt LLM.
    """
    query = payload.query.strip()
    context_parts: list[str] = []
    chroma_hits = 0
    surreal_hits = 0

    # ── 1. ChromaDB semantic retrieval ──────────────────────────────────
    try:
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        for col_name in CHROMA_COLLECTIONS:
            try:
                col = chroma_client.get_collection(col_name)
                results = col.query(query_texts=[query], n_results=payload.n_results)
                docs = results.get("documents", [[]])[0]
                if docs:
                    context_parts.append(f"[{col_name}]")
                    context_parts.extend(f"  • {d}" for d in docs)
                    chroma_hits += len(docs)
            except Exception:
                continue
    except Exception as e:
        context_parts.append(f"[ChromaDB tidak tersedia: {e}]")

    # ── 2. SurrealDB structured query ────────────────────────────────────
    try:
        sql_endpoint = SURREALDB_URL.replace("/rpc", "") + "/sql"
        surreal_query = f"SELECT * FROM clean_pasien_aktif WHERE unit_code IS NOT NONE LIMIT 5;"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                sql_endpoint,
                content=surreal_query,
                headers={
                    "Accept": "application/json",
                    "NS": SURREALDB_NS,
                    "DB": SURREALDB_DB,
                },
                auth=(SURREALDB_USER, SURREALDB_PASSWORD),
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    records = data[0].get("result", [])
                    surreal_hits = len(records)
                    if records:
                        context_parts.append("[SurrealDB clean_pasien_aktif]")
                        for r in records[:3]:
                            context_parts.append(
                                f"  • Pasien {r.get('patient_id')} unit {r.get('unit_code')} "
                                f"status {r.get('status_aktif')}"
                            )
    except Exception as e:
        context_parts.append(f"[SurrealDB tidak tersedia: {e}]")

    if not context_parts:
        context_text = f"Tidak ditemukan konteks relevan untuk query: {query}"
        source = "empty"
    else:
        context_text = "\n".join(context_parts)
        source = "chromadb+surrealdb"

    return ContextResponse(
        source=source,
        context=context_text,
        chroma_hits=chroma_hits,
        surreal_hits=surreal_hits,
    )
