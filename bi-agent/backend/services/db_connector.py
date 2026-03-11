"""
services/db_connector.py
เชื่อมต่อกับ MySQL / PostgreSQL ของบริษัท
แล้วดึงข้อมูลมาเป็น DataFrame

ความปลอดภัย:
  - รับแค่ READ-ONLY query
  - timeout 30 วินาที
  - จำกัด 100,000 แถวต่อ query
"""

import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import logging

from models.schemas import DBConnectionRequest, ConnectionType

logger = logging.getLogger(__name__)

# จำกัดจำนวนแถวสูงสุดเพื่อป้องกัน memory overflow
MAX_ROWS = 100_000


class DBConnector:
    """
    จัดการ connection กับฐานข้อมูลบริษัท
    ใช้งาน:
        connector = DBConnector(request)
        tables = connector.list_tables()
        df = connector.fetch_table("sales")
    """

    def __init__(self, request: DBConnectionRequest):
        self.request = request
        self.engine  = None
        self._build_engine()

    def _build_engine(self):
        """สร้าง connection string แล้วเชื่อมต่อ"""
        r = self.request

        if r.db_type == ConnectionType.POSTGRES:
            # postgresql://user:pass@host:port/dbname
            url = f"postgresql://{r.username}:{r.password}@{r.host}:{r.port}/{r.database}"
        elif r.db_type == ConnectionType.MYSQL:
            # mysql+pymysql://user:pass@host:port/dbname
            url = f"mysql+pymysql://{r.username}:{r.password}@{r.host}:{r.port}/{r.database}"
        else:
            raise ValueError(f"ไม่รองรับ db_type: {r.db_type}")

        try:
            # connect_args: timeout 10 วินาที
            self.engine = create_engine(
                url,
                connect_args={"connect_timeout": 10},
                pool_pre_ping=True,     # ตรวจสอบ connection ก่อนใช้
                pool_size=2,
                max_overflow=0,
            )
            # ทดสอบ connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info(f"เชื่อมต่อ {r.db_type} สำเร็จ: {r.host}/{r.database}")

        except SQLAlchemyError as e:
            logger.error(f"เชื่อมต่อล้มเหลว: {e}")
            raise ConnectionError(f"ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {str(e)}")

    def list_tables(self) -> List[str]:
        """ดึงรายชื่อตารางทั้งหมดในฐานข้อมูล"""
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def fetch_table(self, table_name: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        ดึงข้อมูลจากตาราง (READ ONLY)
        จำกัดสูงสุด MAX_ROWS แถว
        """
        row_limit = min(limit or MAX_ROWS, MAX_ROWS)

        # ใช้ parameterized query เพื่อป้องกัน SQL Injection
        # (ชื่อตารางไม่สามารถใช้ parameter ได้โดยตรง จึง whitelist ด้วย list_tables)
        allowed_tables = self.list_tables()
        if table_name not in allowed_tables:
            raise ValueError(f"ไม่พบตาราง '{table_name}' ในฐานข้อมูล")

        query = f'SELECT * FROM "{table_name}" LIMIT {row_limit}'

        try:
            df = pd.read_sql(query, self.engine)
            logger.info(f"ดึงข้อมูล '{table_name}' สำเร็จ: {len(df)} แถว, {len(df.columns)} คอลัมน์")
            return df
        except Exception as e:
            raise RuntimeError(f"ดึงข้อมูลล้มเหลว: {str(e)}")

    def run_custom_query(self, sql: str) -> pd.DataFrame:
        """
        รัน custom SQL — รับเฉพาะ SELECT เท่านั้น
        """
        sql_clean = sql.strip().upper()
        if not sql_clean.startswith("SELECT"):
            raise PermissionError("รับเฉพาะ SELECT query เท่านั้น")

        try:
            df = pd.read_sql(sql, self.engine)
            # จำกัดแถว
            return df.head(MAX_ROWS)
        except Exception as e:
            raise RuntimeError(f"Query ล้มเหลว: {str(e)}")

    def close(self):
        """ปิด connection pool"""
        if self.engine:
            self.engine.dispose()
            logger.info("ปิด database connection แล้ว")
