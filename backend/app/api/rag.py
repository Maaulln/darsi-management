"""Endpoint RAG DARSI: query terhadap pipeline MCP + Ollama."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rag_service import rag_query

router = APIRouter(prefix="/api/rag", tags=["rag"])


class RagRequest(BaseModel):
    query: str
    n_results: int = 5


class RagResponse(BaseModel):
    query: str
    context_used: str
    answer: str
    source: str
    chroma_hits: int = 0
    surreal_hits: int = 0
    matched_domains: list[str] = []


@router.post("/query", response_model=RagResponse)
async def query_rag(payload: RagRequest) -> RagResponse:
    """Jalankan RAG: retrieve konteks + generate jawaban LLM."""
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query tidak boleh kosong.")
    try:
        result = rag_query(payload.query, n_results=payload.n_results)
        return RagResponse(**result)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error
