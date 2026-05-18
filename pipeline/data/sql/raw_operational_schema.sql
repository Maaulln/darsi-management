-- Skema RAW PostgreSQL untuk seluruh domain operasional DARSI (13 domain).
-- Tujuan: menampung data mentah SIMRS/utilitas/biaya/SDM sebelum proses refinement.
-- Eksekusi cukup 1x: mencakup schema semua tabel + seed data statis (tarif utilitas).
--
-- Domain 1–8  : data operasional inti (pasien, fasilitas, utilitas, biaya, farmasi, SDM, alat)
-- Domain 9–12 : data untuk resource optimization dan cost efficiency
-- Domain 13   : tarif utilitas (statis, seed langsung di akhir file)

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 1: Pasien aktif (snapshot operasional harian)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_pasien_aktif (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'SIMRS',
    source_record_id VARCHAR(100),
    snapshot_at TIMESTAMPTZ NOT NULL,
    patient_id VARCHAR(100) NOT NULL,
    admission_id VARCHAR(100),
    unit_code VARCHAR(50),
    room_code VARCHAR(50),
    class_code VARCHAR(20),
    status_aktif VARCHAR(30) NOT NULL,
    payer_type VARCHAR(30),
    diagnosis_code VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT uq_raw_pasien_aktif UNIQUE (snapshot_at, patient_id, status_aktif)
);

CREATE INDEX IF NOT EXISTS idx_raw_pasien_aktif_snapshot_at
    ON raw_pasien_aktif (snapshot_at);
CREATE INDEX IF NOT EXISTS idx_raw_pasien_aktif_unit_code
    ON raw_pasien_aktif (unit_code);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 2: Okupansi kamar (terisi / kosong / maintenance)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_okupansi_kamar (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'SIMRS',
    source_record_id VARCHAR(100),
    observed_at TIMESTAMPTZ NOT NULL,
    building_code VARCHAR(30),
    floor_code VARCHAR(30),
    unit_code VARCHAR(50),
    room_id VARCHAR(50) NOT NULL,
    room_class VARCHAR(20),
    bed_capacity INTEGER NOT NULL CHECK (bed_capacity >= 0),
    bed_occupied INTEGER NOT NULL CHECK (bed_occupied >= 0),
    room_status VARCHAR(30) NOT NULL,
    maintenance_start TIMESTAMPTZ,
    maintenance_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT chk_raw_okupansi_kamar_occupied_capacity CHECK (bed_occupied <= bed_capacity),
    CONSTRAINT uq_raw_okupansi_kamar UNIQUE (observed_at, room_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_okupansi_kamar_observed_at
    ON raw_okupansi_kamar (observed_at);
CREATE INDEX IF NOT EXISTS idx_raw_okupansi_kamar_unit_code
    ON raw_okupansi_kamar (unit_code);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 3: Meter listrik per gedung / lantai
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_meter_listrik (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'UTILITY_METER',
    meter_id VARCHAR(50) NOT NULL,
    building_code VARCHAR(30) NOT NULL,
    floor_code VARCHAR(30),
    unit_code VARCHAR(50),
    reading_at TIMESTAMPTZ NOT NULL,
    kwh_total NUMERIC(14, 3) NOT NULL CHECK (kwh_total >= 0),
    voltage_avg NUMERIC(10, 3),
    current_avg NUMERIC(10, 3),
    power_factor NUMERIC(6, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT uq_raw_meter_listrik UNIQUE (meter_id, reading_at)
);

CREATE INDEX IF NOT EXISTS idx_raw_meter_listrik_reading_at
    ON raw_meter_listrik (reading_at);
CREATE INDEX IF NOT EXISTS idx_raw_meter_listrik_building_floor
    ON raw_meter_listrik (building_code, floor_code);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 4: Konsumsi air per unit
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_konsumsi_air (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'WATER_METER',
    meter_id VARCHAR(50) NOT NULL,
    building_code VARCHAR(30),
    unit_code VARCHAR(50) NOT NULL,
    reading_at TIMESTAMPTZ NOT NULL,
    volume_m3_total NUMERIC(14, 3) NOT NULL CHECK (volume_m3_total >= 0),
    pressure_avg NUMERIC(10, 3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT uq_raw_konsumsi_air UNIQUE (meter_id, reading_at)
);

CREATE INDEX IF NOT EXISTS idx_raw_konsumsi_air_reading_at
    ON raw_konsumsi_air (reading_at);
CREATE INDEX IF NOT EXISTS idx_raw_konsumsi_air_unit_code
    ON raw_konsumsi_air (unit_code);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 5: Biaya operasional per unit / departemen
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_biaya_operasional_unit (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'FINANCE',
    source_record_id VARCHAR(100),
    period_month DATE NOT NULL,
    unit_code VARCHAR(50) NOT NULL,
    cost_category VARCHAR(50) NOT NULL,
    amount_idr NUMERIC(18, 2) NOT NULL CHECK (amount_idr >= 0),
    budget_idr NUMERIC(18, 2),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT uq_raw_biaya_operasional_unit UNIQUE (period_month, unit_code, cost_category, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_biaya_operasional_unit_period_month
    ON raw_biaya_operasional_unit (period_month);
CREATE INDEX IF NOT EXISTS idx_raw_biaya_operasional_unit_unit_code
    ON raw_biaya_operasional_unit (unit_code);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 6: Konsumsi obat dan alkes per periode
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_konsumsi_obat_alkes (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'PHARMACY',
    source_record_id VARCHAR(100),
    usage_at TIMESTAMPTZ NOT NULL,
    period_month DATE NOT NULL,
    unit_code VARCHAR(50),
    item_code VARCHAR(50) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    item_type VARCHAR(20) NOT NULL,
    quantity NUMERIC(14, 3) NOT NULL CHECK (quantity >= 0),
    uom VARCHAR(30),
    unit_cost_idr NUMERIC(18, 2) CHECK (unit_cost_idr >= 0),
    total_cost_idr NUMERIC(18, 2) CHECK (total_cost_idr >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT uq_raw_konsumsi_obat_alkes UNIQUE (usage_at, item_code, unit_code, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_konsumsi_obat_alkes_usage_at
    ON raw_konsumsi_obat_alkes (usage_at);
CREATE INDEX IF NOT EXISTS idx_raw_konsumsi_obat_alkes_period_month
    ON raw_konsumsi_obat_alkes (period_month);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 7: Biaya lembur staf
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_lembur_staf (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'HR',
    source_record_id VARCHAR(100),
    overtime_date DATE NOT NULL,
    unit_code VARCHAR(50) NOT NULL,
    staff_id VARCHAR(50) NOT NULL,
    role_name VARCHAR(100),
    overtime_hours NUMERIC(8, 2) NOT NULL CHECK (overtime_hours >= 0),
    overtime_cost_idr NUMERIC(18, 2) NOT NULL CHECK (overtime_cost_idr >= 0),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT uq_raw_lembur_staf UNIQUE (overtime_date, staff_id, unit_code, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_lembur_staf_overtime_date
    ON raw_lembur_staf (overtime_date);
CREATE INDEX IF NOT EXISTS idx_raw_lembur_staf_unit_code
    ON raw_lembur_staf (unit_code);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 8: Jadwal operasional alat medis berat
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_jadwal_alat_berat (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'BIOMED',
    source_record_id VARCHAR(100),
    device_id VARCHAR(50) NOT NULL,
    device_name VARCHAR(255) NOT NULL,
    unit_code VARCHAR(50),
    schedule_start TIMESTAMPTZ NOT NULL,
    schedule_end TIMESTAMPTZ NOT NULL,
    schedule_type VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,
    operator_id VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT chk_raw_jadwal_alat_berat_time CHECK (schedule_end > schedule_start),
    CONSTRAINT uq_raw_jadwal_alat_berat UNIQUE (device_id, schedule_start, schedule_type, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_jadwal_alat_berat_schedule_start
    ON raw_jadwal_alat_berat (schedule_start);
CREATE INDEX IF NOT EXISTS idx_raw_jadwal_alat_berat_device_id
    ON raw_jadwal_alat_berat (device_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 9: Volume kunjungan dan tindakan layanan per unit
-- Denominator utama untuk semua metrik cost efficiency (cost-per-service).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_kunjungan_layanan (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'SIMRS',
    source_record_id VARCHAR(100),
    period_date DATE NOT NULL,
    unit_code VARCHAR(50) NOT NULL,
    layanan_type VARCHAR(30) NOT NULL,
    -- rawat_inap | rawat_jalan | igd | operasi | penunjang
    payer_type VARCHAR(30),
    -- bpjs | umum | asuransi | gratis
    jumlah_kunjungan INTEGER NOT NULL DEFAULT 0 CHECK (jumlah_kunjungan >= 0),
    jumlah_tindakan INTEGER NOT NULL DEFAULT 0 CHECK (jumlah_tindakan >= 0),
    jumlah_pasien_baru INTEGER DEFAULT 0 CHECK (jumlah_pasien_baru >= 0),
    jumlah_pasien_keluar INTEGER DEFAULT 0 CHECK (jumlah_pasien_keluar >= 0),
    rata_lama_rawat_hari NUMERIC(8, 2) CHECK (rata_lama_rawat_hari >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT uq_raw_kunjungan_layanan UNIQUE (period_date, unit_code, layanan_type, payer_type)
);

CREATE INDEX IF NOT EXISTS idx_raw_kunjungan_layanan_period_date
    ON raw_kunjungan_layanan (period_date);
CREATE INDEX IF NOT EXISTS idx_raw_kunjungan_layanan_unit_code
    ON raw_kunjungan_layanan (unit_code);
CREATE INDEX IF NOT EXISTS idx_raw_kunjungan_layanan_layanan_type
    ON raw_kunjungan_layanan (layanan_type);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 10: Pendapatan (revenue) per unit dan kategori payer
-- Sisi revenue untuk menghitung cost-to-revenue ratio per unit.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_pendapatan_unit (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'FINANCE',
    source_record_id VARCHAR(100),
    period_month DATE NOT NULL,
    -- selalu hari ke-1 bulan tersebut, e.g. 2025-01-01
    unit_code VARCHAR(50) NOT NULL,
    revenue_category VARCHAR(50) NOT NULL,
    -- jasa_layanan | obat | alkes | laboratorium | radiologi | kamar | lain
    payer_type VARCHAR(30),
    -- bpjs | umum | asuransi | gratis
    amount_idr NUMERIC(18, 2) NOT NULL DEFAULT 0 CHECK (amount_idr >= 0),
    target_idr NUMERIC(18, 2) CHECK (target_idr >= 0),
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT uq_raw_pendapatan_unit UNIQUE (period_month, unit_code, revenue_category, payer_type, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_pendapatan_unit_period_month
    ON raw_pendapatan_unit (period_month);
CREATE INDEX IF NOT EXISTS idx_raw_pendapatan_unit_unit_code
    ON raw_pendapatan_unit (unit_code);
CREATE INDEX IF NOT EXISTS idx_raw_pendapatan_unit_payer_type
    ON raw_pendapatan_unit (payer_type);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 11: Jadwal dan realisasi shift staf reguler
-- Melengkapi raw_lembur_staf untuk analisis staffing optimization.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_jadwal_staf (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'HR',
    source_record_id VARCHAR(100),
    shift_date DATE NOT NULL,
    unit_code VARCHAR(50) NOT NULL,
    staff_id VARCHAR(50) NOT NULL,
    role_name VARCHAR(100),
    shift_type VARCHAR(30) NOT NULL,
    -- pagi | siang | malam | on_call | libur
    scheduled_start TIME NOT NULL,
    scheduled_end TIME NOT NULL,
    actual_start TIME,
    actual_end TIME,
    scheduled_hours NUMERIC(8, 2) NOT NULL CHECK (scheduled_hours >= 0),
    actual_hours NUMERIC(8, 2) CHECK (actual_hours >= 0),
    absent BOOLEAN NOT NULL DEFAULT FALSE,
    absent_reason VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT chk_raw_jadwal_staf_time CHECK (scheduled_end > scheduled_start),
    CONSTRAINT uq_raw_jadwal_staf UNIQUE (shift_date, staff_id, unit_code, shift_type, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_jadwal_staf_shift_date
    ON raw_jadwal_staf (shift_date);
CREATE INDEX IF NOT EXISTS idx_raw_jadwal_staf_unit_code
    ON raw_jadwal_staf (unit_code);
CREATE INDEX IF NOT EXISTS idx_raw_jadwal_staf_staff_id
    ON raw_jadwal_staf (staff_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 12: Downtime dan kerusakan alat medis
-- Melengkapi raw_jadwal_alat_berat — menangkap biaya tersembunyi dan
-- kehilangan kapasitas akibat alat tidak tersedia.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_downtime_alat (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'BIOMED',
    source_record_id VARCHAR(100),
    device_id VARCHAR(50) NOT NULL,
    device_name VARCHAR(255) NOT NULL,
    unit_code VARCHAR(50),
    downtime_start TIMESTAMPTZ NOT NULL,
    downtime_end TIMESTAMPTZ,
    -- NULL jika alat masih down saat insert
    downtime_type VARCHAR(30) NOT NULL,
    -- planned | unplanned | preventive
    downtime_cause VARCHAR(100),
    severity VARCHAR(20),
    -- low | medium | high | critical
    repair_vendor VARCHAR(100),
    repair_cost_idr NUMERIC(18, 2) CHECK (repair_cost_idr >= 0),
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload JSONB,
    CONSTRAINT chk_raw_downtime_alat_time CHECK (downtime_end IS NULL OR downtime_end > downtime_start),
    CONSTRAINT uq_raw_downtime_alat UNIQUE (device_id, downtime_start, downtime_type, source_record_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_downtime_alat_downtime_start
    ON raw_downtime_alat (downtime_start);
CREATE INDEX IF NOT EXISTS idx_raw_downtime_alat_device_id
    ON raw_downtime_alat (device_id);
CREATE INDEX IF NOT EXISTS idx_raw_downtime_alat_unit_code
    ON raw_downtime_alat (unit_code);
CREATE INDEX IF NOT EXISTS idx_raw_downtime_alat_downtime_type
    ON raw_downtime_alat (downtime_type);

-- ─────────────────────────────────────────────────────────────────────────────
-- DOMAIN 13: Tarif utilitas (listrik dan air) per periode
-- Mengonversi volume fisik (kWh, m³) ke IDR untuk kalkulasi biaya aktual.
-- Tabel ini bersifat statis — seed data diisi langsung di bawah.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_tarif_utilitas (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL DEFAULT 'FINANCE',
    utility_type VARCHAR(20) NOT NULL,
    -- listrik | air
    effective_date DATE NOT NULL,
    expired_date DATE,
    -- NULL jika masih berlaku
    tariff_per_unit NUMERIC(18, 4) NOT NULL CHECK (tariff_per_unit > 0),
    unit_uom VARCHAR(20) NOT NULL,
    -- kWh | m3
    currency VARCHAR(10) NOT NULL DEFAULT 'IDR',
    source_ref VARCHAR(100),
    -- e.g. "PLN TDK I3 2025-01", "PDAM Kota Bandung 2025"
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_raw_tarif_utilitas UNIQUE (utility_type, effective_date)
);

CREATE INDEX IF NOT EXISTS idx_raw_tarif_utilitas_utility_type
    ON raw_tarif_utilitas (utility_type);
CREATE INDEX IF NOT EXISTS idx_raw_tarif_utilitas_effective_date
    ON raw_tarif_utilitas (effective_date);

-- ─────────────────────────────────────────────────────────────────────────────
-- Log proses ingestion RAW lintas domain
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_ingestion_log (
    id BIGSERIAL PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL,
    domain_name VARCHAR(50) NOT NULL,
    run_id VARCHAR(100),
    status VARCHAR(20) NOT NULL,
    extracted_rows INTEGER,
    inserted_rows INTEGER,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_raw_ingestion_log_domain_name
    ON raw_ingestion_log (domain_name);
CREATE INDEX IF NOT EXISTS idx_raw_ingestion_log_started_at
    ON raw_ingestion_log (started_at);

-- ─────────────────────────────────────────────────────────────────────────────
-- SEED: Tarif utilitas historis (PLN + PDAM)
-- ON CONFLICT DO NOTHING — aman dijalankan ulang.
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO raw_tarif_utilitas
    (utility_type, effective_date, expired_date, tariff_per_unit, unit_uom, currency, source_ref)
VALUES
    ('listrik', '2023-01-01', '2023-12-31', 1444.70, 'kWh', 'IDR', 'PLN TDK I3 2023'),
    ('listrik', '2024-01-01', '2024-12-31', 1699.53, 'kWh', 'IDR', 'PLN TDK I3 2024'),
    ('listrik', '2025-01-01', NULL,         1814.42, 'kWh', 'IDR', 'PLN TDK I3 2025'),
    ('air',     '2023-01-01', '2023-12-31',  8500.00, 'm3',  'IDR', 'PDAM Niaga Besar 2023'),
    ('air',     '2024-01-01', '2024-12-31', 10200.00, 'm3',  'IDR', 'PDAM Niaga Besar 2024'),
    ('air',     '2025-01-01', NULL,         11500.00, 'm3',  'IDR', 'PDAM Niaga Besar 2025')
ON CONFLICT (utility_type, effective_date) DO NOTHING;

COMMIT;
