# Build Guide: DARSI Management (WP1 & WP2)

This guide provides the necessary steps to build and run the DARSI Management website and its associated services, divided into Work Package 1 (Foundation) and Work Package 2 (Analytics/AI).

## Prerequisites
- **Docker Desktop**: Must be running.
- **Python 3.11+**: For local script execution.
- **Ollama**: For running LLM models (Qwen3.5:2b).

---

## WP1: Core Foundation (Backend & Data)

### 1. Infrastructure Setup
WP1 establishes the core database and backend.
```bash
docker compose up -d postgres backend nginx
```

### 2. Database Schema
The schema is defined in `data/sql/raw_operational_schema.sql`. It is automatically applied if the Postgres container is configured with initialization scripts, otherwise:
```bash
docker exec -i darsi-postgres psql -U darsi_user -d darsi < data/sql/raw_operational_schema.sql
```

### 3. Data Ingestion
Load the raw domain data into PostgreSQL:
```bash
pip install -r data/requirements.txt
python data/ingestion/load_all_raw_simrs_to_postgres.py
```

### 4. Verification
Check the backend health:
```bash
curl http://localhost:8000/health
# or via gateway
curl http://localhost:8080/api/health
```

---

## WP2: Analytics & AI Layer

### 1. AI & Knowledge Base Setup
WP2 integrates the AI components and NoSQL knowledge base.
```bash
docker compose up -d surrealdb chromadb ollama mcp-server
```

### 2. Model Preparation
Pull the required model in Ollama:
```bash
docker exec -it darsi-ollama ollama pull qwen3.5:2b
```

### 3. MCP Server Integration
The MCP (Model Context Protocol) server provides the context for RAG.
```bash
curl -X POST http://localhost:8100/mcp/context \
  -H "Content-Type: application/json" \
  -d '{"query":"Summary of bed occupancy"}'
```

### 4. Frontend Build (React)
The frontend is currently in the scaffold phase.
```bash
cd frontend
# (Future steps: npm install && npm run dev)
```

---

## Summary of Ports
- **Nginx Gateway**: `8080` (Primary access point)
- **FastAPI Backend**: `8000` (Routed via `/api/`)
- **MCP Server**: `8100` (Routed via `/mcp/`)
- **SurrealDB**: `8001`
- **Metabase**: `3001`
- **Ollama**: `11434`
