"""Embed data clean dari SurrealDB ke SurrealDB vector index (HNSW).

Alur:
    clean_{domain} SurrealDB
        → row_to_text()  → kalimat natural language
        → Ollama nomic-embed-text  → vector float[768]
        → vector_darsi_{domain} SurrealDB  (HNSW DIMENSION 768 DIST COSINE)

Dipanggil oleh pipeline-service via POST /pipeline/embed.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from datetime import datetime

import requests

# ─── Config ──────────────────────────────────────────────────────────────────

SURREALDB_URL = os.getenv("SURREALDB_URL", "http://localhost:8001")
SURREALDB_USER = os.getenv("SURREALDB_USER", "root")
SURREALDB_PASSWORD = os.getenv("SURREALDB_PASSWORD", "root")
SURREALDB_NS = os.getenv("SURREALDB_NS", "darsi")
SURREALDB_DB = os.getenv("SURREALDB_DB", "operasional")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = 768  # nomic-embed-text output dimension

RECORD_LIMIT = 40   # max records per domain
BATCH_SIZE = 40      # records per SurrealDB bulk insert

DOMAINS = [
    "pasien_aktif",
    "okupansi_kamar",
    "meter_listrik",
    "konsumsi_air",
    "biaya_operasional",
    "konsumsi_obat_alkes",
    "lembur_staf",
    "jadwal_alat_berat",
]

# ─── SurrealDB helpers ────────────────────────────────────────────────────────

def _sql_endpoint() -> str:
    base = SURREALDB_URL.rstrip("/")
    return base[:-4] + "/sql" if base.endswith("/rpc") else base + "/sql"


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "text/plain",
        "surreal-ns": SURREALDB_NS,
        "surreal-db": SURREALDB_DB,
        "NS": SURREALDB_NS,
        "DB": SURREALDB_DB,
    }


surreal_session = requests.Session()
surreal_session.auth = (SURREALDB_USER, SURREALDB_PASSWORD)
surreal_session.headers.update(_headers())

ollama_session = requests.Session()


def surreal_query(sql: str) -> list[dict]:
    resp = surreal_session.post(
        _sql_endpoint(), data=sql, timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            result = first.get("result", [])
            return result if isinstance(result, list) else []
    return []


def surreal_exec(sql: str) -> None:
    resp = surreal_session.post(
        _sql_endpoint(), data=sql, timeout=60,
    )
    resp.raise_for_status()


# ─── Ollama embedding ─────────────────────────────────────────────────────────

_cached_ollama_url = None

def _get_dynamic_ollama_url() -> str:
    global _cached_ollama_url
    if _cached_ollama_url is not None:
        return _cached_ollama_url

    try:
        r = requests.get("http://backend:8000/api/settings/ai", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("url"):
                _cached_ollama_url = data["url"]
                return _cached_ollama_url
    except Exception:
        pass
    _cached_ollama_url = OLLAMA_BASE_URL
    return _cached_ollama_url

def get_embedding(text: str) -> list[float]:
    url = _get_dynamic_ollama_url()
    resp = ollama_session.post(
        f"{url}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


# ─── Text representation ─────────────────────────────────────────────────────

def row_to_text(domain: str, row: dict) -> str:
    r = {k: str(v) for k, v in row.items() if v is not None and k != "id"}

    if domain == "pasien_aktif":
        return (
            f"Pasien {r.get('patient_id')} unit {r.get('unit_code')} "
            f"kamar {r.get('room_code')} kelas {r.get('class_code')} "
            f"status {r.get('status_aktif')} diagnosis {r.get('diagnosis_code')} "
            f"per {r.get('snapshot_at')}"
        )
    if domain == "okupansi_kamar":
        return (
            f"Kamar {r.get('room_id')} unit {r.get('unit_code')} "
            f"kelas {r.get('room_class')} kapasitas {r.get('bed_capacity')} "
            f"terisi {r.get('bed_occupied')} status {r.get('room_status')} "
            f"per {r.get('observed_at')}"
        )
    if domain == "meter_listrik":
        return (
            f"Konsumsi listrik gedung {r.get('building_code')} "
            f"unit {r.get('unit_code')} total {r.get('kwh_total')} kWh "
            f"per {r.get('reading_at')}"
        )
    if domain == "konsumsi_air":
        return (
            f"Konsumsi air unit {r.get('unit_code')} "
            f"gedung {r.get('building_code')} total {r.get('volume_m3_total')} m3 "
            f"per {r.get('reading_at')}"
        )
    if domain == "biaya_operasional":
        return (
            f"Biaya unit {r.get('unit_code')} kategori {r.get('cost_category')} "
            f"bulan {r.get('period_month')} sebesar Rp{r.get('amount_idr')} "
            f"dari anggaran Rp{r.get('budget_idr')}"
        )
    if domain == "konsumsi_obat_alkes":
        return (
            f"Konsumsi {r.get('item_type')} {r.get('item_name')} "
            f"unit {r.get('unit_code')} jumlah {r.get('quantity')} "
            f"total Rp{r.get('total_cost_idr')} per {r.get('usage_at')}"
        )
    if domain == "lembur_staf":
        return (
            f"Lembur {r.get('role_name')} unit {r.get('unit_code')} "
            f"{r.get('overtime_hours')} jam biaya Rp{r.get('overtime_cost_idr')} "
            f"tanggal {r.get('overtime_date')}"
        )
    if domain == "jadwal_alat_berat":
        return (
            f"Jadwal {r.get('device_name')} unit {r.get('unit_code')} "
            f"tipe {r.get('schedule_type')} status {r.get('status')} "
            f"mulai {r.get('schedule_start')} selesai {r.get('schedule_end')}"
        )
    return json.dumps(r, ensure_ascii=False)


# ─── Vector table setup ───────────────────────────────────────────────────────

def setup_vector_table(domain: str) -> None:
    table = f"vector_darsi_{domain}"
    sql = (
        f"DEFINE TABLE IF NOT EXISTS {table} SCHEMALESS; "
        f"DELETE {table}; "
        f"DEFINE INDEX IF NOT EXISTS idx_hnsw_{domain} "
        f"ON TABLE {table} FIELDS embedding "
        f"HNSW DIMENSION {EMBED_DIM} DIST COSINE;"
    )
    surreal_exec(sql)


# ─── Per-domain embedding ─────────────────────────────────────────────────────

def embed_domain(domain: str) -> int:
    records = surreal_query(f"SELECT * FROM clean_{domain} LIMIT {RECORD_LIMIT};")
    if not records:
        print(f"   [SKIP] {domain}: clean table kosong atau belum ada.")
        return 0

    setup_vector_table(domain)

    texts = [row_to_text(domain, record) for record in records]
    embeddings: list[list[float] | None] = [None] * len(records)

    def _fetch_one(idx: int) -> None:
        try:
            embeddings[idx] = get_embedding(texts[idx])
        except Exception as exc:
            print(f"   [WARN] {domain} baris {idx}: embedding gagal — {exc}")

    # Fetch embeddings in parallel using up to 4 threads
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(_fetch_one, range(len(records)))

    count = 0
    batch: list[str] = []

    for i, record in enumerate(records):
        embedding = embeddings[i]
        if embedding is None:
            continue

        payload = json.dumps(
            {"doc_id": f"{domain}_{i}", "domain": domain, "text": texts[i], "embedding": embedding},
            ensure_ascii=True,
        )
        batch.append(f"CREATE vector_darsi_{domain} CONTENT {payload};")
        count += 1

        if len(batch) >= BATCH_SIZE:
            surreal_exec(" ".join(batch))
            batch = []
            print(f"   ... {count}/{len(records)} records embedded")

    if batch:
        surreal_exec(" ".join(batch))

    return count


# ─── Entry point ─────────────────────────────────────────────────────────────

def run_embedding() -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Memulai embedding ke SurrealDB")
    print(f"Model: {EMBED_MODEL} | Dimensi: {EMBED_DIM} | Limit: {RECORD_LIMIT} rec/domain\n")

    for domain in DOMAINS:
        try:
            n = embed_domain(domain)
            if n > 0:
                print(f" ✓ {domain}: {n} vektor tersimpan di vector_darsi_{domain}")
        except Exception as exc:
            print(f" ✗ {domain}: Gagal — {exc}")

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Selesai. SurrealDB vector index siap untuk RAG.")


if __name__ == "__main__":
    run_embedding()
