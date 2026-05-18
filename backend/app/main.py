"""Entrypoint aplikasi FastAPI untuk DARSI Management."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.chat import router as chat_router
from app.api.data import router as data_router
from app.api.health import router as health_router
from app.api.rag import router as rag_router
from app.api.settings import router as settings_router
from app.api.summary import router as summary_router
from app.core.config import settings


def create_app() -> FastAPI:
    """Membuat instance aplikasi FastAPI dengan seluruh router DARSI."""

    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(data_router)
    app.include_router(summary_router)
    app.include_router(chat_router)
    app.include_router(rag_router)
    app.include_router(analytics_router)
    app.include_router(settings_router)
    return app


app = create_app()
