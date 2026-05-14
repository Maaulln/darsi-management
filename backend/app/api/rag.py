"""API endpoint untuk RAG query DARSI."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_service import rag_query

router = APIRouter(prefix="/api/rag", tags=["rag"])


class RagRequest(BaseModel):
    query: str


class RagResponse(BaseModel):
    query: str
    context_used: str
    answer: str
    source: str


@router.post("/query", response_model=RagResponse)
async def query_rag(payload: RagRequest) -> RagResponse:
    """Menerima pertanyaan user dan mengembalikan jawaban berbasis RAG.

    Args:
        payload: Request berisi query pengguna.

    Returns:
        Jawaban AI dengan konteks data operasional.
    """
    try:
        result = rag_query(payload.query)
        return RagResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
