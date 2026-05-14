# DARSI Management - Complete Implementation Plan
## Project Plan untuk Tahap 1-2 Prototipe dengan Docker

**Status:** Planning Phase  
**Start Date:** [Insert Date]  
**Target Completion:** 8 weeks  
**Last Updated:** May 14, 2026

---

## 📑 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Phase Breakdown](#phase-breakdown)
4. [Detailed Weekly Timeline](#detailed-weekly-timeline)
5. [Deliverables Checklist](#deliverables-checklist)
6. [Docker Environment Setup](#docker-environment-setup)
7. [Development Workflow](#development-workflow)
8. [Testing & Validation](#testing--validation)
9. [Deployment & Handoff](#deployment--handoff)
10. [Risk Management](#risk-management)

---

## Project Overview

### Vision
Mengembangkan sistem **DARSI Management** - platform analytics operasional berbasis Generative AI untuk RSI Surabaya yang memungkinkan pengambilan keputusan berbasis data real-time dengan konteks operasional yang terstruktur.

### Scope - Tahap 1-2
- **WP 1:** Integrasi & persiapan metadata operasional dari SIMRS
- **WP 2:** Pengembangan modul analitik berbasis LLM + RAG

### Not in Scope (untuk tahap 3+)
- Dashboard visualization (WP 3)
- System validation & testing (WP 4)
- Production deployment (WP 5)

### Success Criteria
- ✅ Metadata operasional terintegrasi & terstruktur
- ✅ RAG system dapat menjawab queries operasional
- ✅ Prototype berjalan di local environment
- ✅ Ready untuk WP 3 (Dashboard)

---

## Architecture & Technology Stack

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DARSI Management                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend Layer (WP 3)                                      │
│  ├─ Dashboard (React/Vue)                                  │
│  └─ Visualization (Metabase)                               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  API Layer (nginx + Backend)                                │
│  ├─ REST API (FastAPI)                  Port: 8000         │
│  ├─ MCP Server (Claude Integration)     Port: 8100         │
│  └─ Nginx Reverse Proxy                 Port: 8080         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Core Services                                              │
│  ├─ PostgreSQL (Metadata & Data)        Port: 5432         │
│  ├─ SurrealDB (Graph/Relations)         Port: 8001         │
│  ├─ ChromaDB (Vector Store for RAG)     Port: 8002         │
│  └─ Ollama (LLM Inference)              Port: 11434        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Analytics & BI                                             │
│  └─ Metabase (Dashboarding)             Port: 3001         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack Decision Matrix

| Layer | Technology | Reason | Status |
|-------|-----------|--------|--------|
| **LLM** | Ollama + qwen3:2b | Local, privacy-safe, ~2GB, Indonesian-friendly | ✅ WP2 |
| **Vector DB** | ChromaDB | Lightweight, Python-friendly, RAG-optimized | ✅ WP2 |
| **Relational DB** | PostgreSQL 16 | Operational data, reliability | ✅ WP1 |
| **Graph DB** | SurrealDB | Metadata relationships | ⏳ Optional WP2 |
| **Backend API** | FastAPI | Async, modern, OpenAPI docs | ⏳ WP2 |
| **MCP Server** | Node.js/Python | Claude integration | ⏳ WP2 |
| **Reverse Proxy** | Nginx | Load balancing, security | ✅ WP2 |
| **Analytics** | Metabase | BI & dashboarding | ⏳ WP3 |
| **Orchestration** | Docker Compose | Local development, reproducibility | ✅ Now |

### Docker Services Overview

```yaml
Services (8 total):
├─ postgres       (Database)
├─ surrealdb      (Graph Database)
├─ chromadb       (Vector Database)
├─ ollama         (LLM Engine)
├─ backend        (FastAPI Application)
├─ mcp-server     (Claude Integration)
├─ metabase       (Analytics)
└─ nginx          (Reverse Proxy)

Volumes:
└─ postgres_data  (Data persistence)

Networks:
└─ darsi-network  (Service communication)
```

---

## Phase Breakdown

### Timeline Overview

```
Week 1-2: Setup & Infrastructure (30 hours)
├─ Docker environment setup
├─ Database initialization
├─ Vector store preparation
└─ Development environment validation

Week 3-4: WP1 - Data Pipeline (40 hours)
├─ Metadata identification
├─ Data integration
├─ Data refinement
└─ Vector preparation

Week 5-6: WP2 - RAG & Analytics (50 hours)
├─ Vector database implementation
├─ LLM integration
├─ RAG system development
└─ API endpoints

Week 7-8: Integration & Validation (30 hours)
├─ End-to-end testing
├─ Performance optimization
├─ Documentation
└─ Prototype delivery

Total: ~150 hours (equivalent to ~4 weeks full-time development)
```

### Phase 1: Setup & Infrastructure (Week 1-2)

**Goal:** Semua services berjalan dengan baik, development environment ready

**Tasks:**
- [ ] Setup project repository structure
- [ ] Create Docker Compose configuration
- [ ] Initialize PostgreSQL database
- [ ] Initialize ChromaDB instance
- [ ] Configure Ollama dengan qwen3:2b
- [ ] Setup SurrealDB (optional)
- [ ] Create backend project structure
- [ ] Create MCP server project structure
- [ ] Configure Nginx routing
- [ ] Setup environment variables (.env)
- [ ] Create validation tests
- [ ] Documentation untuk setup

**Deliverables:**
- Docker Compose file (tested & working)
- .env template file
- PostgreSQL schema initialization scripts
- Setup documentation
- Validation test suite

**Success Criteria:**
- ✅ All 8 docker services start successfully
- ✅ All services pass health checks
- ✅ All ports accessible & responding
- ✅ Data persistence working
- ✅ Environment reproducible

---

### Phase 2: WP1 - Data Pipeline (Week 3-4)

**Goal:** Metadata operasional terintegrasi & terstruktur di PostgreSQL

**Tasks:**
- [ ] Design PostgreSQL schema untuk operational metadata
- [ ] Implement metadata discovery from SIMRS
- [ ] Create data integration pipeline
- [ ] Implement data refinement logic
- [ ] Data quality validation
- [ ] Create sample datasets
- [ ] Integration testing
- [ ] Performance benchmarking

**Deliverables:**
- PostgreSQL schema (normalized)
- Data integration scripts
- Integrated operational dataset
- Data refinement pipeline
- Quality assurance report
- Integration documentation

**Success Criteria:**
- ✅ Metadata fully integrated dari SIMRS sources
- ✅ No data quality issues
- ✅ Query response time < 1 second
- ✅ Data volume: 14+ days × 10+ facilities
- ✅ 100% data completeness

---

### Phase 3: WP2 - RAG & Analytics (Week 5-6)

**Goal:** RAG system dapat menjawab operational queries dengan LLM

**Tasks:**
- [ ] Design vector embeddings strategy
- [ ] Prepare documents untuk ChromaDB
- [ ] Implement ChromaDB integration
- [ ] Create RAG retrieval system
- [ ] Develop Ollama integration (LangChain)
- [ ] Create API endpoints (FastAPI)
- [ ] Implement prompt templates
- [ ] Performance optimization
- [ ] Benchmark model performance
- [ ] Create MCP server integration (optional)

**Deliverables:**
- Vector store (ChromaDB) dengan operational metadata
- RAG retrieval system
- FastAPI backend dengan endpoints:
  - POST /api/query (RAG query)
  - POST /api/analyze (Data analysis)
  - GET /api/health (Health check)
  - GET /api/metrics (Performance metrics)
- LLM integration code
- MCP server (optional)
- API documentation (OpenAPI/Swagger)
- Performance benchmarks

**Success Criteria:**
- ✅ RAG query response time < 5 seconds
- ✅ Accuracy: relevant context retrieved
- ✅ LLM response quality: meaningful & actionable
- ✅ API endpoints tested & documented
- ✅ Ollama inference: 400+ tokens/sec (qwen3:2b ~2GB, jauh lebih cepat dari 7B)

---

### Phase 4: Integration & Validation (Week 7-8)

**Goal:** End-to-end system working, ready untuk WP3

**Tasks:**
- [ ] End-to-end testing (happy path & edge cases)
- [ ] Performance profiling & optimization
- [ ] Load testing (concurrent queries)
- [ ] Error handling & recovery testing
- [ ] Documentation completion
- [ ] Setup guides creation
- [ ] Demo preparation
- [ ] Handoff documentation

**Deliverables:**
- Complete test suite (unit + integration)
- Performance optimization report
- Complete documentation:
  - Setup & installation guide
  - API documentation
  - Architecture documentation
  - Development workflow guide
  - Deployment checklist
- Demo scenarios & scripts
- Handoff document untuk WP3 team

**Success Criteria:**
- ✅ All tests passing
- ✅ System stable under load
- ✅ Documentation complete & clear
- ✅ Ready for dashboard integration (WP3)

---

## Detailed Weekly Timeline

### Week 1: Docker & Infrastructure Setup

**Monday-Tuesday: Docker Environment**

```bash
# Tasks
├─ Clone/Create project repository
├─ Create docker-compose.yml
├─ Create Dockerfile untuk backend
├─ Create Dockerfile untuk mcp-server
├─ Setup Nginx configuration
├─ Create .env template
└─ Create directory structure

# Expected Output
├─ docker-compose.yml (8 services)
├─ .env.example
├─ backend/Dockerfile
├─ mcp-server/Dockerfile
├─ nginx/default.conf
└─ Full directory structure
```

**Wednesday-Thursday: Database Initialization**

```bash
# Tasks
├─ Design PostgreSQL schema
│  ├─ operational_metadata table
│  ├─ facilities table
│  ├─ utilities table
│  ├─ services table
│  └─ indexes
├─ Create initialization scripts
├─ Test PostgreSQL connectivity
└─ Create sample data

# Expected Output
├─ schema.sql (normalized)
├─ init-scripts/
│  ├─ 01-create-tables.sql
│  ├─ 02-create-indexes.sql
│  └─ 03-insert-sample-data.sql
└─ Database documentation
```

**Friday: Validation & Documentation**

```bash
# Tasks
├─ Test docker-compose up/down
├─ Verify all services health
├─ Create startup/shutdown scripts
├─ Write setup documentation
└─ Create validation tests

# Expected Output
├─ scripts/start.sh
├─ scripts/stop.sh
├─ scripts/validate.sh
├─ SETUP.md
└─ tests/test_infrastructure.py
```

**Week 1 Validation Checklist:**
- [ ] docker-compose up works completely
- [ ] All 8 services running
- [ ] All health checks passing
- [ ] PostgreSQL accessible & populated
- [ ] ChromaDB accessible
- [ ] Ollama accessible with qwen3:2b
- [ ] All ports working
- [ ] Setup documentation complete

---

### Week 2: Backend Project Structure & API Scaffold

**Monday-Tuesday: Backend Project Setup**

```bash
# Project Structure
backend/
├─ app/
│  ├─ __init__.py
│  ├─ main.py (FastAPI app)
│  ├─ config.py (Settings)
│  ├─ models.py (Pydantic models)
│  └─ dependencies.py
├─ api/
│  ├─ __init__.py
│  ├─ routes/
│  │  ├─ __init__.py
│  │  ├─ health.py
│  │  ├─ data.py
│  │  ├─ rag.py
│  │  └─ analysis.py
│  └─ schemas/
│      ├─ __init__.py
│      ├─ operational.py
│      └─ response.py
├─ core/
│  ├─ __init__.py
│  ├─ database.py (PostgreSQL)
│  ├─ vectordb.py (ChromaDB)
│  └─ llm.py (Ollama)
├─ services/
│  ├─ __init__.py
│  ├─ data_pipeline.py
│  ├─ rag_service.py
│  └─ analytics_service.py
├─ tests/
│  ├─ __init__.py
│  ├─ test_api.py
│  ├─ test_database.py
│  └─ test_rag.py
├─ requirements.txt
├─ Dockerfile
└─ README.md

# Tasks
├─ Create FastAPI application skeleton
├─ Setup Pydantic models
├─ Create database connection (SQLAlchemy)
├─ Setup logging configuration
└─ Create requirements.txt
```

**Wednesday-Thursday: API Routes Scaffold**

```bash
# API Routes to Create
POST /api/health
  └─ Health check endpoint

POST /api/data/upload
  └─ Upload operational data

GET /api/data/summary
  └─ Get data summary

POST /api/rag/query
  └─ RAG query endpoint (WP2)

POST /api/analysis/metadata
  └─ Metadata analysis (WP1)

GET /api/metrics
  └─ System metrics

# Tasks
├─ Create all route files
├─ Add request/response models
├─ Add docstrings & examples
├─ Create error handlers
└─ Setup OpenAPI documentation
```

**Friday: MCP Server & Validation**

```bash
# MCP Server Scaffold
mcp-server/
├─ src/
│  ├─ index.ts (or main.py)
│  ├─ server.ts
│  ├─ tools/
│  │  ├─ query-tool.ts
│  │  └─ analysis-tool.ts
│  └─ utils/
├─ package.json (or requirements.txt)
├─ Dockerfile
└─ README.md

# Tasks
├─ Create MCP server skeleton
├─ Setup basic tools
├─ Create test suite
└─ Update documentation
```

**Week 2 Validation Checklist:**
- [ ] Backend FastAPI app starts successfully
- [ ] All endpoints respond (200 OK)
- [ ] OpenAPI docs accessible
- [ ] Database connections working
- [ ] Logging configured
- [ ] MCP server structure ready
- [ ] Docker build successful

---

### Week 3: WP1 - Data Integration (Part 1)

**Monday-Tuesday: Data Pipeline Architecture**

```python
# core/database.py
- PostgreSQL connection pool
- SQLAlchemy session management
- Connection health checks

# services/data_pipeline.py
- MetadataDiscovery class
- DataIntegrationPipeline class
- Source connectors (SIMRS simulation)

# Tasks
├─ Design data flow architecture
├─ Create PostgreSQL session manager
├─ Implement SIMRS source connectors
├─ Create metadata discovery logic
└─ Add error handling
```

**Wednesday-Thursday: Data Refinement**

```python
# services/data_pipeline.py (continued)
- DataRefinement class
- Validation & quality checks
- Normalization logic
- Outlier detection

# Tasks
├─ Implement data validation
├─ Create normalization functions
├─ Add outlier detection (IQR method)
├─ Implement missing value handling
└─ Add data quality metrics
```

**Friday: Integration & Testing**

```bash
# Tasks
├─ Test data pipeline end-to-end
├─ Load sample datasets
├─ Validate data quality
├─ Create test datasets
└─ Document findings

# Expected Output
├─ Integrated dataset (CSV)
├─ Data quality report
├─ Test data in PostgreSQL
└─ Pipeline documentation
```

**Week 3 Validation Checklist:**
- [ ] Data integration pipeline working
- [ ] Sample data loaded into PostgreSQL
- [ ] Data quality > 95%
- [ ] Query response time < 1 sec
- [ ] Documentation complete

---

### Week 4: WP1 - Vector Preparation (Part 2)

**Monday-Tuesday: Vector Preparation**

```python
# core/vectordb.py
- ChromaDB connection manager
- Document preparation functions
- Embedding utilities

# services/vector_service.py
- VectorDatabaseSetup class
- Document chunking
- Metadata extraction

# Tasks
├─ Design document structure
├─ Create chunking strategy
├─ Implement ChromaDB integration
└─ Prepare embedding pipeline
```

**Wednesday-Thursday: Vector Store Population**

```bash
# Tasks
├─ Convert operational data to documents
├─ Generate embeddings
├─ Index documents in ChromaDB
├─ Verify retrieval functionality
└─ Test similarity search

# Expected Output
├─ ChromaDB populated with 1000+ documents
├─ Metadata properly indexed
├─ Similarity search working
└─ Retrieval performance benchmarked
```

**Friday: WP1 Completion & Handoff**

```bash
# Tasks
├─ Final data validation
├─ Performance benchmarking
├─ Complete documentation
├─ Create handoff guide for WP2
└─ Setup validations

# Deliverables
├─ PostgreSQL: Operational metadata (normalized)
├─ ChromaDB: Prepared documents for RAG
├─ Documentation: Architecture & schema
├─ Tests: Data pipeline tests (passing)
└─ Benchmarks: Performance metrics
```

**Week 4 Validation Checklist:**
- [ ] All metadata in ChromaDB
- [ ] Vector similarity search working
- [ ] Retrieval accuracy > 90%
- [ ] WP1 complete & tested
- [ ] Ready for RAG implementation (WP2)

---

### Week 5-6: WP2 - RAG & Analytics

**Week 5: LLM Integration & RAG**

```python
# core/llm.py
- OllamaLLM wrapper
- Prompt management
- Response processing

# services/rag_service.py
- RAGSystem class
- Context retrieval
- LLM inference
- Response formatting

# Tasks
├─ Implement Ollama integration (LangChain)
├─ Create RAG retrieval system
├─ Design prompt templates
├─ Implement context management
└─ Add response formatting
```

**Week 6: API Implementation & Testing**

```python
# api/routes/rag.py
POST /api/rag/query
├─ Request: {"query": string}
└─ Response: {
    "query": string,
    "context": [documents],
    "response": string,
    "metadata": {...}
}

POST /api/rag/analyze
├─ Request: {"data": object}
└─ Response: Analysis results

# Tasks
├─ Create all RAG endpoints
├─ Add comprehensive error handling
├─ Implement caching (optional)
├─ Create performance monitoring
└─ Test end-to-end
```

**Week 5-6 Validation Checklist:**
- [ ] RAG system working
- [ ] Query response time < 5 sec
- [ ] LLM inference working
- [ ] API endpoints tested
- [ ] Documentation complete

---

### Week 7-8: Integration & Validation

**Week 7: Testing & Optimization**

```bash
# Test Suite
├─ Unit tests (80+ tests)
├─ Integration tests (20+ tests)
├─ Performance tests
└─ End-to-end tests

# Optimization
├─ Profile code
├─ Optimize database queries
├─ Cache frequently used queries
├─ Optimize vector search
└─ Load testing (concurrent users)

# Tasks
├─ Write comprehensive tests
├─ Run performance profiling
├─ Optimize slow components
├─ Load test the system
└─ Document optimizations
```

**Week 8: Documentation & Handoff**

```bash
# Documentation
├─ Setup & Installation Guide
├─ API Documentation (OpenAPI)
├─ Architecture Documentation
├─ Database Schema Documentation
├─ Development Workflow Guide
├─ Deployment Checklist
└─ Known Issues & Limitations

# Deliverables
├─ Complete source code (GitHub)
├─ Docker Compose setup
├─ Database dumps (sample)
├─ API postman collection
├─ Performance metrics
└─ Handoff document for WP3

# Tasks
├─ Write all documentation
├─ Create video tutorials (optional)
├─ Prepare demo scenarios
├─ Create deployment guide
└─ Handoff to WP3 team
```

**Week 7-8 Validation Checklist:**
- [ ] All tests passing (100%)
- [ ] Performance metrics acceptable
- [ ] Documentation complete
- [ ] System stable under load
- [ ] Ready for WP3 integration

---

## Deliverables Checklist

### Phase 1: Infrastructure (Week 1-2)

```
□ Docker Compose Configuration
  ├─ 8 services defined
  ├─ All health checks
  ├─ Volume management
  └─ Network configuration

□ Environment Configuration
  ├─ .env.example
  ├─ .env.local
  └─ Configuration documentation

□ Database Setup
  ├─ PostgreSQL schema
  ├─ Initialization scripts
  ├─ Sample data
  └─ Schema documentation

□ Documentation
  ├─ Setup Guide
  ├─ Architecture Overview
  └─ Developer Guide
```

### Phase 2: WP1 - Data Pipeline (Week 3-4)

```
□ Metadata Integration
  ├─ Data discovery code
  ├─ Integration pipeline
  ├─ Integrated dataset
  └─ Integration documentation

□ Data Refinement
  ├─ Refinement logic
  ├─ Quality validation
  ├─ Refined dataset
  └─ Quality report

□ Vector Preparation
  ├─ Document preparation
  ├─ Chunking strategy
  ├─ Vector store (ChromaDB)
  └─ Indexing validation

□ Testing & Documentation
  ├─ Test suite (unit + integration)
  ├─ Data quality metrics
  ├─ Performance benchmarks
  └─ WP1 documentation
```

### Phase 3: WP2 - RAG & Analytics (Week 5-6)

```
□ Backend API
  ├─ FastAPI application
  ├─ All API endpoints
  ├─ Database integration
  └─ Error handling

□ RAG System
  ├─ Ollama integration
  ├─ RAG retrieval system
  ├─ Prompt templates
  └─ Response formatting

□ MCP Server (Optional)
  ├─ MCP server skeleton
  ├─ Tool definitions
  ├─ Integration with Claude
  └─ Documentation

□ Testing & Documentation
  ├─ API tests
  ├─ Integration tests
  ├─ API documentation (OpenAPI)
  └─ WP2 documentation
```

### Phase 4: Integration & Validation (Week 7-8)

```
□ Complete Test Suite
  ├─ Unit tests (80+)
  ├─ Integration tests (20+)
  ├─ Performance tests
  └─ End-to-end tests

□ Documentation
  ├─ Setup & Installation Guide
  ├─ API Documentation
  ├─ Architecture Guide
  ├─ Database Schema Doc
  ├─ Development Workflow
  ├─ Deployment Checklist
  └─ Troubleshooting Guide

□ Performance Reports
  ├─ Load testing results
  ├─ Performance metrics
  ├─ Optimization report
  └─ Recommendations

□ Handoff Package
  ├─ Complete source code
  ├─ Docker setup
  ├─ Database dumps
  ├─ Demo scenarios
  ├─ Known issues list
  └─ Transition plan for WP3
```

---

## Docker Environment Setup

### Directory Structure

```
darsi-management/
├─ docker-compose.yml          # Main compose file
├─ .env.example                # Environment template
├─ .env.local                  # Local configuration
├─ docker-compose.override.yml # Local overrides (optional)
│
├─ backend/                    # FastAPI Backend
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ models.py
│  │  ├─ dependencies.py
│  │  ├─ api/
│  │  │  ├─ routes/
│  │  │  │  ├─ health.py
│  │  │  │  ├─ data.py
│  │  │  │  ├─ rag.py
│  │  │  │  └─ analysis.py
│  │  │  └─ schemas/
│  │  ├─ core/
│  │  │  ├─ database.py
│  │  │  ├─ vectordb.py
│  │  │  └─ llm.py
│  │  ├─ services/
│  │  │  ├─ data_pipeline.py
│  │  │  ├─ rag_service.py
│  │  │  └─ analytics_service.py
│  │  └─ tests/
│  ├─ requirements.txt
│  ├─ Dockerfile
│  └─ .dockerignore
│
├─ mcp-server/                 # MCP Server (Optional)
│  ├─ src/
│  │  ├─ server.ts
│  │  ├─ tools/
│  │  └─ utils/
│  ├─ package.json
│  ├─ Dockerfile
│  └─ .dockerignore
│
├─ nginx/                      # Nginx Configuration
│  └─ default.conf
│
├─ postgres/                   # PostgreSQL Setup
│  └─ init-scripts/
│     ├─ 01-create-tables.sql
│     ├─ 02-create-indexes.sql
│     └─ 03-insert-sample-data.sql
│
├─ scripts/                    # Utility Scripts
│  ├─ start.sh
│  ├─ stop.sh
│  ├─ validate.sh
│  ├─ logs.sh
│  └─ clean.sh
│
└─ docs/                       # Documentation
   ├─ SETUP.md
   ├─ API.md
   ├─ ARCHITECTURE.md
   ├─ DATABASE.md
   ├─ DEVELOPMENT.md
   └─ DEPLOYMENT.md
```

### Docker Compose Implementation

**File: docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    container_name: darsi-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-darsi}
      POSTGRES_USER: ${POSTGRES_USER:-darsi_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-darsi_password}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init-scripts:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-darsi_user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - darsi-network

  surrealdb:
    image: surrealdb/surrealdb:latest
    container_name: darsi-surrealdb
    command: start --log info --user ${SURREALDB_USER:-root} --pass ${SURREALDB_PASSWORD:-root} memory
    ports:
      - "8001:8000"
    networks:
      - darsi-network

  chromadb:
    image: chromadb/chroma:1.0.12
    container_name: darsi-chromadb
    ports:
      - "8002:8000"
    volumes:
      - chromadb_data:/chroma/data
    networks:
      - darsi-network

  ollama:
    image: ollama/ollama:latest
    container_name: darsi-ollama
    ports:
      - "11434:11434"
    volumes:
      - /Users/maaullntech/.ollama:/root/.ollama:rw
    networks:
      - darsi-network
    environment:
      - OLLAMA_HOST=0.0.0.0:11434

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: darsi-backend
    env_file:
      - .env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      chromadb:
        condition: service_started
      ollama:
        condition: service_started
    networks:
      - darsi-network
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - CHROMADB_URL=http://chromadb:8000
      - OLLAMA_BASE_URL=http://ollama:11434
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  mcp-server:
    build:
      context: ./mcp-server
      dockerfile: Dockerfile
    container_name: darsi-mcp-server
    ports:
      - "8100:8100"
    depends_on:
      - backend
    networks:
      - darsi-network
    environment:
      - BACKEND_URL=http://backend:8000
      - LOG_LEVEL=INFO

  metabase:
    image: metabase/metabase:latest
    container_name: darsi-metabase
    ports:
      - "3001:3000"
    environment:
      - MB_DB_TYPE=postgres
      - MB_DB_DBNAME=${POSTGRES_DB}
      - MB_DB_PORT=5432
      - MB_DB_USER=${POSTGRES_USER}
      - MB_DB_PASS=${POSTGRES_PASSWORD}
      - MB_DB_HOST=postgres
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - darsi-network

  nginx:
    image: nginx:1.27-alpine
    container_name: darsi-nginx
    ports:
      - "8080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - backend
      - mcp-server
    networks:
      - darsi-network

volumes:
  postgres_data:
  chromadb_data:

networks:
  darsi-network:
    driver: bridge
```

### Environment Configuration

**File: .env.example**

```env
# PostgreSQL
POSTGRES_DB=darsi
POSTGRES_USER=darsi_user
POSTGRES_PASSWORD=darsi_password

# SurrealDB
SURREALDB_USER=root
SURREALDB_PASSWORD=root

# Application
APP_NAME=DARSI Management
DEBUG=True
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://darsi_user:darsi_password@localhost:5432/darsi
SQLALCHEMY_ECHO=False

# ChromaDB
CHROMADB_URL=http://localhost:8002
CHROMADB_COLLECTION=operational_metadata

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:2b
OLLAMA_TEMPERATURE=0.2
OLLAMA_TOP_P=0.9

# Backend API
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX=/api

# MCP Server
MCP_HOST=0.0.0.0
MCP_PORT=8100

# Metabase
METABASE_PORT=3001

# Nginx
NGINX_PORT=8080
```

### Docker Build & Runtime Scripts

**File: scripts/start.sh**

```bash
#!/bin/bash

echo "🚀 Starting DARSI Management Docker Environment..."

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Load environment
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
fi

# Build services
echo "🔨 Building services..."
docker-compose build

# Start services
echo "📦 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Run health checks
echo "🧪 Running health checks..."
docker-compose ps

echo ""
echo "✅ DARSI Management is running!"
echo ""
echo "📍 Access Points:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Nginx: http://localhost:8080"
echo "  - PostgreSQL: localhost:5432"
echo "  - ChromaDB: http://localhost:8002"
echo "  - Ollama: http://localhost:11434"
echo "  - Metabase: http://localhost:3001"
echo "  - MCP Server: http://localhost:8100"
echo ""
echo "📝 View logs: ./scripts/logs.sh"
echo "🛑 Stop services: ./scripts/stop.sh"
```

**File: scripts/stop.sh**

```bash
#!/bin/bash

echo "🛑 Stopping DARSI Management..."
docker-compose down
echo "✅ Services stopped"
```

**File: scripts/validate.sh**

```bash
#!/bin/bash

echo "🧪 Validating DARSI Management Infrastructure..."
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

check_service() {
    local service=$1
    local port=$2
    local name=$3
    
    if docker-compose ps $service | grep -q "Up"; then
        echo "✅ $name is running (port $port)"
        ((CHECKS_PASSED++))
    else
        echo "❌ $name is NOT running"
        ((CHECKS_FAILED++))
    fi
}

check_port() {
    local port=$1
    local name=$2
    
    if curl -s http://localhost:$port > /dev/null 2>&1; then
        echo "✅ $name accessible (port $port)"
        ((CHECKS_PASSED++))
    else
        echo "❌ $name NOT accessible (port $port)"
        ((CHECKS_FAILED++))
    fi
}

echo "Checking Services:"
check_service "postgres" "5432" "PostgreSQL"
check_service "chromadb" "8002" "ChromaDB"
check_service "ollama" "11434" "Ollama"
check_service "backend" "8000" "Backend API"
check_service "nginx" "8080" "Nginx"

echo ""
echo "Checking Connectivity:"
check_port "8000" "API Health"
check_port "8002" "ChromaDB"
check_port "11434" "Ollama"
check_port "5432" "PostgreSQL"

echo ""
echo "================================"
echo "Results: $CHECKS_PASSED passed, $CHECKS_FAILED failed"
echo "================================"

if [ $CHECKS_FAILED -eq 0 ]; then
    echo "✅ All checks passed!"
    exit 0
else
    echo "❌ Some checks failed. Run: ./scripts/logs.sh"
    exit 1
fi
```

---

## Development Workflow

### Local Development Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd darsi-management

# 2. Setup environment
cp .env.example .env
# Edit .env for local paths if needed

# 3. Start Docker environment
./scripts/start.sh

# 4. Validate setup
./scripts/validate.sh

# 5. Start development
# Backend: open http://localhost:8000/docs
# Database: psql postgresql://darsi_user:darsi_password@localhost:5432/darsi
# ChromaDB: open http://localhost:8002
# Ollama: curl http://localhost:11434/api/tags
```

### Backend Development

```bash
# Option 1: Develop inside container
docker-compose exec backend bash
cd /app
python -m pytest tests/

# Option 2: Develop locally (optional)
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Database Development

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U darsi_user -d darsi

# View logs
docker-compose logs postgres

# Backup data
docker-compose exec postgres pg_dump -U darsi_user darsi > backup.sql

# Restore data
docker-compose exec -T postgres psql -U darsi_user darsi < backup.sql
```

### Testing Workflow

```bash
# Run all tests
docker-compose exec backend pytest tests/

# Run specific test
docker-compose exec backend pytest tests/test_api.py::test_health

# Run with coverage
docker-compose exec backend pytest --cov=app tests/

# Run performance tests
docker-compose exec backend pytest tests/test_performance.py
```

### Git Workflow

```bash
# Feature development
git checkout -b feature/wp1-data-pipeline
# ... make changes ...
git add .
git commit -m "feat: implement data pipeline for WP1"
git push origin feature/wp1-data-pipeline

# Create pull request for review
# After review and approval, merge to main
```

---

## Testing & Validation

### Test Strategy

```
Unit Tests (Individual Components)
├─ API routes
├─ Service functions
├─ Data validation
└─ LLM integration

Integration Tests (Component Interaction)
├─ Database operations
├─ Vector store operations
├─ RAG system
└─ End-to-end flows

Performance Tests
├─ Query response times
├─ Concurrent requests
├─ Vector search speed
└─ LLM inference speed

End-to-End Tests
├─ Complete workflows
├─ Error scenarios
└─ Edge cases
```

### Test Coverage Goals

```
Phase 1-2 Requirements:
├─ Minimum 80% code coverage
├─ All critical paths tested
├─ Performance benchmarks met
├─ No critical bugs
└─ Documentation complete
```

### Performance Benchmarks

```
Targets:
├─ API response time: < 1 second (simple queries)
├─ RAG response time: < 5 seconds (with LLM)
├─ Database query: < 100ms
├─ Vector search: < 200ms
├─ LLM inference: 200+ tokens/second
├─ Concurrent users: 10+ simultaneous
└─ Uptime: > 99.5%
```

---

## Deployment & Handoff

### Pre-Deployment Checklist

```
Code Quality:
□ All tests passing
□ Code coverage > 80%
□ No linting errors
□ Code reviewed

Documentation:
□ API documentation complete
□ Setup guide complete
□ Architecture documented
□ Database schema documented

Performance:
□ Load testing passed
□ Performance metrics acceptable
□ Optimization completed
□ No memory leaks

Security:
□ Environment variables configured
□ No hardcoded credentials
□ Input validation implemented
□ Error handling proper

Deployment:
□ Docker images built & tested
□ Database migrations work
□ Backup/recovery tested
□ Health checks configured
```

### Handoff to WP3

**Deliverables Package:**

```
Handoff/
├─ Source Code
│  ├─ backend/ (complete)
│  ├─ mcp-server/ (complete)
│  ├─ nginx/ (config)
│  └─ postgres/ (schema & scripts)
├─ Documentation
│  ├─ SETUP.md (installation)
│  ├─ API.md (endpoint reference)
│  ├─ ARCHITECTURE.md
│  ├─ DATABASE.md
│  └─ DEVELOPMENT.md
├─ Docker Configuration
│  ├─ docker-compose.yml
│  ├─ .env.example
│  └─ All Dockerfiles
├─ Database
│  ├─ schema.sql
│  ├─ sample_data.sql
│  └─ db_backup.sql
├─ API Collection
│  └─ postman_collection.json
├─ Test Suite
│  ├─ Unit tests (passed)
│  ├─ Integration tests (passed)
│  └─ Performance benchmarks
├─ Known Issues
│  ├─ ISSUES.md
│  └─ LIMITATIONS.md
└─ Transition Plan
   ├─ WP3_REQUIREMENTS.md
   ├─ INTEGRATION_POINTS.md
   └─ SUPPORT_CONTACTS.md
```

---

## Risk Management

### Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| SIMRS Integration delays | Medium | High | Start with mock data, prepare connectors early |
| LLM performance not meeting targets | Medium | Medium | Test qwen3:2b early, small enough for quick iteration |
| Data quality issues | Medium | High | Implement comprehensive validation, sampling |
| Docker environment issues | Low | Medium | Extensive testing on multiple OS |
| Ollama model memory issues | Very Low | Low | qwen3:2b hanya ~2GB VRAM, sangat ringan |
| Database performance | Low | Medium | Implement proper indexing, query optimization |
| Timeline slipping | Medium | High | Weekly progress reviews, clear milestones |

### Mitigation Strategies

```
Risk: SIMRS Integration delays
├─ Start with mock SIMRS data
├─ Build integration abstractions
├─ Create test data generators
└─ Plan for phased real data integration

Risk: LLM performance issues
├─ Early testing with actual workloads
├─ Have phi as fallback if needed
├─ Monitor inference times
└─ Implement caching layer

Risk: Data quality
├─ Comprehensive validation rules
├─ Sampling & statistical checks
├─ Quality metrics dashboard
└─ Data lineage tracking

Risk: Timeline slipping
├─ Weekly progress meetings
├─ Clear blockers identification
├─ Buffer time for complex tasks
└─ Parallel workstreams where possible
```

---

## Success Metrics

### WP1 - Data Integration
- ✅ 100% of identified metadata sources integrated
- ✅ Data quality score > 95%
- ✅ Query response time < 1 second
- ✅ Data volume: 14+ days of operational data
- ✅ Zero data loss

### WP2 - RAG & Analytics
- ✅ RAG system responds to 10+ operational queries
- ✅ Response accuracy > 80% (correct context)
- ✅ Response time < 5 seconds
- ✅ LLM inference working properly
- ✅ API endpoints fully documented

### Overall
- ✅ All tests passing (100%)
- ✅ Documentation complete
- ✅ System stable under normal load
- ✅ Ready for WP3 integration
- ✅ Zero critical bugs

---

## Appendix

### Command Reference

```bash
# Docker Management
docker-compose up -d              # Start all services
docker-compose down              # Stop all services
docker-compose logs -f           # View logs (live)
docker-compose ps               # View service status
docker-compose exec backend bash # Enter container

# Database
docker-compose exec postgres psql -U darsi_user -d darsi
docker-compose exec postgres pg_dump -U darsi_user darsi > backup.sql

# Testing
docker-compose exec backend pytest tests/
docker-compose exec backend pytest --cov=app tests/

# Cleanup
docker-compose down -v          # Remove everything including volumes
```

### Useful Resources

- Docker Compose: https://docs.docker.com/compose/
- FastAPI: https://fastapi.tiangolo.com/
- ChromaDB: https://docs.trychroma.com/
- PostgreSQL: https://www.postgresql.org/docs/
- Ollama: https://github.com/ollama/ollama
- LangChain: https://python.langchain.com/

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | May 14, 2026 | [Your Name] | Initial plan |

---

**Next Steps:**
1. ✅ Review this plan
2. ✅ Approve timeline & scope
3. ✅ Setup project repository
4. ✅ Begin Week 1 - Infrastructure Setup

**For questions or clarifications, contact:** [Your Email]

---

**Project Status:** Ready for Implementation 🚀