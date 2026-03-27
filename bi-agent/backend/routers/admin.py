"""
routers/admin.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Admin & Monitoring Endpoints

Endpoints:
  GET /admin/stats      — system stats (jobs, Redis, PostgreSQL)
  GET /admin/history    — job history from PostgreSQL
  GET /admin/health     — full health check (all services)
  DELETE /admin/cleanup — clean up old jobs from memory
"""

import os
import time
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header
from typing import Optional

from services.job_store import job_store, REDIS_AVAILABLE, PG_AVAILABLE

router = APIRouter()

ADMIN_KEY = os.getenv("ADMIN_API_KEY", os.getenv("AGENT_API_KEY", "dev-key"))


def _check_admin(x_admin_key: Optional[str]):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


# ─── Health Check ─────────────────────────────────────────────────────────────

@router.get("/health", summary="Full system health check")
def health_check():
    health = {
        "status":    "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "services":  {},
    }

    # Redis
    if REDIS_AVAILABLE:
        try:
            from services.job_store import _redis_client
            _redis_client.ping()
            health["services"]["redis"] = "ok"
        except Exception as e:
            health["services"]["redis"] = f"error: {e}"
            health["status"] = "degraded"
    else:
        health["services"]["redis"] = "not configured (using memory)"

    # PostgreSQL
    if PG_AVAILABLE:
        try:
            from services.job_store import _pg_engine
            from sqlalchemy import text
            with _pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health["services"]["postgres"] = "ok"
        except Exception as e:
            health["services"]["postgres"] = f"error: {e}"
            health["status"] = "degraded"
    else:
        health["services"]["postgres"] = "not configured (using memory)"

    # Ollama
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        r = requests.get(f"{ollama_url}/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        health["services"]["ollama"] = f"ok — models: {', '.join(models[:3])}"
    except Exception as e:
        health["services"]["ollama"] = f"offline: {e}"

    # Job store
    health["services"]["job_store"] = job_store.stats

    return health


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats", summary="System statistics")
def get_stats(x_admin_key: Optional[str] = Header(None)):
    _check_admin(x_admin_key)
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "job_store": job_store.stats,
        "infrastructure": {
            "redis":    REDIS_AVAILABLE,
            "postgres": PG_AVAILABLE,
            "ai_provider": os.getenv("AI_PROVIDER", "ollama"),
        },
    }


# ─── History ─────────────────────────────────────────────────────────────────

@router.get("/history", summary="Job history from PostgreSQL")
def get_history(
    limit: int = 50,
    x_admin_key: Optional[str] = Header(None),
):
    _check_admin(x_admin_key)
    return {
        "jobs":   job_store.list_history(limit=limit),
        "source": "postgres" if PG_AVAILABLE else "memory",
    }


# ─── Cleanup ─────────────────────────────────────────────────────────────────

@router.delete("/cleanup", summary="Clean up old jobs from memory")
def cleanup_jobs(
    hours: int = 6,
    x_admin_key: Optional[str] = Header(None),
):
    _check_admin(x_admin_key)
    before = len(job_store._memory)
    job_store.cleanup_old_jobs(hours=hours)
    after  = len(job_store._memory)
    return {
        "removed": before - after,
        "remaining": after,
    }
