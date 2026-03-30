"""
services/data_profiler.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data Profiler — Full column profiling for AI context

Generates:
  - Full column statistics (numeric, categorical, datetime)
  - Sample data (1000 rows max)
  - Data quality metrics
  - Correlation hints
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ColumnProfile:
    """Complete column statistics for AI context."""
    name: str
    dtype: str  # numeric, categorical, datetime
    nullable: bool
    null_pct: float
    n_unique: int

    # Numeric stats
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    median_val: Optional[float] = None
    std_val: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None

    # Categorical stats
    top_values: List[Any] = field(default_factory=list)
    unique_values: List[str] = field(default_factory=list)

    # DateTime stats
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    date_range_days: Optional[int] = None


@dataclass
class DataProfile:
    """Complete dataset profile for AI."""
    n_rows: int
    n_cols: int
    quality_score: float

    columns: List[ColumnProfile]
    sample_data: List[Dict[str, Any]]  # 1000 rows max

    # High-level stats
    numeric_cols: List[str]
    categorical_cols: List[str]
    datetime_cols: List[str]

    # Correlation hints
    high_correlation_pairs: List[Dict[str, Any]] = field(default_factory=list)

    # Recommended columns for analysis
    suggested_metrics: Dict[str, List[str]] = field(default_factory=dict)


class DataProfiler:
    """Profile dataset for AI analysis."""

    def __init__(self, max_sample_rows: int = 1000):
        self.max_sample_rows = max_sample_rows

    def _detect_dtype(self, col: pd.Series) -> str:
        """Detect column type: numeric, categorical, or datetime."""
        if pd.api.types.is_datetime64_any_dtype(col):
            return "datetime"
        elif pd.api.types.is_numeric_dtype(col):
            return "numeric"
        else:
            n_unique = col.nunique()
            n_total = len(col)
            # If unique ratio is low, treat as categorical
            if n_unique / n_total < 0.5 or n_unique < 50:
                return "categorical"
            return "text"  # Free text

    def _profile_numeric(self, col: pd.Series) -> Dict[str, Any]:
        """Profile numeric column."""
        non_null = col.dropna()
        return {
            "min": float(non_null.min()),
            "max": float(non_null.max()),
            "mean": float(non_null.mean()),
            "median": float(non_null.median()),
            "std": float(non_null.std()),
            "q25": float(non_null.quantile(0.25)),
            "q75": float(non_null.quantile(0.75)),
            "skewness": float(non_null.skew()) if len(non_null) > 2 else 0,
        }

    def _profile_categorical(self, col: pd.Series, top_n: int = 10) -> Dict[str, Any]:
        """Profile categorical column."""
        value_counts = col.value_counts()
        total = len(col)

        top = []
        for val, cnt in value_counts.head(top_n).items():
            top.append({
                "value": str(val),
                "count": int(cnt),
                "pct": round(cnt / total * 100, 2),
            })

        return {
            "n_unique": col.nunique(),
            "top_values": top,
        }

    def _profile_datetime(self, col: pd.Series) -> Dict[str, Any]:
        """Profile datetime column."""
        non_null = col.dropna()
        if len(non_null) == 0:
            return {"date_min": None, "date_max": None, "range_days": None}

        min_date = non_null.min()
        max_date = non_null.max()
        range_days = (max_date - min_date).days

        return {
            "date_min": min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
            "date_max": max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None,
            "range_days": int(range_days) if pd.notna(range_days) else None,
        }

    def profile(self, df: pd.DataFrame) -> DataProfile:
        """Generate complete dataset profile."""
        profiles = []
        numeric_cols = []
        categorical_cols = []
        datetime_cols = []

        for col_name in df.columns:
            col = df[col_name]
            dtype = self._detect_dtype(col)
            null_count = col.isna().sum()
            null_pct = round(null_count / len(df) * 100, 2)
            n_unique = col.nunique()

            profile = ColumnProfile(
                name=col_name,
                dtype=dtype,
                nullable=null_count > 0,
                null_pct=null_pct,
                n_unique=n_unique,
            )

            if dtype == "numeric":
                stats = self._profile_numeric(col)
                profile.min_val = stats["min"]
                profile.max_val = stats["max"]
                profile.mean_val = stats["mean"]
                profile.median_val = stats["median"]
                profile.std_val = stats["std"]
                profile.q25 = stats["q25"]
                profile.q75 = stats["q75"]
                numeric_cols.append(col_name)

            elif dtype == "categorical":
                stats = self._profile_categorical(col)
                profile.top_values = stats["top_values"]
                profile.unique_values = [str(v["value"]) for v in stats["top_values"]]
                categorical_cols.append(col_name)

            elif dtype == "datetime":
                stats = self._profile_datetime(col)
                profile.date_min = stats["date_min"]
                profile.date_max = stats["date_max"]
                profile.date_range_days = stats["range_days"]
                datetime_cols.append(col_name)

            profiles.append(profile)

        # Calculate quality score
        total_nulls = sum(p.null_pct * len(df) / 100 for p in profiles)
        quality = 100 - (total_nulls / len(df) * 100)

        # Generate sample data (max 1000 rows)
        sample_size = min(self.max_sample_rows, len(df))
        sample_df = df.sample(n=sample_size, random_state=42) if sample_size > 0 else df.head(0)
        sample_data = sample_df.fillna("").to_dict("records")

        # Calculate correlations for numeric columns
        high_corr_pairs = []
        if len(numeric_cols) >= 2:
            num_df = df[numeric_cols].select_dtypes(include=[np.number])
            if len(num_df.columns) >= 2:
                corr = num_df.corr()
                # Find high correlations (|r| > 0.7)
                for i, col1 in enumerate(corr.columns):
                    for j, col2 in enumerate(corr.columns):
                        if i < j and abs(corr.iloc[i, j]) > 0.7:
                            high_corr_pairs.append({
                                "col1": col1,
                                "col2": col2,
                                "correlation": round(corr.iloc[i, j], 3),
                            })

        # Suggest metrics for each numeric column
        suggested_metrics = {}
        for col in numeric_cols:
            suggested_metrics[col] = [
                "sum", "avg", "count", "min", "max", "median", "std"
            ]

        return DataProfile(
            n_rows=len(df),
            n_cols=len(df.columns),
            quality_score=round(quality, 1),
            columns=profiles,
            sample_data=sample_data,
            numeric_cols=numeric_cols,
            categorical_cols=categorical_cols,
            datetime_cols=datetime_cols,
            high_correlation_pairs=high_corr_pairs[:5],  # Top 5 correlations
            suggested_metrics=suggested_metrics,
        )

    def to_dict(self, profile: DataProfile) -> Dict[str, Any]:
        """Convert profile to dict for JSON serialization."""
        return {
            "n_rows": profile.n_rows,
            "n_cols": profile.n_cols,
            "quality_score": profile.quality_score,
            "sample_size": len(profile.sample_data),
            "numeric_columns": profile.numeric_cols,
            "categorical_columns": profile.categorical_cols,
            "datetime_columns": profile.datetime_cols,
            "high_correlations": profile.high_correlation_pairs,
            "suggested_metrics": profile.suggested_metrics,
            "columns": [
                {
                    "name": c.name,
                    "dtype": c.dtype,
                    "nullable": c.nullable,
                    "null_pct": c.null_pct,
                    "n_unique": c.n_unique,
                    "numeric_stats": {
                        "min": c.min_val,
                        "max": c.max_val,
                        "mean": c.mean_val,
                        "median": c.median_val,
                        "std": c.std_val,
                        "q25": c.q25,
                        "q75": c.q75,
                    } if c.dtype == "numeric" else None,
                    "categorical_stats": {
                        "n_unique": c.n_unique,
                        "top_values": c.top_values,
                    } if c.dtype == "categorical" else None,
                    "datetime_stats": {
                        "date_min": c.date_min,
                        "date_max": c.date_max,
                        "range_days": c.date_range_days,
                    } if c.dtype == "datetime" else None,
                }
                for c in profile.columns
            ],
            "sample_data": profile.sample_data,
        }


# Convenience function for direct usage
def profile_dataset(df: pd.DataFrame, max_sample: int = 1000) -> Dict[str, Any]:
    """Profile a DataFrame and return dict for JSON."""
    profiler = DataProfiler(max_sample_rows=max_sample)
    profile = profiler.profile(df)
    return profiler.to_dict(profile)
