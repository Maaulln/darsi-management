import pandas as pd
from sqlalchemy import create_engine, text
import os

# Konfigurasi Database
DB_URL = f"postgresql://{os.getenv('POSTGRES_USER', 'darsi_user')}:{os.getenv('POSTGRES_PASSWORD', 'darsi_password')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'darsi')}"

DOMAINS = [
    "pasien_aktif", "okupansi_kamar", "meter_listrik", "konsumsi_air", 
    "biaya_operasional_unit", "konsumsi_obat_alkes", "lembur_staf", "jadwal_alat_berat"
]

def refine_internal():
    engine = create_engine(DB_URL)
    print("Memulai pembersihan data internal di PostgreSQL...")

    for domain in DOMAINS:
        raw_table = f"raw_{domain}"
        refined_table = f"refined_{domain}"
        
        try:
            # 1. Ambil data raw
            df = pd.read_sql(f"SELECT * FROM {raw_table}", con=engine)
            initial_count = len(df)
            
            # 2. Proses Pembersihan
            # a. Hapus baris yang unit_code-nya kosong (karena ini key relasi utama)
            if 'unit_code' in df.columns:
                df = df.dropna(subset=['unit_code'])
            
            # b. Trim whitespace untuk semua kolom string
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            
            # c. Deduplikasi (Drop duplicates)
            df = df.drop_duplicates()
            
            # 3. Simpan ke tabel refined
            df.to_sql(refined_table, engine, if_exists='replace', index=False)
            
            print(f" - {domain}: {initial_count} -> {len(df)} record dibersihkan.")
            
        except Exception as e:
            print(f" - {domain}: Gagal diproses. Error: {str(e)}")

if __name__ == "__main__":
    refine_internal()
