"""Simulator data SIMRS — insert data dummy ke PostgreSQL setiap 10 detik.

Mensimulasikan aliran data real-time dari SIMRS ke tabel raw_* PostgreSQL.
Jumlah record per run: acak antara 1–100 per domain.
"""

from __future__ import annotations

import os
import random
import time
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import create_engine, text

# ─── Config ──────────────────────────────────────────────────────────────────

DB_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'darsi_user')}"
    f":{os.getenv('POSTGRES_PASSWORD', 'darsi_password')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}"
    f":{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.getenv('POSTGRES_DB', 'darsi')}"
)

INTERVAL_SECONDS = int(os.getenv("SIMULATOR_INTERVAL", "10"))
MIN_RECORDS = int(os.getenv("SIMULATOR_MIN_RECORDS", "1"))
MAX_RECORDS = int(os.getenv("SIMULATOR_MAX_RECORDS", "100"))

UNITS = ["UGD", "RI-A", "RI-B", "OK", "LAB", "RAD", "FAR", "ICU"]
BUILDINGS = ["GD-A", "GD-B"]
CLASSES = ["VIP", "Kls1", "Kls2", "Kls3"]

# ─── Generator per domain ─────────────────────────────────────────────────────


def _gen_pasien_aktif(n: int, now: datetime) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        rows.append({
            "source_record_id": f"PX-{random.randint(10000, 99999)}",
            "snapshot_at": now - timedelta(seconds=random.randint(0, 600)),
            "patient_id": f"P-{random.randint(1000, 9999)}",
            "admission_id": f"A-{random.randint(1000, 9999)}",
            "unit_code": random.choice(UNITS),
            "room_code": f"R-{random.randint(101, 505)}",
            "class_code": random.choice(CLASSES),
            "status_aktif": "Rawat Inap",
            "payer_type": random.choice(["BPJS", "Asuransi", "Mandiri"]),
            "diagnosis_code": f"ICD10-{random.randint(100, 999)}",
            "created_at": now,
        })
    return pd.DataFrame(rows)


def _gen_okupansi_kamar(n: int, now: datetime) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        capacity = random.choice([1, 2, 4, 6])
        rows.append({
            "source_record_id": f"OCC-{random.randint(10000, 99999)}",
            "observed_at": now - timedelta(seconds=random.randint(0, 300)),
            "building_code": random.choice(BUILDINGS),
            "floor_code": f"LT-{random.randint(1, 5)}",
            "unit_code": random.choice(["RI-A", "RI-B", "ICU"]),
            "room_id": f"ROOM-{random.randint(1000, 9999)}",
            "room_class": random.choice(CLASSES),
            "bed_capacity": capacity,
            "bed_occupied": random.randint(0, capacity),
            "room_status": "Aktif",
            "created_at": now,
        })
    return pd.DataFrame(rows)


def _gen_meter_listrik(n: int, now: datetime) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        rows.append({
            "meter_id": f"MTR-E-{random.randint(1, 10)}",
            "building_code": random.choice(BUILDINGS),
            "floor_code": f"LT-{random.randint(1, 5)}",
            "unit_code": random.choice(UNITS),
            "reading_at": now - timedelta(seconds=random.randint(0, 300)),
            "kwh_total": round(random.uniform(100, 5000), 2),
            "voltage_avg": round(random.uniform(210, 230), 2),
            "current_avg": round(random.uniform(10, 50), 2),
            "power_factor": round(random.uniform(0.8, 0.95), 3),
            "created_at": now,
        })
    return pd.DataFrame(rows)


def _gen_konsumsi_air(n: int, now: datetime) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        rows.append({
            "meter_id": f"MTR-W-{random.randint(1, 10)}",
            "building_code": random.choice(BUILDINGS),
            "unit_code": random.choice(UNITS),
            "reading_at": now - timedelta(seconds=random.randint(0, 300)),
            "volume_m3_total": round(random.uniform(50, 2000), 2),
            "pressure_avg": round(random.uniform(2.0, 4.5), 2),
            "created_at": now,
        })
    return pd.DataFrame(rows)


def _gen_biaya_operasional(n: int, now: datetime) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        rows.append({
            "source_record_id": f"COST-{random.randint(10000, 99999)}",
            "period_month": datetime(now.year, now.month, 1),
            "unit_code": random.choice(UNITS),
            "cost_category": random.choice(["Gaji", "Listrik", "Air", "Alat Kesehatan", "Lainnya"]),
            "amount_idr": round(random.uniform(1_000_000, 500_000_000), 0),
            "budget_idr": round(random.uniform(10_000_000, 600_000_000), 0),
            "created_at": now,
        })
    return pd.DataFrame(rows)


def _gen_konsumsi_obat_alkes(n: int, now: datetime) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        qty = round(random.uniform(1, 100), 1)
        unit_cost = round(random.uniform(5_000, 100_000), 0)
        rows.append({
            "source_record_id": f"PH-{random.randint(10000, 99999)}",
            "usage_at": now - timedelta(minutes=random.randint(0, 60)),
            "period_month": datetime(now.year, now.month, 1),
            "unit_code": random.choice(UNITS),
            "item_code": f"ITEM-{random.randint(100, 999)}",
            "item_name": random.choice(["Paracetamol", "Infus RL", "Masker Bedah", "Sarung Tangan", "Spuit 3cc"]),
            "item_type": random.choice(["Obat", "Alkes"]),
            "quantity": qty,
            "uom": random.choice(["Botol", "Pcs", "Box"]),
            "unit_cost_idr": unit_cost,
            "total_cost_idr": round(qty * unit_cost, 0),
            "created_at": now,
        })
    return pd.DataFrame(rows)


def _gen_lembur_staf(n: int, now: datetime) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        hours = round(random.uniform(0.5, 5), 1)
        rows.append({
            "source_record_id": f"HR-{random.randint(10000, 99999)}",
            "overtime_date": now.date(),
            "unit_code": random.choice(UNITS),
            "staff_id": f"ST-{random.randint(100, 999)}",
            "role_name": random.choice(["Perawat", "Dokter", "Admin", "Security", "Teknisi"]),
            "overtime_hours": hours,
            "overtime_cost_idr": round(hours * random.uniform(30_000, 80_000), 0),
            "reason": random.choice(["Overload pasien", "Pergantian shift", "Kedaruratan", "Event khusus"]),
            "created_at": now,
        })
    return pd.DataFrame(rows)


def _gen_jadwal_alat_berat(n: int, now: datetime) -> pd.DataFrame:
    rows = []
    for _ in range(n):
        start = now + timedelta(minutes=random.randint(-30, 120))
        rows.append({
            "source_record_id": f"DEV-{random.randint(10000, 99999)}",
            "device_id": f"DIAG-{random.randint(10, 50)}",
            "device_name": random.choice(["MRI", "CT Scan", "X-Ray", "Ventilator", "USG"]),
            "unit_code": random.choice(["RAD", "RI-A", "ICU", "UGD"]),
            "schedule_start": start,
            "schedule_end": start + timedelta(hours=random.randint(1, 3)),
            "schedule_type": "Pemeriksaan",
            "status": random.choice(["Scheduled", "Completed", "Ongoing"]),
            "created_at": now,
        })
    return pd.DataFrame(rows)


# ─── Domain registry ──────────────────────────────────────────────────────────

DOMAINS = [
    ("raw_pasien_aktif",            _gen_pasien_aktif),
    ("raw_okupansi_kamar",          _gen_okupansi_kamar),
    ("raw_meter_listrik",           _gen_meter_listrik),
    ("raw_konsumsi_air",            _gen_konsumsi_air),
    ("raw_biaya_operasional_unit",  _gen_biaya_operasional),
    ("raw_konsumsi_obat_alkes",     _gen_konsumsi_obat_alkes),
    ("raw_lembur_staf",             _gen_lembur_staf),
    ("raw_jadwal_alat_berat",       _gen_jadwal_alat_berat),
]

# ─── Runner ───────────────────────────────────────────────────────────────────


def run_once(engine) -> None:
    now = datetime.now()
    n = random.randint(MIN_RECORDS, MAX_RECORDS)
    total = 0
    print(f"[{now.strftime('%H:%M:%S')}] Inserting {n} records/domain ...", flush=True)
    for table, generator in DOMAINS:
        try:
            df = generator(n, now)
            df.to_sql(table, engine, if_exists="append", index=False)
            total += len(df)
        except Exception as err:
            print(f"  ✗ {table}: {err}", flush=True)
    print(f"  → Total: {total} rows inserted\n", flush=True)


def wait_for_postgres(engine, retries: int = 15, delay: int = 5) -> None:
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("PostgreSQL ready.\n", flush=True)
            return
        except Exception as err:
            print(f"  Waiting for PostgreSQL ({attempt}/{retries}): {err}", flush=True)
            time.sleep(delay)
    raise RuntimeError("PostgreSQL tidak dapat dijangkau.")


def main() -> None:
    print("=" * 50, flush=True)
    print("DARSI SIMRS Simulator", flush=True)
    print(f"Interval : {INTERVAL_SECONDS}s", flush=True)
    print(f"Records  : {MIN_RECORDS}–{MAX_RECORDS} per domain per run", flush=True)
    print("=" * 50 + "\n", flush=True)

    engine = create_engine(DB_URL, pool_pre_ping=True)
    wait_for_postgres(engine)

    while True:
        try:
            run_once(engine)
        except Exception as err:
            print(f"[ERROR] {err}", flush=True)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
