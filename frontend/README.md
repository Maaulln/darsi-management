# Frontend DARSI

Single-page dashboard berbasis HTML/CSS/JS dengan Chart.js. Disajikan oleh Nginx (`/usr/share/nginx/html`) dari folder ini.

## Tabs
- **Dashboard** — KPI utama (BOR, listrik, air, biaya) + chart okupansi & distribusi biaya.
- **Analytics** — Tren konsumsi listrik/air per unit + perbandingan budget vs actual.
- **Chat AI** — Antarmuka RAG; toggle untuk men-disable konteks (mode Ollama-only).
- **Data Explorer** — Browse data clean per domain via SurrealDB.
- **Metabase BI** — iframe ke instance Metabase pada `/metabase/`.

## Endpoint yang dipakai
- `GET /api/readiness`
- `GET /api/analytics/overview`
- `GET /api/analytics/occupancy-by-unit`
- `GET /api/analytics/cost-by-category`
- `GET /api/analytics/utility-trend`
- `GET /api/data/domains`
- `GET /api/data/domain/{name}`
- `POST /api/chat`
