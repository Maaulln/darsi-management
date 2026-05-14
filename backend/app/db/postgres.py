"""Utility koneksi PostgreSQL untuk DARSI backend."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings


def build_postgres_url() -> str:
    """Menyusun URL koneksi PostgreSQL.

    Returns:
        URL koneksi SQLAlchemy untuk PostgreSQL.
    """

    return (
        f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def create_postgres_engine() -> Engine:
    """Membuat SQLAlchemy engine untuk akses database.

    Returns:
        Engine SQLAlchemy yang sudah dikonfigurasi pool sederhana.
    """

    return create_engine(build_postgres_url(), pool_pre_ping=True)
