"""Konfigurasi aplikasi DARSI dari environment variable."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Menyimpan konfigurasi runtime aplikasi.

    Attributes:
        app_name: Nama aplikasi yang ditampilkan pada metadata API.
        app_env: Lingkungan aplikasi, contoh: development atau production.
        app_host: Host bind untuk server FastAPI.
        app_port: Port bind untuk server FastAPI.
        postgres_host: Host layanan PostgreSQL.
        postgres_port: Port layanan PostgreSQL.
        postgres_db: Nama database PostgreSQL.
        postgres_user: Username PostgreSQL.
        postgres_password: Password PostgreSQL.
    """

    app_name: str = "DARSI Management API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "darsi"
    postgres_user: str = "darsi_user"
    postgres_password: str = "darsi_password"

    surrealdb_url: str = "http://surrealdb:8000"
    surrealdb_user: str = "root"
    surrealdb_password: str = "root"
    surrealdb_ns: str = "darsi"
    surrealdb_db: str = "operasional"

    chroma_host: str = "chromadb"
    chroma_port: int = 8000

    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "qwen3.5:2b"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
