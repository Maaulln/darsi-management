"""DAG orkestrasi pipeline DARSI: RAW Ingestion → Internal Refinement → SurrealDB Sync.

Jadwal default: setiap hari pukul 02:00 WIB.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Path ke direktori script ingestion (di-mount ke container Airflow)
SCRIPT_DIR = "/opt/airflow/scripts"

DEFAULT_ARGS = {
    "owner": "darsi",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

POSTGRES_ENV = {
    "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "postgres"),
    "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
    "POSTGRES_DB": os.getenv("POSTGRES_DB", "darsi"),
    "POSTGRES_USER": os.getenv("POSTGRES_USER", "darsi_user"),
    "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "darsi_password"),
    "SURREALDB_URL": os.getenv("SURREALDB_URL", "http://surrealdb:8000"),
    "SURREALDB_USER": os.getenv("SURREALDB_USER", "root"),
    "SURREALDB_PASSWORD": os.getenv("SURREALDB_PASSWORD", "root"),
    "SURREALDB_NS": os.getenv("SURREALDB_NS", "darsi"),
    "SURREALDB_DB": os.getenv("SURREALDB_DB", "operasional"),
}


def run_script(script_name: str, *args: str) -> None:
    """Menjalankan Python script ingestion sebagai subprocess.

    Args:
        script_name: Nama file script di dalam SCRIPT_DIR.
        *args: Argumen tambahan untuk script.
    """
    cmd = ["python", f"{SCRIPT_DIR}/{script_name}"] + list(args)
    env = {**os.environ, **POSTGRES_ENV}
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        raise RuntimeError(f"Script {script_name} gagal:\n{result.stderr}")


def task_bulk_ingestion() -> None:
    """Task 1: Generate/ingest data mentah ke tabel raw_* PostgreSQL."""
    run_script("generate_bulk_dummy_data.py")


def task_internal_refinement() -> None:
    """Task 2: Bersihkan data dari raw_* ke refined_* di PostgreSQL."""
    run_script("refine_postgres_internal.py")


def task_sync_to_surrealdb() -> None:
    """Task 3: Kirim data bersih dari refined_* ke SurrealDB (clean_*)."""
    run_script("refine_raw_to_surrealdb.py", "--apply")


def task_embed_to_chromadb() -> None:
    """Task 4: Embed data refined ke ChromaDB untuk kebutuhan RAG."""
    run_script("embed_to_chromadb.py")


with DAG(
    dag_id="darsi_data_pipeline",
    description="Pipeline lengkap DARSI: Ingestion → Refinement → SurrealDB → ChromaDB",
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 2 * * *",  # Setiap hari jam 02:00
    default_args=DEFAULT_ARGS,
    catchup=False,
    tags=["darsi", "data-pipeline", "fase1"],
) as dag:

    t1_ingestion = PythonOperator(
        task_id="raw_ingestion",
        python_callable=task_bulk_ingestion,
    )

    t2_refinement = PythonOperator(
        task_id="internal_refinement",
        python_callable=task_internal_refinement,
    )

    t3_surrealdb = PythonOperator(
        task_id="sync_to_surrealdb",
        python_callable=task_sync_to_surrealdb,
    )

    t4_chromadb = PythonOperator(
        task_id="embed_to_chromadb",
        python_callable=task_embed_to_chromadb,
    )

    # Alur: Ingestion → Refinement → SurrealDB → ChromaDB
    t1_ingestion >> t2_refinement >> t3_surrealdb >> t4_chromadb
