# Panduan Alur Data (PostgreSQL ➔ SurrealDB)

Sistem DARSI Management menggunakan arsitektur dua lapis untuk penyimpanan data:
1.  **PostgreSQL (RAW Layer)**: Menampung data mentah ("kotor") langsung dari sumber SIMRS/CSV.
2.  **SurrealDB (CLEAN Layer)**: Menampung data yang sudah dibersihkan dan siap dikonsumsi oleh AI (Knowledge Base).

---

## 🛠️ Langkah 1: Ingestion Data Mentah (PostgreSQL)
Sebelum melakukan pembersihan, pastikan data mentah sudah masuk ke PostgreSQL.

```bash
# Menjalankan ingestion bulk (1200+ record)
export POSTGRES_HOST=localhost
python data/ingestion/generate_bulk_dummy_data.py
```
*Hasil: Data tersedia di tabel dengan prefix `raw_*`.*

---

## 🧹 Langkah 2: Pembersihan Internal (PostgreSQL)
**PENTING**: Sebelum dikirim ke SurrealDB, data harus dibersihkan terlebih dahulu di dalam PostgreSQL untuk memastikan kualitas basis pengetahuan AI.

Gunakan script `refine_postgres_internal.py` untuk melakukan:
- **Filtering**: Menghapus data yang tidak memiliki kode unit (`unit_code`).
- **Data Scrubbing**: Menghapus spasi berlebih (*trimming*) pada teks.
- **Deduplikasi**: Menghapus record yang duplikat.

### Jalankan Pembersihan Internal:
```bash
export POSTGRES_HOST=localhost
python data/ingestion/refine_postgres_internal.py
```
*Hasil: Data bersih akan disimpan di tabel dengan prefix `refined_*` di PostgreSQL.*

---

## 🚀 Langkah 3: Transfer ke Knowledge Base (SurrealDB)
Setelah data di PostgreSQL bersih, pindahkan data tersebut ke SurrealDB menggunakan script `refine_raw_to_surrealdb.py`.
```bash
# Jalankan di dalam container atau host dengan akses ke kedua database
export POSTGRES_HOST=localhost
export SURREALDB_URL=http://localhost:8001

# Jalankan mode DRY-RUN (Hanya simulasi)
python data/ingestion/refine_raw_to_surrealdb.py

# Jalankan mode APPLY (Kirim ke SurrealDB)
python data/ingestion/refine_raw_to_surrealdb.py --apply
```

---

## ✅ Langkah 3: Verifikasi Data Clean
Setelah proses refinement selesai, data akan tersedia di SurrealDB dalam tabel dengan prefix `clean_*`.

### Cek via Curl:
```bash
curl -X POST http://localhost:8001/sql \
  -u "root:root" \
  -H "NS: darsi" -H "DB: operasional" \
  -H "Accept: application/json" \
  -d "SELECT count() FROM clean_pasien_aktif GROUP ALL"
```

### Mengapa SurrealDB?
Kami menggunakan SurrealDB sebagai Knowledge Base karena:
- **Skema Fleksibel**: Memudahkan AI dalam membaca konteks data yang kompleks.
- **Relasi Graph**: Memungkinkan pencarian hubungan antar unit/biaya yang lebih cepat.
- **Ready for AI**: Data di SurrealDB dioptimalkan untuk ditarik sebagai konteks oleh MCP Server.

---

## 💡 Tips
Jika Anda menambah data baru di PostgreSQL, cukup jalankan kembali script refinement dengan flag `--apply` untuk memperbarui Knowledge Base Anda.
