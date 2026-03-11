"""
services/cleaner.py
หัวใจของ ETL Pipeline — ทำความสะอาดข้อมูลอัตโนมัติ

Flow:
    raw DataFrame → detect types → fix nulls → remove dupes
                 → fix dates → detect outliers → return clean df + report
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple
import logging

from models.schemas import CleanReport, ColumnProfile

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    ทำความสะอาด DataFrame อัตโนมัติ
    ใช้งาน:
        cleaner = DataCleaner(df)
        clean_df, report = cleaner.run()
    """

    def __init__(self, df: pd.DataFrame, job_id: str, options: dict = None):
        self.original_df = df.copy()
        self.df = df.copy()
        self.job_id = job_id
        self.issues_log = []  # เก็บปัญหาทั้งหมดที่พบ

        # ค่า default ถ้าไม่ระบุ options
        self.options = {
            "remove_duplicates": True,
            "fill_nulls": "mean",
            "normalize_dates": True,
            "remove_outliers": False,
        }
        if options:
            self.options.update(options)

    # ------------------------------------------------------------------
    # PUBLIC METHOD - เรียกใช้จากภายนอก
    # ------------------------------------------------------------------

    def run(self) -> Tuple[pd.DataFrame, CleanReport]:
        """
        รัน pipeline ทั้งหมดตามลำดับ แล้วคืน clean df + report
        """
        logger.info(f"[{self.job_id}] เริ่มทำความสะอาดข้อมูล {len(self.df)} แถว")

        # ขั้นตอนการทำความสะอาด (เรียงตามลำดับสำคัญ)
        self._step_detect_types()
        self._step_remove_duplicates()
        self._step_handle_nulls()
        self._step_normalize_dates()
        self._step_fix_numeric_formats()
        if self.options.get("remove_outliers"):
            self._step_remove_outliers()

        report = self._build_report()
        logger.info(f"[{self.job_id}] ทำความสะอาดเสร็จ คะแนน: {report.quality_score:.1f}/100")

        return self.df, report

    # ------------------------------------------------------------------
    # STEP 1: ตรวจจับและแปลงประเภทข้อมูล
    # ------------------------------------------------------------------

    def _step_detect_types(self):
        """
        ลอง cast ทุก column ให้เป็นประเภทที่เหมาะสม
        เช่น column "age" ที่เป็น string → แปลงเป็น int
        """
        for col in self.df.columns:
            # ถ้าเป็น object (string) ลองแปลงเป็น numeric ก่อน
            if self.df[col].dtype == object:
                converted = pd.to_numeric(self.df[col], errors="coerce")
                # ถ้าแปลงได้เกิน 80% ของแถว ถือว่าเป็น numeric column
                success_rate = converted.notna().sum() / len(self.df)
                if success_rate > 0.8:
                    self.df[col] = converted
                    self.issues_log.append(f"'{col}': แปลงจาก string → numeric สำเร็จ")

    # ------------------------------------------------------------------
    # STEP 2: ลบแถวซ้ำ
    # ------------------------------------------------------------------

    def _step_remove_duplicates(self):
        if not self.options.get("remove_duplicates"):
            return

        before = len(self.df)
        self.df = self.df.drop_duplicates()
        removed = before - len(self.df)

        if removed > 0:
            self.issues_log.append(f"ลบแถวซ้ำออก {removed} แถว ({removed/before*100:.1f}%)")

    # ------------------------------------------------------------------
    # STEP 3: จัดการ Null / Missing values
    # ------------------------------------------------------------------

    def _step_handle_nulls(self):
        strategy = self.options.get("fill_nulls", "mean")

        for col in self.df.columns:
            null_count = self.df[col].isna().sum()
            if null_count == 0:
                continue

            null_pct = null_count / len(self.df) * 100

            if null_pct > 60:
                # มี null มากเกินไป → ลบ column ทิ้ง
                self.df.drop(columns=[col], inplace=True)
                self.issues_log.append(f"'{col}': ลบ column ทิ้ง (null {null_pct:.0f}%)")
                continue

            # เลือกวิธี fill ตาม dtype
            if pd.api.types.is_numeric_dtype(self.df[col]):
                if strategy == "mean":
                    fill_val = self.df[col].mean()
                elif strategy == "median":
                    fill_val = self.df[col].median()
                elif strategy == "mode":
                    fill_val = self.df[col].mode()[0]
                else:  # "drop"
                    self.df.dropna(subset=[col], inplace=True)
                    self.issues_log.append(f"'{col}': ลบแถวที่มี null ({null_count} แถว)")
                    continue

                self.df[col] = self.df[col].fillna(fill_val)
                self.issues_log.append(
                    f"'{col}': เติม null {null_count} ค่า ด้วย {strategy}={fill_val:.2f}"
                )

            else:  # string / category
                # เติมด้วย mode (ค่าที่พบบ่อยที่สุด)
                if len(self.df[col].dropna()) > 0:
                    fill_val = self.df[col].mode()[0]
                    self.df[col].fillna(fill_val, inplace=True)
                    self.issues_log.append(f"'{col}': เติม null {null_count} ค่า ด้วย '{fill_val}'")

    # ------------------------------------------------------------------
    # STEP 4: แปลงวันที่ให้เป็น datetime
    # ------------------------------------------------------------------

    def _step_normalize_dates(self):
        if not self.options.get("normalize_dates"):
            return

        # Keywords ที่มักบ่งบอกว่า column นี้เป็นวันที่
        date_keywords = ["date", "time", "วัน", "เวลา", "created", "updated", "at", "on"]

        for col in self.df.columns:
            if self.df[col].dtype != object:
                continue

            col_lower = col.lower()
            if any(kw in col_lower for kw in date_keywords):
                try:
                    self.df[col] = pd.to_datetime(self.df[col], infer_datetime_format=True)
                    self.issues_log.append(f"'{col}': แปลงเป็น datetime สำเร็จ")
                except Exception:
                    pass  # ถ้าแปลงไม่ได้ก็ข้ามไป

    # ------------------------------------------------------------------
    # STEP 5: แปลง format ตัวเลข (เช่น "1,234.56" → 1234.56)
    # ------------------------------------------------------------------

    def _step_fix_numeric_formats(self):
        for col in self.df.columns:
            if self.df[col].dtype != object:
                continue

            # ลอง strip comma แล้วแปลงเป็น float
            sample = self.df[col].dropna().head(10)
            cleaned = sample.str.replace(",", "", regex=False).str.strip()
            converted = pd.to_numeric(cleaned, errors="coerce")

            if converted.notna().sum() / max(len(sample), 1) > 0.8:
                self.df[col] = pd.to_numeric(
                    self.df[col].astype(str).str.replace(",", "", regex=False).str.strip(),
                    errors="coerce"
                )
                self.issues_log.append(f"'{col}': แก้ไข format ตัวเลข (ลบ comma)")

    # ------------------------------------------------------------------
    # STEP 6 (optional): ลบ Outliers ด้วย IQR method
    # ------------------------------------------------------------------

    def _step_remove_outliers(self):
        """
        IQR method: ข้อมูลที่อยู่นอก [Q1 - 1.5*IQR, Q3 + 1.5*IQR] ถือเป็น outlier
        """
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        before = len(self.df)

        for col in numeric_cols:
            Q1  = self.df[col].quantile(0.25)
            Q3  = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR

            outlier_mask = (self.df[col] < lower) | (self.df[col] > upper)
            outlier_count = outlier_mask.sum()

            if outlier_count > 0:
                self.df = self.df[~outlier_mask]
                self.issues_log.append(
                    f"'{col}': ลบ outlier {outlier_count} ค่า "
                    f"(range [{lower:.2f}, {upper:.2f}])"
                )

        removed = before - len(self.df)
        if removed:
            self.issues_log.append(f"รวมลบ outliers {removed} แถว")

    # ------------------------------------------------------------------
    # สร้าง Report
    # ------------------------------------------------------------------

    def _build_report(self) -> CleanReport:
        """รวบรวมสถิติทั้งหมดแล้วสร้าง CleanReport"""
        columns_profile = []

        for col in self.df.columns:
            dtype = str(self.df[col].dtype)

            # ตรวจหาปัญหาที่ยังเหลืออยู่หลัง clean
            col_issues = []
            null_count = int(self.df[col].isna().sum())
            if null_count > 0:
                col_issues.append(f"ยังมี null {null_count} ค่า")

            if pd.api.types.is_numeric_dtype(self.df[col]):
                skew = self.df[col].skew()
                if abs(skew) > 2:
                    col_issues.append(f"ข้อมูลเบ้ (skewness={skew:.1f})")

            profile = ColumnProfile(
                name=col,
                dtype=dtype,
                null_count=null_count,
                null_percent=round(null_count / max(len(self.df), 1) * 100, 2),
                unique_count=int(self.df[col].nunique()),
                sample_values=self.df[col].dropna().head(5).tolist(),
                issues=col_issues,
            )
            columns_profile.append(profile)

        # คำนวณ quality score (0-100)
        total_cells     = len(self.original_df) * len(self.original_df.columns)
        null_cells      = int(self.df.isna().sum().sum())
        dup_rows        = int(self.original_df.duplicated().sum())
        quality_score   = max(0, 100 - (null_cells / max(total_cells, 1)) * 50
                                      - (dup_rows / max(len(self.original_df), 1)) * 30)

        return CleanReport(
            job_id=self.job_id,
            original_rows=len(self.original_df),
            cleaned_rows=len(self.df),
            removed_rows=len(self.original_df) - len(self.df),
            columns=columns_profile,
            quality_score=round(quality_score, 1),
            issues_summary=self.issues_log,
            created_at=datetime.utcnow(),
        )
