"""
BI Agent - Backend API
Production-grade FastAPI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ingest, pipeline, analyze, export, admin

app = FastAPI(
    title="BI Agent API",
    description="AI-Powered Business Intelligence — From Raw Data to Boardroom Decks",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router,   prefix="/ingest",   tags=["Ingestion"])
app.include_router(pipeline.router, prefix="/pipeline", tags=["ETL"])
app.include_router(analyze.router,  prefix="/analyze",  tags=["AI Analysis"])
app.include_router(export.router,   prefix="/export",   tags=["Export"])
app.include_router(admin.router,    prefix="/admin",    tags=["Admin"])

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "BI Agent API v2.0 🚀"}

@app.get("/health", tags=["Health"])
def health():
    from services.job_store import job_store
    return {"status": "healthy", "stats": job_store.stats}
