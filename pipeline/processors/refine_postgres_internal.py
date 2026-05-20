"""Refinement internal: bersihkan tabel raw_* di PostgreSQL → refined_*.

Tahapan refinement per domain:
    1. Filter baris tanpa kolom kunci (mis. unit_code).
    2. Trim whitespace pada kolom string.
    3. Coerce tipe numeric/datetime (NaN/NaT bila gagal).
    4. Deduplikasi.
    5. Outlier capping menggunakan metode IQR pada kolom numerik utama.
    6. Tulis ke tabel refined_* dan kembalikan metrik kualitas.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DOMAIN_CONFIG: dict[str, dict[str, Any]] = {
    "pasien_aktif": {
        "key_columns": ["unit_code", "patient_id", "snapshot_at"],
        "numeric_columns": [],
        "datetime_columns": ["snapshot_at"],
    },
    "okupansi_kamar": {
        "key_columns": ["unit_code", "room_id", "observed_at"],
        "numeric_columns": ["bed_capacity", "bed_occupied"],
        "datetime_columns": ["observed_at", "maintenance_start", "maintenance_end"],
    },
    "meter_listrik": {
        "key_columns": ["meter_id", "reading_at"],
        "numeric_columns": ["kwh_total", "voltage_avg", "current_avg", "power_factor"],
        "datetime_columns": ["reading_at"],
    },
    "konsumsi_air": {
        "key_columns": ["meter_id", "unit_code", "reading_at"],
        "numeric_columns": ["volume_m3_total", "pressure_avg"],
        "datetime_columns": ["reading_at"],
    },
    "biaya_operasional_unit": {
        "key_columns": ["unit_code", "period_month", "cost_category"],
        "numeric_columns": ["amount_idr", "budget_idr"],
        "datetime_columns": ["period_month"],
    },
    "konsumsi_obat_alkes": {
        "key_columns": ["item_code", "usage_at"],
        "numeric_columns": ["quantity", "unit_cost_idr", "total_cost_idr"],
        "datetime_columns": ["usage_at", "period_month"],
    },
    "lembur_staf": {
        "key_columns": ["unit_code", "staff_id", "overtime_date"],
        "numeric_columns": ["overtime_hours", "overtime_cost_idr"],
        "datetime_columns": ["overtime_date"],
    },
    "jadwal_alat_berat": {
        "key_columns": ["device_id", "schedule_start"],
        "numeric_columns": [],
        "datetime_columns": ["schedule_start", "schedule_end"],
    },
}


@dataclass
class RefinementReport:
    """Ringkasan metrik kualitas hasil refinement satu domain."""

    domain: str
    initial_rows: int = 0
    final_rows: int = 0
    dropped_by_keys: int = 0
    dropped_duplicates: int = 0
    outliers_capped: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "initial_rows": self.initial_rows,
            "final_rows": self.final_rows,
            "dropped_by_keys": self.dropped_by_keys,
            "dropped_duplicates": self.dropped_duplicates,
            "outliers_capped": self.outliers_capped,
            "quality_pct": round(
                100 * self.final_rows / self.initial_rows, 2
            ) if self.initial_rows else 0.0,
            "errors": self.errors,
        }


def build_postgres_url() -> str:
    """Susun URL koneksi PostgreSQL dari environment variable."""

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "darsi")
    user = os.getenv("POSTGRES_USER", "darsi_user")
    password = os.getenv("POSTGRES_PASSWORD", "darsi_password")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def create_engine_from_env() -> Engine:
    return create_engine(build_postgres_url(), pool_pre_ping=True)


def fast_write_df(df: pd.DataFrame, table_name: str, engine: Engine) -> None:
    """Tulis DataFrame ke PostgreSQL menggunakan COPY (jauh lebih cepat dari to_sql).

    Strategi:
        - Jika tabel belum ada, buat dengan to_sql (satu kali, lambat).
        - Jika sudah ada, TRUNCATE lalu stream data via COPY FROM stdin CSV.

    Args:
        df: DataFrame yang sudah dibersihkan.
        table_name: Nama tabel target di PostgreSQL.
        engine: SQLAlchemy engine.
    """

    # Pastikan semua nilai NaT/NaN menjadi None agar CSV-safe
    df = df.where(pd.notna(df), None)

    with engine.connect() as conn:
        raw_conn = conn.connection
        with raw_conn.cursor() as cur:
            # Cek apakah tabel sudah ada
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = %s)",
                (table_name,),
            )
            table_exists = cur.fetchone()[0]

            if not table_exists:
                # Buat tabel dengan struktur DataFrame (hanya sekali)
                df.head(0).to_sql(table_name, engine, if_exists="fail", index=False)

            # Kosongkan tabel tanpa DROP (lebih cepat, pertahankan struktur)
            cur.execute(f"TRUNCATE TABLE {table_name}")

            # Stream data via COPY FROM stdin (format CSV)
            buf = io.StringIO()
            df.to_csv(buf, index=False, header=False, na_rep="")
            buf.seek(0)

            columns = ", ".join(f'"{c}"' for c in df.columns)
            cur.copy_expert(
                f"COPY {table_name} ({columns}) FROM STDIN WITH (FORMAT CSV, NULL '')",
                buf,
            )
        raw_conn.commit()


def trim_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace pada kolom object/string."""

    for column in df.columns:
        if df[column].dtype == object:
            df[column] = df[column].apply(
                lambda value: value.strip() if isinstance(value, str) else value
            )
    return df


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Coerce kolom numeric — nilai non-numeric dijadikan NaN."""

    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def coerce_datetime(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Coerce kolom datetime dengan UTC awareness."""

    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce", utc=True)
    return df


def cap_outliers_iqr(
    df: pd.DataFrame, numeric_columns: list[str], factor: float = 3.0
) -> tuple[pd.DataFrame, int]:
    """Cap outlier (lebih luas dari 1.5×IQR) pada kolom numerik.

    Args:
        df: Dataframe sumber.
        numeric_columns: Kolom numerik yang akan diuji.
        factor: Lebar IQR yang ditoleransi (default 3× untuk konservatif).

    Returns:
        Tuple (dataframe, jumlah nilai yang dipotong).
    """

    total_capped = 0
    for column in numeric_columns:
        if column not in df.columns or df[column].dropna().empty:
            continue
        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lower = q1 - factor * iqr
        upper = q3 + factor * iqr
        mask = (df[column] < lower) | (df[column] > upper)
        capped = int(mask.sum())
        if capped:
            df.loc[df[column] < lower, column] = lower
            df.loc[df[column] > upper, column] = upper
            total_capped += capped
    return df, total_capped


def refine_domain(engine: Engine, domain: str, config: dict[str, Any]) -> RefinementReport:
    """Jalankan refinement satu domain dari raw_* ke refined_*."""

    raw_table = f"raw_{domain}"
    refined_table = f"refined_{domain}"
    report = RefinementReport(domain=domain)

    try:
        df = pd.read_sql(text(f"SELECT * FROM {raw_table}"), con=engine)
    except Exception as error:
        report.errors.append(f"read_raw_failed: {error}")
        return report

    report.initial_rows = len(df)
    if df.empty:
        return report

    key_columns = [c for c in config["key_columns"] if c in df.columns]
    if key_columns:
        before = len(df)
        df = df.dropna(subset=key_columns)
        report.dropped_by_keys = before - len(df)

    df = trim_strings(df)
    df = coerce_numeric(df, config.get("numeric_columns", []))
    df = coerce_datetime(df, config.get("datetime_columns", []))

    before_dup = len(df)
    df = df.drop_duplicates()
    report.dropped_duplicates = before_dup - len(df)

    df, capped = cap_outliers_iqr(df, config.get("numeric_columns", []))
    report.outliers_capped = capped

    df = df.replace({np.nan: None})

    try:
        fast_write_df(df, refined_table, engine)
    except Exception as error:
        report.errors.append(f"write_refined_failed: {error}")
        return report

    report.final_rows = len(df)
    return report


def refine_all(engine: Engine | None = None) -> list[dict[str, Any]]:
    """Refine seluruh domain. Kembalikan list metrik kualitas."""

    engine = engine or create_engine_from_env()
    reports: list[dict[str, Any]] = []
    for domain, config in DOMAIN_CONFIG.items():
        report = refine_domain(engine, domain, config)
        reports.append(report.as_dict())
    return reports


if __name__ == "__main__":
    print("Memulai pembersihan data internal di PostgreSQL...")
    summary = refine_all()
    for item in summary:
        status = "OK" if not item["errors"] else "FAIL"
        print(
            f" - {item['domain']}: {item['initial_rows']} → {item['final_rows']} "
            f"(keys={item['dropped_by_keys']}, dup={item['dropped_duplicates']}, "
            f"outliers={item['outliers_capped']}, q={item['quality_pct']}%, {status})"
        )
        if item["errors"]:
            for err in item["errors"]:
                print(f"     ! {err}")
