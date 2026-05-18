"""Memuat seluruh dataset RAW SIMRS per domain ke PostgreSQL.

Script ini membaca beberapa file CSV domain operasional, melakukan validasi kolom wajib,
melakukan parsing tanggal/waktu dasar, lalu menambahkan data ke tabel `raw_*` di PostgreSQL.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final
from uuid import uuid4

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BASE_RAW_DIR: Final[Path] = Path("data/sample_simrs/raw_domains")

RAW_CONFIG: Final[dict[str, dict[str, object]]] = {
    "raw_pasien_aktif": {
        "file": "raw_pasien_aktif.csv",
        "required": ["snapshot_at", "patient_id", "status_aktif"],
        "datetime_cols": ["snapshot_at"],
        "conflict_cols": ["snapshot_at", "patient_id", "status_aktif"],
    },
    "raw_okupansi_kamar": {
        "file": "raw_okupansi_kamar.csv",
        "required": ["observed_at", "room_id", "bed_capacity", "bed_occupied", "room_status"],
        "datetime_cols": ["observed_at", "maintenance_start", "maintenance_end"],
        "conflict_cols": ["observed_at", "room_id"],
    },
    "raw_meter_listrik": {
        "file": "raw_meter_listrik.csv",
        "required": ["meter_id", "building_code", "reading_at", "kwh_total"],
        "datetime_cols": ["reading_at"],
        "conflict_cols": ["meter_id", "reading_at"],
    },
    "raw_konsumsi_air": {
        "file": "raw_konsumsi_air.csv",
        "required": ["meter_id", "unit_code", "reading_at", "volume_m3_total"],
        "datetime_cols": ["reading_at"],
        "conflict_cols": ["meter_id", "reading_at"],
    },
    "raw_biaya_operasional_unit": {
        "file": "raw_biaya_operasional_unit.csv",
        "required": ["period_month", "unit_code", "cost_category", "amount_idr"],
        "datetime_cols": ["period_month"],
        "conflict_cols": ["period_month", "unit_code", "cost_category", "source_record_id"],
    },
    "raw_konsumsi_obat_alkes": {
        "file": "raw_konsumsi_obat_alkes.csv",
        "required": ["usage_at", "period_month", "item_code", "item_name", "item_type", "quantity"],
        "datetime_cols": ["usage_at", "period_month"],
        "conflict_cols": ["usage_at", "item_code", "unit_code", "source_record_id"],
    },
    "raw_lembur_staf": {
        "file": "raw_lembur_staf.csv",
        "required": ["overtime_date", "unit_code", "staff_id", "overtime_hours", "overtime_cost_idr"],
        "datetime_cols": ["overtime_date"],
        "conflict_cols": ["overtime_date", "staff_id", "unit_code", "source_record_id"],
    },
    "raw_jadwal_alat_berat": {
        "file": "raw_jadwal_alat_berat.csv",
        "required": ["device_id", "device_name", "schedule_start", "schedule_end", "schedule_type", "status"],
        "datetime_cols": ["schedule_start", "schedule_end"],
        "conflict_cols": ["device_id", "schedule_start", "schedule_type", "source_record_id"],
    },
}


def build_postgres_url() -> str:
    """Menyusun URL koneksi PostgreSQL dari environment variable.

    Returns:
        URL SQLAlchemy untuk PostgreSQL.
    """

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "darsi")
    user = os.getenv("POSTGRES_USER", "darsi_user")
    password = os.getenv("POSTGRES_PASSWORD", "darsi_password")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def create_engine_from_env() -> Engine:
    """Membuat SQLAlchemy engine berdasarkan konfigurasi environment.

    Returns:
        Engine SQLAlchemy untuk operasi database.
    """

    return create_engine(build_postgres_url(), pool_pre_ping=True)


def validate_required_columns(dataframe: pd.DataFrame, required_columns: list[str], table_name: str) -> None:
    """Memvalidasi keberadaan kolom wajib pada dataframe.

    Args:
        dataframe: Dataframe hasil baca CSV.
        required_columns: Daftar nama kolom wajib.
        table_name: Nama tabel target untuk konteks pesan error.

    Raises:
        ValueError: Jika ada kolom wajib yang tidak tersedia.
    """

    missing_columns = [column for column in required_columns if column not in dataframe.columns]
    if missing_columns:
        raise ValueError(f"Kolom wajib untuk {table_name} tidak lengkap: {missing_columns}")


def parse_datetime_columns(dataframe: pd.DataFrame, datetime_columns: list[str]) -> pd.DataFrame:
    """Melakukan parsing kolom tanggal/waktu yang tersedia di dataframe.

    Args:
        dataframe: Dataframe sumber.
        datetime_columns: Daftar nama kolom tanggal/waktu.

    Returns:
        Dataframe dengan kolom tanggal/waktu yang sudah diparse.
    """

    for column in datetime_columns:
        if column in dataframe.columns:
            dataframe[column] = pd.to_datetime(dataframe[column], errors="coerce")
    return dataframe


def normalize_records(dataframe: pd.DataFrame) -> list[dict[str, object]]:
    """Mengubah dataframe menjadi list record Python yang aman untuk SQLAlchemy.

    Args:
        dataframe: Dataframe hasil parsing data mentah.

    Returns:
        List dictionary record tanpa nilai NaN/NaT.
    """

    normalized_frame = dataframe.where(pd.notna(dataframe), None)
    return normalized_frame.to_dict(orient="records")


def run_upsert(
    engine: Engine,
    table_name: str,
    records: list[dict[str, object]],
    conflict_columns: list[str],
) -> int:
    """Menjalankan UPSERT data ke tabel target PostgreSQL.

    Args:
        engine: Engine SQLAlchemy.
        table_name: Nama tabel tujuan.
        records: Record yang akan ditulis.
        conflict_columns: Kolom conflict target untuk ON CONFLICT.

    Returns:
        Jumlah record yang diproses.
    """

    if not records:
        return 0

    insert_columns = list(records[0].keys())
    update_columns = [column for column in insert_columns if column not in conflict_columns]

    quoted_insert_columns = ", ".join([f'"{column}"' for column in insert_columns])
    insert_placeholders = ", ".join([f':{column}' for column in insert_columns])
    quoted_conflict_columns = ", ".join([f'"{column}"' for column in conflict_columns])

    if update_columns:
        update_clause = ", ".join([f'"{column}" = EXCLUDED."{column}"' for column in update_columns])
        conflict_action = f"DO UPDATE SET {update_clause}"
    else:
        conflict_action = "DO NOTHING"

    upsert_sql = text(
        f"""
        INSERT INTO {table_name} ({quoted_insert_columns})
        VALUES ({insert_placeholders})
        ON CONFLICT ({quoted_conflict_columns})
        {conflict_action}
        """
    )

    with engine.begin() as connection:
        connection.execute(upsert_sql, records)

    return len(records)


def log_ingestion(
    engine: Engine,
    source_system: str,
    domain_name: str,
    run_id: str,
    status: str,
    extracted_rows: int,
    inserted_rows: int,
    error_message: str | None,
) -> None:
    """Mencatat hasil ingestion domain ke tabel raw_ingestion_log.

    Args:
        engine: Engine SQLAlchemy.
        source_system: Sumber data domain.
        domain_name: Nama domain/tabel yang diproses.
        run_id: ID unik eksekusi ingestion.
        status: Status proses, contoh success atau failed.
        extracted_rows: Jumlah baris yang dibaca dari file.
        inserted_rows: Jumlah baris yang diproses ke tabel target.
        error_message: Pesan error bila terjadi kegagalan.
    """

    insert_log_sql = text(
        """
        INSERT INTO raw_ingestion_log (
            source_system,
            domain_name,
            run_id,
            status,
            extracted_rows,
            inserted_rows,
            error_message,
            started_at,
            finished_at
        ) VALUES (
            :source_system,
            :domain_name,
            :run_id,
            :status,
            :extracted_rows,
            :inserted_rows,
            :error_message,
            NOW(),
            NOW()
        )
        """
    )

    with engine.begin() as connection:
        connection.execute(
            insert_log_sql,
            {
                "source_system": source_system,
                "domain_name": domain_name,
                "run_id": run_id,
                "status": status,
                "extracted_rows": extracted_rows,
                "inserted_rows": inserted_rows,
                "error_message": error_message,
            },
        )


def load_domain_file(engine: Engine, table_name: str, config: dict[str, object]) -> int:
    """Memuat satu file domain ke tabel PostgreSQL target.

    Args:
        engine: Engine SQLAlchemy yang aktif.
        table_name: Nama tabel target di PostgreSQL.
        config: Konfigurasi file dan validasi domain.

    Returns:
        Jumlah baris yang berhasil ditulis ke tabel.

    Raises:
        FileNotFoundError: Jika file CSV domain tidak ditemukan.
        ValueError: Jika validasi kolom wajib gagal.
    """

    filename = str(config["file"])
    required_columns = list(config["required"])
    datetime_columns = list(config["datetime_cols"])
    conflict_columns = list(config["conflict_cols"])

    csv_path = BASE_RAW_DIR / filename
    if not csv_path.exists():
        raise FileNotFoundError(f"File CSV domain tidak ditemukan: {csv_path}")

    dataframe = pd.read_csv(csv_path)
    validate_required_columns(dataframe, required_columns, table_name)
    dataframe = parse_datetime_columns(dataframe, datetime_columns)
    records = normalize_records(dataframe)

    return run_upsert(engine, table_name, records, conflict_columns)


def load_all_domains() -> dict[str, int]:
    """Memuat seluruh domain RAW SIMRS yang terkonfigurasi.

    Returns:
        Dictionary jumlah baris yang dimuat per tabel domain.
    """

    engine = create_engine_from_env()
    loaded_summary: dict[str, int] = {}
    run_id = str(uuid4())
    failure_messages: list[str] = []

    for table_name, config in RAW_CONFIG.items():
        domain_source = str(config.get("source_system", "SIMRS"))
        file_path = BASE_RAW_DIR / str(config["file"])
        extracted_rows = 0

        try:
            if file_path.exists():
                extracted_rows = len(pd.read_csv(file_path))

            inserted_rows = load_domain_file(engine, table_name, config)
            loaded_summary[table_name] = inserted_rows
            log_ingestion(
                engine=engine,
                source_system=domain_source,
                domain_name=table_name,
                run_id=run_id,
                status="success",
                extracted_rows=extracted_rows,
                inserted_rows=inserted_rows,
                error_message=None,
            )
        except Exception as error:  # noqa: BLE001
            failure_message = f"{table_name}: {error}"
            failure_messages.append(failure_message)
            log_ingestion(
                engine=engine,
                source_system=domain_source,
                domain_name=table_name,
                run_id=run_id,
                status="failed",
                extracted_rows=extracted_rows,
                inserted_rows=0,
                error_message=str(error),
            )

    if failure_messages:
        joined_message = "; ".join(failure_messages)
        raise RuntimeError(f"Ingestion gagal pada beberapa domain: {joined_message}")

    return loaded_summary


if __name__ == "__main__":
    summary = load_all_domains()
    for table_name, total_rows in summary.items():
        print(f"{table_name}: {total_rows} baris berhasil dimuat")
