"""
models/schemas.py
กำหนด "รูปร่าง" ของข้อมูลที่รับ-ส่งใน API
ใช้ Pydantic ซึ่ง FastAPI ใช้ validate ข้อมูลให้อัตโนมัติ
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ---- Enums ---------------------------------------------------------------

class ConnectionType(str, Enum):
    """ประเภท database ที่รองรับ"""
    POSTGRES = "postgres"
    MYSQL    = "mysql"


class JobStatus(str, Enum):
    """สถานะของ pipeline job"""
    PENDING    = "pending"
    RUNNING    = "running"
    DONE       = "done"
    FAILED     = "failed"


# ---- Ingest Layer --------------------------------------------------------

class DBConnectionRequest(BaseModel):
    """
    ข้อมูลที่บริษัทส่งมาเพื่อเชื่อมต่อฐานข้อมูล
    ตัวอย่าง:
        {
            "db_type": "postgres",
            "host": "db.mycompany.com",
            "port": 5432,
            "database": "sales_db",
            "username": "readonly_user",
            "password": "secret"
        }
    """
    db_type:  ConnectionType
    host:     str
    port:     int              = Field(default=5432, description="Default 5432=Postgres, 3306=MySQL")
    database: str
    username: str
    password: str
    api_key:  Optional[str]   = Field(None, description="API Key ของบริษัท (ถ้ามี)")


class IngestResponse(BaseModel):
    """ผลลัพธ์หลังรับข้อมูลสำเร็จ"""
    job_id:    str             # UUID สำหรับ track งาน
    status:    JobStatus
    tables:    List[str]       # รายชื่อตารางที่พบ
    row_count: int
    message:   str


# ---- ETL / Pipeline Layer ------------------------------------------------

class ColumnProfile(BaseModel):
    """
    สรุปข้อมูลของแต่ละ column
    สร้างโดย ETL cleaner อัตโนมัติ
    """
    name:           str
    dtype:          str            # int, float, string, datetime, category
    null_count:     int
    null_percent:   float
    unique_count:   int
    sample_values:  List[Any]      # ตัวอย่างค่า 5 ตัว
    issues:         List[str]      # ปัญหาที่เจอ เช่น ["มี null 20%", "พบ outlier"]


class CleanReport(BaseModel):
    """รายงานผลการทำความสะอาดข้อมูล"""
    job_id:            str
    original_rows:     int
    cleaned_rows:      int
    removed_rows:      int
    columns:           List[ColumnProfile]
    quality_score:     float       # 0-100 คะแนนคุณภาพข้อมูล
    issues_summary:    List[str]   # สรุปปัญหาทั้งหมดที่พบ
    created_at:        datetime


class PipelineRequest(BaseModel):
    """คำขอ run ETL pipeline"""
    job_id:          str
    target_table:    str
    clean_options:   Optional[Dict[str, Any]] = Field(
        default={
            "remove_duplicates": True,
            "fill_nulls": "mean",      # mean / median / mode / drop
            "normalize_dates": True,
            "remove_outliers": False,
        }
    )


# ---- AI Analyze Layer ----------------------------------------------------

class AnalysisRequest(BaseModel):
    """
    คำขอให้ AI วิเคราะห์ข้อมูล
    สามารถระบุ focus_areas เพื่อให้วิเคราะห์เฉพาะด้าน
    """
    job_id:       str
    company_name: Optional[str] = "บริษัท"
    focus_areas:  List[str]     = Field(
        default=["trend", "anomaly", "kpi_summary"],
        description="หัวข้อที่ต้องการวิเคราะห์"
    )
    audience:     str           = Field(
        default="executive",
        description="กลุ่มผู้รับรายงาน: executive / analyst / operations"
    )


class AnalysisResult(BaseModel):
    """ผลวิเคราะห์จาก AI"""
    job_id:         str
    summary:        str          # สรุปภาพรวม 2-3 ย่อหน้า
    key_insights:   List[str]    # insights สำคัญ 5-10 ข้อ
    anomalies:      List[str]    # ข้อมูลผิดปกติที่พบ
    recommendations: List[str]   # คำแนะนำ action items
    charts_config:  List[Dict]   # config สำหรับสร้าง chart ใน Streamlit
    created_at:     datetime


# ---- Export Layer --------------------------------------------------------

class ExportRequest(BaseModel):
    """คำขอส่งออกรายงาน"""
    job_id:      str
    format:      str  = Field(default="pdf", description="pdf / pptx / json")
    language:    str  = Field(default="th",  description="th / en")
    logo_url:    Optional[str] = None   # URL โลโก้บริษัท (optional)
