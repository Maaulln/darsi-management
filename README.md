# DARSI Management
> Digital Assistant Rumah Sakit Islam (DARSI) Management — AI-Powered Hospital Operational Analytics System

Prototipe sistem analitik operasional rumah sakit berbasis Generative AI untuk RSI Surabaya. Sistem ini membantu manajemen rumah sakit menyajikan informasi operasional secara terstruktur melalui dashboard interaktif dan ringkasan berbasis data.

---

## Architecture Overview

```
SIMRS Simulator (setiap 10 detik)
      ↓
PostgreSQL (raw_* tables)
      ↓
n8n (Cron trigger, setiap 1 menit)
      ↓
Pipeline Service (FastAPI) → Pandas Refinement → SurrealDB (clean_* + vector index)
      ↓
MCP Server (Connector + Context Manager + LLM Generation)
      ↓
LangChain → SurrealDB Vector Search → RAG Pipeline
      ↓
Ollama + qwen3.5:2b (Local LLM)
      ↓
FastAPI Backend → React + Metabase (Frontend Dashboard)
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data Simulator | Python + Faker | Generate data SIMRS dummy setiap 10 detik ke PostgreSQL |
| Data Ingestion | PostgreSQL 16 | Raw SIMRS data storage |
| Orchestration | n8n | Cron trigger + HTTP orchestration + notifikasi pipeline |
| Data Processing | Pipeline Service (FastAPI + Pandas) | Refinement, sync SurrealDB, embed vector — dipanggil n8n via HTTP |
| Clean Data + Vector Store | SurrealDB | Structured clean data + native vector search (HNSW) |
| Connector | Custom MCP Server | Data connector + Context manager + LLM generation |
| RAG Framework | LangChain | RAG pipeline via SurrealDB vector search |
| LLM (chat) | Ollama + qwen3.5:2b | Local private cloud LLM inference (generasi teks) |
| LLM (embed) | Ollama + nomic-embed-text | Vector embedding untuk RAG (768 dimensi) |
| Backend | FastAPI | REST API layer |
| Frontend | React + Metabase | Dashboard UI + embedded analytics |
| Reverse Proxy | Nginx 1.27 Alpine | Service routing |
| Containerization | Docker + Docker Compose | Service orchestration |

---

## Services & Ports

| Service | Port | Description |
|---|---|---|
| nginx | 8080:80 | Reverse proxy — main entry point |
| frontend | — | React SPA (Vite build, served by inner nginx) |
| backend | 8000:8000 | FastAPI backend |
| mcp-server | 8100:8100 | Custom MCP server |
| pipeline-service | 8200:8200 | Refinement + sync + embed (dipanggil n8n) |
| ollama | 11434:11434 | LLM inference server |
| surrealdb | 8001:8000 | Clean data store + vector search |
| postgres | 5432:5432 | Raw data store |
| simrs-simulator | — | SIMRS data simulator (no exposed port) |
| n8n | 5678:5678 | Pipeline orchestration + notifikasi |
| metabase | 3001:3000 | Analytics dashboard |

---

## Project Structure

```
darsi/
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE.md
├── backend/                         # FastAPI backend (Clean Architecture)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── api/                     # Route handlers
│       │   ├── analytics.py         # GET /api/analytics/*
│       │   ├── chat.py              # POST /api/chat
│       │   ├── data.py              # GET /api/data/*
│       │   ├── health.py            # GET /health, /api/readiness
│       │   ├── rag.py               # POST /api/rag/query
│       │   └── summary.py           # GET /api/summary/*
│       ├── services/
│       │   ├── mcp_client.py        # HTTP client ke MCP Server
│       │   └── rag_service.py       # Thin wrapper RAG via MCP
│       └── core/
│           └── config.py            # Settings (hanya mcp_server_url)
├── mcp-server/                      # Custom MCP Server (AI Layer)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py                  # Data connector + Context manager + LLM generation
├── pipeline-service/                # Pipeline Service — dipanggil n8n via HTTP
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py                  # POST /pipeline/refine, /sync, /embed, /run-all
├── pipeline/                        # Script data processing
│   ├── requirements.txt
│   ├── processors/                  # Script refinement (dipanggil pipeline-service)
│   │   ├── simrs_simulator.py           # Simulator SIMRS real-time (setiap 10 detik, 13 domain)
│   │   ├── generate_bulk_dummy_data.py
│   │   ├── refine_postgres_internal.py
│   │   ├── refine_raw_to_surrealdb.py
│   │   ├── embed_to_surrealdb_vector.py # Embedding ke SurrealDB vector store
│   │   └── ...
│   └── data/
│       ├── sample_simrs/            # CSV dummy SIMRS (13 domain)
│       └── sql/
│           └── raw_operational_schema.sql  # Schema 13 tabel raw_* + seed tarif (1 file, 1x eksekusi)
├── n8n/
│   └── darsi_pipeline_workflow.json # Workflow n8n siap import
├── frontend/                        # React Frontend (Vite + React 18)
│   ├── Dockerfile                   # Multi-stage: node build → nginx serve
│   ├── nginx.conf                   # Inner nginx (SPA routing)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx                 # Entry point + Chart.js registration
│       ├── App.jsx                  # Shell: sidebar, topbar, routing
│       ├── index.css
│       ├── api.js                   # apiFetch, apiPost, useApi hook
│       ├── utils.js                 # fmtRp, fmtNum, fmtPct, PALETTE
│       └── pages/
│           ├── Dashboard.jsx        # 8 KPI cards + 5 charts (incl. cost-to-revenue & staffing)
│           ├── Analytics.jsx        # Charts detail + tabel breakdown
│           ├── Chat.jsx             # Chat AI dengan RAG toggle
│           ├── Summary.jsx          # Ringkasan utilitas & biaya per unit
│           ├── MetabasePage.jsx     # Metabase embedded (iframe)
│           └── StatusPage.jsx       # Health semua service
└── nginx/
    └── default.conf
```

---

## Getting Started

### Prerequisites
- Docker & Docker Compose installed
- RAM minimal 8GB, 16GB disarankan (qwen3.5:2b ~1.5GB + nomic-embed-text ~274MB)
- GPU: disarankan (VRAM 4GB+) untuk performa inferensi optimal

### 1. Clone repository
```bash
git clone https://github.com/your-org/darsi-management.git
cd darsi-management
```

### 2. Setup environment variables
```bash
cp .env.example .env
# Edit .env sesuai konfigurasi lokal
```

### 3. Run all services
```bash
docker compose up -d
```

### 4. Pull model Ollama
```bash
docker exec -it darsi-ollama ollama pull qwen3.5:2b       # model chat/generasi
docker exec -it darsi-ollama ollama pull nomic-embed-text  # model embedding RAG
```

### 5. Import n8n workflow
```
1. Buka http://localhost:5678
2. Workflows → Import from File
3. Pilih: n8n/darsi_pipeline_workflow.json
4. Klik Activate untuk mengaktifkan cron pipeline
```

### 6. Access services
| Service | URL |
|---|---|
| Dashboard | http://localhost:8080 |
| Metabase | http://localhost:3001 |
| n8n | http://localhost:5678 |
| API Docs | http://localhost:8000/docs |
| MCP Server | http://localhost:8100 |
| Pipeline Service | http://localhost:8200/docs |

---

## MVP Features

- [x] Docker infrastructure setup (11 services)
- [x] SIMRS data simulator real-time (setiap 10 detik, 1–100 record/domain, 13 domain)
- [x] Pipeline Service (FastAPI: /refine, /sync, /embed, /run-all)
- [x] n8n workflow JSON (siap import, cron 1 menit → pipeline-service)
- [x] MCP Server (Data Connector + Context Manager + LLM generation via LangChain)
- [x] FastAPI backend endpoints (analytics: overview, cost-by-category, occupancy, utility-trend, efficiency, staffing — chat, summary, rag, data, health)
- [x] React frontend (Vite + React 18, SPA, 6 halaman)
- [x] Dashboard 8 KPI card + 5 chart operasional (Chart.js) — incl. cost-to-revenue ratio & staffing overview
- [x] Chat interface dengan RAG toggle + typing indicator
- [x] Ringkasan utilitas & biaya per unit (tabel + progress bar)
- [x] Metabase embedded via iframe
- [x] Status sistem real-time (health poll tiap 30 detik)
- [x] SurrealDB vector index + embed_to_surrealdb_vector.py (nomic-embed-text via Ollama)
- [x] RAG pipeline via SurrealDB vector search — ChromaDB dihapus, MCP Server diupdate
- [ ] Metabase dashboard configuration (fasilitas, utilitas, tren layanan)

---

## MCP Server Role

MCP Server dalam DARSI memiliki tiga fungsi utama:

1. **Data Connector** — Mengambil data clean dari SurrealDB (structured query) dan vektor dari SurrealDB vector index (semantic search), lalu menyiapkannya sebagai konteks RAG.

2. **Context Manager** — Menerjemahkan hasil retrieval menjadi konteks terstruktur yang siap dikonsumsi LLM — menggabungkan data agregat operasional dengan potongan semantik yang relevan.

3. **LLM Generation** — Memanggil Ollama (qwen3.5:2b) via LangChain dengan konteks yang sudah dikemas, menghasilkan ringkasan analitik dan rekomendasi dalam Bahasa Indonesia.

---

## Database Schema — raw_* Tables (13 Domain)

Schema PostgreSQL tersedia dalam satu file: `pipeline/data/sql/raw_operational_schema.sql`.
Cukup dieksekusi 1x — mencakup DDL semua tabel + seed data statis tarif utilitas.

| # | Tabel | Sumber | Isi |
| --- | --- | --- | --- |
| 1 | `raw_pasien_aktif` | SIMRS | Snapshot pasien aktif: unit, kelas kamar, payer, kode diagnosis |
| 2 | `raw_okupansi_kamar` | SIMRS | Status kamar per observasi: kapasitas bed, terisi, kosong, maintenance |
| 3 | `raw_meter_listrik` | Utility Meter | Pembacaan kWh per meter per gedung/lantai: voltase, arus, power factor |
| 4 | `raw_konsumsi_air` | Water Meter | Volume air (m³) per meter per unit: tekanan rata-rata |
| 5 | `raw_biaya_operasional_unit` | Finance | Realisasi vs budget biaya per unit per bulan per kategori |
| 6 | `raw_konsumsi_obat_alkes` | Pharmacy | Pemakaian obat & alkes: item, qty, unit cost, total cost |
| 7 | `raw_lembur_staf` | HR | Biaya lembur staf: jam lembur, unit, alasan |
| 8 | `raw_jadwal_alat_berat` | Biomedik | Jadwal alat medis berat: start/end, status, operator |
| 9 | `raw_kunjungan_layanan` | SIMRS | Volume kunjungan & tindakan per unit per hari per payer — *denominator cost efficiency* |
| 10 | `raw_pendapatan_unit` | Finance | Revenue per unit per bulan per kategori & payer — *sisi revenue cost-to-revenue ratio* |
| 11 | `raw_jadwal_staf` | HR | Shift reguler staf: jadwal vs realisasi jam, ketidakhadiran — *dasar staffing optimization* |
| 12 | `raw_downtime_alat` | Biomedik | Downtime & kerusakan alat: tipe, severity, biaya perbaikan — *biaya tersembunyi* |
| 13 | `raw_tarif_utilitas` | Finance | Tarif listrik (kWh→IDR) & air (m³→IDR) per periode — *konversi volume ke biaya aktual* |

Domain 1–8 menangani monitoring operasional harian. Domain 9–13 mengaktifkan analisis **resource optimization** dan **cost efficiency** oleh AI layer.

---

## Data Flow

```
[SIMRS Simulator] — insert 1–100 record/domain setiap 10 detik
      ↓
[PostgreSQL] — raw_* tables (13 domain)
      ↓
[n8n] — cron trigger setiap 1 menit
      ↓ HTTP POST
[Pipeline Service]
   → POST /pipeline/refine  — Pandas: raw_* → refined_* (PostgreSQL)
   → POST /pipeline/sync    — sync refined_* → clean_* (SurrealDB)
   → POST /pipeline/embed   — generate embedding → SurrealDB vector index
      ↓
[SurrealDB] — clean_* (structured) + vector index HNSW (semantic)
      ↓ MCP Server query
[LangChain RAG] — structured aggregate + vector similarity search
      ↓
[Ollama qwen3.5:2b] — analytical summary & rekomendasi
      ↓
[FastAPI] — REST API response
      ↓
[React + Metabase] — dashboard & chat interface
```

---

## Human-in-the-Loop

Seluruh hasil analitik yang dihasilkan sistem bersifat **pendukung keputusan**, bukan pengambil keputusan otomatis. Setiap insight dan ringkasan yang dihasilkan LLM tetap memerlukan validasi dari pengguna (manajemen RS) sebelum digunakan lebih lanjut.

---

## Research Outputs

- Prototipe DARSI Management
- Publikasi ilmiah (jurnal nasional terakreditasi / konferensi internasional)
- HKI / Paten Sederhana
- Modul ajar implementasi Generative AI pada sistem informasi kesehatan

---

## Team

Penelitian Terapan — Politeknik Elektronika Negeri Surabaya (PENS)
Mitra: Rumah Sakit Islam (RSI) A. Yani Surabaya
