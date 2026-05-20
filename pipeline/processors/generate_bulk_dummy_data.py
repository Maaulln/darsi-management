import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

UNITS = ['UGD', 'RI-A', 'RI-B', 'OK', 'LAB', 'RAD', 'FAR', 'ICU']
BUILDINGS = ['GD-A', 'GD-B']
CLASSES = ['VIP', 'Kls1', 'Kls2', 'Kls3']

def generate_bulk_data(num_records=150):
    now = datetime.now()

    print(f"Generating {num_records} records per domain (DB insert disabled)...")

    # 1. Pasien Aktif
    data_pasien = []
    for i in range(num_records):
        snapshot = now - timedelta(hours=random.randint(0, 72))
        data_pasien.append({
            'source_record_id': f'PX-{1000+i}',
            'snapshot_at': snapshot,
            'patient_id': f'P-{2000+i}',
            'admission_id': f'A-{3000+i}',
            'unit_code': random.choice(UNITS),
            'room_code': f'R-{random.randint(101, 505)}',
            'class_code': random.choice(CLASSES),
            'status_aktif': 'Rawat Inap',
            'payer_type': random.choice(['BPJS', 'Asuransi', 'Mandiri']),
            'diagnosis_code': f'ICD10-{random.randint(100, 999)}',
            'created_at': now
        })
    df_pasien = pd.DataFrame(data_pasien)
    # df_pasien.to_sql('raw_pasien_aktif', engine, if_exists='append', index=False)
    print(f" - raw_pasien_aktif: {len(df_pasien)} rows generated (not inserted)")

    # 2. Okupansi Kamar
    data_okupansi = []
    for i in range(num_records):
        observed = now - timedelta(hours=random.randint(0, 24))
        capacity = random.choice([1, 2, 4, 6])
        data_okupansi.append({
            'source_record_id': f'OCC-{4000+i}',
            'observed_at': observed,
            'building_code': random.choice(BUILDINGS),
            'floor_code': f'LT-{random.randint(1, 5)}',
            'unit_code': random.choice(['RI-A', 'RI-B', 'ICU']),
            'room_id': f'ROOM-{5000+i}',
            'room_class': random.choice(CLASSES),
            'bed_capacity': capacity,
            'bed_occupied': random.randint(0, capacity),
            'room_status': 'Aktif',
            'created_at': now
        })
    df_okupansi = pd.DataFrame(data_okupansi)
    # df_okupansi.to_sql('raw_okupansi_kamar', engine, if_exists='append', index=False)
    print(f" - raw_okupansi_kamar: {len(df_okupansi)} rows generated (not inserted)")

    # 3. Meter Listrik
    data_listrik = []
    for i in range(num_records):
        reading = now - timedelta(hours=i)
        data_listrik.append({
            'meter_id': f'MTR-E-{random.randint(1, 5)}',
            'building_code': random.choice(BUILDINGS),
            'floor_code': f'LT-{random.randint(1, 5)}',
            'unit_code': random.choice(UNITS),
            'reading_at': reading,
            'kwh_total': random.uniform(1000, 5000),
            'voltage_avg': random.uniform(210, 230),
            'current_avg': random.uniform(10, 50),
            'power_factor': random.uniform(0.8, 0.95),
            'created_at': now
        })
    df_listrik = pd.DataFrame(data_listrik)
    # df_listrik.to_sql('raw_meter_listrik', engine, if_exists='append', index=False)
    print(f" - raw_meter_listrik: {len(df_listrik)} rows generated (not inserted)")

    # 4. Konsumsi Air
    data_air = []
    for i in range(num_records):
        reading = now - timedelta(hours=i)
        data_air.append({
            'meter_id': f'MTR-W-{random.randint(1, 5)}',
            'building_code': random.choice(BUILDINGS),
            'unit_code': random.choice(UNITS),
            'reading_at': reading,
            'volume_m3_total': random.uniform(500, 2000),
            'pressure_avg': random.uniform(2.0, 4.5),
            'created_at': now
        })
    df_air = pd.DataFrame(data_air)
    # df_air.to_sql('raw_konsumsi_air', engine, if_exists='append', index=False)
    print(f" - raw_konsumsi_air: {len(df_air)} rows generated (not inserted)")

    # 5. Biaya Operasional
    data_biaya = []
    for i in range(num_records):
        month = datetime(2024, random.randint(1, 12), 1)
        data_biaya.append({
            'source_record_id': f'COST-{6000+i}',
            'period_month': month,
            'unit_code': random.choice(UNITS),
            'cost_category': random.choice(['Gaji', 'Listrik', 'Air', 'Alat Kesehatan', 'Lainnya']),
            'amount_idr': random.uniform(10_000_000, 500_000_000),
            'budget_idr': random.uniform(50_000_000, 600_000_000),
            'created_at': now
        })
    df_biaya = pd.DataFrame(data_biaya)
    # df_biaya.to_sql('raw_biaya_operasional_unit', engine, if_exists='append', index=False)
    print(f" - raw_biaya_operasional_unit: {len(df_biaya)} rows generated (not inserted)")

    # 6. Konsumsi Obat/Alkes
    data_obat = []
    for i in range(num_records):
        usage = now - timedelta(days=random.randint(0, 30))
        data_obat.append({
            'source_record_id': f'PH-{7000+i}',
            'usage_at': usage,
            'period_month': usage.replace(day=1),
            'unit_code': random.choice(UNITS),
            'item_code': f'ITEM-{random.randint(100, 999)}',
            'item_name': random.choice(['Paracetamol', 'Infus RL', 'Masker Bedah', 'Sarung Tangan']),
            'item_type': random.choice(['Obat', 'Alkes']),
            'quantity': random.uniform(1, 100),
            'uom': random.choice(['Botol', 'Pcs', 'Box']),
            'unit_cost_idr': random.uniform(5000, 100000),
            'total_cost_idr': 0,
            'created_at': now
        })
    df_obat = pd.DataFrame(data_obat)
    df_obat['total_cost_idr'] = df_obat['quantity'] * df_obat['unit_cost_idr']
    # df_obat.to_sql('raw_konsumsi_obat_alkes', engine, if_exists='append', index=False)
    print(f" - raw_konsumsi_obat_alkes: {len(df_obat)} rows generated (not inserted)")

    # 7. Lembur Staf
    data_lembur = []
    for i in range(num_records):
        date = (now - timedelta(days=random.randint(0, 30))).date()
        data_lembur.append({
            'source_record_id': f'HR-{8000+i}',
            'overtime_date': date,
            'unit_code': random.choice(UNITS),
            'staff_id': f'ST-{random.randint(100, 999)}',
            'role_name': random.choice(['Perawat', 'Dokter', 'Admin', 'Security']),
            'overtime_hours': random.uniform(1, 5),
            'overtime_cost_idr': random.uniform(50000, 500000),
            'reason': 'Overload pasien',
            'created_at': now
        })
    df_lembur = pd.DataFrame(data_lembur)
    # df_lembur.to_sql('raw_lembur_staf', engine, if_exists='append', index=False)
    print(f" - raw_lembur_staf: {len(df_lembur)} rows generated (not inserted)")

    # 8. Jadwal Alat Berat
    data_alat = []
    for i in range(num_records):
        start = now + timedelta(hours=random.randint(-24, 72))
        data_alat.append({
            'source_record_id': f'DEV-{9000+i}',
            'device_id': f'DIAG-{random.randint(10, 50)}',
            'device_name': random.choice(['MRI', 'CT Scan', 'X-Ray', 'Ventilator']),
            'unit_code': random.choice(['RAD', 'RI-A', 'ICU']),
            'schedule_start': start,
            'schedule_end': start + timedelta(hours=random.randint(1, 4)),
            'schedule_type': 'Pemeriksaan',
            'status': random.choice(['Scheduled', 'Completed', 'Ongoing']),
            'created_at': now
        })
    df_alat = pd.DataFrame(data_alat)
    # df_alat.to_sql('raw_jadwal_alat_berat', engine, if_exists='append', index=False)
    print(f" - raw_jadwal_alat_berat: {len(df_alat)} rows generated (not inserted)")

# if __name__ == "__main__":
#     generate_bulk_data(150)
