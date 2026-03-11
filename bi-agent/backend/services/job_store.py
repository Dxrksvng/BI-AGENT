"""
services/job_store.py
เก็บสถานะของ jobs ทั้งหมด (ใช้ in-memory dict สำหรับ MVP)
ใน production ควรเปลี่ยนเป็น Redis หรือ PostgreSQL
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional


class JobStore:
    """
    Key-Value store สำหรับเก็บข้อมูล job
    แต่ละ job มี:
      - id:         UUID
      - status:     pending / running / done / failed
      - data:       DataFrame (หลังดึงข้อมูล)
      - clean_data: DataFrame (หลัง ETL)
      - report:     CleanReport
      - analysis:   AnalysisResult
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def create(self) -> str:
        """สร้าง job ใหม่ คืน job_id"""
        job_id = str(uuid.uuid4())
        self._store[job_id] = {
            "id":         job_id,
            "status":     "pending",
            "created_at": datetime.utcnow(),
            "data":       None,
            "clean_data": None,
            "report":     None,
            "analysis":   None,
            "error":      None,
        }
        return job_id

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(job_id)

    def update(self, job_id: str, **kwargs):
        """อัปเดตข้อมูลใน job"""
        if job_id not in self._store:
            raise KeyError(f"ไม่พบ job_id: {job_id}")
        self._store[job_id].update(kwargs)
        self._store[job_id]["updated_at"] = datetime.utcnow()

    def set_status(self, job_id: str, status: str, error: str = None):
        self.update(job_id, status=status, error=error)

    def list_jobs(self) -> list:
        """คืนรายการ jobs ทั้งหมด (ไม่รวม DataFrame)"""
        return [
            {k: v for k, v in job.items() if k not in ("data", "clean_data")}
            for job in self._store.values()
        ]


# Singleton — ทุก router ใช้ instance เดียวกัน
job_store = JobStore()
