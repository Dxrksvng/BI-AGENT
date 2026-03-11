"""
routers/ingest.py
Layer ที่ 1: รับข้อมูลจาก database หรือ CSV ของบริษัท

Endpoints:
  POST /ingest/upload-csv — อัปโหลด CSV (ทดสอบได้เลยไม่ต้องมี DB)
  POST /ingest/connect    — ทดสอบเชื่อมต่อ DB
  POST /ingest/fetch      — ดึงข้อมูลจากตาราง
  GET  /ingest/jobs       — ดูสถานะ jobs ทั้งหมด
  GET  /ingest/jobs/{id}  — ดูสถานะ job
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
# CSV UPLOAD — ใช้ทดสอบได้เลยโดยไม่ต้องมี database จริง
# ---------------------------------------------------------------

@router.post("/upload-csv", summary="📂 อัปโหลด CSV ไฟล์")
async def upload_csv(file: UploadFile = File(...)):
    """
    อัปโหลด CSV แล้วเก็บเป็น job
    ใช้ทดสอบ full pipeline โดยไม่ต้องต่อ database จริง

    วิธีใช้:
      1. กด 'Try it out'
      2. เลือกไฟล์ CSV
      3. กด Execute
      4. copy job_id ที่ได้ไปใช้ใน /pipeline/clean
    """
    # ตรวจสอบนามสกุลไฟล์
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="รับเฉพาะไฟล์ .csv เท่านั้น")

    # อ่านไฟล์
    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except UnicodeDecodeError:
        # ลอง encoding อื่นถ้า utf-8 ไม่ได้
        df = pd.read_csv(io.StringIO(contents.decode("tis-620", errors="replace")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"อ่านไฟล์ไม่ได้: {str(e)}")

    if df.empty:
        raise HTTPException(status_code=400, detail="ไฟล์ CSV ว่างเปล่า")

    # สร้าง job และเก็บข้อมูล
    job_id = job_store.create()
    job_store.update(job_id, data=df, status="done")

    # รัน full pipeline อัตโนมัติ
    background_tasks.add_task(
        run_auto_pipeline,
        job_id=job_id,
        company_name=req.headers.get("X-Company", "Company"),
        industry=req.headers.get("X-Industry", "general"),
        table_name=request.table_name,
    )

    return {
        "job_id":   job_id,
        "status":   "done",
        "filename": file.filename,
        "rows":     len(df),
        "columns":  list(df.columns),
        "message":  f"✅ อัปโหลดสำเร็จ! {len(df)} แถว, {len(df.columns)} คอลัมน์",
        "next_step": f"POST /pipeline/clean  body: {{\"job_id\": \"{job_id}\", \"target_table\": \"{file.filename}\"}}",
    }


# ---------------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------------

class FetchRequest(BaseModel):
    """คำขอดึงข้อมูลจากตาราง"""
    db_config:  DBConnectionRequest
    table_name: str
    limit:      Optional[int] = None


@router.post("/connect", summary="ทดสอบเชื่อมต่อฐานข้อมูล")
def test_connection(request: DBConnectionRequest):
    try:
        connector = DBConnector(request)
        tables    = connector.list_tables()
        connector.close()
        return {
            "status":  "success",
            "message": f"เชื่อมต่อสำเร็จ พบ {len(tables)} ตาราง",
            "tables":  tables,
        }
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")


@router.post("/fetch", response_model=IngestResponse, summary="ดึงข้อมูลจากตาราง")
def fetch_table(request: FetchRequest, background_tasks: BackgroundTasks):
    job_id = job_store.create()
    job_store.set_status(job_id, "running")
    background_tasks.add_task(_fetch_task, job_id, request)
    return IngestResponse(
        job_id=job_id,
        status=JobStatus.RUNNING,
        tables=[request.table_name],
        row_count=0,
        message=f"กำลังดึงข้อมูลจากตาราง '{request.table_name}'...",
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

@router.get("/jobs", summary="ดูสถานะ jobs ทั้งหมด")
def list_jobs():
    return {"jobs": job_store.list_jobs()}


@router.get("/jobs/{job_id}", summary="ดูสถานะ job")
def get_job(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"ไม่พบ job_id: {job_id}")
    return {
        "job_id":    job["id"],
        "status":    job["status"],
        "has_data":  job["data"] is not None,
        "row_count": len(job["data"]) if job["data"] is not None else 0,
        "error":     job.get("error"),
    }

# ---------------------------------------------------------------
# AGENT PUSH — รับข้อมูลจาก Docker Agent ของบริษัท
# ---------------------------------------------------------------

class AgentPushRequest(BaseModel):
    table_name: str
    data:       list
    row_count:  int
    synced_at:  str
    api_key:    Optional[str] = None

@router.post("/push", summary="รับข้อมูลจาก Docker Agent")
def agent_push(request: AgentPushRequest, req: Request, background_tasks: BackgroundTasks):
    # ตรวจสอบ API Key จาก header
    api_key = req.headers.get("X-API-Key", "")
    expected = os.getenv("AGENT_API_KEY", "dev-key")
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    if not request.data:
        raise HTTPException(status_code=400, detail="ไม่มีข้อมูล")

    try:
        df = pd.DataFrame(request.data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"แปลงข้อมูลไม่ได้: {e}")

    job_id = job_store.create()
    job_store.update(job_id, data=df, status="done")

    # รัน auto pipeline ใน background
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
        "message":    f"✅ รับข้อมูล '{request.table_name}' สำเร็จ {len(df)} แถว",
        "next_step":  f"POST /pipeline/clean  body: {{\"job_id\": \"{job_id}\"}}",
    }

