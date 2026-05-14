"""Endpoint chat DARSI — mengarahkan pesan user ke pipeline RAG (default) atau Ollama langsung."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.rag_service import generate_with_ollama, rag_query

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    use_rag: bool = True


class ChatResponse(BaseModel):
    response: str
    source: str
    context_used: str = ""
    matched_domains: list[str] = []


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Tangani pesan chat. Default menggunakan RAG dengan konteks operasional.

    Args:
        payload: Pesan user dan flag `use_rag`.

    Returns:
        Jawaban AI plus konteks yang dipakai (bila RAG aktif).
    """
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    if payload.use_rag:
        try:
            rag_result = rag_query(text)
            return ChatResponse(
                response=rag_result["answer"],
                source=rag_result["source"],
                context_used=rag_result["context_used"],
                matched_domains=rag_result.get("matched_domains", []),
            )
        except Exception as error:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(error)) from error

    try:
        answer = generate_with_ollama(text, context="(no context)")
        return ChatResponse(response=answer, source="ollama_direct")
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=f"Ollama error: {error}") from error
