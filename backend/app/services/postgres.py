"""Database helper untuk interaksi langsung backend dengan PostgreSQL."""

import os
from sqlalchemy import create_engine, text

POSTGRES_USER = os.getenv("POSTGRES_USER", "darsi_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "darsi_password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "darsi")

DB_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DB_URL, pool_pre_ping=True)


def init_settings_db() -> None:
    """Inisialisasi tabel darsi_settings, darsi_incoming_apis, dan darsi_ai_models jika belum ada."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS darsi_settings (
                key VARCHAR(50) PRIMARY KEY,
                value TEXT NOT NULL
            )
        """))
        try:
            conn.execute(text("ALTER TABLE darsi_settings ALTER COLUMN value TYPE TEXT;"))
        except Exception:
            pass
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS darsi_incoming_apis (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                endpoint VARCHAR(255) NOT NULL UNIQUE,
                external_url TEXT,
                metabase_url TEXT,
                raw_data JSONB,
                last_fetched TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS darsi_ai_models (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                api_url TEXT NOT NULL,
                api_key TEXT,
                model_name VARCHAR(100) NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # Tambah kolom api_key jika belum ada
        try:
            conn.execute(text("ALTER TABLE darsi_ai_models ADD COLUMN api_key TEXT;"))
        except Exception:
            pass
        conn.execute(text("""
            INSERT INTO darsi_settings (key, value)
            VALUES ('simulator_enabled', 'true')
            ON CONFLICT (key) DO NOTHING
        """))
        conn.commit()


# Jalankan inisialisasi secara otomatis saat modul dimuat
try:
    init_settings_db()
except Exception as e:
    print(f"[WARN] Inisialisasi PostgreSQL settings gagal: {e}")
