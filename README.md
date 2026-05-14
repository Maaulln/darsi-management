# DARSI Management

Prototipe sistem analitik operasional rumah sakit berbasis Generative AI + RAG untuk RSI Surabaya.

## Arsitektur

```
┌──────────────────────────────────────────────────────────────┐
│ Frontend (Nginx :8080)                                       │
│   └─ Dashboard, Analytics, Chat RAG, Data Explorer, Metabase │
├──────────────────────────────────────────────────────────────┤
│ Backend FastAPI (:8000) — /api/health, /api/chat, /api/rag,  │
│   /api/data, /api/summary, /api/analytics, /api/readiness    │
├──────────────────────────────────────────────────────────────┤
│ MCP Server (:8100) — /mcp/context, /mcp/domains, /mcp/data   │
├──────────────────────────────────────────────────────────────┤
│ PostgreSQL │ SurrealDB │ ChromaDB │ Ollama (qwen3.5:2b) │     │
│ raw/refined│ clean     │ vector   │ LLM inference        │     │
├──────────────────────────────────────────────────────────────┤
│ Airflow (:8888) — orkestrasi pipeline harian                 │
│ Metabase (:3001) — dashboard BI                              │
└──────────────────────────────────────────────────────────────┘
```

## Fase Implementasi (flow.md)

| Fase | Komponen | Status |
|------|---------|--------|
| 1 — Foundation Data | Postgres schema, Pandas refinement (IQR + quality metrics), Airflow DAG, sync → SurrealDB | ✅ |
| 2 — AI Layer | MCP server intent-detection, ChromaDB embedding, RAG pipeline + Ollama | ✅ |
| 3 — Backend & Konektor | FastAPI: analytics, RAG/chat-with-RAG, readiness, MCP client | ✅ |
| 4 — Frontend & Dashboard | Single-page dashboard (Chart.js), tabs + chat + Metabase embed | ✅ |
| 5 — Validasi | UAT, SUS, publikasi | ⏳ |

## Layout Repo

```
backend/         FastAPI app (routes, RAG/MCP client, SurrealDB connector)
mcp-server/      MCP server (ChromaDB + SurrealDB context aggregator)
data/
  sql/           Postgres schema (auto-loaded via init-scripts)
  ingestion/     load, refine (IQR), surrealdb sync, chromadb embed
  sample_simrs/  CSV dummy per domain
dags/            Airflow DAG `darsi_data_pipeline`
frontend/        Static SPA (Chart.js dashboard + RAG chat)
nginx/           Reverse proxy → backend + MCP + Metabase + SPA
docker-compose.yml
```

## Cara menjalankan

Lihat [GETTING_STARTED.md](GETTING_STARTED.md) untuk panduan lengkap.

Ringkas:
```bash
cp .env.example .env
docker compose up --build -d
# Schema postgres auto-load dari ./data/sql.
docker exec -it darsi-ollama ollama pull qwen3.5:2b
# Generate + refinement + sync + embed via Airflow DAG `darsi_data_pipeline` (atau jalankan script manual).
```

Akses:
- Dashboard: http://localhost:8080
- API docs: http://localhost:8000/docs
- MCP server: http://localhost:8100/health
- Metabase: http://localhost:3001 atau via gateway http://localhost:8080/metabase/
- Airflow: http://localhost:8888 (admin/admin)
