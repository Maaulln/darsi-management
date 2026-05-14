Flow Development:
Fase 1 — Foundation Data

Setup PostgreSQL + dummy data SIMRS
Bangun pipeline data refinement dengan Pandas
Orkestrasi pipeline dengan Airflow
Setup SurrealDB untuk data clean hasil refinement

Fase 2 — AI Layer

Bangun custom MCP server sebagai konektor SurrealDB
Setup Ollama + MedLLaMA di lokal
Bangun pipeline RAG dengan LangChain/LlamaIndex
Setup ChromaDB sebagai vector database
Testing embedding dan retrieval data operasional

Fase 3 — Backend & Konektor

Bangun API dengan FastAPI
Integrasi FastAPI ↔ MCP server ↔ RAG pipeline
Endpoint untuk query analitik dan ringkasan AI

Fase 4 — Frontend & Dashboard

Setup Metabase → koneksi ke PostgreSQL dan SurrealDB
Bangun komponen React untuk tampilan utama
Embed Metabase chart ke dalam React
Bangun chat interface untuk interaksi dengan MedLLaMA

Fase 5 — Validasi

UAT bersama manajemen RSI Surabaya
Evaluasi usability dengan SUS
Penyempurnaan sistem
Penyusunan luaran: prototipe, paten, publikasi, materi ajar