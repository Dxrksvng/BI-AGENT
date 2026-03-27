"""
routers/ingest.py
Layer 1: Receive data from CSV upload or Docker Agent

Endpoints:
  POST /ingest/upload-csv — Upload CSV file
  POST /ingest/connect    — Test DB connection
  POST /ingest/fetch      — Fetch table from DB
  GET  /ingest/jobs       — List all jobs
  GET  /ingest/jobs/{id}  — Get job status
  POST /ingest/push       — Receive data from Docker Agent
"""
import io
import pandas as pd
import os
from fastapi import Request

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from models.schemas import DBConnectionRequest, IngestResponse, JobStatus
from services.db_connector import DBConnector
from services.job_store import job_store
from services.auto_pipeline import run_auto_pipeline

router = APIRouter()


# ---------------------------------------------------------------
# CSV UPLOAD
# ---------------------------------------------------------------

@router.post("/upload-csv", summary="Upload CSV file")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload CSV and store as job.
    Use for testing the full pipeline without a real database.

    Steps:
      1. Upload CSV file
      2. Copy the job_id returned
      3. POST /pipeline/clean with the job_id
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except UnicodeDecodeError:
        df = pd.read_csv(io.StringIO(contents.decode("tis-620", errors="replace")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    job_id = job_store.create()
    job_store.update(job_id, data=df, status="done")

    return {
        "job_id":    job_id,
        "status":    "done",
        "filename":  file.filename,
        "rows":      len(df),
        "columns":   list(df.columns),
        "message":   f"Upload successful — {len(df)} rows, {len(df.columns)} columns",
        "next_step": f"POST /pipeline/clean  body: {{\"job_id\": \"{job_id}\", \"target_table\": \"{file.filename}\"}}",
    }


# ---------------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------------

class FetchRequest(BaseModel):
    db_config:  DBConnectionRequest
    table_name: str
    limit:      Optional[int] = None


@router.post("/connect", summary="Test database connection")
def test_connection(request: DBConnectionRequest):
    try:
        connector = DBConnector(request)
        tables    = connector.list_tables()
        connector.close()
        return {
            "status":  "success",
            "message": f"Connected successfully — {len(tables)} tables found",
            "tables":  tables,
        }
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/fetch", response_model=IngestResponse, summary="Fetch table from database")
def fetch_table(request: FetchRequest, background_tasks: BackgroundTasks):
    job_id = job_store.create()
    job_store.set_status(job_id, "running")
    background_tasks.add_task(_fetch_task, job_id, request)
    return IngestResponse(
        job_id=job_id,
        status=JobStatus.RUNNING,
        tables=[request.table_name],
        row_count=0,
        message=f"Fetching data from table '{request.table_name}'...",
    )


def _fetch_task(job_id: str, request: FetchRequest):
    try:
        connector = DBConnector(request.db_config)
        df        = connector.fetch_table(request.table_name, request.limit)
        connector.close()
        job_store.update(job_id, data=df, status="done")
    except Exception as e:
        job_store.set_status(job_id, "failed", error=str(e))


# ---------------------------------------------------------------
# JOB STATUS
# ---------------------------------------------------------------

@router.get("/jobs", summary="List all jobs")
def list_jobs():
    return {"jobs": job_store.list_jobs()}


@router.get("/jobs/{job_id}", summary="Get job status")
def get_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"job_id not found: {job_id}")
    return {
        "job_id":    job["id"],
        "status":    job["status"],
        "has_data":  job["data"] is not None,
        "row_count": len(job["data"]) if job["data"] is not None else 0,
        "error":     job.get("error"),
    }


# ---------------------------------------------------------------
# AGENT PUSH — Receive data from Docker Agent
# ---------------------------------------------------------------

class AgentPushRequest(BaseModel):
    table_name: str
    data:       list
    row_count:  int
    synced_at:  str
    api_key:    Optional[str] = None


@router.post("/push", summary="Receive data from Docker Agent")
def agent_push(request: AgentPushRequest, req: Request, background_tasks: BackgroundTasks):
    api_key  = req.headers.get("X-API-Key", "")
    expected = os.getenv("AGENT_API_KEY", "dev-key")
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    if not request.data:
        raise HTTPException(status_code=400, detail="No data provided")

    try:
        df = pd.DataFrame(request.data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot convert data: {e}")

    job_id = job_store.create()
    job_store.update(job_id, data=df, status="done")

    background_tasks.add_task(
        run_auto_pipeline,
        job_id=job_id,
        company_name=req.headers.get("X-Company", "Company"),
        industry=req.headers.get("X-Industry", "general"),
        table_name=request.table_name,
    )

    return {
        "job_id":     job_id,
        "status":     "done",
        "table_name": request.table_name,
        "rows":       len(df),
        "columns":    list(df.columns),
        "synced_at":  request.synced_at,
        "message":    f"Data '{request.table_name}' received — {len(df)} rows",
        "next_step":  f"POST /pipeline/clean  body: {{\"job_id\": \"{job_id}\"}}",
    }