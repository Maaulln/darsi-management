"""Membersihkan data operasional SIMRS sederhana untuk MVP DARSI."""

import os
from typing import Final

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

RAW_TABLE: Final[str] = "simrs_operasional_raw"
CLEAN_TABLE: Final[str] = "simrs_operasional_clean"


def build_postgres_url() -> str:
    """Menyusun URL koneksi PostgreSQL dari environment variable.

    Returns:
        URL SQLAlchemy PostgreSQL.
    """

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "darsi")
    user = os.getenv("POSTGRES_USER", "darsi_user")
    password = os.getenv("POSTGRES_PASSWORD", "darsi_password")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def create_engine_from_env() -> Engine:
    """Membuat SQLAlchemy engine berdasarkan environment variable.

    Returns:
        Engine SQLAlchemy yang siap digunakan.
    """

    return create_engine(build_postgres_url(), pool_pre_ping=True)


def refine_raw_data() -> int:
    """Menjalankan transformasi sederhana dari tabel raw ke clean.

    Returns:
        Jumlah baris pada tabel hasil pembersihan.
    """

    engine = create_engine_from_env()
    raw_dataframe = pd.read_sql(f"SELECT * FROM {RAW_TABLE}", con=engine)

    clean_dataframe = raw_dataframe.dropna(subset=["record_id", "unit", "indikator", "nilai"])
    clean_dataframe = clean_dataframe.drop_duplicates(subset=["record_id"])

    clean_dataframe.to_sql(CLEAN_TABLE, con=engine, if_exists="replace", index=False)
    return len(clean_dataframe)


if __name__ == "__main__":
    refined_rows = refine_raw_data()
    print(f"Refinement selesai. Total baris clean: {refined_rows}.")
