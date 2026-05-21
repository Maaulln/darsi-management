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
MCP Server (Connector + Context Manager + Optimised LLM Generation Pipeline)
      ↓
LangChain → SurrealDB (HNSW vector + BM25 full-text) → HyDE + Parallel Embedding
      ↓
Cross-Encoder Batch Rerank → Self-RAG → Ollama qwen3.5:2b (Local LLM)
      ↓
FastAPI Backend (async) → React Dashboard (single batch request)
```

---

## Microservice Architecture

DARSI dibangun di atas pola **Layered Microservices** — setiap layanan berjalan sebagai kontainer Docker yang terisolasi, memiliki tanggung jawab tunggal, dan berkomunikasi lewat interface yang terdefinisi (HTTP/REST atau koneksi database langsung).

### Prinsip Utama

| Prinsip | Implementasi |
|---|---|
| **Single Responsibility** | Setiap service hanya menangani satu domain fungsi (data ingest, AI, pipeline, UI) |
| **Loose Coupling** | Antar service berkomunikasi via HTTP REST — tidak ada shared memory atau direct function call |
| **Independent Deployment** | Setiap service dapat di-build, diuji, dan di-restart secara independen via Docker |
| **Private Network** | Semua service berada dalam Docker internal network; hanya Nginx, n8n, dan Metabase yang diekspos keluar |
| **Fully Async** | Seluruh I/O di backend dan MCP Server berjalan async (httpx.AsyncClient + asyncio) — tidak ada blocking call |

### Microservice Breakdown

```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION TIER                        │
│                                                                 │
│  ┌──────────────────┐          ┌────────────────────────────┐   │
│  │  React Frontend  │          │    Metabase (Port 3001)    │   │
│  │  (SPA, Port 80)  │          │  Reporting & BI Dashboard  │   │
│  └────────┬─────────┘          └──────────────┬─────────────┘   │
└───────────┼────────────────────────────────────┼────────────────┘
            │ HTTP                               │ Direct DB
┌───────────▼────────────────────────────────────┼────────────────┐
│                        GATEWAY TIER             │                │
│  ┌──────────────────────────────────────────┐   │                │
│  │           Nginx (Port 8080)              │   │                │
│  │         Reverse Proxy & Router           │   │                │
│  └──────────────────┬───────────────────────┘   │                │
└─────────────────────┼───────────────────────────┼────────────────┘
                      │ HTTP /api/*               │
┌─────────────────────▼───────────────────────────┼────────────────┐
│                    APPLICATION TIER              │                │
│  ┌──────────────────────────────────────────┐   │                │
│  │       FastAPI Backend (Port 8000)        │   │                │
│  │  REST API: analytics (batch + per-metric)│   │                │
│  │  chat, rag, summary, data, health,       │   │                │
│  │  settings; semua async via MCPClient     │   │                │
│  └──────────────────┬───────────────────────┘   │                │
└─────────────────────┼───────────────────────────┼────────────────┘
                      │ HTTP (async)
┌─────────────────────▼───────────────────────────┼────────────────┐
│                       AI TIER                    │                │
│  ┌──────────────────────────────────────────┐    │                │
│  │         MCP Server (Port 8100)           │    │                │
│  │  Data Connector · Context Manager ·      │    │                │
│  │  Optimised LLM Pipeline (RAG + cache)    │    │                │
│  └──────┬────────────────────────┬──────────┘    │                │
│         │                        │               │                │
│  ┌──────▼────────────┐  ┌────────▼─────────┐    │                │
│  │   SurrealDB       │  │  Ollama           │    │                │
│  │  (Port 8001)      │  │  (Port 11434)     │    │                │
│  │ clean_* + HNSW    │  │ qwen3.5:2b        │    │                │
│  │  vector + BM25    │  │ nomic-embed-text  │◄───┘                │
│  └───────────────────┘  └──────────────────┘                     │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                       DATA & PIPELINE TIER                        │
│                                                                   │
│  ┌──────────────┐  ┌───────────┐  ┌─────────────────────────┐    │
│  │  PostgreSQL  │  │    n8n    │  │   Pipeline Service       │    │
│  │  (Port 5432) │  │(Port 5678)│  │      (Port 8200)         │    │
│  │  raw_* tables│  │ Cron 1mnt │──► /refine /sync /embed     │    │
│  │  13 domain   │◄─┤ Orchestrator  └──────────┬──────────────┘    │
│  └──────▲───────┘  └───────────┘             │                    │
│         │                                    ▼                    │
│  ┌──────┴──────────┐                   SurrealDB                  │
│  │ SIMRS Simulator │                 (clean_* + vector + BM25)     │
│  │ setiap 10 dtk   │                                              │
│  └─────────────────┘                                              │
└───────────────────────────────────────────────────────────────────┘
```

### Daftar Microservice

| Service | Port | Tier | Tanggung Jawab |
|---|---|---|---|
| `nginx` | 8080 | Gateway | Reverse proxy, routing `/api/*` → backend, SPA serving |
| `frontend` | — | Presentation | React SPA: dashboard KPI, chat AI, summary, status, settings |
| `metabase` | 3001 | Presentation | BI reporting: chart fasilitas, tren layanan, konsumsi utilitas |
| `backend` | 8000 | Application | FastAPI REST API (fully async): proxy ke MCP Server |
| `mcp-server` | 8100 | AI | Data Connector + Context Manager + Optimised LLM Pipeline |
| `ollama` | 11434 | AI | Local LLM inference: `qwen3.5:2b` (chat) + `nomic-embed-text` (embed) |
| `surrealdb` | 8001 | Data | Clean data (`clean_*`) + vector index HNSW + BM25 full-text |
| `pipeline-service` | 8200 | Pipeline | Pandas refinement + sync SurrealDB + generate embedding |
| `n8n` | 5678 | Pipeline | Cron orchestrator → HTTP trigger ke pipeline-service setiap 1 menit |
| `postgres` | 5432 | Data | Raw SIMRS data store: `raw_*` tables (13 domain) |
| `simrs-simulator` | — | Data | Penghasil data real-time: insert 1–100 record/domain setiap 10 detik |

### Inter-Service Communication

```
[React]          ──── HTTP GET/POST ────► [Nginx] ──► [FastAPI Backend]
[FastAPI]        ──── HTTP REST (async) ─► [MCP Server]
[MCP Server]     ──── httpx (shared) ────► [SurrealDB]  (structured + vector + BM25)
[MCP Server]     ──── LangChain LCEL ────► [Ollama]     (qwen3.5:2b generation)
[Pipeline Svc]   ──── Ollama API ─────────► [Ollama]     (nomic-embed-text embedding)
[Pipeline Svc]   ──── httpx ─────────────► [SurrealDB]  (write clean_* + vector index)
[Pipeline Svc]   ──── SQLAlchemy ─────────► [PostgreSQL] (read raw_*, write refined_*)
[SIMRS Simulator]──── SQLAlchemy ─────────► [PostgreSQL] (insert raw_* setiap 10 detik)
[n8n]            ──── HTTP POST ──────────► [Pipeline Service] (trigger setiap 1 menit)
[Metabase]       ──── Direct DB ──────────► [PostgreSQL] / [SurrealDB]
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Data Simulator | Python + Faker | Generate data SIMRS dummy setiap 10 detik ke PostgreSQL |
| Data Ingestion | PostgreSQL 16 | Raw SIMRS data storage |
| Orchestration | n8n | Cron trigger + HTTP orchestration + notifikasi pipeline |
| Data Processing | Pipeline Service (FastAPI + Pandas) | Refinement, sync SurrealDB, embed vector — dipanggil n8n via HTTP |
| Clean Data + Vector Store | SurrealDB | Structured clean data + native vector search (HNSW) + BM25 full-text |
| Connector | Custom MCP Server | Data connector + Context manager + Optimised LLM generation pipeline |
| RAG Framework | LangChain | RAG pipeline via SurrealDB vector + BM25 search |
| LLM (chat) | Ollama + qwen3.5:2b | Local private cloud LLM inference (generasi teks) |
| LLM (embed) | Ollama + nomic-embed-text | Vector embedding untuk RAG (768 dimensi) |
| Reranker | CrossEncoder ms-marco-MiniLM-L-6-v2 | Batch cross-encoder rerank hasil fusion RRF |
| Backend | FastAPI (fully async) | REST API layer — semua endpoint async, shared httpx.AsyncClient |
| Frontend | React + Metabase | Dashboard UI + embedded analytics |
| Reverse Proxy | Nginx 1.27 Alpine | Service routing |
| Containerization | Docker + Docker Compose | Service orchestration |

---

## Services & Ports

| Service | Port | Description |
|---|---|---|
| nginx | 8080:80 | Reverse proxy — main entry point |
| frontend | — | React SPA (Vite build, served by inner nginx) |
| backend | 8000:8000 | FastAPI backend (async) |
| mcp-server | 8100:8100 | Custom MCP server (AI pipeline) |
| pipeline-service | 8200:8200 | Refinement + sync + embed (dipanggil n8n) |
| ollama | 11434:11434 | LLM inference server |
| surrealdb | 8001:8000 | Clean data store + vector search + BM25 |
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
├── backend/                         # FastAPI backend (Clean Architecture, fully async)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py                  # CORS dari env, router registration
│       ├── api/                     # Route handlers (semua async)
│       │   ├── analytics.py         # GET /api/analytics/dashboard (batch), /overview, etc.
│       │   ├── chat.py              # POST /api/chat
│       │   ├── data.py              # GET /api/data/*
│       │   ├── health.py            # GET /health, /api/readiness
│       │   ├── rag.py               # POST /api/rag/query
│       │   ├── settings.py          # GET/POST /api/settings/* (dynamic API management)
│       │   └── summary.py           # GET /api/summary/*
│       ├── services/
│       │   ├── mcp_client.py        # Async HTTP client (lazy singleton httpx.AsyncClient)
│       │   └── rag_service.py       # Thin wrapper RAG via MCP
│       └── core/
│           └── config.py            # Settings: mcp_server_url, cors_origins
├── mcp-server/                      # Custom MCP Server (AI Layer — optimised pipeline)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py                  # Data connector + Context manager + LLM pipeline
│                                    # Fitur: multi-layer cache, parallel HyDE embed,
│                                    # batch cross-encoder, Self-RAG, BM25 dual retrieval
├── pipeline-service/                # Pipeline Service — dipanggil n8n via HTTP
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── main.py                  # POST /pipeline/refine, /sync, /embed, /run-all
├── pipeline/                        # Script data processing
│   ├── requirements.txt
│   ├── processors/
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
│           ├── Dashboard.jsx        # 8 KPI cards + 5 charts (1 batch request, useMemo)
│           ├── Analytics.jsx        # Charts detail + tabel breakdown
│           ├── Chat.jsx             # Chat AI dengan RAG toggle
│           ├── Summary.jsx          # Ringkasan utilitas & biaya per unit
│           ├── MetabasePage.jsx     # Metabase embedded (iframe)
│           ├── StatusPage.jsx       # Health semua service
│           └── Settings.jsx         # Superadmin: konfigurasi API & sistem
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
# Variable penting:
#   CORS_ORIGINS=http://localhost:5173,http://localhost:80,http://localhost
#   MCP_SERVER_URL=http://mcp-server:8100
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
- [x] FastAPI backend endpoints — **fully async** (analytics: batch dashboard + per-metric, chat, summary, rag, data, health, settings)
- [x] React frontend (Vite + React 18, SPA, 7 halaman incl. Settings)
- [x] Dashboard 8 KPI card + 5 chart operasional (Chart.js) — incl. cost-to-revenue ratio & staffing overview
- [x] Dashboard batch request — 1 HTTP call ke `/api/analytics/dashboard` menggantikan 6 request paralel
- [x] Chat interface dengan RAG toggle + typing indicator
- [x] Ringkasan utilitas & biaya per unit (tabel + progress bar)
- [x] Metabase embedded via iframe
- [x] Status sistem real-time (health poll tiap 30 detik)
- [x] SurrealDB vector index + BM25 full-text index (dual retrieval)
- [x] RAG pipeline via SurrealDB vector + BM25 + RRF fusion + cross-encoder rerank
- [x] **LLM Response Cache** — TTL 60 detik, key `md5(query)[:10]`, response instan pada query berulang
- [x] **Retrieval Cache** — vector & BM25 results di-cache per domain+query hash, TTL 120 detik
- [x] **Parallel HyDE + Direct Embedding** — keduanya berjalan bersamaan via `asyncio.create_task`; HyDE digunakan jika selesai dalam 3 detik, fallback ke direct embedding
- [x] **Batch Cross-Encoder Rerank** — satu `ce.predict()` call untuk semua domain sekaligus (bukan per-domain)
- [x] **Context Truncation** — context dipotong di 6000 karakter untuk menjaga model kecil tetap fokus
- [x] **Smarter Self-RAG** — retry menggunakan top-5 domain berdasarkan keyword overlap score, bukan semua 13 domain
- [x] **BM25 Keyword Expansion Fix** — semua matched domain berkontribusi keyword (bukan hanya 3 domain pertama)
- [x] **Cache Eviction Loop** — background task membersihkan entri cache >600 detik setiap 5 menit
- [x] **Shared SurrealDB HTTP Client** — satu `httpx.AsyncClient` dipakai ulang di seluruh request
- [x] **Tighter Prompt Template** — ~80 token prefix vs 180 token sebelumnya; cocok untuk model 2B
- [x] CORS origins dikonfigurasi via environment variable `CORS_ORIGINS`
- [x] Superadmin Settings dashboard (dynamic API management, konfigurasi sistem)
- [x] PostgreSQL integration untuk settings persistence
- [ ] Metabase dashboard configuration (fasilitas, utilitas, tren layanan)

---

## MCP Server — LLM Generation Pipeline

MCP Server dalam DARSI memiliki empat fungsi utama yang berjalan secara berurutan:

### 1. Data Connector
Mengambil data clean dari SurrealDB via structured query (`SELECT ... math::sum() GROUP BY`) langsung di sisi database — tidak ada aggregasi Python. Tiga query paralel untuk summary resource.

### 2. Context Manager (RAG)
Pipeline retrieval yang dioptimasi:

```
Query Pengguna
      │
      ▼
┌─────────────────────────────────────────────────┐
│  Parallel Embedding Phase                        │
│  ┌───────────────────┐  ┌──────────────────────┐│
│  │  HyDE Embedding   │  │  Direct Embedding    ││
│  │ (hypothetical doc)│  │  (query langsung)    ││
│  └────────┬──────────┘  └──────────┬───────────┘│
│           │ wait_for(3s)           │ await      │
│           └──────────┬─────────────┘            │
│                      ▼ best available            │
│             query_embedding (768-dim)            │
└──────────────────────┬──────────────────────────┘
                       │
      ┌────────────────┼────────────────┐
      ▼                ▼                ▼
[Domain A]        [Domain B]       [Domain N]      ← asyncio.gather
  vector cache?     vector cache?    vector cache?
  bm25 cache?       bm25 cache?      bm25 cache?
  → HNSW search    → HNSW search    → HNSW search
  → BM25 search    → BM25 search    → BM25 search
  → RRF fusion     → RRF fusion     → RRF fusion
      │                │                │
      └────────────────┴────────────────┘
                       ▼
          Global Batch Cross-Encoder Rerank
          (satu ce.predict() untuk semua domain)
                       ▼
          Context Assembly + Truncation (6000 char)
```

### 3. Prompt Engineering
Template ringkas (~80 token) yang terarah untuk model 2B — hanya menyebutkan fakta & angka kunci, tidak memaksa multi-step reasoning panjang.

### 4. LLM Generation + Self-RAG
LangChain LCEL chain (`PromptTemplate | OllamaLLM | StrOutputParser`) dengan `ainvoke()` async. Self-RAG mendeteksi jawaban tidak cukup dan retry ke top-5 domain relevan (bukan semua 13), dengan timeout protection (60 detik per retry attempt).

---

## Multi-Layer Cache Strategy

| Layer | Key | TTL | Estimasi Penghematan |
|---|---|---|---|
| LLM Response | `llm:{md5(query)[:10]}` | 60 detik | 30–120s → ~0ms (query berulang) |
| Vector Retrieval | `vec:{domain}:{md5(embedding)[:10]}` | 120 detik | 500ms–3s per domain |
| BM25 Retrieval | `bm25:{domain}:{md5(keywords)[:10]}` | 120 detik | 200ms–1s per domain |
| Embedding | (internal Ollama cache) | — | — |
| Aggregate Analytics | (SurrealDB query cache, 60 detik) | 60 detik | Per analytics endpoint |

Background eviction task membersihkan entri >600 detik setiap 5 menit untuk mencegah memory leak.

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
   → POST /pipeline/embed   — generate embedding → SurrealDB vector index + BM25
      ↓
[SurrealDB] — clean_* (structured) + vector HNSW + BM25 full-text
      ↓ MCP Server query (async, shared httpx.AsyncClient)
[MCP Server LLM Pipeline]
   → Parallel HyDE + Direct Embedding
   → Multi-domain Vector + BM25 retrieval (with cache)
   → RRF Fusion per domain
   → Batch Cross-Encoder Rerank (satu call)
   → Context Assembly + Truncation
   → LLM Generation (ainvoke, timeout 120s)
   → Self-RAG check → retry if insufficient (top-5 domains, timeout 60s)
   → LLM Response Cache (60s TTL)
      ↓
[FastAPI Backend] — async REST API
   → GET /api/analytics/dashboard — 6 analytics paralel, 1 response
      ↓
[React Dashboard] — single batch fetch, useMemo chart data
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
