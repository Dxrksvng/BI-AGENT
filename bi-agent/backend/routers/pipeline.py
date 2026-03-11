"""
routers/pipeline.py
Layer ที่ 2: ETL — รับ raw data แล้วทำความสะอาด

Endpoints:
  POST /pipeline/clean     — รัน ETL cleaner
  GET  /pipeline/report    — ดู clean report
  GET  /pipeline/preview   — preview ข้อมูลที่ clean แล้ว
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.schemas import PipelineRequest, CleanReport
from services.cleaner import DataCleaner
from services.job_store import job_store

router = APIRouter()


@router.post("/clean", summary="รัน ETL Pipeline")
def run_clean(request: PipelineRequest, background_tasks: BackgroundTasks):
    """
    ทำความสะอาดข้อมูลใน job ที่ระบุ
    ต้อง ingest ข้อมูลก่อน (มี data ใน job_store แล้ว)
    """
    job = job_store.get(request.job_id)

    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบ job_id นี้")

    if job["data"] is None:
        raise HTTPException(
            status_code=400,
            detail="ยังไม่มีข้อมูล กรุณา ingest ก่อน"
        )

    if job["status"] == "running":
        raise HTTPException(status_code=409, detail="Job กำลังทำงานอยู่แล้ว")

    job_store.set_status(request.job_id, "running")
    background_tasks.add_task(_clean_task, request)

    return {
        "job_id":  request.job_id,
        "status":  "running",
        "message": "กำลังทำความสะอาดข้อมูล...",
    }


def _clean_task(request: PipelineRequest):
    """Background task สำหรับ ETL"""
    try:
        job    = job_store.get(request.job_id)
        raw_df = job["data"]

        cleaner  = DataCleaner(raw_df, request.job_id, request.clean_options)
        clean_df, report = cleaner.run()

        job_store.update(
            request.job_id,
            clean_data=clean_df,
            report=report,
            status="done",
        )
    except Exception as e:
        job_store.set_status(request.job_id, "failed", error=str(e))


@router.get("/report/{job_id}", response_model=CleanReport, summary="ดู Clean Report")
def get_report(job_id: str):
    """ดูรายงานผลการทำความสะอาดข้อมูล"""
    job = job_store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบ job_id")

    if job["report"] is None:
        raise HTTPException(
            status_code=400,
            detail="ยังไม่มี report กรุณารัน /pipeline/clean ก่อน"
        )

    return job["report"]


@router.get("/preview/{job_id}", summary="Preview ข้อมูลที่ clean แล้ว")
def preview_data(job_id: str, rows: int = 20):
    """
    แสดงตัวอย่างข้อมูลหลัง clean
    params:
      rows — จำนวนแถวที่ต้องการดู (default 20)
    """
    job = job_store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="ไม่พบ job_id")

    if job["clean_data"] is None:
        raise HTTPException(status_code=400, detail="ยังไม่มีข้อมูล clean")

    df = job["clean_data"].head(rows)

    return {
        "job_id":   job_id,
        "columns":  list(df.columns),
        "dtypes":   df.dtypes.astype(str).to_dict(),
        "shape":    list(job["clean_data"].shape),
        "preview":  df.to_dict(orient="records"),
    }


@router.get("/stats/{job_id}", summary="สถิติพื้นฐานของข้อมูล")
def get_stats(job_id: str):
    """ดูสถิติ describe() ของข้อมูลที่ clean แล้ว"""
    job = job_store.get(job_id)

    if not job or job["clean_data"] is None:
        raise HTTPException(status_code=400, detail="ไม่พบข้อมูล clean")

    df    = job["clean_data"]
    stats = df.describe(include="all").fillna("").to_dict()

    return {"job_id": job_id, "statistics": stats}
