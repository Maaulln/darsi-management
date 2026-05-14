# Panduan Menjalankan DARSI Management

Panduan ini menyusun perintah dari nol sampai dashboard aktif sesuai dengan flow di [flow.md](flow.md).

## 1. Prasyarat
- **Docker Desktop** (jalankan dulu)
- **Python 3.11+** (untuk eksekusi script manual di host, opsional)

## 2. Persiapan Awal
```bash
git clone <repo-url>
cd darsi_v3
cp .env.example .env
```
(`.env` default sudah cocok dengan compose.)

## 3. Jalankan Layanan
```bash
docker compose up --build -d
docker compose ps
```
Schema Postgres otomatis ter-load (init-scripts → `data/sql/raw_operational_schema.sql`).

## 4. Siapkan Model Ollama
```bash
docker exec -it darsi-ollama ollama pull qwen3.5:2b
```

## 5. Pipeline Data (Fase 1)
Dua opsi:

### Opsi A — Lewat Airflow (rekomendasi)
1. Buka http://localhost:8888 (login `admin/admin`).
2. Trigger DAG **`darsi_data_pipeline`**. Tasks:
   - `raw_ingestion` → generate 150 record/domain ke `raw_*`
   - `internal_refinement` → `raw_*` → `refined_*` (filter, trim, IQR cap)
   - `sync_to_surrealdb` → `refined_*` → `clean_*`
   - `embed_to_chromadb` → `refined_*` → ChromaDB collections

### Opsi B — Manual dari host
```bash
pip install -r data/requirements.txt
export POSTGRES_HOST=localhost
export SURREALDB_URL=http://localhost:8001
export CHROMA_HOST=localhost
export CHROMA_PORT=8002

python data/ingestion/generate_bulk_dummy_data.py
python data/ingestion/refine_postgres_internal.py
python data/ingestion/refine_raw_to_surrealdb.py --apply
python data/ingestion/embed_to_chromadb.py
```

## 6. Verifikasi
```bash
curl http://localhost:8080/api/health
curl http://localhost:8080/api/readiness
curl -X POST http://localhost:8080/mcp/context \
  -H "Content-Type: application/json" \
  -d '{"query":"okupansi ICU"}'
```

## 7. Akses Aplikasi

| Layanan | URL | Keterangan |
| :--- | :--- | :--- |
| Dashboard SPA | http://localhost:8080 | Tabs Dashboard/Analytics/Chat/Data/Metabase |
| API docs | http://localhost:8000/docs | Swagger FastAPI |
| MCP server | http://localhost:8100/health | Konektor RAG |
| Airflow | http://localhost:8888 | admin/admin |
| Metabase | http://localhost:3001 | Setup awal Metabase |

## 8. Troubleshooting
- **Schema tidak terload**: pastikan volume `postgres_data` fresh (`docker compose down -v` lalu `up`).
- **Ollama timeout pertama kali**: model baru di-load ke memori, sabar 30–60 detik.
- **ChromaDB query gagal**: pastikan tahap `embed_to_chromadb` sudah berhasil.
- **MCP context kosong**: cek SurrealDB sudah terisi `clean_*` (lihat task `sync_to_surrealdb`).
