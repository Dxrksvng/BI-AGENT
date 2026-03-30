"""
services/validation_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Validation Engine — ตรวจสอบว่าข้อมูลใน deck ถูกต้อง 100%

หลักการ:
  1. ทุกตัวเลขใน bullets/insights ต้องมาจาก stat report
  2. KPI ใน slides ต้องอยู่ใน approved KPI list
  3. Chart columns ต้องมีอยู่จริงใน dataset
  4. ถ้าผิด → auto-correct หรือแจ้งเตือน

ข้อมูลจากบริษัทจริง ต้องไม่มั่ว
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal


@dataclass
class ValidationResult:
    """ผลการตรวจสอบ"""
    is_valid: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    corrected_fields: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0  # 0-100: ความมั่นใจว่าข้อมูลถูกต้อง


class ValidationEngine:
    """
    ตรวจสอบความถูกต้องของข้อมูลใน deck plan กับ statistical report

    ป้องกัน AI hallucination โดยการตรวจสอบทุกตัวเลข
    """

    def __init__(self, stat_report: dict, deck_plan: dict):
        self.stat_report = stat_report
        self.deck_plan = deck_plan

        # สร้าง ground truth lookup tables
        self.kpi_lookup = self._build_kpi_lookup()
        self.column_stats = self._build_column_stats()
        self.chart_recs = self._build_chart_recommendations()

    def _build_kpi_lookup(self) -> Dict[str, Dict]:
        """สร้าง lookup สำหรับ KPIs"""
        lookup = {}
        for kpi in self.stat_report.get("kpis", []):
            key = kpi["name"].lower().strip()
            lookup[key] = {
                "value": kpi["value"],
                "formatted": kpi["formatted"],
                "unit": kpi.get("unit", ""),
                "status": kpi["status"],
                "name": kpi["name"]
            }
        return lookup

    def _build_column_stats(self) -> Dict[str, Dict]:
        """สร้าง lookup สำหรับ column statistics"""
        stats = {}
        for col in self.stat_report.get("column_stats", []):
            key = col["name"]
            stats[key] = {
                "name": col["name"],
                "dtype": col["dtype"],
                "mean": col.get("mean"),
                "median": col.get("median"),
                "min": col.get("min"),
                "max": col.get("max"),
                "std": col.get("std"),
                "n_unique": col.get("n_unique", 0),
            }
        return stats

    def _build_chart_recommendations(self) -> Dict[str, Dict]:
        """สร้าง lookup สำหรับ chart recommendations"""
        recs = {}
        for i, chart in enumerate(self.stat_report.get("chart_recommendations", [])):
            key = f"{chart['x_column']}_{chart['y_column']}"
            recs[key] = {
                "chart_type": chart["chart_type"],
                "x_column": chart["x_column"],
                "y_column": chart["y_column"],
                "priority": chart.get("priority", 99),
            }
        return recs

    def validate_deck_plan(self) -> ValidationResult:
        """
        ตรวจสอบ deck plan ทั้งหมด

        Returns:
            ValidationResult พร้อมข้อมูลเตือนและการแก้ไข
        """
        warnings = []
        errors = []
        corrected = {}

        slides = self.deck_plan.get("slides", [])

        # 1. ตรวจสอบแต่ละ slide
        for i, slide in enumerate(slides):
            slide_warnings, slide_errors, slide_corrected = self._validate_slide(slide)
            warnings.extend([f"Slide {i+1}: {w}" for w in slide_warnings])
            errors.extend([f"Slide {i+1}: {e}" for e in slide_errors])

            if slide_corrected:
                corrected[f"slide_{i+1}"] = slide_corrected

        # 2. คำนวณ confidence score
        confidence = self._calculate_confidence(warnings, errors, len(slides))

        result = ValidationResult(
            is_valid=len(errors) == 0,
            warnings=warnings,
            errors=errors,
            corrected_fields=corrected,
            confidence=confidence
        )

        # Log ผลการตรวจสอบ
        self._log_validation_result(result)

        return result

    def _validate_slide(self, slide: dict) -> Tuple[List[str], List[str], Dict]:
        """ตรวจสอบ slide เดียว"""
        warnings = []
        errors = []
        corrected = {}

        # 1. ตรวจสอบ KPIs
        if slide.get("kpis"):
            kpi_warnings, kpi_errors, kpi_corrected = self._validate_kpis(slide["kpis"])
            warnings.extend(kpi_warnings)
            errors.extend(kpi_errors)
            if kpi_corrected:
                corrected["kpis"] = kpi_corrected

        # 2. ตรวจสอบ bullets (ตัวเลข)
        if slide.get("bullets"):
            bullet_warnings, bullet_corrected = self._validate_bullets(
                slide["bullets"],
                slide.get("title", "")
            )
            warnings.extend(bullet_warnings)
            if bullet_corrected:
                corrected["bullets"] = bullet_corrected

        # 3. ตรวจสอบ chart columns
        if slide.get("chart_type") and slide.get("chart_type") != "none":
            chart_warnings, chart_errors = self._validate_chart(slide)
            warnings.extend(chart_warnings)
            errors.extend(chart_errors)

        # 4. ตรวจสอบ insight
        if slide.get("insight"):
            insight_warnings, insight_corrected = self._validate_insight(
                slide["insight"],
                slide.get("title", "")
            )
            warnings.extend(insight_warnings)
            if insight_corrected:
                corrected["insight"] = insight_corrected

        return warnings, errors, corrected

    def _validate_kpis(self, kpis: List[dict]) -> Tuple[List[str], List[str], Optional[dict]]:
        """ตรวจสอบ KPIs ว่ามีอยู่จริงใน stat report"""
        warnings = []
        errors = []
        corrected = []

        for i, kpi in enumerate(kpis):
            kpi_name = kpi.get("name", "").lower().strip()
            kpi_value = kpi.get("value") or kpi.get("formatted", "")

            # ค้นหา KPI ใน stat report
            found_kpi = None
            for key, kpi_data in self.kpi_lookup.items():
                if kpi_name in key or key in kpi_name:
                    found_kpi = kpi_data
                    break

            if not found_kpi:
                warnings.append(f"KPI '{kpi_name}' ไม่พบใน statistical report")
                # ใช้ KPI ตามต้นฉบับ
                corrected.append(kpi)
                continue

            # ตรวจสอบค่า
            stat_value = str(found_kpi["value"])
            kpi_value_str = str(kpi_value).replace(",", "").replace("$", "").replace("%", "")

            try:
                if kpi_value_str and abs(float(kpi_value_str) - float(stat_value)) > 0.01 * float(stat_value):
                    warnings.append(
                        f"KPI '{kpi_name}' ค่าไม่ตรง: "
                        f"slide={kpi_value}, stat_report={found_kpi['formatted']}"
                    )
                    corrected.append(found_kpi)  # ใช้ค่าจาก stat report
                else:
                    corrected.append(found_kpi)
            except (ValueError, TypeError):
                corrected.append(kpi)  # ไม่สามารถเปรียบเทียบได้

        return warnings, errors, corrected if corrected else None

    def _validate_bullets(self, bullets: List[str], title: str) -> Tuple[List[str], Optional[List[str]]]:
        """
        ตรวจสอบ bullets ว่าเลขที่อ้างถึงถูกต้อง

        Strategy:
        1. Extract ตัวเลขจาก bullets
        2. Check ว่าเลขเหล่านี้มีอยู่ใน stat report ไหม
        3. ถ้าไม่ → แจ้งเตือน
        """
        warnings = []
        corrected = []

        for bullet in bullets:
            # Extract ตัวเลขจาก bullet
            numbers = self._extract_numbers(bullet)

            if not numbers:
                corrected.append(bullet)
                continue

            # Check ว่าเลขเหล่านี้สอดคล้องกับ stat report ไหม
            is_suspicious = False
            for num in numbers:
                if not self._number_exists_in_stat(num):
                    warnings.append(
                        f"ตัวเลข '{num}' ใน bullet อาจไม่ถูกต้อง "
                        f"(ไม่พบใน statistical report): '{bullet[:50]}...'"
                    )
                    is_suspicious = True

            corrected.append(bullet)

        return warnings, corrected if warnings else None

    def _validate_chart(self, slide: dict) -> Tuple[List[str], List[str]]:
        """ตรวจสอบ chart ว่า columns มีอยู่จริง"""
        warnings = []
        errors = []

        chart_type = slide.get("chart_type", "")
        x_col = slide.get("x_column", "")
        y_col = slide.get("y_column", "")

        # ตรวจสอบ chart type validity
        valid_types = {
            "bar_vertical", "bar_horizontal", "line", "donut",
            "scatter", "area", "none", "kpi_card"
        }
        if chart_type not in valid_types:
            errors.append(f"Invalid chart type: '{chart_type}'")

        # ตรวจสอบ columns
        if x_col and x_col not in self.column_stats:
            errors.append(f"x_column '{x_col}' ไม่พบใน dataset")

        if y_col and y_col not in self.column_stats:
            errors.append(f"y_column '{y_col}' ไม่พบใน dataset")

        # ตรวจสอบความเหมาะสมของ chart type vs column types
        if chart_type != "none" and x_col and y_col:
            col_warnings, col_errors = self._validate_chart_type_match(
                chart_type, x_col, y_col
            )
            warnings.extend(col_warnings)
            errors.extend(col_errors)

        return warnings, errors

    def _validate_chart_type_match(
        self, chart_type: str, x_col: str, y_col: str
    ) -> Tuple[List[str], List[str]]:
        """ตรวจสอบว่า chart type เหมาะสมกับ column types"""
        warnings = []
        errors = []

        x_stat = self.column_stats.get(x_col, {})
        y_stat = self.column_stats.get(y_col, {})

        x_type = x_stat.get("dtype", "")
        y_type = y_stat.get("dtype", "")

        # Rule: line/area ต้องมี datetime x-axis
        if chart_type in ("line", "area"):
            if x_type != "datetime":
                errors.append(
                    f"Chart type '{chart_type}' ต้องใช้ datetime column เป็น x-axis "
                    f"(current: {x_col} is {x_type})"
                )

        # Rule: scatter ต้องมี numeric x และ y
        if chart_type == "scatter":
            if x_type != "numeric":
                errors.append(
                    f"Scatter chart ต้องใช้ numeric column เป็น x-axis "
                    f"(current: {x_col} is {x_type})"
                )
            if y_type != "numeric":
                errors.append(
                    f"Scatter chart ต้องใช้ numeric column เป็น y-axis "
                    f"(current: {y_col} is {y_type})"
                )

        # Rule: donut ต้องมี categorical x และ numeric y
        if chart_type == "donut":
            if x_type != "categorical":
                warnings.append(
                    f"Donut chart ควรใช้ categorical column เป็น x-axis "
                    f"(current: {x_col} is {x_type})"
                )
            if y_type != "numeric":
                errors.append(
                    f"Donut chart ต้องใช้ numeric column เป็น y-axis "
                    f"(current: {y_col} is {y_type})"
                )

        # Rule: bar_* ต้องมี categorical x และ numeric y
        if chart_type in ("bar_vertical", "bar_horizontal"):
            if x_type != "categorical":
                warnings.append(
                    f"Bar chart ควรใช้ categorical column เป็น x-axis "
                    f"(current: {x_col} is {x_type})"
                )
            if y_type != "numeric":
                errors.append(
                    f"Bar chart ต้องใช้ numeric column เป็น y-axis "
                    f"(current: {y_col} is {y_type})"
                )

        return warnings, errors

    def _validate_insight(self, insight: str, title: str) -> Tuple[List[str], Optional[str]]:
        """ตรวจสอบ insight ว่าเลขถูกต้อง"""
        warnings = []

        # Extract ตัวเลขจาก insight
        numbers = self._extract_numbers(insight)

        if not numbers:
            return warnings, None

        # Check ว่าเลขเหล่านี้สอดคล้องกับ stat report ไหม
        for num in numbers:
            if not self._number_exists_in_stat(num):
                warnings.append(
                    f"ตัวเลข '{num}' ใน insight อาจไม่ถูกต้อง: '{insight[:50]}...'"
                )

        return warnings, None

    def _extract_numbers(self, text: str) -> List[str]:
        """Extract ตัวเลขจาก text"""
        # Match ตัวเลขทั้งแบบ integer และ decimal, รวมถึงเครื่องหมาย %
        pattern = r'\b[\d,]+(?:\.\d+)?\b%?'
        return re.findall(pattern, text)

    def _number_exists_in_stat(self, num_str: str) -> bool:
        """
        Check ว่าตัวเลขมีอยู่ใน stat report ไหม

        Strategy:
        1. Try exact match in KPIs
        2. Try match in column stats (mean, median, min, max)
        """
        # Clean number string
        clean_num = num_str.replace(",", "").replace("%", "").strip()
        try:
            num_val = float(clean_num)
        except ValueError:
            return False

        # Check in KPIs
        for kpi_data in self.kpi_lookup.values():
            kpi_val = kpi_data["value"]
            if isinstance(kpi_val, (int, float)) and abs(kpi_val - num_val) < 0.01:
                return True

        # Check in column stats
        for col_stat in self.column_stats.values():
            for stat_key in ["mean", "median", "min", "max"]:
                stat_val = col_stat.get(stat_key)
                if stat_val and abs(float(stat_val) - num_val) < 0.01:
                    return True

        return False

    def _calculate_confidence(self, warnings: List[str], errors: List[str], slide_count: int) -> float:
        """คำนวณ confidence score"""
        if slide_count == 0:
            return 0.0

        base_score = 100.0

        # ลดคะแนนตาม errors
        base_score -= len(errors) * 10

        # ลดคะแนนตาม warnings
        base_score -= len(warnings) * 2

        # ต่ำสุด 0 สูงสุด 100
        return round(max(0.0, min(100.0, base_score)), 1)

    def _log_validation_result(self, result: ValidationResult):
        """Log ผลการตรวจสอบ"""
        print(f"\n{'='*60}")
        print(f"VALIDATION ENGINE RESULT")
        print(f"{'='*60}")
        print(f"Valid: {result.is_valid}")
        print(f"Confidence: {result.confidence}%")

        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for w in result.warnings[:10]:
                print(f"  ⚠️  {w}")
            if len(result.warnings) > 10:
                print(f"  ... and {len(result.warnings) - 10} more")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for e in result.errors[:10]:
                print(f"  ❌ {e}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more")

        if result.corrected_fields:
            print(f"\nAuto-corrected fields: {list(result.corrected_fields.keys())}")

        print(f"{'='*60}\n")


# ─── Public API ───────────────────────────────────────────────────────────────

def validate_deck_plan(stat_report: dict, deck_plan: dict) -> ValidationResult:
    """
    Main entry point. Validate deck plan against statistical report.

    Args:
        stat_report: Statistical report from statistical_engine.py
        deck_plan: Deck plan from ai_deck_designer.py

    Returns:
        ValidationResult with warnings, errors, and corrections
    """
    engine = ValidationEngine(stat_report, deck_plan)
    return engine.validate_deck_plan()


def apply_corrections(deck_plan: dict, validation_result: ValidationResult) -> dict:
    """
    Apply auto-corrections to deck plan

    Args:
        deck_plan: Original deck plan
        validation_result: Result from validate_deck_plan

    Returns:
        Corrected deck plan
    """
    if not validation_result.corrected_fields:
        return deck_plan

    corrected_plan = deck_plan.copy()
    slides = corrected_plan.get("slides", []).copy()

    for slide_key, corrections in validation_result.corrected_fields.items():
        if slide_key.startswith("slide_"):
            slide_idx = int(slide_key.split("_")[1]) - 1
            if 0 <= slide_idx < len(slides):
                for field, value in corrections.items():
                    slides[slide_idx][field] = value

    corrected_plan["slides"] = slides

    # Add validation metadata
    corrected_plan["_validation"] = {
        "is_valid": validation_result.is_valid,
        "confidence": validation_result.confidence,
        "warning_count": len(validation_result.warnings),
        "error_count": len(validation_result.errors),
    }

    return corrected_plan
