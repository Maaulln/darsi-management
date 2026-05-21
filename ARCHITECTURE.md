# DARSI Management — Architecture

## Overview

DARSI Management menggunakan arsitektur **Layered Microservices** yang berjalan di atas private cloud (Docker). Setiap layer memiliki tanggung jawab yang terisolasi dan berkomunikasi melalui interface yang terdefinisi dengan baik. Pendekatan ini memastikan setiap komponen dapat dikembangkan, diuji, dan diganti secara independen.

Pattern utama yang digunakan:

- **Layered Architecture** — setiap layer hanya berkomunikasi dengan layer yang berdekatan
- **RAG Pattern** — Retrieval-Augmented Generation via SurrealDB HNSW vector search + BM25 full-text + RRF fusion + cross-encoder rerank untuk grounding output LLM dengan data operasional
- **MCP Pattern** — Model Context Protocol sebagai mediator antara data layer dan AI layer
- **Unified Data Store** — SurrealDB menggabungkan clean structured data, vector store, dan BM25 index dalam satu service
- **Fully Async I/O** — seluruh stack backend (FastAPI + MCPClient + MCP Server) menggunakan `async/await` dengan `httpx.AsyncClient` — tidak ada blocking call di event loop
- **Multi-Layer Cache** — tiga level TTL cache (LLM response, vector retrieval, BM25 retrieval) meminimalkan latensi pada query berulang
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
              │ HTTP (1 batch request per dashboard load)
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
│  │  FastAPI (fully async) — thin REST layer                     │   │
│  │  MCPClient: lazy singleton httpx.AsyncClient                 │   │
│  │  Endpoints: /api/analytics /api/chat /api/rag /api/summary   │   │
│  │             /api/data /api/settings /health                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────┬────────────────────────────────────────────────────────┘
              │ HTTP (async, shared client)
┌─────────────▼────────────────────────────────────────────────────────┐
│  AI TIER                                                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  [mcp-server]  Port 8100                                     │   │
│  │  Data Connector → Context Manager → Optimised LLM Pipeline   │   │
│  │  Shared httpx.AsyncClient + multi-layer in-memory cache      │   │
│  └──────────┬───────────────────────────┬──────────────────────┘   │
│             │ httpx (shared client)      │ LangChain LCEL (ainvoke)  │
│  ┌──────────▼───────────┐   ┌───────────▼──────────────────────┐   │
│  │  [surrealdb] Port 8001│   │  [ollama]  Port 11434            │   │
│  │  clean_* structured  │   │  qwen3.5:2b  — text generation   │   │
│  │  + HNSW vector index │   │  nomic-embed-text — embedding    │   │
│  │  + BM25 full-text    │   │                                  │   │
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
│                              │         vector + BM25 (Ollama)     │  │
│                              └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Microservice Catalog

| Service | Image / Base | Port | Tier | Tanggung Jawab Tunggal |
|---|---|---|---|---|
| `nginx` | nginx:1.27-alpine | 8080 | Gateway | Route traffic; single entry point |
| `frontend` | node → nginx (multi-stage) | — | Presentation | React SPA: KPI dashboard, chat AI, summary, settings |
| `metabase` | metabase/metabase | 3001 | Presentation | BI reporting via direct DB query |
| `backend` | python:3.11 | 8000 | Application | Async REST API — proxy ke MCP Server via shared httpx.AsyncClient |
| `mcp-server` | python:3.11 | 8100 | AI | RAG pipeline: retrieval + context assembly + optimised LLM call |
| `ollama` | ollama/ollama | 11434 | AI | Local LLM inference (qwen3.5:2b + nomic-embed-text) |
| `surrealdb` | surrealdb/surrealdb | 8001 | Data | Clean data store (`clean_*`) + HNSW vector + BM25 full-text |
| `pipeline-service` | python:3.11 | 8200 | Pipeline | Pandas ETL: raw → refined → clean + embed |
| `n8n` | n8nio/n8n | 5678 | Pipeline | Cron orchestrator — HTTP trigger pipeline-service |
| `postgres` | postgres:16 | 5432 | Data | Raw SIMRS data store (`raw_*`, 13 domain) + settings persistence |
| `simrs-simulator` | python:3.11 | — | Data | Real-time data generator ke PostgreSQL |

### Inter-Service Communication Matrix

| From | To | Protokol | Frekuensi | Keterangan |
|---|---|---|---|---|
| React | Nginx | HTTP REST | Per user action | Semua request via single entry point |
| Nginx | Backend | HTTP proxy | Per user action | Route `/api/*` |
| Nginx | Frontend | Static serve | Per page load | SPA files |
| Backend | MCP Server | HTTP REST (async) | Per user action | Delegasi semua logika AI; shared httpx.AsyncClient |
| MCP Server | SurrealDB | httpx (shared client) | Per AI request | Structured query + HNSW vector search + BM25 |
| MCP Server | Ollama | LangChain LCEL (ainvoke) | Per AI request | Text generation (qwen3.5:2b) async |
| Pipeline Service | Ollama | HTTP (Ollama API) | Setiap 1 menit | Embedding (nomic-embed-text) |
| Pipeline Service | SurrealDB | httpx | Setiap 1 menit | Write `clean_*` + vector index + BM25 |
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
║   │    (1 batch request,    │   │  - Facility Usage Report │    ║
║   │     useMemo charts)     │   │                          │    ║
║   │  - AI Summary Display   │   │                          │    ║
║   │  - Settings / Superadmin│   │                          │    ║
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
║              │   (fully async)      │                          ║
║              │                      │                          ║
║              │  - GET /api/analytics/dashboard (batch: 6 metrics║
║              │        di asyncio.gather, 1 response)           ║
║              │  - GET /api/analytics/{metric}                  ║
║              │  - POST /api/chat                               ║
║              │  - POST /api/rag/query                          ║
║              │  - GET /api/summary/*                           ║
║              │  - GET/POST /api/settings/*                     ║
║              │  - GET /health                                  ║
║              └──────────┬───────────┘                          ║
╚═════════════════════════│═══════════════════════════════════════╝
                          │ HTTP (async, shared httpx.AsyncClient)
╔═════════════════════════▼═══════════════════════════════════════╗
║                        AI LAYER                                 ║
║                                                                 ║
║   ┌──────────────────────────────────────────────────────────┐  ║
║   │                    MCP Server (Port 8100)                │  ║
║   │                                                          │  ║
║   │   Fungsi 1 — Data Connector                              │  ║
║   │   SurrealDB ──► math::sum() GROUP BY ──► Aggregate CTX  │  ║
║   │   (3 parallel queries via asyncio.gather)                │  ║
║   │                                                          │  ║
║   │   Fungsi 2 — Context Manager (Optimised RAG Pipeline)    │  ║
║   │                                                          │  ║
║   │   ┌─ Parallel Embedding ─────────────────────────────┐   │  ║
║   │   │  asyncio.create_task(HyDE embed)                 │   │  ║
║   │   │  asyncio.create_task(direct embed)               │   │  ║
║   │   │  wait_for(hyde, timeout=3s) or fallback direct   │   │  ║
║   │   └──────────────────────────────────────────────────┘   │  ║
║   │                                                          │  ║
║   │   ┌─ Multi-Domain Retrieval (asyncio.gather) ────────┐   │  ║
║   │   │  per domain: vec cache? → HNSW search            │   │  ║
║   │   │              bm25 cache? → BM25 search           │   │  ║
║   │   │              → RRF fusion                        │   │  ║
║   │   └──────────────────────────────────────────────────┘   │  ║
║   │                                                          │  ║
║   │   Batch Cross-Encoder Rerank (1 ce.predict() call)       │  ║
║   │   Context Assembly + Truncation (≤6000 chars)            │  ║
║   │                                                          │  ║
║   │   Fungsi 3 — Prompt Engineering (~80 token prefix)       │  ║
║   │   context + query → PromptTemplate → Final Prompt        │  ║
║   │                                                          │  ║
║   │   Fungsi 4 — LLM Generation + Self-RAG                   │  ║
║   │   chain.ainvoke() → LLM Response Cache check             │  ║
║   │   if insufficient → retry top-5 ranked domains           │  ║
║   │   (timeout 60s per retry, tidak semua 13 domain)         │  ║
║   └───────────┬──────────────────────────┬───────────────────┘  ║
║               │                          │                       ║
║   ┌───────────▼──────────┐  ┌────────────▼──────────────────┐   ║
║   │     LangChain        │  │   Ollama + qwen3.5:2b         │   ║
║   │   RAG Pipeline       │  │     Port 11434                │   ║
║   │   (LCEL Chain)       │  │   Local LLM (ainvoke async)   │   ║
║   └──────────────────────┘  └───────────────────────────────┘   ║
╚═════════════════════════════════════════════════════════════════╝

╔═════════════════════════════════════════════════════════════════╗
║                       DATA LAYER                                ║
║                                                                 ║
║   ┌──────────────┐   ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ║
║   │  PostgreSQL  │   │     n8n     │  │Pipeline Svc  │  │  SurrealDB  │  ║
║   │  Port 5432   │   │ Port 5678   │  │  Port 8200   │  │  Port 8001  │  ║
║   │              │   │             │  │              │  │             │  ║
║   │  raw_* tables│   │ Cron 1 mnt  │  │ POST /refine │  │  clean_*    │  ║
║   │  13 domain   │   │ HTTP trigger│─►│ POST /sync   │─►│  + HNSW     │  ║
║   │  + settings  │   │             │  │ POST /embed  │  │  + BM25     │  ║
║   └──────┬───────┘   └─────────────┘  └──────────────┘  └─────────────┘  ║
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

Dashboard menampilkan **8 KPI card** (pasien aktif, BOR, total biaya, listrik, air, lembur, cost-to-revenue ratio, overtime ratio) dan **5 chart** (biaya per kategori, okupansi bed per unit, utilitas per unit, cost-to-revenue per unit, jam kerja vs lembur per unit). Seluruh data dashboard diambil dalam **satu HTTP request** ke endpoint `/api/analytics/dashboard` yang mengembalikan 6 analytics sekaligus. Seluruh komputasi chart data di-memoize via `useMemo` untuk menghindari recompute berulang saat re-render.

Halaman Settings (Superadmin) menyediakan konfigurasi dinamis API dan sistem — perubahan disimpan ke PostgreSQL dan dapat diterapkan tanpa restart layanan.

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

---

### 3. Application Layer

**FastAPI Backend (Port 8000)**

Menggunakan **Clean Architecture** dengan arsitektur fully async:

```
backend/app/
├── api/
│   ├── analytics.py  # GET /api/analytics/dashboard (batch 6-in-1)
│   │                 # GET /api/analytics/{overview,cost-by-category,
│   │                 #      occupancy-by-unit,utility-trend,efficiency,staffing}
│   ├── chat.py       # POST /api/chat
│   ├── rag.py        # POST /api/rag/query
│   ├── summary.py    # GET /api/summary/*
│   ├── data.py       # GET /api/data/*
│   ├── settings.py   # GET/POST /api/settings/* (dynamic API management)
│   └── health.py     # GET /health, /api/readiness
├── services/
│   ├── mcp_client.py # Async HTTP client — lazy singleton httpx.AsyncClient
│   └── rag_service.py
└── core/
    └── config.py     # Settings: mcp_server_url, cors_origins (dari env)
```

**CORS** dikonfigurasi dari environment variable `CORS_ORIGINS` (CSV) bukan wildcard — menghindari kebocoran data lintas origin.

**MCPClient** menggunakan lazy singleton `httpx.AsyncClient` yang dipakai ulang di seluruh request, menghindari overhead membuka koneksi baru per request:

```python
class MCPClient:
    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
```

**Batch Dashboard Endpoint** menjalankan 6 analytics secara paralel via `asyncio.gather` dan mengembalikan satu response — mengurangi round-trip dari 6 menjadi 1:

```python
@router.get("/api/analytics/dashboard")
async def get_dashboard(date_from=None, date_to=None):
    results = await asyncio.gather(
        mcp_client.fetch_analytics("overview", params),
        mcp_client.fetch_analytics("cost-by-category", params),
        mcp_client.fetch_analytics("occupancy-by-unit", params),
        mcp_client.fetch_analytics("utility-trend", params),
        mcp_client.fetch_analytics("efficiency", params),
        mcp_client.fetch_analytics("staffing", params),
        return_exceptions=True,
    )
    # error per-key, bukan raise — partial data tetap dikirim ke frontend
```

FastAPI tidak berkomunikasi langsung ke database — semua akses data dikelola oleh MCP Server.

---

### 4. AI Layer

Layer paling kritis dalam arsitektur DARSI. MCP Server menjalankan empat fungsi dalam satu service.

**MCP Server (Port 8100)**

#### Fungsi 1 — Data Connector

Mengambil data agregat dari SurrealDB menggunakan `math::sum() GROUP BY` langsung di sisi database — tidak ada aggregasi Python di sisi aplikasi. Tiga query paralel via `asyncio.gather` untuk summary resource:

```sql
SELECT unit_code, math::sum(kwh_total) AS kwh, math::sum(biaya_listrik) AS biaya
FROM clean_meter_listrik
GROUP BY unit_code
```

Endpoint analytics yang tersedia di MCP Server:

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

#### Fungsi 2 — Context Manager (Optimised RAG Pipeline)

```
Query Pengguna
      │
      ├─ [Intent Detection] → matched_domains (keyword overlap scoring)
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Parallel Embedding Phase (asyncio.create_task × 2)     │
│                                                         │
│  Task A: HyDE Embedding                                 │
│   generate_hypothetical_doc(query) → LLM draft text     │
│   → nomic-embed-text → float[768]                       │
│                                                         │
│  Task B: Direct Embedding                               │
│   query → nomic-embed-text → float[768]                 │
│                                                         │
│  Strategy: await direct_task (fast path)                │
│  Then: wait_for(shield(hyde_task), timeout=3s)          │
│  Use HyDE if ready; fallback to direct otherwise        │
└─────────────────────┬───────────────────────────────────┘
                      │ query_embedding (768-dim)
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Multi-Domain Retrieval (asyncio.gather per domain)     │
│                                                         │
│  For each matched domain:                               │
│    vec_key  = "vec:{domain}:{md5(embedding)[:10]}"      │
│    bm25_key = "bm25:{domain}:{md5(keywords)[:10]}"      │
│                                                         │
│    ├─ Cache HIT  → _noop(cached_value)                  │
│    └─ Cache MISS → SurrealDB query                      │
│                                                         │
│    vector_docs  ← HNSW cosine similarity search         │
│    bm25_docs    ← BM25 full-text search (expanded kws)  │
│    fused_docs   ← RRF(vector_docs, bm25_docs)           │
│                                                         │
│    Cache set: vec_key → vector_docs (TTL 120s)          │
│    Cache set: bm25_key → bm25_docs  (TTL 120s)          │
└─────────────────────┬───────────────────────────────────┘
                      │ all domain fused_docs
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Batch Cross-Encoder Rerank                             │
│                                                         │
│  Flatten all domain docs → single list                  │
│  pairs = [(query, doc) for doc in all_docs]             │
│  scores = ce.predict(pairs)   ← ONE call for all        │
│  Group back per domain, keep top N                      │
└─────────────────────┬───────────────────────────────────┘
                      │ reranked docs per domain
                      ▼
           Context Assembly (join per domain)
           _truncate_context(ctx, limit=6000 chars)
```

**Reciprocal Rank Fusion (RRF):**

```
score(doc) = Σ 1 / (k + rank(doc))   k=60 (default)
```

Menggabungkan hasil vector search dan BM25 tanpa perlu threshold manual.

**BM25 Keyword Expansion:**

Semua matched domain berkontribusi keyword (bukan hanya 3 domain pertama — bug lama yang sudah diperbaiki). Total keyword di-cap di 12 kata.

#### Fungsi 3 — Prompt Engineering

Template ringkas (~80 token prefix) yang terarah untuk model 2B:

```
Anda adalah analis data RS DARSI Surabaya.

DATA OPERASIONAL:
{context}

PERTANYAAN: {query}

Instruksi: Jawab singkat dan spesifik dalam Bahasa Indonesia.
Gunakan HANYA data di atas. Sebutkan angka/fakta kunci.
Jika data tidak cukup, nyatakan secara eksplisit.

JAWABAN:
```

Dibandingkan template sebelumnya (~180 token) yang memaksa 3-step reasoning — template baru lebih cocok untuk model 2B yang cenderung confuse pada instruksi panjang.

#### Fungsi 4 — LLM Generation + Self-RAG + Cache

```
Final Prompt
      ↓
llm_cache_key = "llm:{md5(query)[:10]}"
cache hit? → return cached response immediately (~0ms)
      ↓ cache miss
chain.ainvoke({"context": ctx, "query": query})   ← async, timeout 120s
      ↓
answer = StrOutputParser output
      ↓
[Self-RAG Check]
  if answer berisi "tidak ada data" / "tidak tersedia" / confidence rendah:
    retry_domains = matched_domains + _rank_retry_domains(query, matched_domains)
    # _rank_retry_domains: score unchecked domains by keyword overlap, top-5 only
    # BUKAN semua 13 domain — mengurangi retry dari 60s → 20-25s
    rebuild context → reinvoke LLM (asyncio.wait_for timeout=60s)
      ↓
_cache_set(llm_cache_key, response, TTL=60s)
return GenerateResponse
```

**Shared SurrealDB HTTP Client:**

Modul-level `_SURREAL_HTTP: httpx.AsyncClient` dibuat saat startup dan dipakai ulang seluruh request. Endpoint dan header di-precompute sebagai konstanta modul.

**Cache Eviction Background Task:**

```python
async def _cache_evict_loop():
    while True:
        await asyncio.sleep(300)  # setiap 5 menit
        expired = [k for k, (_, ts) in _CACHE.items() if (now - ts) > 600]
        for k in expired: _CACHE.pop(k, None)
```

---

### 5. Data Layer

**PostgreSQL (Port 5432)**

Menyimpan dua jenis data:
1. **Raw SIMRS** — `raw_*` tables (13 domain), diisi terus-menerus oleh SIMRS Simulator setiap 10 detik
2. **Settings Persistence** — konfigurasi sistem dan API management dari Superadmin dashboard

Schema DDL tersedia di `pipeline/data/sql/raw_operational_schema.sql` (1x eksekusi, mencakup DDL + seed tarif utilitas).

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

Service Python yang berjalan terus-menerus (`restart: unless-stopped`). Setiap 10 detik menginsert 1–100 record acak per domain ke tabel `raw_*` PostgreSQL.

**n8n (Port 5678)**

Mengorkestrasikan pipeline via HTTP trigger setiap 1 menit. Workflow linear:
1. Cron trigger (setiap 1 menit)
2. HTTP POST `pipeline-service/pipeline/refine`
3. HTTP POST `pipeline-service/pipeline/sync`
4. HTTP POST `pipeline-service/pipeline/embed`

Workflow tersedia di `n8n/darsi_pipeline_workflow.json` — siap import via UI n8n.

**Pipeline Service (Port 8200)**

FastAPI tipis yang mengekspos logika Pandas refinement sebagai HTTP endpoint:

- `POST /pipeline/refine` — baca `raw_*` PostgreSQL → Pandas cleaning → tulis `refined_*`
- `POST /pipeline/sync` — baca `refined_*` → tulis `clean_*` SurrealDB
- `POST /pipeline/embed` — generate embedding (nomic-embed-text via Ollama) → simpan ke SurrealDB vector + BM25 index
- `POST /pipeline/run-all` — jalankan ketiga step sekaligus (trigger manual)

**SurrealDB (Port 8001)**

Single source of truth untuk seluruh AI Layer dengan tiga peran:
- **Clean Data Store** — tabel `clean_*` untuk structured query dan agregasi (`math::sum() GROUP BY`)
- **Vector Store** — HNSW vector index per domain (`vector::similarity::cosine`)
- **Full-Text Store** — BM25 full-text index per domain (`search::score(1)`)

Dipilih karena multi-model (document + relational + vector + full-text) — menggantikan kebutuhan ChromaDB sebagai database terpisah.

---

## Communication Patterns

```
React ──────── HTTP/REST ────────► Nginx ──► FastAPI
React ──────── iframe embed ─────► Metabase ──► PostgreSQL (direct)

FastAPI ─────── HTTP/REST (async) ─► MCP Server (shared httpx.AsyncClient)
MCP Server ──── httpx (shared) ───► SurrealDB (structured query)
MCP Server ──── httpx (shared) ───► SurrealDB (HNSW vector + BM25 search)
MCP Server ──── LangChain LCEL ───► Ollama (qwen3.5:2b, ainvoke)

SIMRS Simulator ── SQLAlchemy ────► PostgreSQL (setiap 10 detik)

n8n ────────────── HTTP POST ──────► Pipeline Service (setiap 1 menit)
Pipeline Service ─ SQLAlchemy ────► PostgreSQL (read raw_*, write refined_*)
Pipeline Service ─ Pandas ─────────► Data Refinement
Pipeline Service ─ httpx ──────────► SurrealDB (write clean_* + vector + BM25)
```

Semua komunikasi antar service berjalan di dalam Docker network internal. Hanya Nginx (8080), n8n (5678), dan Metabase (3001) yang diekspos ke luar.

---

## Multi-Layer Cache Architecture

Cache diimplementasikan sebagai in-memory dict `_CACHE: dict[str, tuple[Any, float]]` di dalam proses MCP Server. Tidak memerlukan Redis karena volume traffic satu instance.

| Layer | Key Pattern | TTL | Scope | Penghematan |
|---|---|---|---|---|
| LLM Response | `llm:{md5(query)[:10]}` | 60 detik | Seluruh pipeline | 30–120s → ~0ms (query sama) |
| Vector Results | `vec:{domain}:{md5(embed)[:10]}` | 120 detik | Per domain per query | 500ms–3s per domain |
| BM25 Results | `bm25:{domain}:{md5(kws)[:10]}` | 120 detik | Per domain per keyword set | 200ms–1s per domain |

Background task `_cache_evict_loop()` membersihkan entri yang berumur >600 detik setiap 5 menit.

Perkiraan latensi setelah optimasi:

| Skenario | Sebelum | Sesudah |
|---|---|---|
| Query sama (< 60s) | 30–120s | ~0ms (LLM cache hit) |
| Query baru, retrieval cache warm | 35–130s | 5–15s |
| Query baru, cold cache | 35–130s | 15–25s |
| Self-RAG retry triggered | +60–120s tambahan | +20–40s tambahan |

---

## Design Decisions

| Keputusan | Alasan |
|---|---|
| Self-hosted semua service | Data RS bersifat sensitif, tidak boleh keluar ke cloud publik |
| qwen3.5:2b sebagai LLM generasi | Model ringan (2B parameter) yang cukup untuk ringkasan analitik; berjalan lokal |
| nomic-embed-text sebagai embedding | Model khusus embedding (768 dim) via Ollama — lebih efisien dan akurat |
| SurrealDB sebagai clean data + vector + BM25 | Multi-model — menggantikan kebutuhan ChromaDB dan Elasticsearch terpisah |
| MCP Server sebagai mediator | Sentralisasi RAG pipeline; backend tetap thin REST layer |
| Fully async I/O | Menghindari blocking event loop — critical untuk throughput tinggi dengan model LLM yang lambat |
| Shared httpx.AsyncClient | Menghindari overhead pembuatan koneksi baru per request |
| Batch dashboard endpoint | Satu round-trip menggantikan 6 — mengurangi latensi dashboard load signifikan |
| Parallel HyDE + direct embedding | Mengurangi bottleneck embedding dari 4–11s sequential menjadi 3–6s paralel |
| Batch cross-encoder rerank | Satu ce.predict() call untuk semua domain — lebih efisien dari N serial calls |
| In-memory TTL cache | Cukup untuk satu instance; tanpa overhead Redis untuk prototype ini |
| CORS dari environment variable | Hindari wildcard `*` pada credentials; konfigurasi per environment |
| Smarter Self-RAG (top-5 ranked) | Retry ke 13 domain memakan 60–120s; scoring keyword memilih 5 domain paling relevan |
| Context truncation (6000 chars) | Model 2B optimal dengan context ≤1500 token — melebihi ini menurunkan akurasi |
| Prompt template ringkas (~80 token) | Model kecil lebih baik dengan instruksi singkat dan tegas |
| SIMRS Simulator sebagai service tersendiri | Data mengalir real-time setiap 10 detik, terpisah dari pipeline refinement |
| n8n menggantikan Airflow | Pipeline linear tanpa dependensi kompleks — n8n lebih ringan, built-in notifikasi |
| Pipeline Service sebagai HTTP service | n8n tidak bisa eksekusi Python langsung; memisahkan logika Pandas ke service HTTP |
| Metabase embedded di React | Metabase unggul untuk reporting, React untuk komponen AI-driven |
| Human-in-the-Loop | Seluruh output AI bersifat advisory, validasi tetap di tangan pengguna |
| RAG bukan fine-tuning | Data operasional RS berubah periodik, RAG lebih adaptif tanpa perlu retrain model |

---

## Alur Metodologi Penelitian (Tahap 1–4)

### Tahap 1 — Integrasi dan Persiapan Data Operasional

```
Metadata Operasional SIMRS (PostgreSQL raw_*)
    ↓
[Pipeline Service] Proses Data Refinement (Pandas)
    ↓
[Pipeline Service] Sync → SurrealDB clean_*
    ↓
[Pipeline Service] Embed → SurrealDB vector HNSW + BM25 index
    ↓
Data Operasional Terstruktur (SurrealDB clean_* + vector + BM25)
```

Orkestrasi oleh n8n (cron 1 menit): `/refine` → `/sync` → `/embed`.

---

### Tahap 2 — Pengembangan Modul Analitik Berbasis AI

Alur yang benar di dalam **MCP Server** (setelah optimasi):

```
Query Pengguna
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│                    MCP Server (Port 8100)                     │
│                                                               │
│  Fungsi 1 — Data Connector                                    │
│  SurrealDB clean_* → math::sum() GROUP BY → Aggregate Context │
│  (3 parallel queries via asyncio.gather)                      │
│                                        │                      │
│  Fungsi 2 — Context Manager (Arsitektur RAG Teroptimasi)     │
│  Query → Parallel Embed (HyDE + Direct, asyncio.create_task)  │
│        → Multi-domain HNSW + BM25 (asyncio.gather, cached)   │
│        → RRF Fusion per domain                                │
│        → Batch Cross-Encoder Rerank (1 ce.predict() call)     │
│        → Context Assembly + Truncation (≤6000 chars)          │
│                                        │                      │
│                               ─────────┘                      │
│                               ↓                               │
│  Fungsi 3 — Strategi Prompt Engineering (~80 token)           │
│  context (structured + semantic) + query                      │
│        → PromptTemplate.format(context=..., query=...)        │
│        → Final Prompt                                         │
│                               ↓                               │
│  Fungsi 4 — LLM Generation + Self-RAG + Cache                │
│  LLM Cache check → chain.ainvoke() → StrOutputParser          │
│  Self-RAG: if insufficient → retry top-5 ranked domains       │
│  Cache set: llm_cache_key (TTL 60s)                           │
│                               ↓                               │
│                         Jawaban / Insight                     │
└───────────────────────────────────────────────────────────────┘
```

**Posisi komponen dalam pipeline:**

| Komponen | Posisi dalam Pipeline | Hubungan |
|---|---|---|
| Data Connector | Pertama — structured aggregate | Output → masuk ke context builder |
| Arsitektur RAG | Kedua — semantic retrieval | Output (context) → masuk ke Prompt |
| Strategi Prompt Engineering | Ketiga — setelah RAG | Merakit context + query → final prompt |
| LLM Generation | Keempat — setelah Prompt | Final Prompt → model → answer |
| Self-RAG | Post-generation check | Trigger retry jika jawaban tidak cukup |

---

### Tahap 3 — Pembangunan Sistem Analitik & Visualisasi Dashboard

```
Hasil Analisis AI (MCP Server output)
    ↓
FastAPI Backend (async) → React Frontend
    ↓
Dashboard Interaktif (8 KPI card + 5 chart, 1 batch request)
    + Metabase embedded (reporting BI)
    ↓
Insight Operasional
    ↓
[Human-in-the-Loop Validation]
    ├── Valid   → Digunakan sebagai referensi manajemen
    └── Tidak Valid → Refinement query ke MCP Server
```

---

### Tahap 4 — Validasi Sistem dan Evaluasi Pengguna

```
UAT bersama Manajemen RS
    ↓
Evaluasi dan Penyempurnaan Sistem
    ↓
Luaran:
  - Prototipe (sistem ini)
  - Paten Sederhana
  - Publikasi Ilmiah
  - Materi Ajar
    ↓
Prototype Sistem Analitik Manajerial Berbasis AI untuk DARSI Management
```

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
