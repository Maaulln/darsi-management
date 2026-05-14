from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from app.core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@router.post("", response_model=ChatResponse)
async def chat_with_ollama(payload: ChatRequest):
    """Kirim pesan ke Ollama dan kembalikan responnya."""
    try:
        ollama_url = f"{settings.ollama_base_url}/api/generate"
        payload_ollama = {
            "model": settings.ollama_model,
            "prompt": payload.message,
            "stream": False
        }
        
        response = requests.post(ollama_url, json=payload_ollama, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        return ChatResponse(response=data.get("response", "No response from Ollama"))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
