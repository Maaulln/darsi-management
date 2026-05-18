"""Memuat data SIMRS dummy dari CSV ke PostgreSQL."""

import os
from typing import Final

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

DEFAULT_CSV_PATH: Final[str] = "data/sample_simrs/dummy_simrs.csv"
TABLE_NAME: Final[str] = "simrs_operasional_raw"


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


def load_csv_to_postgres(csv_path: str = DEFAULT_CSV_PATH) -> int:
    """Membaca CSV SIMRS dan menyimpan ke PostgreSQL.

    Args:
        csv_path: Lokasi file CSV input.

    Returns:
        Jumlah baris data yang berhasil dimuat.

    Raises:
        FileNotFoundError: Jika file CSV tidak ditemukan.
    """

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File CSV tidak ditemukan: {csv_path}")

    dataframe = pd.read_csv(csv_path)
    engine = create_engine_from_env()
    dataframe.to_sql(TABLE_NAME, con=engine, if_exists="replace", index=False)
    return len(dataframe)


if __name__ == "__main__":
    inserted_rows = load_csv_to_postgres()
    print(f"Berhasil memuat {inserted_rows} baris ke tabel {TABLE_NAME}.")
