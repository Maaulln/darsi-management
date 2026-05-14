# DARSI Management - Discovery Analysis
**Status:** In Progress - THOROUGH Architecture Analysis
**Workspace:** /Users/maaullntech/Documents/Project/Darsi/Program/Darsi (empty)

## Arsitektur Target (Full Stack)
- **Data Ingestion:** SIMRS (dummy) → PostgreSQL
- **Processing:** Pandas + Airflow orchestration
- **NoSQL/Graph:** SurrealDB (knowledge base)
- **Custom Integration:** MCP Server
- **AI/RAG:** LangChain/LlamaIndex + Ollama Qwen3.5:2b
- **Vector DB:** ChromaDB (dev) → Qdrant (prod)
- **API:** FastAPI
- **Frontend:** React + Metabase embedded
- **Infra:** Docker Compose + Nginx

## Key Decision Points
1. LangChain vs LlamaIndex (impact on RAG architecture)
2. ChromaDB → Qdrant migration path (timing & strategy)
3. SurrealDB role (metadata/knowledge vs document storage)
4. MCP server scope (data integration vs AI coordination)
5. Airflow necessity for MVP (vs simple scheduler)

## Analysis Focus Areas
- Safe implementation order
- MVP-critical components per phase
- Cross-dependencies & blockers
- Verification strategy per phase
- Monorepo structure
- Tech decisions to lock early
