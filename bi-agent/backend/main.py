"""
BI Agent - Backend API
Entry point สำหรับ FastAPI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ingest, pipeline, analyze, export

app = FastAPI(
    title="BI Agent API",
    description="Business Intelligence AI Agent - รับข้อมูล ทำความสะอาด วิเคราะห์ ออกรายงาน",
    version="1.0.0",
)

# อนุญาตให้ frontend (Streamlit) เรียก API ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ใน production ควรระบุ domain จริง
    allow_methods=["*"],
    allow_headers=["*"],
)

# ลงทะเบียน routers ทั้งหมด
app.include_router(ingest.router,   prefix="/ingest",   tags=["1. รับข้อมูล"])
app.include_router(pipeline.router, prefix="/pipeline", tags=["2. ETL / Clean"])
app.include_router(analyze.router,  prefix="/analyze",  tags=["3. AI วิเคราะห์"])
app.include_router(export.router,   prefix="/export",   tags=["4. ส่งออกรายงาน"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "BI Agent API is running 🚀"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}
