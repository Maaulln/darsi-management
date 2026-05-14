"""Service RAG DARSI: melakukan retrieval konteks dari ChromaDB lalu generate jawaban via Ollama."""

from __future__ import annotations

import httpx
import chromadb
from app.core.config import settings


def _get_chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


COLLECTION_NAMES = [
    "darsi_pasien_aktif",
    "darsi_okupansi_kamar",
    "darsi_biaya_operasional",
    "darsi_konsumsi_obat_alkes",
    "darsi_lembur_staf",
    "darsi_meter_listrik",
]


def retrieve_context(query: str, n_results: int = 5) -> str:
    """Mencari dokumen relevan dari ChromaDB berdasarkan query.

    Args:
        query: Pertanyaan pengguna.
        n_results: Jumlah dokumen yang dikembalikan per collection.

    Returns:
        Gabungan teks konteks yang relevan.
    """
    client = _get_chroma_client()
    all_docs: list[str] = []

    for col_name in COLLECTION_NAMES:
        try:
            collection = client.get_collection(col_name)
            results = collection.query(query_texts=[query], n_results=n_results)
            docs = results.get("documents", [[]])[0]
            all_docs.extend(docs)
        except Exception:
            # Collection belum ada atau kosong, skip
            continue

    if not all_docs:
        return "Tidak ada data operasional yang relevan ditemukan."

    return "\n".join(f"- {doc}" for doc in all_docs[:15])  # Batasi konteks


def generate_with_ollama(query: str, context: str) -> str:
    """Mengirim prompt RAG ke Ollama dan mengembalikan jawaban.

    Args:
        query: Pertanyaan pengguna.
        context: Konteks yang diambil dari ChromaDB.

    Returns:
        Jawaban dari model LLM.

    Raises:
        httpx.HTTPError: Jika koneksi ke Ollama gagal.
    """
    prompt = f"""Anda adalah asisten analitik operasional rumah sakit DARSI.
Gunakan data konteks berikut untuk menjawab pertanyaan dengan ringkas dan akurat.
Jika data tidak cukup, katakan demikian.

KONTEKS DATA OPERASIONAL:
{context}

PERTANYAAN: {query}

JAWABAN:"""

    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
    }

    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json=payload,
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json().get("response", "Model tidak memberikan jawaban.")


def rag_query(query: str) -> dict:
    """Pipeline RAG lengkap: retrieve → generate.

    Args:
        query: Pertanyaan pengguna.

    Returns:
        Dictionary berisi konteks dan jawaban AI.
    """
    context = retrieve_context(query)
    answer = generate_with_ollama(query, context)
    return {
        "query": query,
        "context_used": context,
        "answer": answer,
        "source": "chromadb_rag",
    }
