"""
tests/test_cleaner.py
ทดสอบ DataCleaner ด้วยข้อมูลจำลอง
รัน: python -m pytest tests/ -v
"""

import sys
sys.path.insert(0, "../backend")

import pandas as pd
import numpy as np
import pytest
from backend.services.cleaner import DataCleaner


@pytest.fixture
def dirty_df():
    """สร้าง DataFrame ที่มีปัญหาต่างๆ สำหรับทดสอบ"""
    return pd.DataFrame({
        "id":       [1, 2, 2, 3, 4, 5],           # มีซ้ำ (row 2)
        "name":     ["Alice", "Bob", None, "Dave", "Eve", "Frank"],  # มี null
        "revenue":  ["1,200", "950", "1,100", "800", None, "2,000"], # format ผิด + null
        "date":     ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        "age":      [25, 30, 30, 28, None, 35],    # มี null
    })


def test_remove_duplicates(dirty_df):
    cleaner = DataCleaner(dirty_df, "test-001")
    clean_df, report = cleaner.run()

    # ต้องลบแถวซ้ำออก (จาก 6 → 5 แถว)
    assert len(clean_df) == 5
    assert report.removed_rows >= 1


def test_fix_numeric_format(dirty_df):
    cleaner = DataCleaner(dirty_df, "test-002")
    clean_df, _ = cleaner.run()

    # revenue "1,200" ต้องแปลงเป็น 1200.0
    assert pd.api.types.is_numeric_dtype(clean_df["revenue"])


def test_fill_null_numeric(dirty_df):
    cleaner = DataCleaner(dirty_df, "test-003", options={"fill_nulls": "mean"})
    clean_df, _ = cleaner.run()

    # age และ revenue ต้องไม่มี null
    assert clean_df["age"].isna().sum() == 0


def test_quality_score(dirty_df):
    cleaner = DataCleaner(dirty_df, "test-004")
    _, report = cleaner.run()

    # คะแนนต้องอยู่ระหว่าง 0-100
    assert 0 <= report.quality_score <= 100


def test_issues_logged(dirty_df):
    cleaner = DataCleaner(dirty_df, "test-005")
    _, report = cleaner.run()

    # ต้องมี issues ที่บันทึกไว้
    assert len(report.issues_summary) > 0
    print("\nIssues found:")
    for issue in report.issues_summary:
        print(f"  • {issue}")


if __name__ == "__main__":
    # รันทดสอบแบบ manual
    df = pd.DataFrame({
        "id":      [1, 2, 2, 3],
        "revenue": ["1,200", "950", "950", None],
        "date":    ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"],
    })
    cleaner  = DataCleaner(df, "manual-test")
    clean_df, report = cleaner.run()

    print(f"\n✅ Clean complete!")
    print(f"   Rows: {report.original_rows} → {report.cleaned_rows}")
    print(f"   Quality Score: {report.quality_score}/100")
    print(f"\n   Issues:")
    for issue in report.issues_summary:
        print(f"     • {issue}")

    print(f"\n   Clean data preview:")
    print(clean_df.to_string())
