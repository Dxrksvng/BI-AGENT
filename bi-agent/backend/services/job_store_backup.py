"""
services/job_store.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Production-grade Job Store with Redis backend.
Falls back to in-memory dict if Redis is not available.

Redis stores: job metadata (JSON)
DataFrame objects stored in memory (not serializable to Redis)
PostgreSQL stores: completed job history for audit trail
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import uuid
import json
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pandas as pd

# ─── Try Redis ────────────────────────────────────────────────────────────────
try:
    import redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    _redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    _redis_client.ping()
    REDIS_AVAILABLE = True
    print(f"[job_store] Redis connected: {REDIS_URL}")
except Exception as e:
    REDIS_AVAILABLE = False
    _redis_client = None
    print(f"[job_store] Redis not available ({e}) — using in-memory fallback")

# ─── Try PostgreSQL ───────────────────────────────────────────────────────────
try:
    from sqlalchemy import create_engine, text, Column, String, Integer, Float, DateTime, Text
    from sqlalchemy.orm import declarative_base, sessionmaker
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if DATABASE_URL:
        _pg_engine  = create_engine(DATABASE_URL, pool_pre_ping=True)
        _PgSession  = sessionmaker(bind=_pg_engine)
        PG_AVAILABLE = True
        print(f"[job_store] PostgreSQL connected")
    else:
        PG_AVAILABLE = False
        _pg_engine   = None
        _PgSession   = None
except Exception as e:
    PG_AVAILABLE = False
    _pg_engine   = None
    _PgSession   = None
    print(f"[job_store] PostgreSQL not available ({e})")

# ─── PostgreSQL Schema ────────────────────────────────────────────────────────
if PG_AVAILABLE:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()

    class JobRecord(Base):
        __tablename__ = "bi_jobs"
        id           = Column(String, primary_key=True)
        status       = Column(String, default="pending")
        company_name = Column(String, default="")
        filename     = Column(String, default="")
        row_count    = Column(Integer, default=0)
        col_count    = Column(Integer, default=0)
        quality_score= Column(Float,   default=0.0)
        summary      = Column(Text,    default="")
        error        = Column(Text,    default="")
        created_at   = Column(DateTime, default=datetime.utcnow)
        completed_at = Column(DateTime, nullable=True)

    try:
        Base.metadata.create_all(_pg_engine)
        print("[job_store] PostgreSQL tables ready")
    except Exception as e:
        print(f"[job_store] PostgreSQL table creation failed: {e}")
        PG_AVAILABLE = False

JOB_TTL_SECONDS = 60 * 60 * 6  # 6 hours TTL in Redis


# ─── JobStore Class ───────────────────────────────────────────────────────────

class JobStore:
    """
    Production-grade job store.

    Storage strategy:
    - Redis: job metadata (status, report, analysis JSON) with 6h TTL
    - Memory: DataFrame objects (not JSON-serializable, same process only)
    - PostgreSQL: completed job history for audit trail and analytics

    Falls back to pure in-memory if Redis/PG not available.
    """

    def __init__(self):
        self._memory: Dict[str, Dict[str, Any]] = {}   # always available
        self.use_redis = REDIS_AVAILABLE
        self.use_pg    = PG_AVAILABLE

    # ─── Serialization helpers ────────────────────────────────────────────────

    def _to_redis_key(self, job_id: str) -> str:
        return f"bi_agent:job:{job_id}"

    def _serialize_for_redis(self, job: dict) -> bytes:
        """Serialize job metadata to Redis (exclude DataFrames)."""
        safe = {}
        for k, v in job.items():
            if isinstance(v, pd.DataFrame):
                continue  # stored in memory only
            elif isinstance(v, datetime):
                safe[k] = v.isoformat()
            elif hasattr(v, "dict"):
                safe[k] = v.dict()  # Pydantic model
            elif hasattr(v, "__dict__"):
                try:
                    safe[k] = json.loads(json.dumps(v.__dict__, default=str))
                except Exception:
                    safe[k] = str(v)
            else:
                try:
                    json.dumps(v)
                    safe[k] = v
                except Exception:
                    safe[k] = str(v)
        return json.dumps(safe, default=str).encode()

    def _deserialize_from_redis(self, data: bytes) -> dict:
        return json.loads(data.decode())

    # ─── Core CRUD ───────────────────────────────────────────────────────────

    def create(self) -> str:
        job_id = str(uuid.uuid4())
        job = {
            "id":         job_id,
            "status":     "pending",
            "created_at": datetime.utcnow(),
            "data":       None,
            "clean_data": None,
            "report":     None,
            "analysis":   None,
            "error":      None,
            "company_name": "",
            "filename":   "",
        }
        self._memory[job_id] = job

        if self.use_redis:
            try:
                key = self._to_redis_key(job_id)
                _redis_client.setex(key, JOB_TTL_SECONDS, self._serialize_for_redis(job))
            except Exception as e:
                print(f"[job_store] Redis write failed: {e}")

        return job_id

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        # Always return from memory (has DataFrames)
        if job_id in self._memory:
            # Refresh metadata from Redis if available
            if self.use_redis:
                try:
                    key  = self._to_redis_key(job_id)
                    data = _redis_client.get(key)
                    if data:
                        meta = self._deserialize_from_redis(data)
                        # Merge Redis metadata but keep DataFrames from memory
                        for k, v in meta.items():
                            if k not in ("data", "clean_data"):
                                self._memory[job_id][k] = v
                except Exception as e:
                    print(f"[job_store] Redis read failed: {e}")
            return self._memory[job_id]

        # Try to restore from Redis (job from another process)
        if self.use_redis:
            try:
                key  = self._to_redis_key(job_id)
                data = _redis_client.get(key)
                if data:
                    job = self._deserialize_from_redis(data)
                    job["data"]       = None  # DataFrame lost across processes
                    job["clean_data"] = None
                    self._memory[job_id] = job
                    return job
            except Exception as e:
                print(f"[job_store] Redis restore failed: {e}")

        return None

    def update(self, job_id: str, **kwargs):
        if job_id not in self._memory:
            # Try restore from Redis first
            if not self.get(job_id):
                raise KeyError(f"job_id not found: {job_id}")

        self._memory[job_id].update(kwargs)
        self._memory[job_id]["updated_at"] = datetime.utcnow()

        if self.use_redis:
            try:
                key = self._to_redis_key(job_id)
                _redis_client.setex(key, JOB_TTL_SECONDS,
                                    self._serialize_for_redis(self._memory[job_id]))
            except Exception as e:
                print(f"[job_store] Redis update failed: {e}")

        # Save to PostgreSQL when job completes
        status = kwargs.get("status") or self._memory[job_id].get("status")
        if status == "done" and self.use_pg:
            self._save_to_pg(job_id)

    def set_status(self, job_id: str, status: str, error: str = None):
        self.update(job_id, status=status, error=error)

    # ─── PostgreSQL persistence ───────────────────────────────────────────────

    def _save_to_pg(self, job_id: str):
        """Save completed job summary to PostgreSQL for audit trail."""
        try:
            job     = self._memory.get(job_id, {})
            report  = job.get("report") or {}
            analysis= job.get("analysis") or {}

            if hasattr(report, "dict"):
                report = report.dict()
            if hasattr(analysis, "dict"):
                analysis = analysis.dict()

            session = _PgSession()
            try:
                record = JobRecord(
                    id            = job_id,
                    status        = job.get("status", "done"),
                    company_name  = job.get("company_name", ""),
                    filename      = job.get("filename", ""),
                    row_count     = report.get("cleaned_rows", 0) if isinstance(report, dict) else 0,
                    col_count     = report.get("n_cols", 0)       if isinstance(report, dict) else 0,
                    quality_score = report.get("quality_score", 0) if isinstance(report, dict) else 0,
                    summary       = (analysis.get("summary", "") if isinstance(analysis, dict) else "")[:500],
                    created_at    = job.get("created_at", datetime.utcnow()),
                    completed_at  = datetime.utcnow(),
                )
                session.merge(record)
                session.commit()
                print(f"[job_store] Saved job {job_id[:8]} to PostgreSQL")
            finally:
                session.close()
        except Exception as e:
            print(f"[job_store] PostgreSQL save failed: {e}")

    # ─── List & Admin ─────────────────────────────────────────────────────────

    def list_jobs(self) -> list:
        """Return all jobs without DataFrames."""
        jobs = []
        for job in self._memory.values():
            safe = {k: v for k, v in job.items()
                    if k not in ("data", "clean_data") and not isinstance(v, pd.DataFrame)}
            # Convert datetime to string
            for k, v in safe.items():
                if isinstance(v, datetime):
                    safe[k] = v.isoformat()
            jobs.append(safe)
        return sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)

    def list_history(self, limit: int = 50) -> list:
        """Return job history from PostgreSQL."""
        if not self.use_pg:
            return self.list_jobs()
        try:
            session = _PgSession()
            try:
                records = session.execute(
                    text("SELECT * FROM bi_jobs ORDER BY created_at DESC LIMIT :limit"),
                    {"limit": limit}
                ).fetchall()
                return [dict(r._mapping) for r in records]
            finally:
                session.close()
        except Exception as e:
            print(f"[job_store] PostgreSQL history failed: {e}")
            return self.list_jobs()

    def cleanup_old_jobs(self, hours: int = 6):
        """Remove jobs older than N hours from memory."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        to_delete = [
            job_id for job_id, job in self._memory.items()
            if job.get("created_at", datetime.utcnow()) < cutoff
        ]
        for job_id in to_delete:
            del self._memory[job_id]
        if to_delete:
            print(f"[job_store] Cleaned up {len(to_delete)} old jobs")

    @property
    def stats(self) -> dict:
        """Return store stats for admin dashboard."""
        jobs = list(self._memory.values())
        return {
            "total_jobs":   len(jobs),
            "pending":      sum(1 for j in jobs if j.get("status") == "pending"),
            "running":      sum(1 for j in jobs if j.get("status") == "running"),
            "done":         sum(1 for j in jobs if j.get("status") == "done"),
            "failed":       sum(1 for j in jobs if j.get("status") == "failed"),
            "redis":        self.use_redis,
            "postgres":     self.use_pg,
            "memory_jobs":  len(self._memory),
        }


# Singleton
job_store = JobStore()
