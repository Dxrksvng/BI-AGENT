"""
services/report_builder.py
BI Report PDF Builder — English output, signature matches export.py
"""

import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except Exception:
    WEASYPRINT_AVAILABLE = False


# ─── FONT ────────────────────────────────────────────────────────────────────

def _find_font() -> Optional[str]:
    for p in [
        "fonts/Sarabun-Regular.ttf",
        "/Library/Fonts/THSarabunNew.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
    ]:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            return abs_p
    return None


def _font_css() -> str:
    p = _find_font()
    if p:
        return f"""
@font-face {{
    font-family: 'BIFont';
    src: url('file://{p}');
}}
body {{ font-family: 'BIFont', Helvetica, Arial, sans-serif; }}
"""
    return "body { font-family: Helvetica, Arial, sans-serif; }"


# ─── HTML CONTENT BUILDER ────────────────────────────────────────────────────

def _build_content(
    analysis: dict,
    report: dict,
    df: pd.DataFrame,
    company_name: str,
) -> str:
    now = datetime.now().strftime("%d %B %Y")
    qs  = report.get("quality_score", 0)
    qs_color = "#059669" if qs >= 80 else "#D97706" if qs >= 50 else "#DC2626"

    # ── KPI bar ──────────────────────────────────────────────────────────────
    orig    = report.get("original_rows", len(df))
    cleaned = report.get("cleaned_rows",  len(df))
    n_cols  = report.get("n_cols", len(df.columns))

    kpi_html = f"""
<div class="kpi-row">
  <div class="kpi-box">
    <div class="kpi-val" style="color:{qs_color}">{qs}</div>
    <div class="kpi-lbl">Data Quality Score</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-val">{orig:,}</div>
    <div class="kpi-lbl">Original Rows</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-val">{cleaned:,}</div>
    <div class="kpi-lbl">Clean Rows</div>
  </div>
  <div class="kpi-box">
    <div class="kpi-val">{n_cols}</div>
    <div class="kpi-lbl">Columns</div>
  </div>
</div>"""

    # ── Executive Summary ─────────────────────────────────────────────────────
    summary = analysis.get("summary", "")
    summary_html = f"""
<h2>Executive Summary</h2>
<div class="summary-box">{summary}</div>"""

    # ── Key Insights ─────────────────────────────────────────────────────────
    insights = analysis.get("key_insights", [])
    insights_html = ""
    if insights:
        items = "".join(f'<li>{i}</li>' for i in insights)
        insights_html = f"""
<h2>Key Insights</h2>
<ul class="insight-list">{items}</ul>"""

    # ── Anomalies ─────────────────────────────────────────────────────────────
    anomalies = [a for a in analysis.get("anomalies", [])
                 if "no anomal" not in a.lower() and a.strip()]
    anomalies_html = ""
    if anomalies:
        items = "".join(f'<li>{a}</li>' for a in anomalies)
        anomalies_html = f"""
<h2>Anomalies & Risk Flags</h2>
<ul class="anomaly-list">{items}</ul>"""

    # ── Recommendations ───────────────────────────────────────────────────────
    recs = analysis.get("recommendations", [])
    recs_html = ""
    if recs:
        rows = "".join(
            f'<tr><td>{i+1}</td><td>{r}</td></tr>'
            for i, r in enumerate(recs)
        )
        recs_html = f"""
<h2>Strategic Recommendations</h2>
<table>
  <tr><th>#</th><th>Recommendation</th></tr>
  {rows}
</table>"""

    # ── Data Sample ───────────────────────────────────────────────────────────
    sample_html = ""
    if not df.empty:
        sample = df.head(8)
        headers = "".join(f"<th>{c}</th>" for c in sample.columns)
        body_rows = ""
        for _, row in sample.iterrows():
            cells = "".join(f"<td>{v}</td>" for v in row.values)
            body_rows += f"<tr>{cells}</tr>"
        sample_html = f"""
<h2>Data Sample (first 8 rows)</h2>
<div class="table-wrap">
<table>
  <tr>{headers}</tr>
  {body_rows}
</table>
</div>"""

    return f"""
<div class="report-date">Generated: {now}  |  Prepared for: {company_name}</div>
{kpi_html}
{summary_html}
{insights_html}
{anomalies_html}
{recs_html}
{sample_html}
"""


# ─── CSS ─────────────────────────────────────────────────────────────────────

_CSS = """
@page {
    size: A4;
    margin: 2cm 1.8cm;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-size: 11px;
    color: #1F2937;
    line-height: 1.5;
}

.report-date {
    font-size: 9px;
    color: #6B7280;
    margin-bottom: 16px;
    border-bottom: 1px solid #E5E7EB;
    padding-bottom: 6px;
}

h1 {
    font-size: 22px;
    color: #1A1F5E;
    margin-bottom: 4px;
    font-weight: 700;
}

.subtitle {
    font-size: 11px;
    color: #6B7280;
    margin-bottom: 20px;
}

h2 {
    font-size: 13px;
    color: #1A1F5E;
    font-weight: 700;
    margin-top: 20px;
    margin-bottom: 8px;
    padding-bottom: 3px;
    border-bottom: 2px solid #1A1F5E;
}

/* KPI row */
.kpi-row {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    margin-top: 16px;
}
.kpi-box {
    flex: 1;
    background: #F5F6FA;
    border-left: 4px solid #1A1F5E;
    padding: 10px 12px;
}
.kpi-val {
    font-size: 22px;
    font-weight: 700;
    color: #1A1F5E;
}
.kpi-lbl {
    font-size: 9px;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 2px;
}

/* Summary */
.summary-box {
    background: #EFF6FF;
    border-left: 4px solid #2563EB;
    padding: 12px 14px;
    font-size: 11px;
    color: #1F2937;
    margin-top: 8px;
}

/* Insights */
.insight-list {
    list-style: none;
    margin-top: 8px;
}
.insight-list li {
    padding: 7px 10px 7px 14px;
    border-left: 3px solid #00AEAB;
    background: #F0FFFE;
    margin-bottom: 5px;
}

/* Anomalies */
.anomaly-list {
    list-style: none;
    margin-top: 8px;
}
.anomaly-list li {
    padding: 7px 10px 7px 14px;
    border-left: 3px solid #DC2626;
    background: #FFF5F5;
    margin-bottom: 5px;
}

/* Tables */
.table-wrap { overflow-x: auto; }
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
    font-size: 10px;
}
th {
    background: #1A1F5E;
    color: #FFFFFF;
    padding: 6px 8px;
    text-align: left;
    font-weight: 600;
}
td {
    border: 1px solid #E5E7EB;
    padding: 5px 8px;
}
tr:nth-child(even) td { background: #F9FAFB; }

/* Footer */
.footer {
    margin-top: 24px;
    padding-top: 8px;
    border-top: 1px solid #E5E7EB;
    font-size: 9px;
    color: #9CA3AF;
    text-align: center;
}
"""


# ─── FULL HTML ────────────────────────────────────────────────────────────────

def _build_html(
    analysis: dict,
    report: dict,
    df: pd.DataFrame,
    company_name: str,
) -> str:
    content = _build_content(analysis, report, df, company_name)
    font_css = _font_css()
    title    = f"Business Intelligence Report — {company_name}"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
{font_css}
{_CSS}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="subtitle">AI-Powered Business Intelligence  |  Confidential</p>
{content}
<div class="footer">Generated by BI Agent  |  Confidential  |  Not for distribution</div>
</body>
</html>"""


# ─── PUBLIC API ──────────────────────────────────────────────────────────────

def build_pdf(
    analysis: dict,
    report: dict,
    df: pd.DataFrame,
    company_name: str = "Company",
    output_path: str  = "bi_report.pdf",
) -> str:
    """
    Build PDF from analysis + report + dataframe.
    Signature matches export.py call:
        build_pdf(analysis, report, df, company_name, output_path)
    Returns output_path on success.
    """
    html = _build_html(analysis, report, df, company_name)

    if not WEASYPRINT_AVAILABLE:
        # fallback: write HTML so at least something is returned
        html_path = output_path.replace(".pdf", ".html")
        Path(html_path).write_text(html, encoding="utf-8")
        raise RuntimeError(
            "WeasyPrint not installed. HTML saved to: " + html_path
        )

    HTML(string=html, base_url=str(Path.cwd())).write_pdf(output_path)
    return output_path


# ─── CLI TEST ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pandas as pd

    dummy_analysis = {
        "summary":         "Revenue grew 18% QoQ driven by Segment B expansion. Customer retention risk detected in Tier-3 accounts.",
        "key_insights":    ["Segment B revenue +34% — primary growth driver", "Tier-3 churn rate 12% — above acceptable threshold", "Q3 margin compression due to logistics cost increase"],
        "anomalies":       ["Unusual spike in returns week 42", "3 accounts with zero activity for 60+ days"],
        "recommendations": ["Accelerate Segment B investment", "Launch Tier-3 retention programme within 30 days", "Renegotiate logistics contracts Q1"],
    }
    dummy_report = {
        "quality_score": 87,
        "original_rows": 5000,
        "cleaned_rows":  4821,
        "n_cols":        12,
    }
    dummy_df = pd.DataFrame({
        "Month":   ["Jan", "Feb", "Mar", "Apr"],
        "Revenue": [120000, 138000, 142000, 158000],
        "Segment": ["A", "B", "A", "B"],
    })

    path = build_pdf(dummy_analysis, dummy_report, dummy_df, "Demo Corp", "test_report.pdf")
    print("✅ PDF →", path)