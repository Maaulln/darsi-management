# DARSI Management

Prototipe sistem analitik operasional rumah sakit berbasis Generative AI untuk RSI Surabaya.

## Cakupan Implementasi Saat Ini

- Fondasi monorepo untuk backend, pipeline data, frontend placeholder, dan konfigurasi infra.
- Backend FastAPI dengan endpoint awal:
  - `GET /health`
  - `GET /data/list`
  - `GET /data/{record_id}`
- Pipeline data dummy:
  - `data/ingestion/load_simrs_to_postgres.py`
  - `data/ingestion/refine_simrs_data.py`
- Infrastruktur container awal:
  - PostgreSQL
  - SurrealDB
  - ChromaDB
  - Ollama
  - FastAPI backend
  - MCP server (stub)
  - Metabase
  - Nginx

## Cara Menjalankan

Untuk panduan lengkap mulai dari instalasi hingga menjalankan program, silakan baca:
👉 **[PANDUAN GETTING STARTED](GETTING_STARTED.md)**

### Ringkasan Cepat:
```bash
docker compose up --build -d
docker exec -i darsi-postgres psql -U darsi_user -d darsi < data/sql/raw_operational_schema.sql
python data/ingestion/load_all_raw_simrs_to_postgres.py
```

## Catatan
- File konfigurasi default ada di `.env`.
- Frontend dapat diakses di `http://localhost:8080`.
- AI menggunakan model `qwen3.5:2b` melalui Ollama.
