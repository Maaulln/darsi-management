"""DARSI MCP Server — konektor SurrealDB + ChromaDB untuk konteks RAG.

Endpoint:
    GET  /health                 → status service.
    POST /mcp/context            → konteks gabungan (Chroma + Surreal) berbasis intent query.
    GET  /mcp/domains            → daftar domain yang dikenal.
    GET  /mcp/data/{domain}      → ambil data clean langsung dari SurrealDB.
"""

from __future__ import annotations

import os
import re
from typing import Any

import chromadb
import httpx
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


DOMAINS: dict[str, dict[str, Any]] = {
    "pasien_aktif": {
        "chroma": "darsi_pasien_aktif",
        "surreal": "clean_pasien_aktif",
        "keywords": ["pasien", "patient", "rawat", "diagnosis"],
        "summary": "SELECT count() AS total, unit_code FROM clean_pasien_aktif GROUP BY unit_code;",
    },
    "okupansi_kamar": {
        "chroma": "darsi_okupansi_kamar",
        "surreal": "clean_okupansi_kamar",
        "keywords": ["okupansi", "kamar", "bed", "ranjang", "tempat tidur", "bor"],
        "summary": "SELECT unit_code, math::sum(bed_capacity) AS capacity, math::sum(bed_occupied) AS occupied FROM clean_okupansi_kamar GROUP BY unit_code;",
    },
    "biaya_operasional": {
        "chroma": "darsi_biaya_operasional",
        "surreal": "clean_biaya_operasional",
        "keywords": ["biaya", "cost", "budget", "anggaran", "pengeluaran"],
        "summary": "SELECT unit_code, cost_category, math::sum(amount_idr) AS total_cost FROM clean_biaya_operasional GROUP BY unit_code, cost_category;",
    },
    "konsumsi_obat_alkes": {
        "chroma": "darsi_konsumsi_obat_alkes",
        "surreal": "clean_konsumsi_obat_alkes",
        "keywords": ["obat", "alkes", "farmasi", "konsumsi obat"],
        "summary": "SELECT unit_code, item_type, math::sum(quantity) AS qty FROM clean_konsumsi_obat_alkes GROUP BY unit_code, item_type;",
    },
    "lembur_staf": {
        "chroma": "darsi_lembur_staf",
        "surreal": "clean_lembur_staf",
        "keywords": ["lembur", "overtime", "staf", "perawat", "dokter"],
        "summary": "SELECT unit_code, math::sum(overtime_hours) AS hours, math::sum(overtime_cost_idr) AS cost FROM clean_lembur_staf GROUP BY unit_code;",
    },
    "meter_listrik": {
        "chroma": "darsi_meter_listrik",
        "surreal": "clean_meter_listrik",
        "keywords": ["listrik", "kwh", "energi", "electricity"],
        "summary": "SELECT unit_code, math::sum(kwh_total) AS kwh FROM clean_meter_listrik GROUP BY unit_code;",
    },
    "konsumsi_air": {
        "chroma": "darsi_konsumsi_air",
        "surreal": "clean_konsumsi_air",
        "keywords": ["air", "water", "m3"],
        "summary": "SELECT unit_code, math::sum(volume_m3_total) AS volume FROM clean_konsumsi_air GROUP BY unit_code;",
    },
    "jadwal_alat_berat": {
        "chroma": "darsi_jadwal_alat_berat",
        "surreal": "clean_jadwal_alat_berat",
        "keywords": ["alat berat", "jadwal", "mri", "ct scan", "rontgen", "device"],
        "summary": "SELECT device_name, count() AS total FROM clean_jadwal_alat_berat GROUP BY device_name;",
    },
}


class ContextRequest(BaseModel):
    query: str
    n_results: int = 5
    domains: list[str] | None = None


class ContextResponse(BaseModel):
    source: str
    context: str
    surreal_hits: int = 0
    chroma_hits: int = 0
    matched_domains: list[str] = []


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Status service MCP."""
    return {"status": "ok", "service": "mcp-server"}


@app.get("/mcp/domains")
async def list_domains() -> dict[str, Any]:
    """Daftar domain operasional yang tersedia."""
    return {
        "domains": [
            {"name": name, "keywords": cfg["keywords"]}
            for name, cfg in DOMAINS.items()
        ]
    }


def detect_intent(query: str) -> list[str]:
    """Tebak domain relevan berdasarkan keyword pada query."""
    query_lower = query.lower()
    matched: list[str] = []
    for name, cfg in DOMAINS.items():
        if any(kw in query_lower for kw in cfg["keywords"]):
            matched.append(name)
    return matched or list(DOMAINS.keys())[:3]


async def query_surrealdb(sql: str) -> list[dict[str, Any]]:
    """Eksekusi query SQL ke SurrealDB. Kembalikan list dict (boleh kosong)."""
    sql_endpoint = SURREALDB_URL.rstrip("/").replace("/rpc", "") + "/sql"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            sql_endpoint,
            content=sql,
            headers={
                "Accept": "application/json",
                "surreal-ns": SURREALDB_NS,
                "surreal-db": SURREALDB_DB,
                "NS": SURREALDB_NS,
                "DB": SURREALDB_DB,
            },
            auth=(SURREALDB_USER, SURREALDB_PASSWORD),
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                result = first.get("result", [])
                return result if isinstance(result, list) else []
    return []


def query_chroma_domain(query: str, collection_name: str, n_results: int) -> list[str]:
    """Ambil dokumen relevan dari satu collection ChromaDB."""
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(collection_name)
        results = collection.query(query_texts=[query], n_results=n_results)
        docs = results.get("documents", [[]])[0]
        return list(docs)
    except Exception:
        return []


@app.post("/mcp/context", response_model=ContextResponse)
async def build_context(payload: ContextRequest) -> ContextResponse:
    """Bangun konteks operasional berdasarkan intent query.

    Strategi:
        1. Deteksi domain dari keyword (bila tidak di-provide eksplisit).
        2. Ambil top-k dokumen ChromaDB per domain (semantic).
        3. Eksekusi summary query SurrealDB per domain (structured).
        4. Susun konteks string siap pakai untuk prompt LLM.
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")

    target_domains = payload.domains or detect_intent(query)
    target_domains = [d for d in target_domains if d in DOMAINS]
    if not target_domains:
        target_domains = list(DOMAINS.keys())[:3]

    context_parts: list[str] = []
    chroma_hits = 0
    surreal_hits = 0

    for domain in target_domains:
        cfg = DOMAINS[domain]

        docs = query_chroma_domain(query, cfg["chroma"], payload.n_results)
        if docs:
            context_parts.append(f"[ChromaDB · {domain}]")
            context_parts.extend(f"  • {doc}" for doc in docs)
            chroma_hits += len(docs)

        try:
            records = await query_surrealdb(cfg["summary"])
        except Exception:
            records = []

        if records:
            context_parts.append(f"[SurrealDB · {domain} (aggregate)]")
            for record in records[:8]:
                snippet = ", ".join(
                    f"{key}={value}" for key, value in record.items() if value is not None
                )
                context_parts.append(f"  • {snippet}")
            surreal_hits += len(records)

    if not context_parts:
        return ContextResponse(
            source="empty",
            context=f"Tidak ditemukan konteks relevan untuk query: {query}",
            matched_domains=target_domains,
        )

    return ContextResponse(
        source="chromadb+surrealdb",
        context="\n".join(context_parts),
        chroma_hits=chroma_hits,
        surreal_hits=surreal_hits,
        matched_domains=target_domains,
    )


@app.get("/mcp/data/{domain}")
async def get_clean_domain(domain: str, limit: int = 50) -> dict[str, Any]:
    """Ambil data clean langsung dari SurrealDB untuk satu domain.

    Args:
        domain: Nama domain (mis. pasien_aktif).
        limit: Batas jumlah record.
    """
    if domain not in DOMAINS:
        raise HTTPException(status_code=404, detail=f"Domain {domain} tidak dikenal.")

    cfg = DOMAINS[domain]
    safe_limit = max(1, min(int(limit), 500))
    sql = f"SELECT * FROM {cfg['surreal']} LIMIT {safe_limit};"
    try:
        records = await query_surrealdb(sql)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"SurrealDB error: {error}") from error

    return {
        "domain": domain,
        "table": cfg["surreal"],
        "count": len(records),
        "records": records,
    }
