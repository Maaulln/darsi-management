"""Script untuk embed data refined dari PostgreSQL ke ChromaDB sebagai vector store RAG."""

from __future__ import annotations

import os
import json
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text
import chromadb
from chromadb.config import Settings as ChromaSettings

# ─── Koneksi ─────────────────────────────────────────────────────────────────

def get_postgres_engine():
    url = (
        f"postgresql+psycopg2://"
        f"{os.getenv('POSTGRES_USER', 'darsi_user')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'darsi_password')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'darsi')}"
    )
    return create_engine(url, pool_pre_ping=True)


def get_chroma_client() -> chromadb.HttpClient:
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8002"))
    return chromadb.HttpClient(host=host, port=port)


# ─── Domain Queries ──────────────────────────────────────────────────────────

DOMAIN_QUERIES: dict[str, str] = {
    "pasien_aktif": "SELECT snapshot_at, patient_id, unit_code, room_code, class_code, status_aktif, diagnosis_code FROM refined_pasien_aktif LIMIT 500",
    "okupansi_kamar": "SELECT observed_at, room_id, unit_code, room_class, bed_capacity, bed_occupied, room_status FROM refined_okupansi_kamar LIMIT 500",
    "biaya_operasional": "SELECT period_month, unit_code, cost_category, amount_idr, budget_idr FROM refined_biaya_operasional_unit LIMIT 500",
    "konsumsi_obat_alkes": "SELECT usage_at, unit_code, item_name, item_type, quantity, total_cost_idr FROM refined_konsumsi_obat_alkes LIMIT 500",
    "lembur_staf": "SELECT overtime_date, unit_code, role_name, overtime_hours, overtime_cost_idr FROM refined_lembur_staf LIMIT 500",
    "meter_listrik": "SELECT reading_at, building_code, unit_code, kwh_total FROM refined_meter_listrik LIMIT 500",
}


def row_to_text(domain: str, row: dict) -> str:
    """Mengubah satu baris data menjadi teks natural language untuk embedding."""
    row_clean = {k: str(v) for k, v in row.items() if v is not None}

    if domain == "pasien_aktif":
        return (f"Pasien {row_clean.get('patient_id')} di unit {row_clean.get('unit_code')} "
                f"kamar {row_clean.get('room_code')} kelas {row_clean.get('class_code')} "
                f"status {row_clean.get('status_aktif')} diagnosis {row_clean.get('diagnosis_code')} "
                f"per {row_clean.get('snapshot_at')}")

    elif domain == "okupansi_kamar":
        return (f"Kamar {row_clean.get('room_id')} unit {row_clean.get('unit_code')} "
                f"kelas {row_clean.get('room_class')} kapasitas {row_clean.get('bed_capacity')} "
                f"terisi {row_clean.get('bed_occupied')} status {row_clean.get('room_status')} "
                f"per {row_clean.get('observed_at')}")

    elif domain == "biaya_operasional":
        return (f"Biaya unit {row_clean.get('unit_code')} kategori {row_clean.get('cost_category')} "
                f"bulan {row_clean.get('period_month')} sebesar Rp{row_clean.get('amount_idr')} "
                f"dari budget Rp{row_clean.get('budget_idr')}")

    elif domain == "konsumsi_obat_alkes":
        return (f"Konsumsi {row_clean.get('item_type')} {row_clean.get('item_name')} "
                f"di unit {row_clean.get('unit_code')} sejumlah {row_clean.get('quantity')} "
                f"total biaya Rp{row_clean.get('total_cost_idr')} "
                f"per {row_clean.get('usage_at')}")

    elif domain == "lembur_staf":
        return (f"Lembur {row_clean.get('role_name')} di unit {row_clean.get('unit_code')} "
                f"selama {row_clean.get('overtime_hours')} jam biaya Rp{row_clean.get('overtime_cost_idr')} "
                f"tanggal {row_clean.get('overtime_date')}")

    elif domain == "meter_listrik":
        return (f"Konsumsi listrik gedung {row_clean.get('building_code')} "
                f"unit {row_clean.get('unit_code')} total {row_clean.get('kwh_total')} kWh "
                f"per {row_clean.get('reading_at')}")

    return json.dumps(row_clean, ensure_ascii=False)


def embed_domain(engine, chroma_client, domain: str, query: str) -> int:
    """Embed satu domain ke ChromaDB collection."""
    df = pd.read_sql(text(query), con=engine)
    if df.empty:
        print(f"   [SKIP] {domain}: tabel refined kosong.")
        return 0

    collection_name = f"darsi_{domain}"
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass
    collection = chroma_client.create_collection(name=collection_name)

    documents, ids, metadatas = [], [], []
    for i, row in df.iterrows():
        row_dict = row.to_dict()
        doc_text = row_to_text(domain, row_dict)
        documents.append(doc_text)
        ids.append(f"{domain}_{i}")
        metadatas.append({"domain": domain, "row_index": i})

    # Batch upsert ke ChromaDB (maks 500 per batch)
    batch_size = 100
    for start in range(0, len(documents), batch_size):
        collection.add(
            documents=documents[start:start + batch_size],
            ids=ids[start:start + batch_size],
            metadatas=metadatas[start:start + batch_size],
        )

    return len(documents)


def run_embedding() -> None:
    engine = get_postgres_engine()
    chroma_client = get_chroma_client()
    print(f"Memulai embedding ke ChromaDB [{datetime.now().strftime('%H:%M:%S')}]...")

    for domain, query in DOMAIN_QUERIES.items():
        try:
            count = embed_domain(engine, chroma_client, domain, query)
            print(f" ✓ {domain}: {count} dokumen di-embed")
        except Exception as e:
            print(f" ✗ {domain}: Gagal - {e}")

    print("Selesai. ChromaDB siap untuk RAG retrieval.")


if __name__ == "__main__":
    run_embedding()
