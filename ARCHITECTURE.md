# DARSI Management — Architecture

## Overview

DARSI Management menggunakan arsitektur **Layered Microservices** yang berjalan di atas private cloud (Docker). Setiap layer memiliki tanggung jawab yang terisolasi dan berkomunikasi melalui interface yang terdefinisi dengan baik. Pendekatan ini memastikan setiap komponen dapat dikembangkan, diuji, dan diganti secara independen.

Pattern utama yang digunakan:
- **Layered Architecture** — setiap layer hanya berkomunikasi dengan layer yang berdekatan
- **RAG Pattern** — Retrieval-Augmented Generation via SurrealDB vector search (HNSW) untuk grounding output LLM dengan data operasional
- **MCP Pattern** — Model Context Protocol sebagai mediator antara data layer dan AI layer
- **Unified Data Store** — SurrealDB menggabungkan clean structured data dan vector store dalam satu service
- **Human-in-the-Loop** — seluruh output AI bersifat advisory, bukan keputusan otomatis

---

## Microservice Architecture

DARSI terdiri dari **11 microservice** yang masing-masing berjalan sebagai kontainer Docker terisolasi. Setiap service memiliki Dockerfile dan lifecycle tersendiri — dapat di-build, diuji, dan di-restart secara independen tanpa memengaruhi service lain.

### Prinsip Desain

| Prinsip | Implementasi dalam DARSI |
|---|---|
| **Single Responsibility** | Tiap service hanya menangani satu domain fungsi |
| **Loose Coupling** | Komunikasi via HTTP REST atau koneksi DB langsung — tidak ada shared memory |
| **Independent Deployment** | `docker compose up --build <service>` dapat dijalankan per service |
| **Private Network** | Semua service berada dalam Docker internal network; hanya Nginx (8080), n8n (5678), dan Metabase (3001) yang diekspos ke host |
| **Stateless Services** | Backend, MCP Server, dan Pipeline Service tidak menyimpan state — state ada di PostgreSQL dan SurrealDB |

### Service Boundaries

```
┌──────────────────────────────────────────────────────────────────────┐
│  PRESENTATION TIER                                                   │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐    │
│  │  [frontend]          │    │  [metabase]                      │    │
│  │  React SPA           │    │  BI Reporting & Embedded Charts  │    │
│  │  Vite + React 18     │    │  Direct DB query ke PostgreSQL   │    │
│  └──────────┬───────────┘    └──────────────────────────────────┘    │
└─────────────┼────────────────────────────────────────────────────────┘
              │ HTTP
┌─────────────▼────────────────────────────────────────────────────────┐
│  GATEWAY TIER                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [nginx]  Port 8080                                          │   │
│  │  Reverse proxy — routes /api/* → backend, / → frontend      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────┬────────────────────────────────────────────────────────┘
              │ HTTP /api/*
┌─────────────▼────────────────────────────────────────────────────────┐
│  APPLICATION TIER                                                    │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [backend]  Port 8000                                        │   │
│  │  FastAPI — thin REST layer, semua logika delegasi ke MCP     │   │
│  │  Endpoints: /api/analytics /api/chat /api/rag /api/summary   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────┬────────────────────────────────────────────────────────┘
              │ HTTP
┌─────────────▼────────────────────────────────────────────────────────┐
│  AI TIER                                                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [mcp-server]  Port 8100                                     │   │
│  │  Data Connector → Context Manager → LLM Generation           │   │
│  │  Orchestrates: SurrealDB query + vector search + Ollama call │   │
│  └──────────┬───────────────────────────┬──────────────────────┘   │
│             │ httpx                      │ LangChain LCEL            │
│  ┌──────────▼───────────┐   ┌───────────▼──────────────────────┐   │
│  │  [surrealdb] Port 8001│   │  [ollama]  Port 11434            │   │
│  │  clean_* structured  │   │  qwen3.5:2b  — text generation   │   │
│  │  + HNSW vector index │   │  nomic-embed-text — embedding    │   │
│  └──────────────────────┘   └──────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  DATA & PIPELINE TIER                                                │
│                                                                      │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  [simrs-simulator]│  │  [postgres]  │  │  [n8n]  Port 5678     │  │
│  │  No exposed port │  │  Port 5432   │  │  Cron orchestrator    │  │
│  │  Insert raw_*    │─►│  raw_* tables│  │  HTTP trigger 1 menit │  │
│  │  setiap 10 detik │  │  13 domain   │  └───────────┬────────────┘  │
│  └─────────────────┘  └──────────────┘              │ HTTP POST     │
│                                                      ▼               │
│                              ┌────────────────────────────────────┐  │
│                              │  [pipeline-service]  Port 8200     │  │
│                              │  POST /refine → Pandas cleaning    │  │
│                              │  POST /sync   → write SurrealDB    │  │
│                              │  POST /embed  → generate + store   │  │
│                              │               vector (Ollama)       │  │
│                              └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Microservice Catalog

| Service | Image / Base | Port | Tier | Tanggung Jawab Tunggal |
|---|---|---|---|---|
| `nginx` | nginx:1.27-alpine | 8080 | Gateway | Route traffic; single entry point |
| `frontend` | node → nginx (multi-stage) | — | Presentation | React SPA: KPI dashboard, chat AI, summary |
| `metabase` | metabase/metabase | 3001 | Presentation | BI reporting via direct DB query |
| `backend` | python:3.11 | 8000 | Application | REST API — proxy & translate request ke MCP Server |
| `mcp-server` | python:3.11 | 8100 | AI | RAG pipeline: data retrieval + context assembly + LLM call |
| `ollama` | ollama/ollama | 11434 | AI | Local LLM inference (qwen3.5:2b + nomic-embed-text) |
| `surrealdb` | surrealdb/surrealdb | 8001 | Data | Clean data store (`clean_*`) + HNSW vector index |
| `pipeline-service` | python:3.11 | 8200 | Pipeline | Pandas ETL: raw → refined → clean + embed |
| `n8n` | n8nio/n8n | 5678 | Pipeline | Cron orchestrator — HTTP trigger pipeline-service |
| `postgres` | postgres:16 | 5432 | Data | Raw SIMRS data store (`raw_*`, 13 domain) |
| `simrs-simulator` | python:3.11 | — | Data | Real-time data generator ke PostgreSQL |

### Inter-Service Communication Matrix

| From | To | Protokol | Frekuensi | Keterangan |
|---|---|---|---|---|
| React | Nginx | HTTP REST | Per user action | Semua request via single entry point |
| Nginx | Backend | HTTP proxy | Per user action | Route `/api/*` |
| Nginx | Frontend | Static serve | Per page load | SPA files |
| Backend | MCP Server | HTTP REST | Per user action | Delegasi semua logika AI |
| MCP Server | SurrealDB | httpx | Per AI request | Structured query + vector search |
| MCP Server | Ollama | LangChain LCEL | Per AI request | Text generation (qwen3.5:2b) |
| Pipeline Service | Ollama | HTTP (Ollama API) | Setiap 1 menit | Embedding (nomic-embed-text) |
| Pipeline Service | SurrealDB | httpx | Setiap 1 menit | Write `clean_*` + vector index |
| Pipeline Service | PostgreSQL | SQLAlchemy | Setiap 1 menit | Read `raw_*`, write `refined_*` |
| n8n | Pipeline Service | HTTP POST | Setiap 1 menit (cron) | Trigger `/refine` → `/sync` → `/embed` |
| SIMRS Simulator | PostgreSQL | SQLAlchemy | Setiap 10 detik | Insert `raw_*` |
| Metabase | PostgreSQL | JDBC direct | Per dashboard load | Reporting query |

---

## System Diagram

```
╔══════════════════════════════════════════════════════════════════╗
║                        USER INTERFACE LAYER                      ║
║                                                                  ║
║   ┌─────────────────────────┐   ┌──────────────────────────┐    ║
║   │      React Frontend     │   │    Metabase (Embedded)   │    ║
║   │  - Chat Interface       │   │  - Operational Charts    │    ║
║   │  - Dashboard UI         │   │  - Trend Visualization   │    ║
║   │  - AI Summary Display   │   │  - Facility Usage Report │    ║
║   └────────────┬────────────┘   └─────────────┬────────────┘    ║
╚════════════════│═════════════════════════════╗ │ ═══════════════╝
                 │ HTTP                        ║ │ Direct DB Query
╔════════════════▼════════════════════════════╗ │ ═══════════════╗
║                    GATEWAY LAYER            ║ │                ║
║                                             ║ │                ║
║              ┌──────────────┐               ║ │                ║
║              │    Nginx     │               ║ │                ║
║              │  Port 8080   │               ║ │                ║
║              │ Reverse Proxy│               ║ │                ║
║              └──────┬───────┘               ║ │                ║
╚═════════════════════│═══════════════════════╝ │ ═══════════════╝
                      │ HTTP                    │
╔═════════════════════▼═══════════════════════════════════════════╗
║                      APPLICATION LAYER                          ║
║                                                                 ║
║              ┌──────────────────────┐                          ║
║              │    FastAPI Backend   │                          ║
║              │      Port 8000       │                          ║
║              │                      │                          ║
║              │  - /api/analytics    │                          ║
║              │  - /api/chat         │                          ║
║              │  - /api/rag          │                          ║
║              │  - /api/summary      │                          ║
║              └──────────┬───────────┘                          ║
╚═════════════════════════│═══════════════════════════════════════╝
                          │ HTTP
╔═════════════════════════▼═══════════════════════════════════════╗
║                        AI LAYER                                 ║
║                                                                 ║
║   ┌──────────────────────────────────────────────────────────┐  ║
║   │                    MCP Server (Port 8100)                │  ║
║   │                                                          │  ║
║   │   Function 1: Data Connector                             │  ║
║   │   SurrealDB ──► Structured Query ──► Aggregate Context   │  ║
║   │                                                          │  ║
║   │   Function 2: Context Manager                            │  ║
║   │   SurrealDB ──► Vector Search ──► Semantic Context       │  ║
║   │                                                          │  ║
║   │   Function 3: LLM Generation                             │  ║
║   │   Context ──► LangChain Prompt ──► Ollama ──► Answer     │  ║
║   └───────────┬──────────────────────────┬───────────────────┘  ║
║               │                          │                       ║
║   ┌───────────▼──────────┐  ┌────────────▼──────────────────┐   ║
║   │     LangChain        │  │   Ollama + qwen3.5:2b         │   ║
║   │   RAG Pipeline       │  │     Port 11434                │   ║
║   │   (LCEL Chain)       │  │   Local LLM Inference         │   ║
║   └──────────────────────┘  └───────────────────────────────┘   ║
╚═════════════════════════════════════════════════════════════════╝

╔═════════════════════════════════════════════════════════════════╗
║                       DATA LAYER                                ║
║                                                                 ║
║   ┌──────────────┐   ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ║
║   │  PostgreSQL  │   │     n8n     │  │Pipeline Svc  │  │  SurrealDB   │  ║
║   │  Port 5432   │   │ Port 5678   │  │  Port 8200   │  │  Port 8001   │  ║
║   │              │   │             │  │              │  │              │  ║
║   │  raw_* tables│   │ Cron 1 mnt  │  │ POST /refine │  │  clean_*     │  ║
║   │  13 domain   │   │ HTTP trigger│─►│ POST /sync   │─►│  + Vector    │  ║
║   └──────┬───────┘   └─────────────┘  │ POST /embed  │  │  Index HNSW  │  ║
║          │◄──────────────────────────  └──────────────┘  └──────────────┘  ║
║          ▲                                                                  ║
║   ┌──────┴───────┐                                                          ║
║   │SIMRS Simulator│                                                         ║
║   │ setiap 10 dtk│                                                          ║
║   │ 1–100 record │                                                          ║
║   └──────────────┘                                                          ║
╚═════════════════════════════════════════════════════════════════╝
```

---

## Layer Breakdown

### 1. User Interface Layer

Terdiri dari dua komponen yang bekerja bersama dalam satu tampilan:

**React Frontend**
Menangani semua interaksi pengguna yang bersifat dinamis dan AI-driven. Komponen utamanya meliputi chat interface untuk bertanya ke LLM (qwen3.5:2b via MCP Server), tampilan ringkasan analitik hasil AI, dan wrapper container untuk embed Metabase.

Dashboard menampilkan **8 KPI card** (pasien aktif, BOR, total biaya, listrik, air, lembur, cost-to-revenue ratio, overtime ratio) dan **5 chart** (biaya per kategori, okupansi bed per unit, utilitas per unit, cost-to-revenue per unit, jam kerja vs lembur per unit). Dua KPI dan dua chart terakhir berasal dari endpoint analytics efisiensi yang hanya bisa dihitung setelah domain 9–13 tersedia.

**Metabase (Self-hosted, Port 3001)**
Ditanamkan (embedded) ke dalam React melalui iframe menggunakan fitur Metabase Embedding. Metabase bertugas khusus untuk visualisasi data reporting — chart penggunaan fasilitas, tren layanan, konsumsi utilitas — dengan query langsung ke PostgreSQL dan SurrealDB.

Pembagian tanggung jawab yang jelas:
- Hal yang **AI-driven dan dinamis** → React component
- Hal yang **data reporting dan statis** → Metabase embedded

---

### 2. Gateway Layer

**Nginx (Port 8080)**
Bertindak sebagai single entry point untuk seluruh traffic. Melakukan routing berdasarkan path:

```
/         → React Frontend
/api/*    → FastAPI Backend (Port 8000)
/metabase → Metabase (Port 3001)
/n8n      → n8n UI (Port 5678)
```

Selain routing, Nginx juga menangani SSL termination dan load balancing jika diperlukan di masa mendatang.

---

### 3. Application Layer

**FastAPI Backend (Port 8000)**
Menggunakan **Clean Architecture** dengan pembagian sebagai berikut:

```
backend/app/
├── api/              # Route handlers
│   ├── analytics.py  # GET /api/analytics/*
│   ├── chat.py       # POST /api/chat
│   ├── rag.py        # POST /api/rag/query
│   ├── summary.py    # GET /api/summary/*
│   ├── data.py       # GET /api/data/*
│   └── health.py     # GET /health, /api/readiness
├── services/
│   ├── mcp_client.py # HTTP client ke MCP Server
│   └── rag_service.py
└── core/
    └── config.py     # Settings (hanya mcp_server_url)
```

FastAPI berkomunikasi ke AI Layer melalui HTTP request ke MCP Server. Tidak ada komunikasi langsung dari FastAPI ke database — semua akses data dikelola oleh MCP Server.

---

### 4. AI Layer

Ini adalah layer paling kritis dalam arsitektur DARSI. Terdiri dari tiga komponen yang bekerja secara berurutan.

**MCP Server (Port 8100)**

Memiliki tiga fungsi yang berjalan dalam satu service:

*Fungsi 1 — Data Connector:*
Melakukan structured query ke SurrealDB (`SELECT ... GROUP BY ...`) untuk mengambil data agregat operasional per domain — 13 domain mencakup pasien, okupansi, utilitas, biaya, farmasi, SDM, alat medis, kunjungan layanan, pendapatan, jadwal staf, downtime alat, dan tarif utilitas. Hasil query diformat menjadi konteks teks untuk RAG.

Domain registry MCP Server memetakan setiap domain ke tiga properti: `surreal` (nama tabel `clean_*` di SurrealDB), `vector` (nama vector index HNSW), dan `keywords` (untuk intent detection pada query pengguna).

Endpoint analytics yang tersedia:

| Endpoint | Fungsi |
| --- | --- |
| `GET /mcp/analytics/overview` | KPI agregat semua domain (pasien, BOR, biaya, utilitas, lembur) |
| `GET /mcp/analytics/cost-by-category` | Breakdown biaya operasional per kategori |
| `GET /mcp/analytics/occupancy-by-unit` | Okupansi bed per unit |
| `GET /mcp/analytics/utility-trend` | Konsumsi listrik & air per unit |
| `GET /mcp/analytics/efficiency` | Cost-per-service & cost-to-revenue ratio per unit (join domain 5, 9, 10) |
| `GET /mcp/analytics/staffing` | Shift coverage vs overtime ratio per unit (join domain 7, 11) |
| `GET /mcp/summary/resource` | Ringkasan utilitas resource per unit |
| `GET /mcp/summary/cost` | Ringkasan biaya per unit & kategori |

*Fungsi 2 — Context Manager:*
Melakukan vector similarity search ke SurrealDB vector index (`vector::similarity::cosine`) berdasarkan query semantik pengguna. Menggabungkan hasil structured query dan semantic search menjadi satu konteks terstruktur yang siap dikonsumsi LLM.

*Fungsi 3 — LLM Generation:*
Menggunakan LangChain (LCEL: `PromptTemplate | OllamaLLM | StrOutputParser`) untuk memanggil Ollama dengan konteks yang sudah dikemas. Seluruh pipeline RAG — retrieval hingga generation — berjalan di dalam MCP Server.

**LangChain (di dalam MCP Server)**

Digunakan sebagai RAG framework untuk:
1. Menyusun prompt dengan `PromptTemplate`
2. Memanggil Ollama via `OllamaLLM`
3. Mem-parse output LLM via `StrOutputParser`

Vector retrieval dilakukan langsung ke SurrealDB menggunakan `vector::similarity::cosine` — tidak memerlukan vector database terpisah.

**Ollama (Port 11434) — dua model**

Ollama berjalan sepenuhnya lokal di private cloud — tidak ada data yang keluar ke luar jaringan. Digunakan untuk dua fungsi berbeda:

| Model | Fungsi | Ukuran |
|---|---|---|
| `qwen3.5:2b` | Generasi teks — chat, ringkasan, rekomendasi via LangChain | ~1.5 GB |
| `nomic-embed-text` | Embedding teks → vector float[768] untuk RAG index | ~274 MB |

`qwen3.5:2b` dipanggil oleh LangChain di dalam MCP Server untuk generasi jawaban. `nomic-embed-text` dipanggil oleh `embed_to_surrealdb_vector.py` saat pipeline embed, dan oleh MCP Server saat query-time untuk menghasilkan embedding dari pertanyaan user.

---

### 5. Data Layer

**PostgreSQL (Port 5432)**
Menyimpan data mentah SIMRS dalam skema relasional (`raw_*` tables, 13 domain). Data terus-menerus diisi oleh SIMRS Simulator setiap 10 detik. Schema seluruh tabel tersedia dalam satu file: `pipeline/data/sql/raw_operational_schema.sql` (mencakup DDL + seed data statis tarif utilitas, cukup dieksekusi 1x).

**Tabel raw_* — 13 Domain:**

| # | Tabel | Sumber | Isi |
| --- | --- | --- | --- |
| 1 | `raw_pasien_aktif` | SIMRS | Snapshot pasien yang sedang dirawat: unit, kelas, payer, kode diagnosis |
| 2 | `raw_okupansi_kamar` | SIMRS | Status tiap kamar: kapasitas bed, terisi, kosong, maintenance |
| 3 | `raw_meter_listrik` | Utility Meter | Pembacaan kWh per meter per gedung/lantai: voltase, arus, power factor |
| 4 | `raw_konsumsi_air` | Water Meter | Volume air (m³) per meter per unit: tekanan rata-rata |
| 5 | `raw_biaya_operasional_unit` | Finance | Realisasi vs budget biaya per unit per bulan: kategori biaya |
| 6 | `raw_konsumsi_obat_alkes` | Pharmacy | Pemakaian obat & alat kesehatan: item, qty, unit cost, total cost |
| 7 | `raw_lembur_staf` | HR | Biaya lembur staf per orang per hari: jam lembur, alasan |
| 8 | `raw_jadwal_alat_berat` | Biomedik | Jadwal pemakaian alat medis berat: start/end, status, operator |
| 9 | `raw_kunjungan_layanan` | SIMRS | Volume kunjungan & tindakan per unit per hari per payer — **denominator cost efficiency** |
| 10 | `raw_pendapatan_unit` | Finance | Revenue per unit per bulan per kategori & payer — **sisi revenue cost-to-revenue ratio** |
| 11 | `raw_jadwal_staf` | HR | Shift reguler staf: jadwal vs realisasi jam kerja, ketidakhadiran — **dasar staffing optimization** |
| 12 | `raw_downtime_alat` | Biomedik | Downtime & kerusakan alat: tipe (planned/unplanned), severity, biaya perbaikan — **biaya tersembunyi** |
| 13 | `raw_tarif_utilitas` | Finance | Tarif listrik (kWh→IDR) & air (m³→IDR) per periode — **konversi volume fisik ke biaya aktual** |

Domain 1–8 menangani monitoring operasional harian. Domain 9–13 ditambahkan khusus untuk mengaktifkan kemampuan AI dalam menghitung metrik **resource optimization** (staffing ratio, equipment utilization) dan **cost efficiency** (cost-per-service, cost-to-revenue ratio, biaya utilitas aktual).

**SIMRS Simulator (Docker service, no exposed port)**
Service Python yang berjalan terus-menerus (`restart: unless-stopped`). Setiap 10 detik menginsert 1–100 record acak per domain ke tabel `raw_*` PostgreSQL — mensimulasikan aliran data real-time dari SIMRS rumah sakit.

**n8n (Port 5678)**
Mengorkestrasikan pipeline via HTTP trigger setiap 1 menit. Workflow linear:
1. Cron trigger (setiap 1 menit)
2. HTTP POST `pipeline-service/pipeline/refine` — jalankan Pandas refinement
3. HTTP POST `pipeline-service/pipeline/sync` — sync ke SurrealDB
4. HTTP POST `pipeline-service/pipeline/embed` — generate + simpan vector ke SurrealDB

Dipilih karena pipeline linear tanpa dependensi kompleks — n8n cukup dan jauh lebih ringan dari Airflow. Tambahan: built-in notifikasi (email/Slack) saat pipeline gagal.

Workflow sudah tersedia dalam format JSON di `n8n/darsi_pipeline_workflow.json` — siap import via UI n8n.

**Pipeline Service (Port 8200)**
FastAPI tipis yang mengekspos logika Pandas refinement sebagai HTTP endpoint. Dipanggil oleh n8n secara berurutan:
- `POST /pipeline/refine` — baca `raw_*` PostgreSQL → Pandas cleaning → tulis `refined_*`
- `POST /pipeline/sync` — baca `refined_*` → tulis `clean_*` SurrealDB
- `POST /pipeline/embed` — generate embedding dari `clean_*` → simpan ke SurrealDB vector index
- `POST /pipeline/run-all` — jalankan ketiga step sekaligus (untuk trigger manual)

**SurrealDB (Port 8001)**
Menjadi **single source of truth** untuk seluruh AI Layer dengan dua peran:
- **Clean Data Store** — tabel `clean_*` menyimpan data operasional terstruktur untuk structured query dan agregasi
- **Vector Store** — vector index HNSW per domain menyimpan embedding untuk semantic search RAG

Dipilih karena multi-model (document + relational + vector) sehingga menggantikan kebutuhan ChromaDB sebagai database terpisah.

---

## Communication Patterns

```
React ──────── HTTP/REST ────────► Nginx ──► FastAPI
React ──────── iframe embed ─────► Metabase ──► PostgreSQL / SurrealDB (direct)

FastAPI ─────── HTTP/REST ────────► MCP Server
MCP Server ──── httpx ────────────► SurrealDB (structured query)
MCP Server ──── httpx ────────────► SurrealDB (vector similarity search)
MCP Server ──── LangChain LCEL ───► Ollama (qwen3.5:2b)

SIMRS Simulator ── SQLAlchemy ────► PostgreSQL (setiap 10 detik)

n8n ────────────── HTTP POST ──────► Pipeline Service (setiap 1 menit)
Pipeline Service ─ SQLAlchemy ────► PostgreSQL (read raw_*, write refined_*)
Pipeline Service ─ Pandas ─────────► Data Refinement
Pipeline Service ─ httpx ──────────► SurrealDB (write clean_* + vector index)
```

Semua komunikasi antar service berjalan di dalam Docker network internal. Hanya Nginx (8080), n8n (5678), dan Metabase (3001) yang diekspos ke luar untuk keperluan akses pengguna.

---

## Design Decisions

| Keputusan | Alasan |
|---|---|
| Self-hosted semua service | Data RS bersifat sensitif, tidak boleh keluar ke cloud publik |
| qwen3.5:2b sebagai LLM generasi | Model ringan (2B parameter) yang cukup untuk ringkasan analitik; berjalan lokal, data tidak keluar jaringan |
| nomic-embed-text sebagai embedding | Model khusus embedding (768 dim) via Ollama — lebih efisien dan akurat dibanding memakai model generatif untuk embedding |
| SurrealDB sebagai clean data + vector store | Multi-model (relational + vector HNSW) — menggantikan kebutuhan ChromaDB terpisah, satu service lebih sedikit |
| MCP Server sebagai mediator | Sentralisasi logika structured query + vector search + LLM generation; backend tetap thin REST layer |
| SIMRS Simulator sebagai service tersendiri | Data mengalir real-time setiap 10 detik, terpisah dari pipeline refinement |
| n8n menggantikan Airflow | Pipeline linear tanpa dependensi kompleks — Airflow overkill; n8n lebih ringan, built-in notifikasi |
| Pipeline Service sebagai HTTP service | n8n tidak bisa eksekusi Python langsung; memisahkan logika Pandas ke service tersendiri yang bisa dipanggil via HTTP |
| Metabase embedded di React | Metabase unggul untuk reporting, React untuk komponen AI-driven |
| Human-in-the-Loop | Seluruh output AI bersifat advisory, validasi tetap di tangan pengguna |
| RAG bukan fine-tuning | Data operasional RS berubah periodik, RAG lebih adaptif tanpa perlu retrain model |

---

## Human-in-the-Loop Architecture

```
  qwen3.5:2b Output (Analytical Summary)
            │
            ▼
    ┌───────────────┐
    │ Dashboard UI  │  ← Pengguna melihat insight
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │   Validation  │  ← Manajemen RS memvalidasi
    └───────┬───────┘
            │
      ┌─────┴──────┐
      │            │
    Valid        Tidak Valid
      │            │
      ▼            ▼
  Digunakan    Kembali ke
  sebagai      MCP Server
  referensi    (refinement)
```

Tidak ada output AI yang langsung digunakan sebagai keputusan operasional tanpa melalui validasi pengguna terlebih dahulu.
