# Panduan Menjalankan DARSI Management

Dokumen ini berisi panduan langkah demi langkah untuk menjalankan proyek DARSI Management dari awal.

## 1. Prasyarat (Prerequisites)
Pastikan perangkat Anda sudah terinstall:
- **Docker Desktop**: [Download di sini](https://www.docker.com/products/docker-desktop/) (Pastikan aplikasi Docker sedang berjalan).
- **Python 3.11+**: Untuk menjalankan script ingestion data di luar container.
- **Git**: Untuk melakukan clone repository.

---

## 2. Persiapan Awal
Lakukan clone repository dan masuk ke direktori proyek:
```bash
git clone <repository-url>
cd Darsi
```

Buat file konfigurasi environment:
```bash
cp .env.example .env
```
*(Catatan: Pengaturan default di `.env` sudah dikonfigurasi untuk berjalan di lingkungan Docker local).*

---

## 3. Menjalankan Layanan (Docker)
Gunakan Docker Compose untuk membangun dan menjalankan seluruh kontainer (PostgreSQL, SurrealDB, Ollama, Backend, MCP, Nginx, Metabase):

```bash
docker compose up --build -d
```

Pastikan semua kontainer berjalan dengan status `Running`:
```bash
docker compose ps
```

---

## 4. Inisialisasi Data (WP1)
Setelah kontainer berjalan, kita perlu memuat skema database dan data operasional awal.

### A. Memuat Skema Database
```bash
docker exec -i darsi-postgres psql -U darsi_user -d darsi < data/sql/raw_operational_schema.sql
```

### C. Pembersihan Data Internal (Refinement)
Sebelum dikirim ke SurrealDB, data di PostgreSQL harus dibersihkan secara internal:
```bash
python data/ingestion/refine_postgres_internal.py
```
*Hasil: Data akan berpindah dari tabel `raw_*` ke `refined_*`.*

### D. Sinkronisasi ke Knowledge Base (SurrealDB)
Setelah data bersih di PostgreSQL, kirimkan ke SurrealDB:
```bash
export SURREALDB_URL=http://localhost:8001
python data/ingestion/refine_raw_to_surrealdb.py --apply
```
*Hasil: Data siap dikonsumsi oleh AI di SurrealDB.*

---

## 5. Menyiapkan Model AI (Ollama)
Pastikan model `qwen3.5:2b` sudah terunduh di dalam kontainer Ollama:
```bash
docker exec -it darsi-ollama ollama pull qwen3.5:2b
```

---

## 6. Mengakses Aplikasi
Sistem sekarang dapat diakses melalui Gateway Nginx:

| Layanan | Alamat (URL) | Keterangan |
| :--- | :--- | :--- |
| **Frontend UI** | [http://localhost:8080](http://localhost:8080) | Antarmuka Chat AI DARSI |
| **API Health** | [http://localhost:8080/api/health](http://localhost:8080/api/health) | Cek status backend |
| **Data List** | [http://localhost:8080/api/data/list](http://localhost:8080/api/data/list) | List data operasional |
| **Metabase** | [http://localhost:3001](http://localhost:3001) | Dashboard BI (Perlu setup awal) |

---

## 7. Troubleshooting
- **Docker Error**: Pastikan Docker Desktop sudah aktif. Jika error "port already in use", cek apakah ada layanan lain yang menggunakan port 8080, 5432, atau 8000.
- **AI Timeout**: Jika pertama kali mengirim pesan AI terasa lambat, ini karena Ollama sedang memuat model ke memori. Tunggu beberapa saat dan coba kirim kembali.
- **Database Connection**: Jika script ingestion gagal, pastikan `.env` memiliki `POSTGRES_HOST=localhost` saat dijalankan dari host machine.
