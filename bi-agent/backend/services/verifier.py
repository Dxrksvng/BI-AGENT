"""
services/verifier.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verification Engine — Validate all AI claims against source data

Features:
  - Parse AI query instructions
  - Execute queries against DataFrame
  - Generate audit trail for each claim
  - Confidence scoring
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import re


@dataclass
class DataClaim:
    """Single data claim with verification."""
    claim_id: str
    claim_type: str  # kpi, metric, comparison, trend
    slide_num: int
    description: str  # Original AI text

    # Verified data
    verified_value: Any
    row_count: int
    calculation: str  # Formula used

    # Verification status
    is_valid: bool
    confidence: float  # 0-100

    # Metadata
    source_columns: List[str]
    query_used: str


@dataclass
class VerificationReport:
    """Complete verification report for a deck."""
    total_claims: int
    verified_claims: int
    overall_confidence: float
    claims: List[DataClaim]
    unverified_claims: List[str]


class DataVerifier:
    """Verify AI claims against source DataFrame."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_cols = df.select_dtypes(exclude=[np.number, "datetime"]).columns.tolist()
        self.datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

    def _execute_query(self, query: Dict[str, Any]) -> Tuple[Any, int, str]:
        """Execute query against DataFrame.

        Returns: (value, row_count, calculation)
        """
        query_type = query.get("type", "")

        if query_type == "count":
            col = query.get("column")
            if col and col in self.df.columns:
                count = self.df[col].count()
                return count, count, f"COUNT({col})"
            return 0, 0, "COUNT()"

        elif query_type == "sum":
            col = query.get("column")
            if col and col in self.df.columns:
                total = self.df[col].sum()
                return total, len(self.df[col].dropna()), f"SUM({col})"
            return 0, 0, "SUM()"

        elif query_type == "avg":
            col = query.get("column")
            if col and col in self.df.columns:
                avg = self.df[col].mean()
                return avg, len(self.df[col].dropna()), f"AVG({col})"
            return 0, 0, "AVG()"

        elif query_type == "median":
            col = query.get("column")
            if col and col in self.df.columns:
                med = self.df[col].median()
                return med, len(self.df[col].dropna()), f"MEDIAN({col})"
            return 0, 0, "MEDIAN()"

        elif query_type == "min":
            col = query.get("column")
            if col and col in self.df.columns:
                min_val = self.df[col].min()
                return min_val, len(self.df[col]), f"MIN({col})"
            return 0, 0, "MIN()"

        elif query_type == "max":
            col = query.get("column")
            if col and col in self.df.columns:
                max_val = self.df[col].max()
                return max_val, len(self.df[col]), f"MAX({col})"
            return 0, 0, "MAX()"

        elif query_type == "group_count":
            group_col = query.get("group_by")
            if group_col and group_col in self.df.columns:
                grouped = self.df.groupby(group_col).size()
                return grouped.to_dict(), len(self.df), f"GROUP_COUNT({group_col})"
            return {}, 0, "GROUP_COUNT()"

        elif query_type == "group_sum":
            group_col = query.get("group_by")
            value_col = query.get("column")
            if group_col and group_col in self.df.columns and value_col in self.df.columns:
                grouped = self.df.groupby(group_col)[value_col].sum()
                return grouped.to_dict(), len(self.df), f"GROUP_SUM({value_col} BY {group_col})"
            return {}, 0, "GROUP_SUM()"

        elif query_type == "group_avg":
            group_col = query.get("group_by")
            value_col = query.get("column")
            if group_col and group_col in self.df.columns and value_col in self.df.columns:
                grouped = self.df.groupby(group_col)[value_col].mean()
                return grouped.to_dict(), len(self.df), f"GROUP_AVG({value_col} BY {group_col})"
            return {}, 0, "GROUP_AVG()"

        elif query_type == "percent":
            group_col = query.get("group_by")
            value_col = query.get("column")
            if group_col and group_col in self.df.columns and value_col in self.df.columns:
                total = self.df[value_col].sum()
                grouped = self.df.groupby(group_col)[value_col].sum()
                percs = {k: round(v / total * 100, 2) for k, v in grouped.items()}
                return percs, len(self.df), f"PERCENT({value_col} BY {group_col})"
            return {}, 0, "PERCENT()"

        elif query_type == "correlation":
            col1 = query.get("column1")
            col2 = query.get("column2")
            if col1 and col2 and col1 in self.numeric_cols and col2 in self.numeric_cols:
                corr = self.df[[col1, col2]].corr().iloc[0, 1]
                return round(corr, 3), len(self.df[[col1, col2]].dropna()), f"CORR({col1}, {col2})"
            return 0, 0, "CORR()"

        return 0, 0, "UNKNOWN"

    def _parse_query_from_text(self, text: str, available_cols: List[str]) -> Dict[str, Any]:
        """Parse query from AI text description.

        Examples:
        - "average of revenue by category" → {"type": "group_avg", "column": "revenue", "group_by": "category"}
        - "total churn rate" → {"type": "group_avg", "column": "churn_rate"}
        - "count of customers" → {"type": "count", "column": "customer_id"}
        """
        text_lower = text.lower()
        query = {}

        # Detect aggregation type
        agg_keywords = {
            "average": "avg", "mean": "avg", "avg": "avg",
            "total": "sum", "sum": "sum",
            "count": "count", "number of": "count",
            "percentage": "percent", "percent of": "percent",
            "median": "median",
            "minimum": "min",
            "maximum": "max",
            "correlation": "correlation", "correlated with": "correlation",
        }

        # Match aggregation keywords
        for keyword, agg_type in agg_keywords.items():
            if keyword in text_lower:
                query["type"] = agg_type
                break

        if "type" not in query:
            query["type"] = "avg"

        # Find column names
        for col in available_cols:
            if col.lower() in text_lower:
                if "column" not in query:
                    query["column"] = col
                elif "column2" in query or "column1" not in query:
                    # Second column for correlation
                    if "column1" not in query:
                        query["column1"] = col
                    else:
                        query["column2"] = col
                else:
                    # Already have column1, this is column2
                    query["column2"] = col
            else:
                # Already have column
                    pass

        # Find group_by column
        for col in self.categorical_cols:
            if col.lower() in text_lower and col not in query.values():
                query["group_by"] = col
                break

        # Detect "by" keyword for grouping
        by_pattern = r'by\s+(\w+)'
        match = re.search(by_pattern, text_lower)
        if match:
            group_word = match.group(1)
            for col in available_cols:
                if group_word in col.lower() and col not in query.values():
                    query["group_by"] = col
                    break

        return query

    def verify_slide_claims(self, slide_spec: Dict[str, Any]) -> List[DataClaim]:
        """Verify all claims in a single slide."""
        claims = []
        slide_num = slide_spec.get("slide_num", 0)

        # Verify KPIs
        for kpi in slide_spec.get("kpis", []):
            claim_id = f"kpi_{slide_num}_{kpi.get('name', 'unknown').replace(' ', '_')}"
            kpi_name = kpi.get("name", "")
            kpi_value = kpi.get("value", "")
            kpi_unit = kpi.get("unit", "")

            # Extract numeric value from kpi text
            import re
            numbers = re.findall(r'[\d,]+\.?\d*', str(kpi_value))
            target_value = float(numbers[0]) if numbers else None

            # Try to find matching column
            matching_cols = [c for c in self.df.columns if kpi_name.lower() in c.lower()]

            if target_value is not None and matching_cols:
                # Verify the KPI value
                verified = False
                actual_value = 0
                calc = ""
                row_count = 0

                col = matching_cols[0]

                # Check for percentage
                if kpi_unit == "%" or "%" in str(kpi_value):
                    total = self.df[col].sum()
                    actual_value = target_value / 100 * total
                    verified = abs(actual_value - target_value) < total * 0.01  # 1% tolerance
                    row_count = len(self.df[col].dropna())
                    calc = f"PERCENT({col} = {target_value}%)"

                else:
                    # Check for direct match or close to sum/avg
                    total = self.df[col].sum()
                    avg = self.df[col].mean()

                    if abs(target_value - total) < abs(target_value - avg) * 0.5:
                        actual_value = total
                        verified = abs(actual_value - target_value) < max(total * 0.01, 1)
                        calc = f"SUM({col})"
                    else:
                        actual_value = avg
                        verified = abs(actual_value - target_value) < max(avg * 0.1, 1)
                        calc = f"AVG({col})"

                    row_count = len(self.df[col].dropna())

                # Confidence based on row count
                confidence = min(100, (row_count / len(self.df)) * 100)

                claims.append(DataClaim(
                    claim_id=claim_id,
                    claim_type="kpi",
                    slide_num=slide_num,
                    description=f"{kpi_name}: {kpi_value}{kpi_unit}",
                    verified_value=actual_value,
                    row_count=row_count,
                    calculation=calc,
                    is_valid=verified,
                    confidence=confidence,
                    source_columns=[col],
                    query_used=f"Verify KPI value",
                ))
            else:
                # Cannot verify without numeric value
                claims.append(DataClaim(
                    claim_id=claim_id,
                    claim_type="kpi",
                    slide_num=slide_num,
                    description=f"{kpi_name}: {kpi_value}",
                    verified_value="N/A",
                    row_count=0,
                    calculation="Could not extract numeric value",
                    is_valid=False,
                    confidence=0,
                    source_columns=matching_cols if matching_cols else [],
                    query_used="No numeric value to verify",
                ))

        # Verify bullets (extract numbers and verify)
        for bullet in slide_spec.get("bullets", []):
            claim_id = f"bullet_{slide_num}_{len(claims)}"

            # Extract numbers from bullet
            numbers = re.findall(r'[\d,]+\.?\d*', str(bullet))

            if numbers:
                # Find closest matching values
                for num_str in numbers[:3]:  # Verify up to 3 numbers per bullet
                    target = float(num_str)

                    # Try to find matching column value
                    best_match = None
                    best_col = None
                    best_diff = float('inf')

                    for col in self.numeric_cols:
                        col_vals = self.df[col].dropna()
                        for val in col_vals:
                            diff = abs(val - target)
                            if diff < best_diff:
                                best_diff = diff
                                best_match = val
                                best_col = col

                    if best_match is not None:
                        row_count = len(self.df[best_col].dropna())
                        verified = best_diff / best_match < 0.05
                        confidence = min(100, (row_count / len(self.df)) * 100)

                        claims.append(DataClaim(
                            claim_id=claim_id,
                            claim_type="bullet",
                            slide_num=slide_num,
                            description=bullet[:100],
                            verified_value=best_match,
                            row_count=row_count,
                            calculation=f"Found in {best_col} (diff: {round(best_diff, 2)})",
                            is_valid=verified,
                            confidence=confidence,
                            source_columns=[best_col],
                            query_used=f"Match numeric value {target}",
                        ))

        # Verify chart data
        chart_type = slide_spec.get("chart_type", "")
        x_col = slide_spec.get("x_column", "")
        y_col = slide_spec.get("y_column", "")

        if x_col and y_col and chart_type != "none":
            claim_id = f"chart_{slide_num}"
            chart_query = {
                "type": "group_avg" if x_col in self.categorical_cols else "avg",
                "column": y_col,
            }
            if x_col in self.categorical_cols:
                chart_query["group_by"] = x_col

            value, row_count, calc = self._execute_query(chart_query)

            # Chart data confidence based on row count
            confidence = min(100, (row_count / len(self.df)) * 100)

            claims.append(DataClaim(
                claim_id=claim_id,
                claim_type="chart_data",
                slide_num=slide_num,
                description=f"Chart: {chart_type} showing {y_col} by {x_col}",
                verified_value=value,
                row_count=row_count,
                calculation=calc,
                is_valid=True,
                confidence=confidence,
                source_columns=[y_col, x_col] if x_col else [y_col],
                query_used=calc,
            ))

        return claims

    def verify_deck(self, deck_plan: Dict[str, Any]) -> VerificationReport:
        """Verify all claims across the entire deck."""
        all_claims = []

        for slide in deck_plan.get("slides", []):
            slide_claims = self.verify_slide_claims(slide)
            all_claims.extend(slide_claims)

        # Calculate overall statistics
        total = len(all_claims)
        verified = sum(1 for c in all_claims if c.is_valid)
        unverified = [c.description for c in all_claims if not c.is_valid]

        # Overall confidence = weighted average by row count
        if all_claims:
            total_rows = sum(c.row_count for c in all_claims)
            if total_rows > 0:
                overall_conf = sum(c.confidence * c.row_count for c in all_claims) / total_rows
            else:
                overall_conf = 0

        return VerificationReport(
            total_claims=total,
            verified_claims=verified,
            overall_confidence=round(overall_conf, 1),
            claims=all_claims,
            unverified_claims=unverified[:10],  # First 10 unverified claims
        )

    def to_dict(self, report: VerificationReport) -> Dict[str, Any]:
        """Convert verification report to dict for JSON export."""
        return {
            "total_claims": report.total_claims,
            "verified_claims": report.verified_claims,
            "verification_rate": round(report.verified_claims / max(report.total_claims, 1) * 100, 1),
            "overall_confidence": report.overall_confidence,
            "unverified_claims": report.unverified_claims,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "claim_type": c.claim_type,
                    "slide_num": c.slide_num,
                    "description": c.description,
                    "verified_value": c.verified_value,
                    "row_count": c.row_count,
                    "calculation": c.calculation,
                    "is_valid": c.is_valid,
                    "confidence": c.confidence,
                    "source_columns": c.source_columns,
                    "query_used": c.query_used,
                }
                for c in report.claims
            ],
        }


def verify_dataset(df: pd.DataFrame, deck_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to verify a deck against data."""
    verifier = DataVerifier(df)
    report = verifier.verify_deck(deck_plan)
    return verifier.to_dict(report)
