# DARSI Management — Panduan Menjalankan Program

Panduan ini menyusun langkah demi langkah untuk menjalankan keseluruhan stack DARSI Management mulai dari prasyarat, ingestion data, sampai akses dashboard.

> Target audience: siapa saja yang clone repo ini dan ingin menjalankan prototipenya dari nol.

---

## 1. Prasyarat

| Tool | Versi minimum | Keterangan |
| :--- | :--- | :--- |
| Docker Desktop | 4.x | Harus running (Linux containers) |
| Docker Compose | v2 (built-in Docker Desktop) | - |
| Python | 3.11+ | Hanya jika ingin menjalankan script ingestion dari host |
| Git | terbaru | Untuk clone repo |
| RAM | ≥ 8 GB | Ollama + Postgres + Surreal + Metabase butuh ruang |
| Disk kosong | ≥ 5 GB | Model `qwen3.5:2b` ~2 GB, Postgres data, dsb. |

> Catatan Windows: jalankan semua perintah dari PowerShell di direktori repo. Folder repo aktif di sesi ini adalah `d:\Nitip\darsi_v3`.

---

## 2. Persiapan File `.env`

```powershell
copy .env.example .env
```

Default sudah cocok dengan compose. Variabel penting:
- `POSTGRES_*` — kredensial database
- `SURREALDB_*` — koneksi knowledge base
- `CHROMA_HOST/PORT` — vector DB
- `OLLAMA_BASE_URL` & `OLLAMA_MODEL`
- `MCP_SERVER_URL` — URL MCP server untuk dipanggil backend

Edit nilai default hanya bila ada konflik port.

---

## 3. Menyalakan Stack

```powershell
docker compose up --build -d
```

Compose akan menjalankan 8 service:

| Service | Host port | Internal |
| :--- | :--- | :--- |
| `postgres` | 5432 | 5432 |
| `surrealdb` | 8001 | 8000 |
| `chromadb` | 8002 | 8000 |
| `ollama` | 11434 | 11434 |
| `backend` (FastAPI) | 8000 | 8000 |
| `mcp-server` | 8100 | 8100 |
| `metabase` | 3001 | 3000 |
| `nginx` (gateway) | 8080 | 80 |
| `airflow` | 8888 | 8080 |

Cek status:
```powershell
docker compose ps
```

Tunggu semua status `running` / `healthy`. Postgres butuh ~10 detik untuk healthy karena ada auto-init schema.

---

## 4. Verifikasi Schema Postgres

Schema [data/sql/raw_operational_schema.sql](data/sql/raw_operational_schema.sql) otomatis dieksekusi pertama kali Postgres start (via mount `/docker-entrypoint-initdb.d`).

Untuk memastikan:
```powershell
docker exec -it darsi-postgres psql -U darsi_user -d darsi -c "\dt"
```

Harus muncul tabel: `raw_pasien_aktif`, `raw_okupansi_kamar`, `raw_meter_listrik`, `raw_konsumsi_air`, `raw_biaya_operasional_unit`, `raw_konsumsi_obat_alkes`, `raw_lembur_staf`, `raw_jadwal_alat_berat`, `raw_ingestion_log`.

> Jika tabel kosong (volume sudah pernah dipakai sebelumnya), lakukan reset:
> ```powershell
> docker compose down -v
> docker compose up --build -d
> ```

---

## 5. Pull Model LLM (Ollama)

```powershell
docker exec -it darsi-ollama ollama pull qwen3.5:2b
```

Verifikasi model tersedia:
```powershell
docker exec -it darsi-ollama ollama list
```

---

## 6. Jalankan Pipeline Data (Fase 1)

Pipeline lengkap: **raw_* (Postgres) → refined_* (Postgres) → clean_* (SurrealDB) → darsi_* (ChromaDB)**.

### Opsi A — Lewat Airflow (rekomendasi)

1. Buka `http://localhost:8888`
2. Login `admin` / `admin`
3. Aktifkan DAG **`darsi_data_pipeline`** (toggle ON)
4. Klik **Trigger DAG ▶**
5. Pantau 4 task:
   - `raw_ingestion` — generate dummy ke `raw_*`
   - `internal_refinement` — bersihkan → `refined_*` (IQR cap, dedup, trim)
   - `sync_to_surrealdb` — sinkronisasi → `clean_*`
   - `embed_to_chromadb` — embedding → koleksi `darsi_*`

### Opsi B — Manual dari Host

Setup environment Python sekali saja:
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r data/requirements.txt
```

Jalankan tahap demi tahap (dari host, port di-expose ke localhost):
```powershell
$env:POSTGRES_HOST="localhost"
$env:SURREALDB_URL="http://localhost:8001"
$env:CHROMA_HOST="localhost"
$env:CHROMA_PORT="8002"

# 1. Generate dummy data (150 record/domain) ke Postgres
python data\ingestion\generate_bulk_dummy_data.py

# 2. Bersihkan internal Postgres → refined_* (IQR + dedup + trim)
python data\ingestion\refine_postgres_internal.py

# 3. Sinkronkan refined_* ke SurrealDB clean_*
python data\ingestion\refine_raw_to_surrealdb.py --apply

# 4. Embedding refined_* ke ChromaDB
python data\ingestion\embed_to_chromadb.py
```

> Mode dry-run untuk SurrealDB tersedia dengan menghilangkan flag `--apply`.

### Opsi C — Eksekusi di dalam container backend
```powershell
docker exec -it darsi-backend bash -c "cd /app && python -c 'from data.ingestion.refine_postgres_internal import refine_all; print(refine_all())'"
```

---

## 7. Smoke Test

```powershell
# Health backend
curl http://localhost:8080/api/health

# Readiness (cek Postgres + MCP + Ollama)
curl http://localhost:8080/api/readiness

# Daftar domain via MCP
curl http://localhost:8080/mcp/domains

# Konteks RAG (intent detection berdasarkan kata kunci)
curl -X POST http://localhost:8080/mcp/context -H "Content-Type: application/json" -d "{`"query`":`"okupansi ICU`"}"

# Analytics overview
curl http://localhost:8080/api/analytics/overview

# Chat RAG (akan memanggil Ollama → bisa lambat di request pertama)
curl -X POST http://localhost:8080/api/chat -H "Content-Type: application/json" -d "{`"message`":`"Ringkas biaya operasional bulan ini`",`"use_rag`":true}"
```

---

## 8. Akses Aplikasi

| Layanan | URL | Catatan |
| :--- | :--- | :--- |
| **Dashboard SPA** | http://localhost:8080 | Tabs: Dashboard, Analytics, Chat, Data Explorer, Metabase |
| **API docs (Swagger)** | http://localhost:8000/docs | OpenAPI FastAPI |
| **MCP server** | http://localhost:8100/health | `/mcp/context`, `/mcp/domains`, `/mcp/data/{domain}` |
| **Metabase BI** | http://localhost:3001 | Setup user pertama saat akses awal |
| **Airflow** | http://localhost:8888 | `admin/admin`, lihat DAG `darsi_data_pipeline` |
| **SurrealDB SQL** | http://localhost:8001/sql | Auth basic `root/root`, header `NS: darsi`, `DB: operasional` |
| **ChromaDB** | http://localhost:8002 | API endpoint untuk klien |

---

## 9. Eksplorasi Dashboard

Buka http://localhost:8080 lalu navigasi sidebar:

1. **Dashboard** — KPI utama (pasien aktif, BOR, kWh, m³, biaya, lembur) + 2 chart (okupansi per unit + doughnut biaya).
2. **Analytics** — Tren konsumsi listrik & air per unit + bar Budget vs Actual.
3. **Chat AI** — Tanya bebas, panel kanan menampilkan konteks RAG yang dipakai. Toggle "RAG aktif" untuk mode Ollama-only.
4. **Data Explorer** — Pilih domain di kiri untuk melihat sample data clean dari SurrealDB.
5. **Metabase BI** — iframe ke instance Metabase di gateway `/metabase/`.

> Indikator status di sidebar (kanan-bawah) menampilkan hasil `/api/readiness` setiap 30 detik.

---

## 10. Setup Awal Metabase (sekali saja)

1. Buka http://localhost:3001
2. Buat akun admin (email + password)
3. Hubungkan ke PostgreSQL DARSI:
   - Type: **PostgreSQL**
   - Host: `postgres` (atau `host.docker.internal` jika akses dari host)
   - Port: `5432`
   - DB name: `darsi`
   - User: `darsi_user` / `darsi_password`
4. Buat dashboard/question, lalu publish.
5. (Opsional) embed iframe ke aplikasi via Admin → Embedding → Public.

---

## 11. Menjalankan Tes

### Backend
```powershell
docker exec -it darsi-backend pytest -q
# atau dari host:
cd backend
pip install -r requirements.txt
pytest -q
```

Tes meliputi:
- [test_health.py](backend/tests/test_health.py) — `/health`, `/api/health`, `/api/readiness`
- [test_data.py](backend/tests/test_data.py) — data dummy & MCP proxy domain list
- [test_chat_rag.py](backend/tests/test_chat_rag.py) — chat & rag (mocked, offline-friendly)
- [test_analytics.py](backend/tests/test_analytics.py) — struktur respons analytics

### MCP server
```powershell
cd mcp-server
pip install -r requirements.txt
pytest -q
```

---

## 12. Operasional Harian

| Perintah | Fungsi |
| :--- | :--- |
| `docker compose ps` | Status semua service |
| `docker compose logs -f backend` | Tail log backend |
| `docker compose restart backend` | Restart backend setelah edit |
| `docker compose down` | Stop semua service (data persisten) |
| `docker compose down -v` | Stop + hapus volume (reset data) |
| `docker exec -it darsi-postgres psql -U darsi_user -d darsi` | Shell SQL |
| `docker exec -it darsi-surrealdb /surreal sql --user root --pass root --ns darsi --db operasional` | Shell SurrealQL |

---

## 13. Troubleshooting

### Port sudah dipakai
Cek aplikasi lain yang pakai 8080/8000/5432:
```powershell
netstat -ano | findstr :8080
```
Ganti mapping port di `docker-compose.yml` (kiri = host, kanan = container).

### Ollama timeout pertama kali
Request pertama akan lambat (10–30 detik) karena model di-load ke memori. Tunggu sesaat lalu coba lagi.

### Schema Postgres tidak ter-load
Init-script hanya jalan di volume kosong. Reset:
```powershell
docker compose down -v
docker compose up --build -d
```

### MCP context selalu kosong
Pipeline ingestion belum dijalankan. Trigger DAG Airflow atau jalankan langkah 6 Opsi B.

### ChromaDB error saat embedding
Pastikan tabel `refined_*` ada isinya:
```powershell
docker exec -it darsi-postgres psql -U darsi_user -d darsi -c "SELECT COUNT(*) FROM refined_pasien_aktif;"
```

### Frontend menampilkan `–`
Berarti analytics endpoint mengembalikan empty (SurrealDB belum diisi). Jalankan `sync_to_surrealdb`.

### Airflow DAG tidak muncul
Tunggu ~30 detik setelah container start. Refresh browser. Cek log:
```powershell
docker compose logs -f airflow
```

---

## 14. Reset Penuh

```powershell
docker compose down -v
docker volume prune -f
docker compose up --build -d
docker exec -it darsi-ollama ollama pull qwen3.5:2b
# Trigger DAG di Airflow atau jalankan langkah 6 Opsi B
```

---

## 15. Tabel Endpoint Singkat

### Backend FastAPI (gateway `/api/*`)

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/api/health` | Health check (alias `/health`) |
| GET | `/api/readiness` | Cek Postgres + MCP + Ollama |
| GET | `/api/data/list` | Sample data dummy |
| GET | `/api/data/domains` | Daftar domain via MCP |
| GET | `/api/data/domain/{name}` | Record clean per domain |
| GET | `/api/summary/resource` | Ringkasan resource per unit |
| GET | `/api/summary/cost` | Ringkasan biaya per unit/kategori |
| GET | `/api/analytics/overview` | KPI utama dashboard |
| GET | `/api/analytics/cost-by-category` | Biaya per kategori |
| GET | `/api/analytics/occupancy-by-unit` | Okupansi per unit |
| GET | `/api/analytics/utility-trend` | Tren listrik/air |
| GET | `/api/analytics/mcp-status` | Status & domain MCP |
| POST | `/api/chat` | Chat RAG (default) atau Ollama-only |
| POST | `/api/rag/query` | RAG eksplisit |

### MCP server (gateway `/mcp/*`)

| Method | Path | Fungsi |
| :--- | :--- | :--- |
| GET | `/mcp/domains` | List domain operasional |
| POST | `/mcp/context` | Konteks gabungan Chroma + Surreal |
| GET | `/mcp/data/{domain}` | Data clean per domain |

---

## 16. Referensi Cepat

- Arsitektur tinggi-level: [plan.md](plan.md)
- Alur data: [guide.md](guide.md) (file ini) & [README.md](README.md)
- Fase development: [flow.md](flow.md)
- Build per WP: [build_guide.md](build_guide.md)
- Discovery awal: [darsi_discovery_analisis.md](darsi_discovery_analisis.md)
