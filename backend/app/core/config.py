"""Konfigurasi aplikasi DARSI dari environment variable."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurasi runtime backend DARSI.

    Backend hanya perlu tahu tentang dirinya sendiri dan MCP Server.
    Semua akses ke database dan LLM dikelola oleh MCP Server.
    """

    app_name: str = "DARSI Management API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    mcp_server_url: str = "http://mcp-server:8100"
    cors_origins: str = "http://localhost:5173,http://localhost:80,http://localhost"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
