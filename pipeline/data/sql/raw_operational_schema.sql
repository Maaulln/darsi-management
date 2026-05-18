-- Skema RAW PostgreSQL untuk domain operasional DARSI.
-- Tujuan: menampung data mentah SIMRS/utilitas/biaya sebelum proses refinement ke data clean.

BEGIN;

-- Domain 1: Pasien aktif (snapshot operasional harian)
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

-- Domain 2: Okupansi kamar (terisi/kosong/maintenance)
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

-- Domain 3: Meter listrik per gedung/lantai
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

-- Domain 4: Konsumsi air per unit
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

-- Domain 5: Biaya operasional per unit/departemen
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

-- Domain 6: Konsumsi obat dan alkes per periode
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

-- Domain 7: Biaya lembur staf
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

-- Domain 8: Jadwal operasional alat medis berat
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

-- Log proses ingestion RAW lintas domain
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

COMMIT;
