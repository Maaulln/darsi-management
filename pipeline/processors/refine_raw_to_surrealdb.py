"""Menyiapkan dan mengirim data clean dari PostgreSQL RAW ke SurrealDB.

Default berjalan pada mode dry-run untuk validasi transformasi tanpa menulis ke SurrealDB.
Gunakan `--apply` bila ingin mengirim hasil transformasi ke SurrealDB.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Final

import pandas as pd
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DOMAIN_QUERY: Final[dict[str, str]] = {
    "pasien_aktif": """
        SELECT snapshot_at, patient_id, unit_code, room_code, class_code, status_aktif, diagnosis_code
        FROM refined_pasien_aktif
    """,
    "okupansi_kamar": """
        SELECT observed_at, room_id, unit_code, room_class, bed_capacity, bed_occupied, room_status
        FROM refined_okupansi_kamar
    """,
    "meter_listrik": """
        SELECT reading_at, meter_id, building_code, floor_code, unit_code, kwh_total
        FROM refined_meter_listrik
    """,
    "konsumsi_air": """
        SELECT reading_at, meter_id, building_code, unit_code, volume_m3_total
        FROM refined_konsumsi_air
    """,
    "biaya_operasional": """
        SELECT period_month, unit_code, cost_category, amount_idr, budget_idr
        FROM refined_biaya_operasional_unit
    """,
    "konsumsi_obat_alkes": """
        SELECT usage_at, period_month, unit_code, item_code, item_name, item_type, quantity, total_cost_idr
        FROM refined_konsumsi_obat_alkes
    """,
    "lembur_staf": """
        SELECT overtime_date, unit_code, staff_id, role_name, overtime_hours, overtime_cost_idr
        FROM refined_lembur_staf
    """,
    "jadwal_alat_berat": """
        SELECT schedule_start, schedule_end, device_id, device_name, unit_code, schedule_type, status
        FROM refined_jadwal_alat_berat
    """,
}


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
    """Membuat SQLAlchemy engine PostgreSQL.

    Returns:
        Engine SQLAlchemy.
    """

    return create_engine(build_postgres_url(), pool_pre_ping=True)


def build_surreal_sql_endpoint() -> str:
    """Menyusun endpoint SQL SurrealDB dari environment variable.

    Returns:
        URL endpoint SQL SurrealDB.
    """

    url = os.getenv("SURREALDB_URL", "http://localhost:8001/rpc")
    if url.endswith("/rpc"):
        return url[:-4] + "/sql"
    return url.rstrip("/") + "/sql"


def fetch_domain_dataframe(engine: Engine, domain_name: str) -> pd.DataFrame:
    """Mengambil data raw per domain dari PostgreSQL.

    Args:
        engine: Engine SQLAlchemy PostgreSQL.
        domain_name: Nama domain yang tersedia pada DOMAIN_QUERY.

    Returns:
        Dataframe data raw untuk domain terkait.
    """

    query = DOMAIN_QUERY[domain_name]
    return pd.read_sql(text(query), con=engine)


def transform_to_clean_records(dataframe: pd.DataFrame) -> list[dict[str, object]]:
    """Mengubah dataframe menjadi list record clean untuk sinkronisasi SurrealDB.

    Args:
        dataframe: Dataframe sumber dari PostgreSQL.

    Returns:
        List dictionary record clean.
    """

    normalized_frame = dataframe.where(pd.notna(dataframe), None)
    return normalized_frame.to_dict(orient="records")


_BATCH_SIZE: Final[int] = 50


def build_domain_init_query(domain_name: str) -> str:
    return f"DEFINE TABLE IF NOT EXISTS clean_{domain_name} SCHEMALESS; DELETE clean_{domain_name};"


def build_domain_batch_query(domain_name: str, records: list[dict[str, object]]) -> str:
    statements = []
    for record in records:
        json_payload = json.dumps(record, default=str, ensure_ascii=True)
        statements.append(f"CREATE clean_{domain_name} CONTENT {json_payload};")
    return " ".join(statements)


def validate_surreal_sql_response(response: requests.Response, domain_name: str) -> None:
    """Memvalidasi bahwa seluruh statement SurrealDB selesai dengan status OK.

    Args:
        response: Objek response HTTP dari endpoint /sql SurrealDB.
        domain_name: Nama domain yang sedang diproses.

    Raises:
        RuntimeError: Jika ada status statement yang bukan OK.
    """

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError(
            f"Respons SurrealDB domain {domain_name} tidak valid JSON: {response.text}"
        ) from error

    if not isinstance(payload, list):
        raise RuntimeError(f"Respons SurrealDB domain {domain_name} tidak berbentuk list: {payload}")

    failed_statements = [item for item in payload if item.get("status") != "OK"]
    if failed_statements:
        raise RuntimeError(
            f"Eksekusi SQL SurrealDB gagal pada domain {domain_name}: {failed_statements}"
        )


def send_to_surrealdb(domain_name: str, records: list[dict[str, object]]) -> None:
    """Mengirim record clean ke SurrealDB menggunakan endpoint SQL, dalam batch.

    Args:
        domain_name: Nama domain clean target.
        records: Record clean yang akan dikirim.

    Raises:
        RuntimeError: Jika request ke SurrealDB gagal.
    """

    if not records:
        return

    surreal_endpoint = build_surreal_sql_endpoint()
    surreal_user = os.getenv("SURREALDB_USER", "root")
    surreal_password = os.getenv("SURREALDB_PASSWORD", "root")
    surreal_namespace = os.getenv("SURREALDB_NS", "darsi")
    surreal_database = os.getenv("SURREALDB_DB", "operasional")

    headers = {
        "Accept": "application/json",
        "surreal-ns": surreal_namespace,
        "surreal-db": surreal_database,
        "NS": surreal_namespace,
        "DB": surreal_database,
    }

    def _post(query: str) -> None:
        try:
            response = requests.post(
                surreal_endpoint,
                data=query,
                headers=headers,
                auth=(surreal_user, surreal_password),
                timeout=60,
            )
            response.raise_for_status()
            validate_surreal_sql_response(response, domain_name)
        except requests.RequestException as error:
            raise RuntimeError(f"Gagal kirim data domain {domain_name} ke SurrealDB: {error}") from error

    _post(build_domain_init_query(domain_name))

    for offset in range(0, len(records), _BATCH_SIZE):
        batch = records[offset : offset + _BATCH_SIZE]
        _post(build_domain_batch_query(domain_name, batch))


def refine_all_domains(apply: bool) -> dict[str, int]:
    """Menjalankan refinement seluruh domain raw menuju payload clean.

    Args:
        apply: Jika True, kirim hasil transformasi ke SurrealDB.

    Returns:
        Ringkasan jumlah record clean per domain.
    """

    engine = create_engine_from_env()
    summary: dict[str, int] = {}

    for domain_name in DOMAIN_QUERY:
        dataframe = fetch_domain_dataframe(engine, domain_name)
        records = transform_to_clean_records(dataframe)
        summary[domain_name] = len(records)

        if apply:
            send_to_surrealdb(domain_name, records)

    return summary


def parse_args() -> argparse.Namespace:
    """Membaca argument CLI script refinement.

    Returns:
        Namespace argumen CLI.
    """

    parser = argparse.ArgumentParser(description="Refinement RAW PostgreSQL ke clean payload SurrealDB")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Kirim hasil transformasi ke SurrealDB. Tanpa flag ini hanya dry-run.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    result_summary = refine_all_domains(apply=arguments.apply)
    mode = "APPLY" if arguments.apply else "DRY-RUN"
    print(f"Mode refinement: {mode}")
    for domain_name, total_records in result_summary.items():
        print(f"clean_{domain_name}: {total_records} record siap")