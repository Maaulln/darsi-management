"""Endpoint chat DARSI — mengarahkan pesan user ke MCP Server (RAG atau direct LLM)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rag_service import direct_query, rag_query

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
    """Tangani pesan chat. Default menggunakan RAG dengan konteks operasional."""
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    try:
        if payload.use_rag:
            result = rag_query(text)
        else:
            result = direct_query(text)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return ChatResponse(
        response=result.get("answer", ""),
        source=result.get("source", "unknown"),
        context_used=result.get("context_used", ""),
        matched_domains=result.get("matched_domains", []),
    )
