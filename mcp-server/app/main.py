"""DARSI MCP Server — Data Connector + Context Manager + AI Generation.

Endpoint:
    GET  /health                         → status service.
    GET  /mcp/health/downstream          → status semua downstream (SurrealDB, Ollama).
    GET  /mcp/domains                    → daftar domain yang dikenal.
    GET  /mcp/data/{domain}              → data clean dari SurrealDB per domain.
    POST /mcp/context                    → konteks gabungan (vector + structured) berbasis query.
    POST /mcp/generate                   → RAG retrieval + LLM generation via LangChain.
    GET  /mcp/analytics/overview         → KPI agregat semua domain.
    GET  /mcp/analytics/cost-by-category → biaya operasional per kategori.
    GET  /mcp/analytics/occupancy-by-unit→ okupansi bed per unit.
    GET  /mcp/analytics/utility-trend    → tren konsumsi listrik & air per unit.
    GET  /mcp/summary/resource           → ringkasan utilitas resource per unit.
    GET  /mcp/summary/cost               → ringkasan biaya per unit & kategori.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM
from pydantic import BaseModel

app = FastAPI(title="DARSI MCP Server")

# ─── Config ──────────────────────────────────────────────────────────────────

SURREALDB_URL = os.getenv("SURREALDB_URL", "http://surrealdb:8000")
SURREALDB_USER = os.getenv("SURREALDB_USER", "root")
SURREALDB_PASSWORD = os.getenv("SURREALDB_PASSWORD", "root")
SURREALDB_NS = os.getenv("SURREALDB_NS", "darsi")
SURREALDB_DB = os.getenv("SURREALDB_DB", "operasional")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = 768

# ─── LangChain Chain ─────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "Anda adalah asisten analitik operasional rumah sakit DARSI Surabaya.\n"
    "Gunakan KONTEKS DATA OPERASIONAL berikut untuk menjawab pertanyaan dengan ringkas,\n"
    "akurat, dan dalam Bahasa Indonesia. Jika data tidak cukup, jelaskan terbatas pada\n"
    "fakta yang tersedia dan sarankan data tambahan yang dibutuhkan.\n\n"
    "KONTEKS DATA OPERASIONAL:\n"
    "{context}\n\n"
    "PERTANYAAN: {query}\n\n"
    "JAWABAN:"
)


def _build_chain():
    llm = OllamaLLM(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, timeout=120)
    return _PROMPT_TEMPLATE | llm | StrOutputParser()


# ─── Domain Registry ─────────────────────────────────────────────────────────

DOMAINS: dict[str, dict[str, Any]] = {
    "pasien_aktif": {
        "surreal": "clean_pasien_aktif",
        "vector": "vector_darsi_pasien_aktif",
        "keywords": ["pasien", "patient", "rawat", "diagnosis"],
        "summary": "SELECT count() AS total, unit_code FROM clean_pasien_aktif GROUP BY unit_code;",
    },
    "okupansi_kamar": {
        "surreal": "clean_okupansi_kamar",
        "vector": "vector_darsi_okupansi_kamar",
        "keywords": ["okupansi", "kamar", "bed", "ranjang", "tempat tidur", "bor"],
        "summary": "SELECT unit_code, math::sum(bed_capacity) AS capacity, math::sum(bed_occupied) AS occupied FROM clean_okupansi_kamar GROUP BY unit_code;",
    },
    "biaya_operasional": {
        "surreal": "clean_biaya_operasional",
        "vector": "vector_darsi_biaya_operasional",
        "keywords": ["biaya", "cost", "budget", "anggaran", "pengeluaran"],
        "summary": "SELECT unit_code, cost_category, math::sum(amount_idr) AS total_cost FROM clean_biaya_operasional GROUP BY unit_code, cost_category;",
    },
    "konsumsi_obat_alkes": {
        "surreal": "clean_konsumsi_obat_alkes",
        "vector": "vector_darsi_konsumsi_obat_alkes",
        "keywords": ["obat", "alkes", "farmasi", "konsumsi obat"],
        "summary": "SELECT unit_code, item_type, math::sum(quantity) AS qty FROM clean_konsumsi_obat_alkes GROUP BY unit_code, item_type;",
    },
    "lembur_staf": {
        "surreal": "clean_lembur_staf",
        "vector": "vector_darsi_lembur_staf",
        "keywords": ["lembur", "overtime", "staf", "perawat", "dokter"],
        "summary": "SELECT unit_code, math::sum(overtime_hours) AS hours, math::sum(overtime_cost_idr) AS cost FROM clean_lembur_staf GROUP BY unit_code;",
    },
    "meter_listrik": {
        "surreal": "clean_meter_listrik",
        "vector": "vector_darsi_meter_listrik",
        "keywords": ["listrik", "kwh", "energi", "electricity"],
        "summary": "SELECT unit_code, math::sum(kwh_total) AS kwh FROM clean_meter_listrik GROUP BY unit_code;",
    },
    "konsumsi_air": {
        "surreal": "clean_konsumsi_air",
        "vector": "vector_darsi_konsumsi_air",
        "keywords": ["air", "water", "m3"],
        "summary": "SELECT unit_code, math::sum(volume_m3_total) AS volume FROM clean_konsumsi_air GROUP BY unit_code;",
    },
    "jadwal_alat_berat": {
        "surreal": "clean_jadwal_alat_berat",
        "vector": "vector_darsi_jadwal_alat_berat",
        "keywords": ["alat berat", "jadwal", "mri", "ct scan", "rontgen", "device"],
        "summary": "SELECT device_name, count() AS total FROM clean_jadwal_alat_berat GROUP BY device_name;",
    },
}

# ─── Schemas ─────────────────────────────────────────────────────────────────


class ContextRequest(BaseModel):
    query: str
    n_results: int = 5
    domains: list[str] | None = None


class ContextResponse(BaseModel):
    source: str
    context: str
    surreal_hits: int = 0
    vector_hits: int = 0
    matched_domains: list[str] = []


class GenerateRequest(BaseModel):
    query: str
    n_results: int = 5
    use_rag: bool = True


class GenerateResponse(BaseModel):
    query: str
    answer: str
    context_used: str = ""
    source: str = "ollama"
    vector_hits: int = 0
    surreal_hits: int = 0
    matched_domains: list[str] = []


# ─── Internal Helpers ─────────────────────────────────────────────────────────


async def _query_surrealdb(sql: str) -> list[dict[str, Any]]:
    """Eksekusi SQL ke SurrealDB. Kembalikan list dari result statement terakhir."""
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
            last = payload[-1]
            if isinstance(last, dict):
                result = last.get("result", [])
                return result if isinstance(result, list) else []
    return []


async def _get_query_embedding(text: str) -> list[float]:
    """Generate embedding vector untuk query teks via Ollama."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def _query_surrealdb_vector(query: str, vector_table: str, n_results: int) -> list[str]:
    """Semantic search pada SurrealDB vector index untuk satu domain."""
    try:
        embedding = await _get_query_embedding(query)
    except Exception:
        return []

    emb_json = json.dumps(embedding)
    sql = (
        f"SELECT text, vector::similarity::cosine(embedding, {emb_json}) AS score "
        f"FROM {vector_table} "
        f"ORDER BY score DESC LIMIT {n_results};"
    )
    try:
        records = await _query_surrealdb(sql)
        return [r["text"] for r in records if "text" in r]
    except Exception:
        return []


def _detect_intent(query: str) -> list[str]:
    """Tebak domain relevan berdasarkan keyword pada query."""
    query_lower = query.lower()
    matched: list[str] = []
    for name, cfg in DOMAINS.items():
        if any(kw in query_lower for kw in cfg["keywords"]):
            matched.append(name)
    return matched or list(DOMAINS.keys())[:3]


async def _build_rag_context(
    query: str, n_results: int, target_domains: list[str]
) -> tuple[str, int, int]:
    """Susun konteks dari SurrealDB vector + structured untuk domain yang ditargetkan."""
    context_parts: list[str] = []
    vector_hits = 0
    surreal_hits = 0

    for domain in target_domains:
        cfg = DOMAINS[domain]

        # Vector similarity search
        docs = await _query_surrealdb_vector(query, cfg["vector"], n_results)
        if docs:
            context_parts.append(f"[Vector Search · {domain}]")
            context_parts.extend(f"  • {doc}" for doc in docs)
            vector_hits += len(docs)

        # Structured aggregate query
        try:
            records = await _query_surrealdb(cfg["summary"])
        except Exception:
            records = []

        if records:
            context_parts.append(f"[Agregat · {domain}]")
            for record in records[:8]:
                snippet = ", ".join(
                    f"{k}={v}" for k, v in record.items() if v is not None
                )
                context_parts.append(f"  • {snippet}")
            surreal_hits += len(records)

    context = "\n".join(context_parts) if context_parts else ""
    return context, vector_hits, surreal_hits


# ─── Health ───────────────────────────────────────────────────────────────────


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "mcp-server"}


@app.get("/mcp/health/downstream")
async def health_downstream() -> dict[str, object]:
    """Periksa konektivitas ke SurrealDB dan Ollama."""
    status: dict[str, object] = {}

    try:
        await _query_surrealdb("RETURN 1;")
        status["surrealdb"] = "ok"
    except Exception as error:
        status["surrealdb"] = f"down: {error}"

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
        status["ollama"] = "ok"
    except Exception as error:
        status["ollama"] = f"down: {error}"

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    status["overall"] = overall
    return status


# ─── Domains & Data ──────────────────────────────────────────────────────────


@app.get("/mcp/domains")
async def list_domains() -> dict[str, Any]:
    return {
        "domains": [
            {"name": name, "keywords": cfg["keywords"]}
            for name, cfg in DOMAINS.items()
        ]
    }


@app.get("/mcp/data/{domain}")
async def get_clean_domain(domain: str, limit: int = 50) -> dict[str, Any]:
    if domain not in DOMAINS:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' tidak dikenal.")
    cfg = DOMAINS[domain]
    safe_limit = max(1, min(int(limit), 500))
    sql = f"SELECT * FROM {cfg['surreal']} LIMIT {safe_limit};"
    try:
        records = await _query_surrealdb(sql)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"SurrealDB error: {error}") from error
    return {"domain": domain, "table": cfg["surreal"], "count": len(records), "records": records}


# ─── Context ─────────────────────────────────────────────────────────────────


@app.post("/mcp/context", response_model=ContextResponse)
async def build_context(payload: ContextRequest) -> ContextResponse:
    """Bangun konteks operasional berbasis intent query (SurrealDB vector + structured)."""
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")

    target_domains = payload.domains or _detect_intent(query)
    target_domains = [d for d in target_domains if d in DOMAINS] or list(DOMAINS.keys())[:3]

    context, vector_hits, surreal_hits = await _build_rag_context(
        query, payload.n_results, target_domains
    )

    if not context:
        return ContextResponse(
            source="empty",
            context=f"Tidak ditemukan konteks relevan untuk query: {query}",
            matched_domains=target_domains,
        )

    return ContextResponse(
        source="surrealdb_vector+structured",
        context=context,
        vector_hits=vector_hits,
        surreal_hits=surreal_hits,
        matched_domains=target_domains,
    )


# ─── Generate (RAG + LLM via LangChain) ──────────────────────────────────────


@app.post("/mcp/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest) -> GenerateResponse:
    """RAG retrieval (SurrealDB vector + structured) + LLM generation via LangChain + Ollama."""
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")

    context = "(no context)"
    vector_hits = 0
    surreal_hits = 0
    matched_domains: list[str] = []
    source = "ollama_direct"

    if payload.use_rag:
        target_domains = _detect_intent(query)
        target_domains = [d for d in target_domains if d in DOMAINS] or list(DOMAINS.keys())[:3]
        matched_domains = target_domains

        context, vector_hits, surreal_hits = await _build_rag_context(
            query, payload.n_results, target_domains
        )
        if not context:
            context = "Tidak ada data operasional yang relevan ditemukan."
        source = "surrealdb_vector+structured+ollama"

    try:
        chain = _build_chain()
        answer = chain.invoke({"context": context, "query": query})
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"LLM error: {error}") from error

    return GenerateResponse(
        query=query,
        answer=answer,
        context_used=context,
        source=source,
        vector_hits=vector_hits,
        surreal_hits=surreal_hits,
        matched_domains=matched_domains,
    )


# ─── Analytics ────────────────────────────────────────────────────────────────


@app.get("/mcp/analytics/overview")
async def analytics_overview() -> dict[str, Any]:
    """KPI ringkasan tingkat tinggi dari semua domain."""
    queries = {
        "pasien_total": "SELECT count() AS total FROM clean_pasien_aktif GROUP ALL",
        "okupansi": "SELECT math::sum(bed_capacity) AS capacity, math::sum(bed_occupied) AS occupied FROM clean_okupansi_kamar GROUP ALL",
        "listrik": "SELECT math::sum(kwh_total) AS kwh FROM clean_meter_listrik GROUP ALL",
        "air": "SELECT math::sum(volume_m3_total) AS volume FROM clean_konsumsi_air GROUP ALL",
        "biaya": "SELECT math::sum(amount_idr) AS total_cost, math::sum(budget_idr) AS total_budget FROM clean_biaya_operasional GROUP ALL",
        "lembur": "SELECT math::sum(overtime_hours) AS hours, math::sum(overtime_cost_idr) AS cost FROM clean_lembur_staf GROUP ALL",
    }

    result: dict[str, Any] = {}
    for key, sql in queries.items():
        try:
            records = await _query_surrealdb(sql)
            result[key] = records[0] if records else {}
        except Exception:
            result[key] = {}

    capacity = result.get("okupansi", {}).get("capacity") or 0
    occupied = result.get("okupansi", {}).get("occupied") or 0
    bor_pct = round(100 * occupied / capacity, 2) if capacity else 0.0

    total_cost = result.get("biaya", {}).get("total_cost") or 0
    total_budget = result.get("biaya", {}).get("total_budget") or 0
    budget_usage_pct = round(100 * total_cost / total_budget, 2) if total_budget else 0.0

    return {
        "kpi": {
            "pasien_aktif": result.get("pasien_total", {}).get("total", 0),
            "bed_capacity": capacity,
            "bed_occupied": occupied,
            "bor_pct": bor_pct,
            "kwh_total": result.get("listrik", {}).get("kwh", 0),
            "air_m3_total": result.get("air", {}).get("volume", 0),
            "total_cost_idr": total_cost,
            "total_budget_idr": total_budget,
            "budget_usage_pct": budget_usage_pct,
            "overtime_hours": result.get("lembur", {}).get("hours", 0),
            "overtime_cost_idr": result.get("lembur", {}).get("cost", 0),
        },
        "raw": result,
    }


@app.get("/mcp/analytics/cost-by-category")
async def analytics_cost_by_category() -> dict[str, Any]:
    sql = (
        "SELECT cost_category, math::sum(amount_idr) AS total_cost,"
        " math::sum(budget_idr) AS total_budget"
        " FROM clean_biaya_operasional GROUP BY cost_category"
    )
    try:
        records = await _query_surrealdb(sql)
    except Exception:
        records = []
    return {"categories": records}


@app.get("/mcp/analytics/occupancy-by-unit")
async def analytics_occupancy_by_unit() -> dict[str, Any]:
    sql = (
        "SELECT unit_code, math::sum(bed_capacity) AS capacity,"
        " math::sum(bed_occupied) AS occupied"
        " FROM clean_okupansi_kamar GROUP BY unit_code"
    )
    try:
        records = await _query_surrealdb(sql)
    except Exception:
        records = []
    return {"units": records}


@app.get("/mcp/analytics/utility-trend")
async def analytics_utility_trend() -> dict[str, Any]:
    try:
        listrik = await _query_surrealdb(
            "SELECT unit_code, math::sum(kwh_total) AS kwh FROM clean_meter_listrik GROUP BY unit_code"
        )
    except Exception:
        listrik = []
    try:
        air = await _query_surrealdb(
            "SELECT unit_code, math::sum(volume_m3_total) AS volume FROM clean_konsumsi_air GROUP BY unit_code"
        )
    except Exception:
        air = []
    return {"listrik": listrik, "air": air}


# ─── Summary ──────────────────────────────────────────────────────────────────


@app.get("/mcp/summary/resource")
async def summary_resource() -> dict[str, Any]:
    """Ringkasan utilitas resource (listrik, air, okupansi) per unit."""
    try:
        listrik_records = await _query_surrealdb(
            "SELECT unit_code, meter_id, building_code, kwh_total, reading_at FROM clean_meter_listrik"
        )
    except Exception:
        listrik_records = []
    try:
        air_records = await _query_surrealdb(
            "SELECT unit_code, meter_id, volume_m3_total, reading_at FROM clean_konsumsi_air"
        )
    except Exception:
        air_records = []
    try:
        okupansi_records = await _query_surrealdb(
            "SELECT unit_code, room_class, bed_capacity, bed_occupied, room_status FROM clean_okupansi_kamar"
        )
    except Exception:
        okupansi_records = []

    unit_map: dict[str, dict[str, Any]] = {}

    for record in listrik_records:
        unit = record.get("unit_code", "unknown")
        unit_map.setdefault(unit, {"unit_code": unit, "listrik_kwh": 0, "air_m3": 0, "bed_occupied": 0, "bed_capacity": 0})
        unit_map[unit]["listrik_kwh"] += record.get("kwh_total", 0)

    for record in air_records:
        unit = record.get("unit_code", "unknown")
        unit_map.setdefault(unit, {"unit_code": unit, "listrik_kwh": 0, "air_m3": 0, "bed_occupied": 0, "bed_capacity": 0})
        unit_map[unit]["air_m3"] += record.get("volume_m3_total", 0)

    for record in okupansi_records:
        unit = record.get("unit_code", "unknown")
        unit_map.setdefault(unit, {"unit_code": unit, "listrik_kwh": 0, "air_m3": 0, "bed_occupied": 0, "bed_capacity": 0})
        unit_map[unit]["bed_occupied"] += record.get("bed_occupied", 0)
        unit_map[unit]["bed_capacity"] += record.get("bed_capacity", 0)

    return {"units": list(unit_map.values())}


@app.get("/mcp/summary/cost")
async def summary_cost() -> dict[str, Any]:
    """Ringkasan biaya operasional per unit & kategori."""
    try:
        cost_records = await _query_surrealdb(
            "SELECT unit_code, cost_category, amount_idr, budget_idr, period_month FROM clean_biaya_operasional"
        )
    except Exception:
        cost_records = []

    unit_map: dict[str, dict[str, Any]] = {}
    for record in cost_records:
        unit = record.get("unit_code", "unknown")
        unit_map.setdefault(unit, {"unit_code": unit, "total_cost_idr": 0, "total_budget_idr": 0, "categories": {}})
        cat = record.get("cost_category", "other")
        amount = record.get("amount_idr", 0)
        budget = record.get("budget_idr", 0)
        unit_map[unit]["total_cost_idr"] += amount
        unit_map[unit]["total_budget_idr"] += budget
        unit_map[unit]["categories"].setdefault(cat, {"amount_idr": 0, "budget_idr": 0})
        unit_map[unit]["categories"][cat]["amount_idr"] += amount
        unit_map[unit]["categories"][cat]["budget_idr"] += budget

    return {"units": list(unit_map.values())}
