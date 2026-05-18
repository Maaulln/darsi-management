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
║   │  8 domain    │   │ HTTP trigger│─►│ POST /sync   │─►│  + Vector    │  ║
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
Melakukan structured query ke SurrealDB (`SELECT ... GROUP BY ...`) untuk mengambil data agregat operasional per domain — pasien, okupansi, biaya, utilitas, dll. Hasil query diformat menjadi konteks teks untuk RAG.

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
Menyimpan data mentah SIMRS dalam skema relasional (`raw_*` tables, 8 domain). Data terus-menerus diisi oleh SIMRS Simulator setiap 10 detik.

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
