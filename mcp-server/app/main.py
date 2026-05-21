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
    GET  /mcp/analytics/efficiency       → cost-per-service & cost-to-revenue ratio per unit.
    GET  /mcp/analytics/staffing         → shift coverage vs overtime per unit.
    GET  /mcp/summary/resource           → ringkasan utilitas resource per unit.
    GET  /mcp/summary/cost               → ringkasan biaya per unit & kategori.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM
from pydantic import BaseModel
from sentence_transformers import CrossEncoder

app = FastAPI(title="DARSI MCP Server")


_SURREAL_HTTP: httpx.AsyncClient | None = None


def _get_surreal_http() -> httpx.AsyncClient:
    global _SURREAL_HTTP
    if _SURREAL_HTTP is None or _SURREAL_HTTP.is_closed:
        _SURREAL_HTTP = httpx.AsyncClient(timeout=10)
    return _SURREAL_HTTP


async def _cache_evict_loop() -> None:
    """Hapus cache entry yang sudah expired setiap 5 menit."""
    while True:
        await asyncio.sleep(300)
        now = time.monotonic()
        expired = [k for k, (_, ts) in list(_CACHE.items()) if (now - ts) > 600]
        for k in expired:
            _CACHE.pop(k, None)
        if expired:
            print(f"[INFO] Cache evicted {len(expired)} expired entries")


@app.on_event("startup")
async def _startup() -> None:
    """Inisialisasi shared HTTP client, pre-load cross-encoder, dan cache eviction."""
    global _SURREAL_HTTP
    _SURREAL_HTTP = httpx.AsyncClient(timeout=10)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _get_cross_encoder)
    asyncio.create_task(_cache_evict_loop())
    print(f"[INFO] Cross-encoder loaded: {_CROSS_ENCODER_MODEL}")


@app.on_event("shutdown")
async def _shutdown() -> None:
    global _SURREAL_HTTP
    if _SURREAL_HTTP and not _SURREAL_HTTP.is_closed:
        await _SURREAL_HTTP.aclose()

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

# ─── TTL Cache ────────────────────────────────────────────────────────────────
# Key → (value, timestamp). Digunakan untuk aggregate SurrealDB, embedding query,
# dan AI config agar tidak dipanggil ulang setiap request.

_CACHE: dict[str, tuple[Any, float]] = {}
_TTL_AGGREGATE    = 60.0   # detik — sinkron dengan interval n8n pipeline
_TTL_EMBEDDING    = 300.0  # 5 menit — query sama sering diulang user
_TTL_AI_CONFIG    = 30.0   # 30 detik — setting jarang berubah
_TTL_RETRIEVAL    = 120.0  # 2 menit — vector/BM25 results per (domain, query)
_TTL_LLM_RESPONSE = 60.0  # 1 menit — full LLM answer per query


def _cache_get(key: str, ttl: float) -> Any | None:
    entry = _CACHE.get(key)
    if entry and (time.monotonic() - entry[1]) < ttl:
        return entry[0]
    _CACHE.pop(key, None)
    return None


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (value, time.monotonic())


def _qhash(text: str) -> str:
    """Hash MD5 pendek untuk cache key retrieval."""
    return hashlib.md5(text.encode()).hexdigest()[:10]


async def _noop(value: Any) -> Any:
    """Coroutine placeholder — langsung return nilai cache hit."""
    return value


# ─── LLM Singleton Pool ───────────────────────────────────────────────────────
# OllamaLLM diinstansiasi sekali per (url, model) dan di-reuse antar request.

_LLM_POOL: dict[tuple[str, str], OllamaLLM] = {}


def _get_llm(url: str, model: str) -> OllamaLLM:
    key = (url, model)
    if key not in _LLM_POOL:
        _LLM_POOL[key] = OllamaLLM(base_url=url, model=model, timeout=120)
    return _LLM_POOL[key]


# ─── Cross-Encoder Singleton ──────────────────────────────────────────────────
# Model ringan (~22MB) untuk re-ranking kandidat dokumen setelah RRF.
# ms-marco-MiniLM-L-6-v2: fast CPU inference, ~50-150ms untuk 15 dokumen.

_CROSS_ENCODER_MODEL = os.getenv(
    "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
_CROSS_ENCODER: CrossEncoder | None = None


def _get_cross_encoder() -> CrossEncoder:
    global _CROSS_ENCODER
    if _CROSS_ENCODER is None:
        _CROSS_ENCODER = CrossEncoder(_CROSS_ENCODER_MODEL)
    return _CROSS_ENCODER


async def _rerank_batch_async(
    query: str,
    domain_docs: list[tuple[str, list[str]]],
    top_k: int,
) -> dict[str, list[str]]:
    """Batch cross-encoder re-rank untuk semua domain sekaligus — satu CPU call.

    Menggabungkan semua kandidat dokumen dari setiap domain ke dalam satu
    predict() call, lebih efisien dibanding N panggilan per-domain terpisah.
    Mengembalikan dict {domain: [top_k docs]}.
    """
    if not domain_docs:
        return {}

    # Flatten: [(domain, doc), ...]
    flat: list[tuple[str, str]] = [
        (domain, doc)
        for domain, docs in domain_docs
        for doc in docs
    ]
    if not flat:
        return {domain: [] for domain, _ in domain_docs}

    ce = _get_cross_encoder()
    pairs = [(query, doc) for _, doc in flat]
    loop = asyncio.get_running_loop()
    all_scores = await loop.run_in_executor(None, ce.predict, pairs)

    # Grup skor kembali per domain
    domain_scored: dict[str, list[tuple[float, str]]] = {}
    for (domain, doc), score in zip(flat, all_scores):
        domain_scored.setdefault(domain, []).append((score, doc))

    return {
        domain: [doc for _, doc in sorted(scored, key=lambda x: x[0], reverse=True)[:top_k]]
        for domain, scored in domain_scored.items()
    }


def _truncate_context(ctx: str, limit: int = 6000) -> str:
    """Potong context di batas karakter terakhir yang lengkap (baris penuh).

    Model 2B tidak perlu context >6000 karakter (~1500 token) —
    terlalu banyak justru menurunkan fokus dan memperlambat generasi.
    """
    if len(ctx) <= limit:
        return ctx
    truncated = ctx[:limit]
    last_nl = truncated.rfind('\n')
    return truncated[:last_nl] if last_nl > 0 else truncated


def _rank_retry_domains(query: str, checked: list[str]) -> list[str]:
    """Ranking domain yang belum dicari berdasarkan relevansi terhadap query.

    Digunakan Self-RAG retry agar tidak membabi-buta mencari ke 13 domain —
    cukup top-5 domain yang paling relevan dengan kata kunci query.
    """
    q_lower = query.lower()
    q_words = set(q_lower.split())
    unchecked = [d for d in DOMAINS if d not in checked]

    def _score(domain: str) -> float:
        kws = DOMAINS[domain]["keywords"]
        exact = sum(1.0 for kw in kws if kw in q_lower)
        word_overlap = len(q_words & set(" ".join(kws).split()))
        return exact * 2.0 + word_overlap * 0.5

    return sorted(unchecked, key=_score, reverse=True)[:5]


# ─── LangChain Chain ─────────────────────────────────────────────────────────

# Prompt ringkas dan terarah untuk model kecil (2B) — hindari instruksi verbose
# yang memaksa model menghasilkan terlalu banyak token sebelum menjawab inti.
_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "Anda adalah analis data RS DARSI Surabaya.\n\n"
    "DATA OPERASIONAL:\n{context}\n\n"
    "PERTANYAAN: {query}\n\n"
    "Instruksi: Jawab singkat dan spesifik dalam Bahasa Indonesia. "
    "Gunakan HANYA data di atas. Sebutkan angka/fakta kunci. "
    "Jika data tidak cukup, nyatakan secara eksplisit.\n\n"
    "JAWABAN:"
)

# Prompt ringkas untuk HyDE — generate jawaban hipotetis singkat
# agar embedding-nya lebih mendekati dokumen di vector store daripada embedding query mentah.
_HYDE_PROMPT = PromptTemplate.from_template(
    "Buat satu kalimat singkat dalam Bahasa Indonesia yang merupakan contoh data "
    "operasional rumah sakit yang relevan dengan pertanyaan berikut:\n\n"
    "Pertanyaan: {query}\n\nContoh data:"
)


async def _get_ai_config() -> tuple[str, str]:
    cached = _cache_get("ai_config", _TTL_AI_CONFIG)
    if cached is not None:
        return cached
    url = OLLAMA_BASE_URL
    model = OLLAMA_MODEL
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get("http://backend:8000/api/settings/ai")
            if r.status_code == 200:
                data = r.json()
                if data.get("url"):
                    u = data["url"].strip()
                    if u.endswith("/"): u = u[:-1]
                    if u.endswith("/api/generate"): u = u[:-13]
                    elif u.endswith("/api/embeddings"): u = u[:-15]
                    if u.endswith("/"): u = u[:-1]
                    url = u
                if data.get("model"): model = data["model"]
    except Exception:
        pass
    result = (url, model)
    _cache_set("ai_config", result)
    return result


async def _build_chain(
    has_context: bool = True,
    ai_url: str | None = None,
    ai_model: str | None = None,
):
    url = ai_url
    model = ai_model
    if not url or not model:
        db_url, db_model = await _get_ai_config()
        if not url: url = db_url
        if not model: model = db_model

    llm = _get_llm(url, model)

    if has_context:
        prompt = _PROMPT_TEMPLATE
    else:
        # Prompt super minimal untuk query non-operasional/sapaan
        # Ini menghemat prompt-prefill token secara drastis pada CPU Ollama lambat
        prompt = PromptTemplate.from_template("{query}")

    return prompt | llm | StrOutputParser()


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
    "kunjungan_layanan": {
        "surreal": "clean_kunjungan_layanan",
        "vector": "vector_darsi_kunjungan_layanan",
        "keywords": ["kunjungan", "pasien baru", "tindakan", "rawat jalan", "rawat inap", "igd", "operasi", "throughput"],
        "summary": "SELECT unit_code, layanan_type, math::sum(jumlah_kunjungan) AS total_kunjungan, math::sum(jumlah_tindakan) AS total_tindakan FROM clean_kunjungan_layanan GROUP BY unit_code, layanan_type;",
    },
    "pendapatan_unit": {
        "surreal": "clean_pendapatan_unit",
        "vector": "vector_darsi_pendapatan_unit",
        "keywords": ["pendapatan", "revenue", "pemasukan", "penerimaan", "bpjs", "tarif layanan"],
        "summary": "SELECT unit_code, payer_type, math::sum(amount_idr) AS total_revenue, math::sum(target_idr) AS total_target FROM clean_pendapatan_unit GROUP BY unit_code, payer_type;",
    },
    "jadwal_staf": {
        "surreal": "clean_jadwal_staf",
        "vector": "vector_darsi_jadwal_staf",
        "keywords": ["jadwal staf", "shift", "absensi", "kehadiran", "perawat shift", "jam kerja"],
        "summary": "SELECT unit_code, shift_type, count() AS total_shift, math::sum(scheduled_hours) AS scheduled_hours, math::sum(actual_hours) AS actual_hours FROM clean_jadwal_staf GROUP BY unit_code, shift_type;",
    },
    "downtime_alat": {
        "surreal": "clean_downtime_alat",
        "vector": "vector_darsi_downtime_alat",
        "keywords": ["downtime", "kerusakan alat", "alat rusak", "maintenance alat", "perbaikan", "unplanned"],
        "summary": "SELECT device_name, downtime_type, count() AS total_event, math::sum(repair_cost_idr) AS total_repair_cost FROM clean_downtime_alat GROUP BY device_name, downtime_type;",
    },
    "tarif_utilitas": {
        "surreal": "clean_tarif_utilitas",
        "vector": "vector_darsi_tarif_utilitas",
        "keywords": ["tarif listrik", "tarif air", "harga kwh", "harga air", "pln tarif", "pdam tarif"],
        "summary": "SELECT utility_type, tariff_per_unit, unit_uom, effective_date FROM clean_tarif_utilitas ORDER BY effective_date DESC LIMIT 10;",
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
    ai_url: str | None = None
    ai_model: str | None = None


class GenerateResponse(BaseModel):
    query: str
    answer: str
    context_used: str = ""
    source: str = "ollama"
    vector_hits: int = 0
    surreal_hits: int = 0
    matched_domains: list[str] = []


# ─── Internal Helpers ─────────────────────────────────────────────────────────


_SURREAL_SQL_ENDPOINT = SURREALDB_URL.rstrip("/").replace("/rpc", "") + "/sql"
_SURREAL_HEADERS = {
    "Accept": "application/json",
    "surreal-ns": SURREALDB_NS,
    "surreal-db": SURREALDB_DB,
    "NS": SURREALDB_NS,
    "DB": SURREALDB_DB,
}


async def _query_surrealdb(sql: str) -> list[dict[str, Any]]:
    """Eksekusi SQL ke SurrealDB. Kembalikan list dari result statement terakhir."""
    response = await _get_surreal_http().post(
        _SURREAL_SQL_ENDPOINT,
        content=sql,
        headers=_SURREAL_HEADERS,
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


async def _get_query_embedding(text: str, ai_url: str | None = None) -> list[float]:
    """Generate embedding vector untuk query teks via Ollama."""
    url = ai_url
    if not url:
        db_url, _ = await _get_ai_config()
        url = db_url
    # Menggunakan timeout 5 detik agar gagal cepat jika server remote lambat/tidak punya model embedding
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(
            f"{url}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def _query_surrealdb_vector(embedding: list[float], vector_table: str, n_results: int) -> list[str]:
    """Semantic search pada SurrealDB vector index untuk satu domain menggunakan embedding query yang sudah di-generate."""
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


# Stopword Indonesia ringan untuk keyword extraction BM25
_ID_STOPWORDS = {
    "dan", "di", "ke", "dari", "yang", "ini", "itu", "dengan", "untuk",
    "adalah", "ada", "pada", "dalam", "berapa", "bagaimana", "apa", "mana",
    "bisa", "apakah", "tolong", "mohon", "tampilkan", "lihat", "tunjukkan",
}


def _extract_keywords(text: str) -> str:
    """Ekstrak kata kunci dari query untuk BM25 full-text search.

    Filter stopword Indonesia dan karakter non-alfanumerik, ambil max 8 kata.
    """
    words = re.findall(r"\b\w+\b", text.lower())
    keywords = [w for w in words if w not in _ID_STOPWORDS and len(w) > 2]
    return " ".join(keywords[:8])


def _expand_keywords(keywords: str, target_domains: list[str]) -> str:
    """Perkaya keyword BM25 dengan sinonim dari domain registry.

    Domain registry sudah berisi keyword operasional yang relevan per domain
    (misal: 'biaya' → ['biaya', 'cost', 'budget', 'anggaran', 'pengeluaran']).
    Penggabungan ini meningkatkan recall BM25 tanpa memanggil LLM tambahan.
    """
    base = set(keywords.split())
    for domain in target_domains:  # semua domain yang terdeteksi
        base.update(DOMAINS[domain]["keywords"][:3])
    return " ".join(list(base)[:12])


async def _query_surrealdb_bm25(keywords: str, vector_table: str, n_results: int) -> list[str]:
    """BM25 full-text search pada vector table menggunakan SurrealDB SEARCH index."""
    if not keywords.strip():
        return []
    # Escape single quote agar aman dimasukkan ke SQL string
    safe_kw = keywords.replace("'", "\\'")
    sql = (
        f"SELECT text, search::score(1) AS bm25_score "
        f"FROM {vector_table} "
        f"WHERE text @1@ '{safe_kw}' "
        f"ORDER BY bm25_score DESC LIMIT {n_results};"
    )
    try:
        records = await _query_surrealdb(sql)
        return [r["text"] for r in records if "text" in r]
    except Exception:
        return []


def _rrf(
    vector_docs: list[str],
    bm25_docs: list[str],
    k: int = 60,
) -> list[str]:
    """Reciprocal Rank Fusion — gabungkan ranking cosine dan BM25.

    Dokumen yang muncul di kedua daftar mendapat skor lebih tinggi.
    Formula: score(d) = Σ 1/(k + rank(d)) untuk setiap ranking list.
    """
    scores: dict[str, float] = {}
    for rank, doc in enumerate(vector_docs):
        scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank + 1)
    for rank, doc in enumerate(bm25_docs):
        scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda d: scores[d], reverse=True)


def _detect_intent(query: str) -> list[str]:
    """Tebak domain relevan berdasarkan keyword pada query."""
    query_lower = query.lower().strip()
    
    # Jika query sangat pendek atau sapaan umum, lewati pencarian domain agar tidak lambat
    if len(query_lower) < 6 or query_lower in ["halo", "hi", "hey", "pagi", "siang", "sore", "malam", "test", "tes", "hello", "p", "siap", "tanya"]:
        return []

    matched: list[str] = []
    for name, cfg in DOMAINS.items():
        if any(kw in query_lower for kw in cfg["keywords"]):
            matched.append(name)
    
    # Hanya kembalikan yang cocok. Jangan paksa default ke 3 domain jika tidak ada keyword yang cocok,
    # karena jika tidak cocok berarti ini adalah sapaan atau pertanyaan umum non-operasional.
    return matched


async def _generate_hypothetical_doc(
    query: str, ai_url: str | None = None, ai_model: str | None = None
) -> str:
    """HyDE: generate jawaban hipotetis singkat lalu embed hasilnya untuk retrieval.

    Embedding dari kalimat yang mirip jawaban lebih dekat ke dokumen di vector store
    dibanding embedding dari pertanyaan langsung. Timeout 6s — fallback ke query asli.
    """
    cache_key = f"hyde:{query}"
    cached = _cache_get(cache_key, _TTL_EMBEDDING)
    if cached is not None:
        return cached

    url = ai_url
    model = ai_model
    if not url or not model:
        url, model = await _get_ai_config()

    try:
        llm = _get_llm(url, model)
        chain = _HYDE_PROMPT | llm | StrOutputParser()
        hyp = await asyncio.wait_for(chain.ainvoke({"query": query}), timeout=6.0)
        result = hyp.strip() or query
    except Exception:
        result = query  # fallback ke query asli agar retrieval tetap berjalan

    _cache_set(cache_key, result)
    return result


async def _fetch_single_domain(
    domain: str,
    query_embedding: list[float] | None,
    keywords: str,
    n_results: int,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """Fetch vector + BM25 + RRF + structured aggregate untuk satu domain.

    Re-ranking tidak dilakukan di sini — dikerjakan secara batch global
    di _build_rag_context agar satu cross-encoder call cukup untuk semua domain.
    Vector dan BM25 results di-cache per (domain, query/keywords) selama 2 menit.
    """
    cfg = DOMAINS[domain]
    pool = n_results * 3  # kandidat untuk RRF, lebih banyak dari top-K final

    # ── Vector search — cache per (domain, embedding hash) ───────────────────
    vec_key = f"vec:{domain}:{_qhash(str(query_embedding))}" if query_embedding else ""
    vector_docs: list[str] = _cache_get(vec_key, _TTL_RETRIEVAL) if vec_key else None  # type: ignore[assignment]

    # ── BM25 search — cache per (domain, keywords hash) ──────────────────────
    bm25_key = f"bm25:{domain}:{_qhash(keywords)}"
    bm25_docs: list[str] = _cache_get(bm25_key, _TTL_RETRIEVAL)  # type: ignore[assignment]

    vector_task = (
        _noop(vector_docs) if vector_docs is not None
        else _query_surrealdb_vector(query_embedding, cfg["vector"], pool) if query_embedding
        else _noop([])
    )
    bm25_task = (
        _noop(bm25_docs) if bm25_docs is not None
        else _query_surrealdb_bm25(keywords, cfg["vector"], pool)
    )

    vector_docs, bm25_docs = await asyncio.gather(vector_task, bm25_task, return_exceptions=True)

    if isinstance(vector_docs, Exception):
        vector_docs = []
    if isinstance(bm25_docs, Exception):
        bm25_docs = []

    if vec_key and _cache_get(vec_key, _TTL_RETRIEVAL) is None:
        _cache_set(vec_key, vector_docs)
    if _cache_get(bm25_key, _TTL_RETRIEVAL) is None:
        _cache_set(bm25_key, bm25_docs)

    # RRF: gabungkan dua ranking list, simpan pool untuk batch rerank global
    fused_docs = _rrf(vector_docs, bm25_docs)[:pool]

    # Structured aggregate — cache 60s
    agg_key = f"agg:{domain}"
    records = _cache_get(agg_key, _TTL_AGGREGATE)
    if records is None:
        try:
            records = await _query_surrealdb(cfg["summary"])
        except Exception:
            records = []
        _cache_set(agg_key, records)

    return domain, fused_docs, records


async def _build_rag_context(
    query: str, n_results: int, target_domains: list[str], ai_url: str | None = None
) -> tuple[str, int, int]:
    """Susun konteks RAG dari SurrealDB vector + structured untuk domain yang ditargetkan.

    Optimasi utama vs versi sebelumnya:
    - HyDE + direct embedding berjalan PARALEL (bukan sequential 4-11s)
    - Cross-encoder re-rank satu batch untuk semua domain (bukan N call per domain)
    - Context di-truncate ke 6000 char agar model 2B tidak kewalahan
    """
    embed_key = f"emb:{query}"
    query_embedding: list[float] | None = _cache_get(embed_key, _TTL_EMBEDDING)

    if query_embedding is None:
        # Jalankan HyDE+embed dan direct embed secara paralel.
        # Direct embed lebih cepat; HyDE digunakan jika selesai dalam 3s tambahan.
        async def _hyde_embed() -> list[float] | None:
            try:
                hyde_text = await _generate_hypothetical_doc(query, ai_url=ai_url)
                return await _get_query_embedding(hyde_text, ai_url=ai_url)
            except Exception:
                return None

        async def _direct_embed() -> list[float] | None:
            try:
                return await _get_query_embedding(query, ai_url=ai_url)
            except Exception:
                return None

        hyde_task   = asyncio.create_task(_hyde_embed())
        direct_task = asyncio.create_task(_direct_embed())

        direct_result = await direct_task
        try:
            hyde_result = await asyncio.wait_for(asyncio.shield(hyde_task), timeout=3.0)
            query_embedding = hyde_result or direct_result
        except asyncio.TimeoutError:
            hyde_task.cancel()
            query_embedding = direct_result

        if query_embedding is not None:
            _cache_set(embed_key, query_embedding)
        else:
            print(f"[WARN] Gagal mendapatkan embedding untuk query: {query!r}")

    # Query expansion: semua domain yang terdeteksi berkontribusi keyword
    keywords = _expand_keywords(_extract_keywords(query), target_domains)

    # Parallel fetch semua domain (vector + BM25 + RRF + aggregate)
    tasks = [_fetch_single_domain(d, query_embedding, keywords, n_results) for d in target_domains]
    domain_results = await asyncio.gather(*tasks, return_exceptions=True)

    valid: list[tuple[str, list[str], list[dict[str, Any]]]] = [
        r for r in domain_results if not isinstance(r, Exception)
    ]

    # Batch cross-encoder re-rank: satu call untuk semua domain sekaligus
    domain_docs_for_rerank = [(domain, fused) for domain, fused, _ in valid if fused]
    reranked: dict[str, list[str]] = {}
    if domain_docs_for_rerank:
        reranked = await _rerank_batch_async(query, domain_docs_for_rerank, top_k=n_results)

    context_parts: list[str] = []
    vector_hits = 0
    surreal_hits = 0

    for domain, fused_docs, records in valid:
        final_docs = reranked.get(domain, fused_docs[:n_results])

        if final_docs:
            context_parts.append(f"[Vector Search · {domain}]")
            context_parts.extend(f"  • {doc}" for doc in final_docs)
            vector_hits += len(final_docs)

        if records:
            context_parts.append(f"[Agregat · {domain}]")
            for record in records[:8]:
                snippet = ", ".join(f"{k}={v}" for k, v in record.items() if v is not None)
                context_parts.append(f"  • {snippet}")
            surreal_hits += len(records)

    context = _truncate_context("\n".join(context_parts)) if context_parts else ""
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


# ─── Self-RAG Helper ──────────────────────────────────────────────────────────

_INSUFFICIENT_MARKERS = [
    "tidak ada data", "tidak ditemukan", "data tidak cukup",
    "tidak tersedia", "belum ada", "tidak dapat menemukan",
    "tidak memiliki informasi", "tidak terdapat", "kurang informasi",
]


def _is_insufficient(answer: str) -> bool:
    """Cek apakah jawaban LLM mengindikasikan konteks tidak cukup."""
    lower = answer.lower()
    return any(marker in lower for marker in _INSUFFICIENT_MARKERS)


# ─── Generate (RAG + LLM via LangChain) ──────────────────────────────────────


@app.post("/mcp/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest) -> GenerateResponse:
    """RAG retrieval (SurrealDB vector + structured) + LLM generation via LangChain + Ollama."""
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")

    # ── LLM Response Cache — kembalikan instan jika query sama dalam 60s ─────
    llm_cache_key = f"llm:{_qhash(query)}"
    cached_response = _cache_get(llm_cache_key, _TTL_LLM_RESPONSE)
    if cached_response is not None:
        return GenerateResponse(**{**cached_response, "source": cached_response["source"] + "+cached"})

    context = "(no context)"
    vector_hits = 0
    surreal_hits = 0
    matched_domains: list[str] = []
    source = "ollama_direct"

    if payload.use_rag:
        target_domains = [d for d in _detect_intent(query) if d in DOMAINS]
        matched_domains = target_domains

        if target_domains:
            context, vector_hits, surreal_hits = await _build_rag_context(
                query, payload.n_results, target_domains, ai_url=payload.ai_url
            )
            if not context:
                context = "Tidak ada data operasional yang relevan ditemukan."
            source = "surrealdb_vector+structured+ollama"

    try:
        has_real_context = bool(context and context != "(no context)" and "Tidak ada data operasional" not in context)
        chain = await _build_chain(
            has_context=has_real_context,
            ai_url=payload.ai_url,
            ai_model=payload.ai_model,
        )

        if has_real_context:
            answer = await chain.ainvoke({"context": context, "query": query})
        else:
            answer = await chain.ainvoke({"query": query})

        # Self-RAG: retry dengan top-5 domain terpilih (bukan 13) jika data kurang.
        if (
            payload.use_rag
            and _is_insufficient(answer)
            and len(matched_domains) < len(DOMAINS)
        ):
            try:
                retry_domains = matched_domains + _rank_retry_domains(query, matched_domains)
                retry_context, rv, rs = await asyncio.wait_for(
                    _build_rag_context(query, payload.n_results, retry_domains, ai_url=payload.ai_url),
                    timeout=60.0,
                )
                if retry_context and "Tidak ada data" not in retry_context:
                    retry_chain = await _build_chain(
                        has_context=True,
                        ai_url=payload.ai_url,
                        ai_model=payload.ai_model,
                    )
                    answer = await asyncio.wait_for(
                        retry_chain.ainvoke({"context": retry_context, "query": query}),
                        timeout=120.0,
                    )
                    context, vector_hits, surreal_hits = retry_context, rv, rs
                    matched_domains = retry_domains
                    source = "surrealdb_self_rag_retry+ollama"
            except asyncio.TimeoutError:
                print("[WARN] Self-RAG retry timeout — menggunakan jawaban pertama")

    except Exception as error:
        import traceback
        print(f"[ERROR] Gagal memanggil LLM: {error}")
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"LLM error: {error}") from error

    # Simpan ke cache untuk query yang sama dalam 60s berikutnya
    _cache_set(llm_cache_key, {
        "query": query, "answer": answer, "context_used": context,
        "source": source, "vector_hits": vector_hits,
        "surreal_hits": surreal_hits, "matched_domains": matched_domains,
    })

    return GenerateResponse(
        query=query,
        answer=answer,
        context_used=context,
        source=source,
        vector_hits=vector_hits,
        surreal_hits=surreal_hits,
        matched_domains=matched_domains,
    )


@app.post("/mcp/generate/stream")
async def generate_stream(payload: GenerateRequest) -> StreamingResponse:
    """RAG retrieval + LLM generation dengan token streaming (text/plain chunked).

    Token dikirim ke client saat LLM menghasilkannya — user tidak perlu menunggu
    seluruh jawaban selesai. Context-building tetap dilakukan sebelum streaming mulai.
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")

    context = ""
    matched_domains: list[str] = []

    if payload.use_rag:
        target_domains = [d for d in _detect_intent(query) if d in DOMAINS]
        matched_domains = target_domains
        if target_domains:
            context, _, _ = await _build_rag_context(
                query, payload.n_results, target_domains, ai_url=payload.ai_url
            )

    has_real_context = bool(
        context and context != "(no context)" and "Tidak ada data operasional" not in context
    )
    chain = await _build_chain(
        has_context=has_real_context,
        ai_url=payload.ai_url,
        ai_model=payload.ai_model,
    )
    input_data = {"context": context, "query": query} if has_real_context else {"query": query}

    async def token_generator():
        async for chunk in chain.astream(input_data):
            yield chunk

    return StreamingResponse(token_generator(), media_type="text/plain")


# ─── Analytics ────────────────────────────────────────────────────────────────


def _date_where(field: str, date_from: str | None, date_to: str | None) -> str:
    """Build SurrealDB WHERE clause untuk filter rentang tanggal."""
    parts: list[str] = []
    if date_from:
        parts.append(f"{field} >= '{date_from}T00:00:00Z'")
    if date_to:
        parts.append(f"{field} <= '{date_to}T23:59:59Z'")
    return (" WHERE " + " AND ".join(parts)) if parts else ""


@app.get("/mcp/analytics/overview")
async def analytics_overview(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """KPI ringkasan tingkat tinggi dari semua domain."""
    w_pasien = _date_where("snapshot_at", date_from, date_to)
    w_occ    = _date_where("observed_at", date_from, date_to)
    w_listrik = _date_where("reading_at", date_from, date_to)
    w_air    = _date_where("reading_at", date_from, date_to)
    w_biaya  = _date_where("period_month", date_from, date_to)
    w_lembur = _date_where("overtime_date", date_from, date_to)

    queries = {
        "pasien_total": f"SELECT count() AS total FROM clean_pasien_aktif{w_pasien} GROUP ALL",
        "okupansi": f"SELECT math::sum(bed_capacity) AS capacity, math::sum(bed_occupied) AS occupied FROM clean_okupansi_kamar{w_occ} GROUP ALL",
        "listrik": f"SELECT math::sum(kwh_total) AS kwh FROM clean_meter_listrik{w_listrik} GROUP ALL",
        "air": f"SELECT math::sum(volume_m3_total) AS volume FROM clean_konsumsi_air{w_air} GROUP ALL",
        "biaya": f"SELECT math::sum(amount_idr) AS total_cost, math::sum(budget_idr) AS total_budget FROM clean_biaya_operasional{w_biaya} GROUP ALL",
        "lembur": f"SELECT math::sum(overtime_hours) AS hours, math::sum(overtime_cost_idr) AS cost FROM clean_lembur_staf{w_lembur} GROUP ALL",
    }

    async def _run_query(k: str, q: str) -> tuple[str, Any]:
        try:
            records = await _query_surrealdb(q)
            return k, (records[0] if records else {})
        except Exception:
            return k, {}

    tasks = [_run_query(k, q) for k, q in queries.items()]
    results = await asyncio.gather(*tasks)
    result = dict(results)

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
async def analytics_cost_by_category(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    w = _date_where("period_month", date_from, date_to)
    sql = (
        f"SELECT cost_category, math::sum(amount_idr) AS total_cost,"
        f" math::sum(budget_idr) AS total_budget"
        f" FROM clean_biaya_operasional{w} GROUP BY cost_category"
    )
    try:
        records = await _query_surrealdb(sql)
    except Exception:
        records = []
    return {"categories": records}


@app.get("/mcp/analytics/occupancy-by-unit")
async def analytics_occupancy_by_unit(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    w = _date_where("observed_at", date_from, date_to)
    sql = (
        f"SELECT unit_code, math::sum(bed_capacity) AS capacity,"
        f" math::sum(bed_occupied) AS occupied"
        f" FROM clean_okupansi_kamar{w} GROUP BY unit_code"
    )
    try:
        records = await _query_surrealdb(sql)
    except Exception:
        records = []
    return {"units": records}


@app.get("/mcp/analytics/utility-trend")
async def analytics_utility_trend(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    w = _date_where("reading_at", date_from, date_to)
    try:
        listrik = await _query_surrealdb(
            f"SELECT unit_code, math::sum(kwh_total) AS kwh FROM clean_meter_listrik{w} GROUP BY unit_code"
        )
    except Exception:
        listrik = []
    try:
        air = await _query_surrealdb(
            f"SELECT unit_code, math::sum(volume_m3_total) AS volume FROM clean_konsumsi_air{w} GROUP BY unit_code"
        )
    except Exception:
        air = []
    return {"listrik": listrik, "air": air}


@app.get("/mcp/analytics/efficiency")
async def analytics_efficiency(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Cost efficiency per unit: cost-per-service dan cost-to-revenue ratio."""
    w_biaya = _date_where("period_month", date_from, date_to)
    w_kunjungan = _date_where("tanggal", date_from, date_to)
    w_pendapatan = _date_where("period_month", date_from, date_to)

    try:
        cost_rows = await _query_surrealdb(
            f"SELECT unit_code, math::sum(amount_idr) AS total_cost"
            f" FROM clean_biaya_operasional{w_biaya} GROUP BY unit_code"
        )
    except Exception:
        cost_rows = []

    try:
        visit_rows = await _query_surrealdb(
            f"SELECT unit_code, math::sum(jumlah_kunjungan) AS total_kunjungan,"
            f" math::sum(jumlah_tindakan) AS total_tindakan"
            f" FROM clean_kunjungan_layanan{w_kunjungan} GROUP BY unit_code"
        )
    except Exception:
        visit_rows = []

    try:
        revenue_rows = await _query_surrealdb(
            f"SELECT unit_code, math::sum(amount_idr) AS total_revenue,"
            f" math::sum(target_idr) AS total_target"
            f" FROM clean_pendapatan_unit{w_pendapatan} GROUP BY unit_code"
        )
    except Exception:
        revenue_rows = []

    cost_map = {r["unit_code"]: r.get("total_cost", 0) for r in cost_rows if "unit_code" in r}
    visit_map = {r["unit_code"]: r for r in visit_rows if "unit_code" in r}
    revenue_map = {r["unit_code"]: r for r in revenue_rows if "unit_code" in r}

    all_units = set(cost_map) | set(visit_map) | set(revenue_map)
    units: list[dict[str, Any]] = []
    for unit in sorted(all_units):
        cost = cost_map.get(unit, 0) or 0
        kunjungan = (visit_map.get(unit) or {}).get("total_kunjungan") or 0
        tindakan = (visit_map.get(unit) or {}).get("total_tindakan") or 0
        revenue = (revenue_map.get(unit) or {}).get("total_revenue") or 0
        target = (revenue_map.get(unit) or {}).get("total_target") or 0

        cost_per_kunjungan = round(cost / kunjungan, 2) if kunjungan else None
        cost_per_tindakan = round(cost / tindakan, 2) if tindakan else None
        cost_to_revenue = round(cost / revenue * 100, 2) if revenue else None
        revenue_achievement = round(revenue / target * 100, 2) if target else None

        units.append({
            "unit_code": unit,
            "total_cost_idr": cost,
            "total_kunjungan": kunjungan,
            "total_tindakan": tindakan,
            "total_revenue_idr": revenue,
            "cost_per_kunjungan_idr": cost_per_kunjungan,
            "cost_per_tindakan_idr": cost_per_tindakan,
            "cost_to_revenue_pct": cost_to_revenue,
            "revenue_achievement_pct": revenue_achievement,
        })

    return {"units": units}


@app.get("/mcp/analytics/staffing")
async def analytics_staffing(
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Staffing optimization: shift coverage vs overtime per unit."""
    w_shift  = _date_where("shift_date", date_from, date_to)
    w_lembur = _date_where("overtime_date", date_from, date_to)

    try:
        shift_rows = await _query_surrealdb(
            f"SELECT unit_code, math::sum(scheduled_hours) AS scheduled_hours,"
            f" math::sum(actual_hours) AS actual_hours,"
            f" count() AS total_shift,"
            f" math::sum(IF absent THEN 1 ELSE 0 END) AS total_absent"
            f" FROM clean_jadwal_staf{w_shift} GROUP BY unit_code"
        )
    except Exception:
        shift_rows = []

    try:
        overtime_rows = await _query_surrealdb(
            f"SELECT unit_code, math::sum(overtime_hours) AS overtime_hours,"
            f" math::sum(overtime_cost_idr) AS overtime_cost"
            f" FROM clean_lembur_staf{w_lembur} GROUP BY unit_code"
        )
    except Exception:
        overtime_rows = []

    shift_map = {r["unit_code"]: r for r in shift_rows if "unit_code" in r}
    overtime_map = {r["unit_code"]: r for r in overtime_rows if "unit_code" in r}

    all_units = set(shift_map) | set(overtime_map)
    units: list[dict[str, Any]] = []
    for unit in sorted(all_units):
        shift = shift_map.get(unit) or {}
        ot = overtime_map.get(unit) or {}

        scheduled = shift.get("scheduled_hours") or 0
        actual = shift.get("actual_hours") or 0
        overtime = ot.get("overtime_hours") or 0
        total_shift = shift.get("total_shift") or 0
        total_absent = shift.get("total_absent") or 0

        attendance_rate = round((1 - total_absent / total_shift) * 100, 2) if total_shift else None
        overtime_ratio = round(overtime / actual * 100, 2) if actual else None

        units.append({
            "unit_code": unit,
            "scheduled_hours": scheduled,
            "actual_hours": actual,
            "overtime_hours": overtime,
            "overtime_cost_idr": ot.get("overtime_cost") or 0,
            "total_shift": total_shift,
            "total_absent": total_absent,
            "attendance_rate_pct": attendance_rate,
            "overtime_ratio_pct": overtime_ratio,
        })

    return {"units": units}


@app.get("/mcp/analytics/daily-trend")
async def analytics_daily_trend(year: int, month: int) -> dict[str, Any]:
    """Agregat pasien aktif & lembur per hari dalam satu bulan (untuk kalender heatmap)."""
    import calendar as _cal
    last_day = _cal.monthrange(year, month)[1]
    date_from = f"{year:04d}-{month:02d}-01"
    date_to   = f"{year:04d}-{month:02d}-{last_day:02d}"

    try:
        pasien_rows = await _query_surrealdb(
            f"SELECT string::slice(string(snapshot_at), 0, 10) AS day, count() AS total"
            f" FROM clean_pasien_aktif"
            f" WHERE snapshot_at >= '{date_from}T00:00:00Z'"
            f" AND snapshot_at <= '{date_to}T23:59:59Z'"
            f" GROUP BY day ORDER BY day"
        )
    except Exception:
        pasien_rows = []

    try:
        lembur_rows = await _query_surrealdb(
            f"SELECT string::slice(string(overtime_date), 0, 10) AS day,"
            f" math::sum(overtime_hours) AS hours"
            f" FROM clean_lembur_staf"
            f" WHERE overtime_date >= '{date_from}T00:00:00Z'"
            f" AND overtime_date <= '{date_to}T23:59:59Z'"
            f" GROUP BY day ORDER BY day"
        )
    except Exception:
        lembur_rows = []

    pasien_map = {r["day"]: r.get("total", 0) for r in pasien_rows if "day" in r}
    lembur_map = {r["day"]: r.get("hours", 0) for r in lembur_rows if "day" in r}

    days: list[dict[str, Any]] = []
    for d in range(1, last_day + 1):
        day_str = f"{year:04d}-{month:02d}-{d:02d}"
        days.append({
            "date": day_str,
            "pasien": pasien_map.get(day_str, 0),
            "lembur_hours": lembur_map.get(day_str, 0),
            "has_data": day_str in pasien_map or day_str in lembur_map,
        })

    return {"year": year, "month": month, "days": days}


# ─── Summary ──────────────────────────────────────────────────────────────────


@app.get("/mcp/summary/resource")
async def summary_resource() -> dict[str, Any]:
    """Ringkasan utilitas resource (listrik, air, okupansi) per unit."""
    async def _q(sql: str) -> list[dict[str, Any]]:
        try:
            return await _query_surrealdb(sql)
        except Exception:
            return []

    listrik_rows, air_rows, occ_rows = await asyncio.gather(
        _q("SELECT unit_code, math::sum(kwh_total) AS listrik_kwh"
           " FROM clean_meter_listrik GROUP BY unit_code"),
        _q("SELECT unit_code, math::sum(volume_m3_total) AS air_m3"
           " FROM clean_konsumsi_air GROUP BY unit_code"),
        _q("SELECT unit_code, math::sum(bed_capacity) AS bed_capacity,"
           " math::sum(bed_occupied) AS bed_occupied"
           " FROM clean_okupansi_kamar GROUP BY unit_code"),
    )

    unit_map: dict[str, dict[str, Any]] = {}
    _default = lambda u: {"unit_code": u, "listrik_kwh": 0, "air_m3": 0, "bed_occupied": 0, "bed_capacity": 0}

    for r in listrik_rows:
        u = r.get("unit_code", "unknown")
        unit_map.setdefault(u, _default(u))
        unit_map[u]["listrik_kwh"] = r.get("listrik_kwh") or 0

    for r in air_rows:
        u = r.get("unit_code", "unknown")
        unit_map.setdefault(u, _default(u))
        unit_map[u]["air_m3"] = r.get("air_m3") or 0

    for r in occ_rows:
        u = r.get("unit_code", "unknown")
        unit_map.setdefault(u, _default(u))
        unit_map[u]["bed_occupied"] = r.get("bed_occupied") or 0
        unit_map[u]["bed_capacity"] = r.get("bed_capacity") or 0

    return {"units": list(unit_map.values())}


@app.get("/mcp/summary/cost")
async def summary_cost() -> dict[str, Any]:
    """Ringkasan biaya operasional per unit & kategori."""
    try:
        agg_rows = await _query_surrealdb(
            "SELECT unit_code, cost_category,"
            " math::sum(amount_idr) AS amount_idr,"
            " math::sum(budget_idr) AS budget_idr"
            " FROM clean_biaya_operasional GROUP BY unit_code, cost_category"
        )
    except Exception:
        agg_rows = []

    unit_map: dict[str, dict[str, Any]] = {}
    for r in agg_rows:
        unit = r.get("unit_code", "unknown")
        unit_map.setdefault(unit, {"unit_code": unit, "total_cost_idr": 0, "total_budget_idr": 0, "categories": {}})
        cat = r.get("cost_category", "other")
        amount = r.get("amount_idr") or 0
        budget = r.get("budget_idr") or 0
        unit_map[unit]["total_cost_idr"] += amount
        unit_map[unit]["total_budget_idr"] += budget
        unit_map[unit]["categories"][cat] = {"amount_idr": amount, "budget_idr": budget}

    return {"units": list(unit_map.values())}
