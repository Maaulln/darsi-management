# DARSI Management — Getting Started Guide

Panduan lengkap untuk menjalankan sistem DARSI dari nol, baik untuk developer maupun pengguna akhir (manajemen RS).

---

## Daftar Isi

1. [Prasyarat](#1-prasyarat)
2. [Instalasi & Menjalankan Sistem](#2-instalasi--menjalankan-sistem)
3. [Setup Awal (Satu Kali)](#3-setup-awal-satu-kali)
4. [Verifikasi Semua Service Berjalan](#4-verifikasi-semua-service-berjalan)
5. [Akses Layanan](#5-akses-layanan)
6. [Memahami Alur Data](#6-memahami-alur-data)
7. [Menggunakan API](#7-menggunakan-api)
8. [Troubleshooting](#8-troubleshooting)
9. [Catatan Developer](#9-catatan-developer)

---

## 1. Prasyarat

Pastikan software berikut sudah terinstal di mesin kamu:

| Software | Versi Minimum | Cek Instalasi |
|---|---|---|
| Docker Desktop | 24.x | `docker --version` |
| Docker Compose | 2.x | `docker compose version` |

**Spesifikasi minimum yang disarankan:**
- RAM: 8 GB minimum, 16 GB disarankan
- Disk: 15 GB free (images + model qwen3.5:2b ~4GB + data volumes)
- OS: Windows 10/11, macOS, atau Linux
- GPU: Disarankan (VRAM 4GB+) untuk performa inferensi qwen3.5:2b yang optimal

---

## 2. Instalasi & Menjalankan Sistem

### Langkah 1 — Clone repository

```bash
git clone https://github.com/your-org/darsi-management.git
cd darsi-management
```

### Langkah 2 — Setup environment variables

```bash
cp .env.example .env
```

File `.env` default sudah siap digunakan untuk development lokal. Tidak perlu diubah kecuali kamu ingin mengganti password atau port.

**Isi default `.env`:**
```env
POSTGRES_DB=darsi
POSTGRES_USER=darsi_user
POSTGRES_PASSWORD=darsi_password

SURREALDB_USER=root
SURREALDB_PASSWORD=root
SURREALDB_NS=darsi
SURREALDB_DB=operasional

OLLAMA_MODEL=qwen3.5:2b
MCP_SERVER_URL=http://mcp-server:8100
```

### Langkah 3 — Jalankan semua service

```bash
docker compose up -d
```

Proses ini akan:
- Build image untuk `backend`, `mcp-server`, `pipeline-service`, dan **`frontend`** (Vite build → nginx)
- Pull image untuk PostgreSQL, SurrealDB, Ollama, n8n, Metabase, Nginx
- Membuat schema PostgreSQL otomatis dari `pipeline/data/sql/raw_operational_schema.sql`
- Menjalankan SIMRS Simulator (data mulai masuk ke PostgreSQL setiap 10 detik)

> Build pertama membutuhkan waktu **5–15 menit** tergantung kecepatan internet (termasuk `npm ci` dan `npm run build` untuk frontend).

---

## 3. Setup Awal (Satu Kali)

Beberapa langkah ini hanya perlu dilakukan sekali setelah pertama kali menjalankan sistem.

### 3a — Pull model Ollama

DARSI menggunakan dua model Ollama dengan peran berbeda:

```bash
# Model chat/generasi — untuk menjawab pertanyaan
docker exec -it darsi-ollama ollama pull qwen3.5:2b

# Model embedding — untuk RAG vector search (wajib untuk fitur chat dengan konteks data)
docker exec -it darsi-ollama ollama pull nomic-embed-text
```

| Model | Ukuran | Fungsi |
|---|---|---|
| `qwen3.5:2b` | ~1.5 GB | Generasi teks (chat, ringkasan, rekomendasi) |
| `nomic-embed-text` | ~274 MB | Embedding teks untuk vector search RAG |

Verifikasi kedua model tersedia:
```bash
docker exec -it darsi-ollama ollama list
```

### 3b — Import workflow n8n

n8n bertugas menjalankan pipeline data (refinement → SurrealDB → embedding) setiap 1 menit.

1. Buka **http://localhost:5678**
2. Daftar akun (pertama kali) atau login
3. Klik menu **Workflows** di sidebar kiri
4. Klik tombol **⋮** → **Import from File**
5. Pilih file: `n8n/darsi_pipeline_workflow.json`
6. Setelah workflow terbuka, klik toggle **Inactive → Active** di kanan atas

Pipeline akan otomatis berjalan setiap 1 menit sejak diaktifkan.

> Kamu bisa test pipeline secara manual dengan klik node **Start** → **Execute Workflow** tanpa menunggu cron.

### 3c — Setup Metabase (opsional)

Metabase digunakan untuk dashboard analitik berbasis chart.

1. Buka **http://localhost:3001**
2. Ikuti wizard setup awal (buat akun admin)
3. Tambah database connection:
   - Type: **PostgreSQL**
   - Host: `postgres`
   - Port: `5432`
   - Database: `darsi`
   - Username: `darsi_user`
   - Password: `darsi_password`

---

## 4. Verifikasi Semua Service Berjalan

Cek status semua container:

```bash
docker compose ps
```

Output yang diharapkan (semua `running`):

```
NAME                    STATUS
darsi-postgres          running (healthy)
darsi-surrealdb         running
darsi-ollama            running
darsi-backend           running
darsi-mcp-server        running
darsi-pipeline-service  running
darsi-simrs-simulator   running
darsi-frontend          running
darsi-n8n               running
darsi-metabase          running
darsi-nginx             running
```

### Cek health endpoint backend

```bash
curl http://localhost:8000/api/readiness
```

Response yang diharapkan:

```json
{
  "mcp_server": "ok",
  "surrealdb": "ok",
  "ollama": "ok",
  "overall": "ok"
}
```

Jika ada service yang `down`, lihat bagian [Troubleshooting](#8-troubleshooting).

---

## 5. Akses Layanan

| Layanan | URL | Keterangan |
|---|---|---|
| **Dashboard** | http://localhost:8080 | UI utama (Frontend) |
| **Metabase** | http://localhost:3001 | Dashboard analitik BI |
| **n8n** | http://localhost:5678 | Pipeline orchestration |
| **API Docs** | http://localhost:8000/docs | FastAPI Swagger UI |
| **Pipeline Service** | http://localhost:8200/docs | Endpoint pipeline manual |
| **MCP Server** | http://localhost:8100/docs | AI layer endpoints |
| **SurrealDB** | http://localhost:8001 | Database UI (opsional) |

---

## 6. Memahami Alur Data

```
[SIMRS Simulator]
  Setiap 10 detik → insert 1–100 record ke 8 tabel raw_* di PostgreSQL
        │
        ▼
[PostgreSQL] — Menyimpan data mentah SIMRS
        │
        ▼ (setiap 1 menit, dipicu n8n)
[Pipeline Service]
  /pipeline/refine → Pandas cleaning: raw_* → refined_* (PostgreSQL)
  /pipeline/sync   → Sync: refined_* → clean_* (SurrealDB)
  /pipeline/embed  → Embedding: clean_* → SurrealDB vector index
        │
        ▼
[SurrealDB] — Data bersih + vector index siap untuk RAG
        │
        ▼
[MCP Server] — Ambil konteks (structured + semantic) + generate via LangChain
        │
        ▼
[Ollama qwen3.5:2b] — Menghasilkan ringkasan & rekomendasi
        │
        ▼
[FastAPI Backend] → [Frontend / Metabase]
```

**8 Domain Data SIMRS yang disimulasikan:**

| Domain | Tabel Raw | Informasi |
|---|---|---|
| Pasien aktif | `raw_pasien_aktif` | Kunjungan, unit, payer, diagnosis |
| Okupansi kamar | `raw_okupansi_kamar` | Bed capacity vs occupied per unit |
| Meter listrik | `raw_meter_listrik` | Konsumsi kWh per gedung/unit |
| Konsumsi air | `raw_konsumsi_air` | Volume m³ per unit |
| Biaya operasional | `raw_biaya_operasional_unit` | Realisasi vs budget per kategori |
| Konsumsi obat/alkes | `raw_konsumsi_obat_alkes` | Penggunaan farmasi & alat kesehatan |
| Lembur staf | `raw_lembur_staf` | Jam & biaya lembur per unit |
| Jadwal alat berat | `raw_jadwal_alat_berat` | Jadwal MRI, CT Scan, X-Ray, dll. |

---

## 7. Menggunakan API

### Chat dengan AI (RAG)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Bagaimana kondisi okupansi kamar saat ini?", "use_rag": true}'
```

### Dashboard KPI

```bash
curl http://localhost:8000/api/analytics/overview
```

### Trigger pipeline manual (tanpa n8n)

```bash
curl -X POST http://localhost:8200/pipeline/run-all
```

### Lihat data domain tertentu

```bash
curl http://localhost:8000/api/data/domain/pasien_aktif?limit=10
```

### Cek domain yang tersedia di MCP Server

```bash
curl http://localhost:8100/mcp/domains
```

---

## 8. Troubleshooting

### Service tidak mau start

```bash
# Lihat log service tertentu
docker logs darsi-backend --tail 50
docker logs darsi-mcp-server --tail 50
docker logs darsi-pipeline-service --tail 50
```

### Ollama belum punya model

```
Error: model 'qwen3.5:2b' not found
```
**Solusi:**
```bash
docker exec -it darsi-ollama ollama pull qwen3.5:2b
```

### PostgreSQL belum ready saat container lain start

Tunggu 30 detik lalu restart container yang gagal:
```bash
docker compose restart backend mcp-server pipeline-service
```

### Pipeline n8n gagal jalan

1. Buka http://localhost:5678
2. Klik workflow → tab **Executions**
3. Lihat execution yang failed → klik untuk melihat error detail
4. Pastikan `pipeline-service` running: `docker compose ps pipeline-service`

### Reset semua data (mulai dari awal)

```bash
docker compose down -v   # hapus semua container + volumes
docker compose up -d     # mulai ulang dari nol
```

> **Peringatan:** Perintah di atas menghapus seluruh data PostgreSQL, SurrealDB, dan n8n.

---

## 9. Catatan Developer

### Struktur service dan tanggung jawab

| Service | Port | Tanggung Jawab |
|---|---|---|
| `backend` | 8000 | REST API — thin layer, semua logic ke MCP |
| `mcp-server` | 8100 | Data connector + SurrealDB vector RAG + LLM generation |
| `pipeline-service` | 8200 | Pandas refinement + SurrealDB sync + vector embedding |
| `simrs-simulator` | — | Insert data dummy ke PostgreSQL tiap 10 detik |
| `n8n` | 5678 | Trigger pipeline-service setiap 1 menit via HTTP |
| `frontend` | — | React SPA (Vite build, served by inner nginx) |

### Environment variables penting

| Variable | Default | Keterangan |
|---|---|---|
| `SIMULATOR_INTERVAL` | `10` | Interval simulator dalam detik |
| `SIMULATOR_MIN_RECORDS` | `1` | Minimum record per domain per run |
| `SIMULATOR_MAX_RECORDS` | `100` | Maksimum record per domain per run |
| `OLLAMA_MODEL` | `qwen3.5:2b` | Model LLM yang digunakan |
| `PROCESSORS_DIR` | `/app/processors` | Path ke script pipeline di container |

### Menjalankan pipeline sekali tanpa n8n

```bash
# Refine saja
curl -X POST http://localhost:8200/pipeline/refine

# Semua step sekaligus
curl -X POST http://localhost:8200/pipeline/run-all
```

### Rebuild image setelah mengubah kode

```bash
# Rebuild satu service
docker compose build backend
docker compose up -d backend

# Rebuild frontend setelah mengubah kode React
docker compose build frontend
docker compose up -d frontend

# Rebuild semua
docker compose build
docker compose up -d
```

### Melihat log real-time simulator

```bash
docker logs -f darsi-simrs-simulator
```

Contoh output normal:
```
[10:15:30] Inserting 47 records/domain ...
  ✓ raw_pasien_aktif: 47 rows
  ✓ raw_okupansi_kamar: 47 rows
  ...
  → Total: 376 rows inserted
```

---

### Pengembangan Frontend (dev mode)

Untuk iterasi cepat tanpa perlu rebuild Docker, jalankan frontend langsung dengan Vite dev server:

**Prasyarat:** Node.js 20+ dan npm terinstal di host.

```bash
cd frontend
npm install
npm run dev
# Server berjalan di http://localhost:3000
```

Vite sudah dikonfigurasi proxy ke backend lokal:
- `/api/*` → `http://localhost:8000` (FastAPI backend)
- `/metabase/*` → `http://localhost:3001` (Metabase)

Pastikan backend sudah running (via Docker) sebelum menjalankan dev server.

**Halaman yang tersedia:**

| Route | Halaman | Deskripsi |
|---|---|---|
| `/` | Dashboard | KPI cards + 3 chart operasional |
| `/analytics` | Analitik | Charts detail + tabel breakdown biaya & okupansi |
| `/chat` | Chat AI | Chat dengan qwen3.5:2b via RAG pipeline |
| `/summary` | Ringkasan | Tabel utilitas & biaya per unit dengan progress bar |
| `/metabase` | Metabase | Metabase embedded via iframe |
| `/status` | Status Sistem | Health semua service + domain data aktif |
