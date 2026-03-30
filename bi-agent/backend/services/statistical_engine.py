"""
services/statistical_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Statistical Engine — คำนวณจริง ก่อนส่งให้ AI

หลักการ: AI ไม่ควรเดาตัวเลข
ทุก insight ต้องมาจากการคำนวณ Python จริงๆ
AI ทำหน้าที่แค่ "อธิบาย" และ "ตีความ" เท่านั้น

Output ใช้เป็น ground truth ส่งให้ AI
ทำให้ AI ไม่สามารถมั่วตัวเลขได้
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import pandas as pd
import numpy as np
from scipy import stats
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


# ─── Output Schema ────────────────────────────────────────────────────────────

@dataclass
class ColumnStat:
    name:        str
    dtype:       str           # numeric / categorical / datetime / boolean
    n_unique:    int
    n_null:      int
    null_pct:    float
    # numeric only
    mean:        Optional[float] = None
    median:      Optional[float] = None
    std:         Optional[float] = None
    min:         Optional[float] = None
    max:         Optional[float] = None
    q25:         Optional[float] = None
    q75:         Optional[float] = None
    skewness:    Optional[float] = None
    # categorical only
    top_values:  List[Tuple[str, int, float]] = field(default_factory=list)  # (value, count, pct)

@dataclass
class Anomaly:
    column:      str
    type:        str        # outlier / sudden_change / impossible_value / skewed
    description: str        # human-readable description with real numbers
    severity:    str        # high / medium / low
    evidence:    Dict       # actual numbers proving the anomaly

@dataclass
class Correlation:
    col_a:       str
    col_b:       str
    coefficient: float      # -1 to 1
    strength:    str        # strong / moderate / weak
    direction:   str        # positive / negative
    interpretation: str     # "when X increases, Y tends to increase by Z%"

@dataclass
class Trend:
    column:      str
    direction:   str        # increasing / decreasing / stable / volatile
    change_pct:  float      # % change from first to last
    description: str        # "Revenue increased 23% over the period"

@dataclass
class KPI:
    name:        str
    value:       float
    unit:        str        # "$", "%", "units", etc.
    formatted:   str        # "$1,234,567" or "23.4%"
    benchmark:   Optional[str] = None   # "industry avg: 15%"
    status:      str = "neutral"        # good / warning / critical / neutral

@dataclass
class ChartRecommendation:
    chart_type:  str        # bar / line / pie / scatter / histogram / heatmap / waterfall / funnel
    x_column:    str
    y_column:    str
    title:       str        # conclusion-first title
    why:         str        # why this chart type is appropriate
    priority:    int        # 1 = most important

@dataclass
class StatisticalReport:
    n_rows:           int
    n_cols:           int
    column_stats:     List[ColumnStat]
    kpis:             List[KPI]
    anomalies:        List[Anomaly]
    correlations:     List[Correlation]
    trends:           List[Trend]
    chart_recommendations: List[ChartRecommendation]
    data_story:       str       # 3-sentence statistical summary (facts only, no AI fluff)
    confidence_score: float     # 0-100: how reliable is the analysis


# ─── Main Engine ──────────────────────────────────────────────────────────────

class StatisticalEngine:
    """
    Calculates ALL numbers before sending to AI.
    AI receives verified facts → cannot hallucinate numbers.
    """

    def __init__(self, df: pd.DataFrame):
        self.df      = df.copy()
        self.n_rows  = len(df)
        self.n_cols  = len(df.columns)
        self._num_cols  = list(df.select_dtypes(include="number").columns)
        self._cat_cols  = list(df.select_dtypes(include=["object", "category", "bool"]).columns)
        self._date_cols = list(df.select_dtypes(include=["datetime"]).columns)

    def run(self) -> StatisticalReport:
        """Run full statistical analysis. Returns verified numbers for AI."""
        print("[stat_engine] Running statistical analysis...")

        col_stats  = self._analyze_columns()
        kpis       = self._extract_kpis()
        anomalies  = self._detect_anomalies()
        corrs      = self._compute_correlations()
        trends     = self._detect_trends()
        charts     = self._recommend_charts()
        story      = self._build_data_story(kpis, anomalies, trends)
        confidence = self._compute_confidence_score(anomalies)

        print(f"[stat_engine] Done — {len(kpis)} KPIs, {len(anomalies)} anomalies, {len(corrs)} correlations")

        return StatisticalReport(
            n_rows=self.n_rows,
            n_cols=self.n_cols,
            column_stats=col_stats,
            kpis=kpis,
            anomalies=anomalies,
            correlations=corrs,
            trends=trends,
            chart_recommendations=charts,
            data_story=story,
            confidence_score=confidence,
        )

    # ─── Column Analysis ──────────────────────────────────────────────────────

    def _analyze_columns(self) -> List[ColumnStat]:
        results = []
        for col in self.df.columns:
            s     = self.df[col]
            dtype = self._classify_dtype(s)
            base  = ColumnStat(
                name     = col,
                dtype    = dtype,
                n_unique = int(s.nunique()),
                n_null   = int(s.isna().sum()),
                null_pct = round(s.isna().mean() * 100, 2),
            )
            if dtype == "numeric":
                num = pd.to_numeric(s, errors="coerce").dropna()
                if len(num) > 0:
                    base.mean     = round(float(num.mean()), 4)
                    base.median   = round(float(num.median()), 4)
                    base.std      = round(float(num.std()), 4)
                    base.min      = round(float(num.min()), 4)
                    base.max      = round(float(num.max()), 4)
                    base.q25      = round(float(num.quantile(0.25)), 4)
                    base.q75      = round(float(num.quantile(0.75)), 4)
                    base.skewness = round(float(num.skew()), 4)
            elif dtype == "categorical":
                vc = s.value_counts(normalize=False).head(5)
                base.top_values = [
                    (str(v), int(c), round(c / self.n_rows * 100, 2))
                    for v, c in vc.items()
                ]
            results.append(base)
        return results

    def _classify_dtype(self, s: pd.Series) -> str:
        if pd.api.types.is_numeric_dtype(s):
            return "numeric"
        if pd.api.types.is_datetime64_any_dtype(s):
            return "datetime"
        if pd.api.types.is_bool_dtype(s):
            return "boolean"
        # try parsing as datetime
        if s.dtype == object and s.notna().sum() > 0:
            try:
                pd.to_datetime(s.dropna().head(5))
                return "datetime"
            except Exception:
                pass
        return "categorical"

    # ─── KPI Extraction ───────────────────────────────────────────────────────

    def _extract_kpis(self) -> List[KPI]:
        """Extract meaningful KPIs based on column names and types."""
        kpis = []

        # Revenue / Sales / Amount columns
        revenue_keywords = ["revenue", "sales", "amount", "price", "cost", "profit", "income", "spend"]
        for col in self._num_cols:
            col_lower = col.lower()
            if any(kw in col_lower for kw in revenue_keywords):
                vals = self.df[col].dropna()
                if len(vals) == 0:
                    continue
                total = vals.sum()
                avg   = vals.mean()
                kpis.append(KPI(
                    name      = f"Total {col}",
                    value     = round(total, 2),
                    unit      = "$" if any(k in col_lower for k in ["revenue", "sales", "price", "amount"]) else "",
                    formatted = f"${total:,.0f}" if total > 1000 else f"${total:.2f}",
                    status    = "neutral",
                ))
                kpis.append(KPI(
                    name      = f"Avg {col}",
                    value     = round(avg, 2),
                    unit      = "$",
                    formatted = f"${avg:,.2f}",
                    status    = "neutral",
                ))

        # Churn / Rate / Pct columns
        rate_keywords = ["churn", "rate", "pct", "percent", "ratio", "score"]
        for col in self._cat_cols + self._num_cols:
            col_lower = col.lower()
            if any(kw in col_lower for kw in rate_keywords):
                vals = self.df[col].dropna()
                if col in self._num_cols:
                    avg = vals.mean()
                    status = "critical" if avg > 0.3 else "warning" if avg > 0.1 else "good"
                    kpis.append(KPI(
                        name      = col,
                        value     = round(avg * 100, 2),
                        unit      = "%",
                        formatted = f"{avg*100:.1f}%",
                        status    = status,
                    ))
                elif col in self._cat_cols and vals.nunique() == 2:
                    # binary categorical — calculate rate of "yes/true/1"
                    positive = vals.astype(str).str.lower().isin(["yes", "true", "1", "y"]).mean()
                    status = "critical" if positive > 0.3 else "warning" if positive > 0.1 else "good"
                    kpis.append(KPI(
                        name      = f"{col} Rate",
                        value     = round(positive * 100, 2),
                        unit      = "%",
                        formatted = f"{positive*100:.1f}%",
                        status    = status,
                        benchmark = "Industry avg: 5-15%" if "churn" in col_lower else None,
                    ))

        # Count KPIs
        kpis.append(KPI(
            name      = "Total Records",
            value     = self.n_rows,
            unit      = "rows",
            formatted = f"{self.n_rows:,}",
            status    = "neutral",
        ))

        return kpis[:10]  # top 10 KPIs only

    # ─── Anomaly Detection ────────────────────────────────────────────────────

    def _detect_anomalies(self) -> List[Anomaly]:
        """Detect real statistical anomalies with evidence."""
        anomalies = []

        for col in self._num_cols:
            vals = self.df[col].dropna()
            if len(vals) < 10:
                continue

            # IQR Outlier detection
            q1, q3  = vals.quantile(0.25), vals.quantile(0.75)
            iqr     = q3 - q1
            lower   = q1 - 1.5 * iqr
            upper   = q3 + 1.5 * iqr
            outliers= vals[(vals < lower) | (vals > upper)]

            if len(outliers) > 0:
                pct = len(outliers) / len(vals) * 100
                severity = "high" if pct > 10 else "medium" if pct > 3 else "low"
                anomalies.append(Anomaly(
                    column      = col,
                    type        = "outlier",
                    description = (
                        f"{col} has {len(outliers)} outliers ({pct:.1f}% of data). "
                        f"Normal range: {lower:.2f}–{upper:.2f}. "
                        f"Outlier range: {outliers.min():.2f}–{outliers.max():.2f}."
                    ),
                    severity    = severity,
                    evidence    = {
                        "n_outliers": int(len(outliers)),
                        "pct":        round(pct, 2),
                        "normal_min": round(float(lower), 2),
                        "normal_max": round(float(upper), 2),
                        "outlier_min":round(float(outliers.min()), 2),
                        "outlier_max":round(float(outliers.max()), 2),
                    }
                ))

            # High skewness
            skew = float(vals.skew())
            if abs(skew) > 2:
                direction = "right (many low values, few very high)" if skew > 0 else "left (many high values, few very low)"
                anomalies.append(Anomaly(
                    column      = col,
                    type        = "skewed",
                    description = f"{col} is highly skewed ({skew:.2f}) — {direction}. Mean ({vals.mean():.2f}) ≠ Median ({vals.median():.2f}).",
                    severity    = "medium",
                    evidence    = {"skewness": round(skew, 2), "mean": round(float(vals.mean()), 2), "median": round(float(vals.median()), 2)}
                ))

        # Categorical imbalance
        for col in self._cat_cols:
            vc    = self.df[col].value_counts(normalize=True)
            if len(vc) >= 2 and vc.iloc[0] > 0.8:
                anomalies.append(Anomaly(
                    column      = col,
                    type        = "imbalance",
                    description = f"{col} is dominated by '{vc.index[0]}' ({vc.iloc[0]*100:.1f}%). Other categories are underrepresented.",
                    severity    = "low",
                    evidence    = {"dominant_value": str(vc.index[0]), "dominant_pct": round(float(vc.iloc[0]*100), 2)}
                ))

        return sorted(anomalies, key=lambda x: {"high":0,"medium":1,"low":2}[x.severity])[:6]

    # ─── Correlation ──────────────────────────────────────────────────────────

    def _compute_correlations(self) -> List[Correlation]:
        """Find real correlations between numeric columns."""
        if len(self._num_cols) < 2:
            return []

        corrs = []
        num_df = self.df[self._num_cols].dropna()

        for i, col_a in enumerate(self._num_cols):
            for col_b in self._num_cols[i+1:]:
                if num_df[[col_a, col_b]].dropna().shape[0] < 10:
                    continue
                try:
                    r, p = stats.pearsonr(
                        num_df[col_a].dropna(),
                        num_df[col_b].dropna(),
                    )
                except Exception:
                    continue

                if abs(r) < 0.3:
                    continue  # skip weak correlations

                strength  = "strong" if abs(r) > 0.7 else "moderate"
                direction = "positive" if r > 0 else "negative"
                interp    = (
                    f"When {col_a} increases, {col_b} tends to {'increase' if r > 0 else 'decrease'} "
                    f"(r={r:.2f}, {'statistically significant' if p < 0.05 else 'not significant'})"
                )
                corrs.append(Correlation(
                    col_a          = col_a,
                    col_b          = col_b,
                    coefficient    = round(float(r), 3),
                    strength       = strength,
                    direction      = direction,
                    interpretation = interp,
                ))

        return sorted(corrs, key=lambda x: abs(x.coefficient), reverse=True)[:5]

    # ─── Trend Detection ──────────────────────────────────────────────────────

    def _detect_trends(self) -> List[Trend]:
        """Detect trends over time or sequence."""
        trends = []

        # Look for date/time column
        date_col = None
        for col in self.df.columns:
            if any(kw in col.lower() for kw in ["date", "time", "month", "year", "period", "tenure"]):
                date_col = col
                break

        for col in self._num_cols[:5]:
            if col == date_col:
                continue
            vals = self.df[col].dropna()
            if len(vals) < 5:
                continue

            # Simple trend: compare first 20% vs last 20%
            n     = len(vals)
            first = vals.iloc[:max(1, n//5)].mean()
            last  = vals.iloc[-max(1, n//5):].mean()

            if first == 0:
                continue
            change_pct = (last - first) / abs(first) * 100
            std_ratio  = vals.std() / (vals.mean() + 1e-9)

            if std_ratio > 0.5:
                direction = "volatile"
                desc = f"{col} is highly volatile (CV={std_ratio:.2f}) — inconsistent values throughout the dataset."
            elif abs(change_pct) < 5:
                direction = "stable"
                desc = f"{col} is relatively stable (change: {change_pct:+.1f}%)."
            elif change_pct > 0:
                direction = "increasing"
                desc = f"{col} shows an upward trend (+{change_pct:.1f}% from start to end)."
            else:
                direction = "decreasing"
                desc = f"{col} shows a downward trend ({change_pct:.1f}% from start to end)."

            trends.append(Trend(
                column     = col,
                direction  = direction,
                change_pct = round(change_pct, 2),
                description= desc,
            ))

        return trends[:4]

    # ─── Chart Recommendations ────────────────────────────────────────────────

    def _recommend_charts(self) -> List[ChartRecommendation]:
        """
        Recommend chart types with strict rules — NO pie, NO histogram.

        Rules (enforced):
          datetime × numeric          → line   (trends over time)
          categorical (≤10) × numeric → bar_vertical   (compare categories)
          categorical (>10) × numeric → bar_horizontal (ranked list, labels readable)
          categorical (2-8) × numeric → donut  (part-of-whole composition)
          numeric × numeric (r>0.4)   → scatter (correlation)
          single numeric KPI          → bar_vertical (fallback comparison)

        NEVER: pie (visual distortion), histogram (slide_builder doesn't support)
        """
        charts   = []
        priority = 1

        # ── Rule 1: Time axis → line chart (highest priority) ──────────────────
        date_col = None
        for col in self.df.columns:
            if any(kw in col.lower() for kw in ("date", "time", "month", "year", "period", "week", "quarter")):
                if pd.api.types.is_datetime64_any_dtype(self.df[col]):
                    date_col = col
                    break
                # try parse
                try:
                    parsed = pd.to_datetime(self.df[col], infer_datetime_format=True, errors="coerce")
                    if parsed.notna().sum() / len(self.df) > 0.7:
                        date_col = col
                        break
                except Exception:
                    pass

        if date_col and self._num_cols:
            for num_col in self._num_cols[:3]:
                agg = self.df.groupby(date_col)[num_col].sum()
                if len(agg) < 3:
                    continue
                first_v = float(agg.iloc[0])
                last_v  = float(agg.iloc[-1])
                chg_pct = (last_v - first_v) / (abs(first_v) + 1e-9) * 100
                charts.append(ChartRecommendation(
                    chart_type = "line",
                    x_column   = date_col,
                    y_column   = num_col,
                    title      = (
                        f"{num_col.replace('_',' ').title()} "
                        f"{'↑' if chg_pct > 0 else '↓'}{abs(chg_pct):.0f}% over period"
                    ),
                    why        = f"Line chart for time series: {date_col} × {num_col} ({len(agg)} periods)",
                    priority   = priority,
                ))
                priority += 1
                if priority > 3:
                    break

        # ── Rule 2: Categorical × Numeric → bar_vertical or bar_horizontal ────
        for num_col in self._num_cols[:4]:
            for cat_col in self._cat_cols[:4]:
                n_cat = self.df[cat_col].nunique()
                if n_cat < 2 or n_cat > 30:
                    continue
                agg = self.df.groupby(cat_col)[num_col].mean().sort_values(ascending=False)
                if len(agg) < 2:
                    continue
                diff_pct = (agg.iloc[0] - agg.iloc[-1]) / (abs(agg.iloc[-1]) + 1e-9) * 100
                top_val  = str(agg.index[0])
                # ≤10 categories → vertical, >10 → horizontal (labels don't overlap)
                ct = "bar_vertical" if n_cat <= 10 else "bar_horizontal"
                charts.append(ChartRecommendation(
                    chart_type = ct,
                    x_column   = cat_col,
                    y_column   = num_col,
                    title      = (
                        f"'{top_val}' leads {num_col.replace('_',' ')} "
                        f"by {diff_pct:.0f}% vs lowest"
                        if diff_pct > 5 else
                        f"{num_col.replace('_',' ').title()} by {cat_col.replace('_',' ').title()}"
                    ),
                    why        = (
                        f"{'Vertical' if ct == 'bar_vertical' else 'Horizontal'} bar: "
                        f"{n_cat} categories in '{cat_col}' — "
                        f"{'horizontal for readability' if n_cat > 10 else 'vertical for comparison'}"
                    ),
                    priority   = priority,
                ))
                priority += 1
                if priority > 7:
                    break
            if priority > 7:
                break

        # ── Rule 3: Composition → donut (2-8 categories, NOT pie) ─────────────
        donut_added = False
        for cat_col in self._cat_cols:
            n_cat = self.df[cat_col].nunique()
            if 2 <= n_cat <= 8 and not donut_added:
                vc = self.df[cat_col].value_counts(normalize=True)
                if vc.iloc[0] < 0.85 and self._num_cols:  # not too skewed
                    num_col = self._num_cols[0]
                    charts.append(ChartRecommendation(
                        chart_type = "donut",
                        x_column   = cat_col,
                        y_column   = num_col,
                        title      = f"Composition of {cat_col.replace('_',' ').title()} — {n_cat} segments",
                        why        = (
                            f"Donut (not pie) for part-of-whole: {n_cat} balanced categories. "
                            f"Pie distorts area perception — donut is the modern standard."
                        ),
                        priority   = priority,
                    ))
                    priority += 1
                    donut_added = True

        # ── Rule 4: Correlation → scatter (only if r > 0.4, statistically meaningful) ──
        for corr in self._compute_correlations():
            if abs(corr.coefficient) >= 0.4:
                charts.append(ChartRecommendation(
                    chart_type = "scatter",
                    x_column   = corr.col_a,
                    y_column   = corr.col_b,
                    title      = (
                        f"{corr.col_a.replace('_',' ').title()} vs "
                        f"{corr.col_b.replace('_',' ').title()} — "
                        f"r={corr.coefficient:.2f} ({corr.strength})"
                    ),
                    why        = (
                        f"Scatter reveals {corr.strength} {corr.direction} correlation "
                        f"(r={corr.coefficient:.2f}). Threshold: |r|≥0.4"
                    ),
                    priority   = priority,
                ))
                priority += 1
            if priority > 10:
                break

        return sorted(charts, key=lambda x: x.priority)[:8]

    # ─── Data Story ───────────────────────────────────────────────────────────

    def _build_data_story(self, kpis: List[KPI], anomalies: List[Anomaly], trends: List[Trend]) -> str:
        """Build a 3-sentence statistical summary — facts only, no AI guessing."""
        parts = []

        # Sentence 1: Dataset overview
        parts.append(
            f"Dataset contains {self.n_rows:,} records across {self.n_cols} columns "
            f"with {len(self._num_cols)} numeric and {len(self._cat_cols)} categorical variables."
        )

        # Sentence 2: Key numbers
        critical_kpis = [k for k in kpis if k.status == "critical"]
        if critical_kpis:
            kpi_text = ", ".join(f"{k.name}: {k.formatted}" for k in critical_kpis[:2])
            parts.append(f"Critical metrics requiring attention: {kpi_text}.")
        elif kpis:
            kpi_text = ", ".join(f"{k.name}: {k.formatted}" for k in kpis[:3])
            parts.append(f"Key metrics: {kpi_text}.")

        # Sentence 3: Anomalies
        high_anomalies = [a for a in anomalies if a.severity == "high"]
        if high_anomalies:
            parts.append(f"High-severity anomalies detected in: {', '.join(a.column for a in high_anomalies[:3])}.")
        elif anomalies:
            parts.append(f"{len(anomalies)} anomaly/anomalies detected — review recommended before decision-making.")
        else:
            parts.append("No significant anomalies detected — data appears consistent.")

        return " ".join(parts)

    def _compute_confidence_score(self, anomalies: List[Anomaly]) -> float:
        """How reliable is this analysis? 0-100."""
        score = 100.0

        # Penalize for missing data
        null_pcts = [self.df[c].isna().mean() for c in self.df.columns]
        avg_null  = np.mean(null_pcts) if null_pcts else 0
        score    -= avg_null * 50

        # Penalize for high-severity anomalies
        high_count = sum(1 for a in anomalies if a.severity == "high")
        score     -= high_count * 5

        # Bonus for large dataset
        if self.n_rows > 1000:
            score += 5
        elif self.n_rows < 50:
            score -= 20

        return round(max(0, min(100, score)), 1)


# ─── Public API ───────────────────────────────────────────────────────────────

def run_statistical_analysis(df: pd.DataFrame) -> StatisticalReport:
    """Main entry point. Returns verified statistical report."""
    engine = StatisticalEngine(df)
    return engine.run()


def report_to_dict(report: StatisticalReport) -> dict:
    """Convert to dict for JSON serialization and AI prompt."""
    return {
        "n_rows": report.n_rows,
        "n_cols": report.n_cols,
        "confidence_score": report.confidence_score,
        "data_story": report.data_story,
        "kpis": [
            {
                "name": k.name, "value": k.value,
                "formatted": k.formatted, "status": k.status,
                "benchmark": k.benchmark,
            }
            for k in report.kpis
        ],
        "anomalies": [
            {
                "column": a.column, "type": a.type,
                "description": a.description,
                "severity": a.severity, "evidence": a.evidence,
            }
            for a in report.anomalies
        ],
        "correlations": [
            {
                "col_a": c.col_a, "col_b": c.col_b,
                "coefficient": c.coefficient,
                "strength": c.strength, "direction": c.direction,
                "interpretation": c.interpretation,
            }
            for c in report.correlations
        ],
        "trends": [
            {
                "column": t.column, "direction": t.direction,
                "change_pct": t.change_pct, "description": t.description,
            }
            for t in report.trends
        ],
        "chart_recommendations": [
            {
                "chart_type": c.chart_type,   # bar_vertical/bar_horizontal/line/donut/scatter — never pie/histogram
                "x_column":  c.x_column,
                "y_column":  c.y_column,
                "title":     c.title,
                "why":       c.why,
                "priority":  c.priority,
            }
            for c in report.chart_recommendations
        ],
        "column_stats": [
            {
                "name": c.name, "dtype": c.dtype,
                "n_unique": c.n_unique, "null_pct": c.null_pct,
                "mean": c.mean, "median": c.median, "std": c.std,
                "min": c.min, "max": c.max,
                "skewness": c.skewness,
                "top_values": c.top_values,
            }
            for c in report.column_stats
        ],
    }