"""Pipeline Service DARSI — dipanggil oleh n8n via HTTP.

Endpoint:
    GET  /health              → liveness probe.
    POST /pipeline/refine     → Pandas refinement: raw_* → refined_* (PostgreSQL).
    POST /pipeline/sync       → Sync: refined_* → clean_* (SurrealDB).
    POST /pipeline/embed      → Embedding: clean_* → SurrealDB vector index.
    POST /pipeline/run-all    → Jalankan ketiga step berurutan (trigger manual).
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException

app = FastAPI(title="DARSI Pipeline Service")

PROCESSORS_DIR = os.getenv("PROCESSORS_DIR", "/app/processors")

SCRIPT_ENV = {
    **os.environ,
    "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "postgres"),
    "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
    "POSTGRES_DB": os.getenv("POSTGRES_DB", "darsi"),
    "POSTGRES_USER": os.getenv("POSTGRES_USER", "darsi_user"),
    "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "darsi_password"),
    "SURREALDB_URL": os.getenv("SURREALDB_URL", "http://surrealdb:8000"),
    "SURREALDB_USER": os.getenv("SURREALDB_USER", "root"),
    "SURREALDB_PASSWORD": os.getenv("SURREALDB_PASSWORD", "root"),
    "SURREALDB_NS": os.getenv("SURREALDB_NS", "darsi"),
    "SURREALDB_DB": os.getenv("SURREALDB_DB", "operasional"),
    "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
    "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "qwen3.5:2b"),
}


def _run_script(script_name: str, *args: str) -> dict[str, Any]:
    """Jalankan script Python di processors/ sebagai subprocess."""
    script_path = f"{PROCESSORS_DIR}/{script_name}"
    cmd = [sys.executable, script_path] + list(args)
    started_at = datetime.now()

    result = subprocess.run(cmd, env=SCRIPT_ENV, capture_output=True, text=True)

    duration_ms = int((datetime.now() - started_at).total_seconds() * 1000)

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "script": script_name,
                "stderr": result.stderr[-2000:],
                "duration_ms": duration_ms,
            },
        )

    return {
        "script": script_name,
        "status": "ok",
        "duration_ms": duration_ms,
        "stdout": result.stdout[-1000:],
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "pipeline-service"}


@app.post("/pipeline/refine")
async def refine() -> dict[str, Any]:
    """Pandas refinement: raw_* → refined_* di PostgreSQL."""
    return _run_script("refine_postgres_internal.py")


@app.post("/pipeline/sync")
async def sync() -> dict[str, Any]:
    """Sync refined_* PostgreSQL → clean_* SurrealDB."""
    return _run_script("refine_raw_to_surrealdb.py", "--apply")


@app.post("/pipeline/embed")
async def embed() -> dict[str, Any]:
    """Generate embedding clean_* → SurrealDB vector index."""
    return _run_script("embed_to_surrealdb_vector.py")


@app.post("/pipeline/run-all")
async def run_all() -> dict[str, Any]:
    """Jalankan ketiga step berurutan — untuk trigger manual atau testing."""
    started_at = datetime.now()
    results = []

    for script, args in [
        ("refine_postgres_internal.py", []),
        ("refine_raw_to_surrealdb.py", ["--apply"]),
        ("embed_to_surrealdb_vector.py", []),
    ]:
        try:
            result = _run_script(script, *args)
            results.append(result)
        except HTTPException as err:
            return {
                "status": "failed",
                "failed_at": script,
                "detail": err.detail,
                "completed_steps": results,
            }

    total_ms = int((datetime.now() - started_at).total_seconds() * 1000)
    return {"status": "ok", "total_duration_ms": total_ms, "steps": results}
