"""
frontend/dashboard.py — fixed polling + English UI
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time, json, io

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="BI Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Sora', sans-serif; background:#0a0a0f; color:#e8e8f0; }
.main-header { background:linear-gradient(135deg,#0d0d1a,#1a1a2e,#0d0d1a);
  border:1px solid #2a2a4a; border-radius:16px; padding:2rem 2.5rem; margin-bottom:2rem; }
.step-badge { background:#1a1a2e; border:1px solid #3b3b6b; border-radius:20px;
  padding:4px 14px; font-size:11px; color:#8888cc; letter-spacing:2px;
  display:inline-block; margin-bottom:8px; }
.insight-card { background:#1a1f3a; border-left:3px solid #6366f1; border-radius:8px;
  padding:12px 16px; margin:6px 0; font-size:13px; }
.anomaly-card  { background:#2a1a1a; border-left:3px solid #f43f5e; border-radius:8px;
  padding:12px 16px; margin:6px 0; font-size:13px; }
.rec-card      { background:#1a2a1a; border-left:3px solid #10b981; border-radius:8px;
  padding:12px 16px; margin:6px 0; font-size:13px; }
.status-ok   { color:#10b981; font-weight:600; }
.status-fail { color:#f43f5e; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ── helpers ───────────────────────────────────────────────────────────────────

def api_get(path):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=10)
        return r.json() if r.status_code < 500 else None
    except:
        return None

def api_post(path, data=None, files=None):
    try:
        if files:
            r = requests.post(f"{API_URL}{path}", files=files, timeout=30)
        else:
            r = requests.post(f"{API_URL}{path}", json=data, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def make_chart(cfg, df):
    chart_type = cfg.get("type", "bar")
    x_col  = cfg.get("x_column")
    y_col  = cfg.get("y_column")
    title  = cfg.get("title", "Chart")
    if not x_col or not y_col:
        return None
    if x_col not in df.columns or y_col not in df.columns:
        return None
    colors = ["#6366f1","#8b5cf6","#a78bfa","#818cf8"]
    try:
        if chart_type == "bar":
            agg = df.groupby(x_col)[y_col].sum().reset_index()
            return px.bar(agg, x=x_col, y=y_col, title=title, color=x_col,
                          color_discrete_sequence=colors,
                          template="plotly_dark")
        elif chart_type == "line":
            return px.line(df, x=x_col, y=y_col, title=title,
                           color_discrete_sequence=colors, template="plotly_dark")
        elif chart_type == "pie":
            agg = df.groupby(x_col)[y_col].sum().reset_index()
            return px.pie(agg, names=x_col, values=y_col, title=title,
                          color_discrete_sequence=colors)
        elif chart_type == "scatter":
            return px.scatter(df, x=x_col, y=y_col, title=title,
                              color_discrete_sequence=colors, template="plotly_dark")
    except Exception:
        return None

# ── session state ─────────────────────────────────────────────────────────────

for k, v in [("job_id",None),("df",None),("report",None),
             ("analysis",None),("step",1),("company","My Company"),("audience","executive")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
  <h1 style="margin:0;font-size:28px;color:#e8e8f0">📊 BI Agent</h1>
  <p style="margin:4px 0 0;color:#8888cc;font-size:13px">
    AI-Powered Business Intelligence · McKinsey-Grade Analysis
  </p>
</div>
""", unsafe_allow_html=True)

# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Pipeline Status")
    steps_done = st.session_state.step
    for num, name, done in [
        ("1","Upload Data",   steps_done >= 2),
        ("2","ETL / Clean",   steps_done >= 3),
        ("3","AI Analysis",   steps_done >= 4),
        ("4","Dashboard",     steps_done >= 4),
    ]:
        icon  = "✅" if done else "⏳"
        color = "#10b981" if done else "#4b5563"
        st.markdown(f'<span style="color:{color}">{icon} Step {num} — {name}</span>',
                    unsafe_allow_html=True)

    st.markdown("---")
    try:
        health = api_get("/health")
        if health:
            st.markdown('<span class="status-ok">● API Online</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-fail">● API Offline</span>', unsafe_allow_html=True)
    except:
        st.markdown('<span class="status-fail">● API Offline</span>', unsafe_allow_html=True)

    provider = api_get("/analyze/provider") or {}
    st.markdown(f"**AI:** `{provider.get('provider','?').upper()}`")

    st.markdown("---")
    if st.button("🔄 Reset"):
        for k in ["job_id","df","report","analysis"]:
            st.session_state[k] = None
        st.session_state.step = 1
        st.rerun()

# ── STEP 1: UPLOAD ────────────────────────────────────────────────────────────

if st.session_state.step == 1:
    st.markdown('<div class="step-badge">STEP 01 / 04</div>', unsafe_allow_html=True)
    st.markdown("### Upload Data")

    uploaded = st.file_uploader("Select CSV file", type=["csv"])
    col1, col2 = st.columns([2,1])
    with col1:
        company  = st.text_input("Company name", value="My Company")
    with col2:
        audience = st.selectbox("Report audience", ["executive","analyst","operations"])

    if uploaded and st.button("🚀 Start Pipeline"):
        with st.spinner("Uploading..."):
            result = api_post(
                "/ingest/upload-csv",
                files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")},
            )
        if "job_id" in result:
            st.session_state.job_id   = result["job_id"]
            st.session_state.company  = company
            st.session_state.audience = audience
            st.session_state.df = pd.read_csv(io.StringIO(uploaded.getvalue().decode("utf-8")))
            st.success(f"✅ Uploaded — job_id: {result['job_id'][:8]}...")
            st.session_state.step = 2
            st.rerun()
        else:
            st.error(f"❌ Upload failed: {result}")

# ── STEP 2: ETL ───────────────────────────────────────────────────────────────

elif st.session_state.step == 2:
    st.markdown('<div class="step-badge">STEP 02 / 04</div>', unsafe_allow_html=True)
    st.markdown("### ETL — Data Cleaning")

    with st.spinner("Cleaning data..."):
        result = api_post("/pipeline/clean", {
            "job_id":        st.session_state.job_id,
            "target_table":  "uploaded_data",
            "clean_options": {
                "remove_duplicates": True,
                "fill_nulls":        "mean",
                "normalize_dates":   True,
                "remove_outliers":   False,
            },
        })

    if result and "quality_score" in result or (
        api_get(f"/pipeline/report/{st.session_state.job_id}") is not None
    ):
        report = api_get(f"/pipeline/report/{st.session_state.job_id}")
        if report:
            st.session_state.report = report
            qs    = report.get("quality_score", 0)
            color = "#10b981" if qs>=80 else "#f59e0b" if qs>=50 else "#f43f5e"
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Quality Score", f"{qs}/100")
            c2.metric("Original Rows",  report.get("original_rows",0))
            c3.metric("Clean Rows",     report.get("cleaned_rows",0))
            c4.metric("Columns",        report.get("n_cols",0))

            issues = report.get("issues_found", [])
            if issues:
                with st.expander("Issues found"):
                    for i in issues:
                        st.markdown(f'<div class="anomaly-card">⚠️ {i}</div>',
                                    unsafe_allow_html=True)

            st.session_state.step = 3
            time.sleep(0.5)
            st.rerun()
    else:
        st.error(f"❌ ETL failed: {result}")

# ── STEP 3: ANALYZE ───────────────────────────────────────────────────────────

elif st.session_state.step == 3:
    st.markdown('<div class="step-badge">STEP 03 / 04</div>', unsafe_allow_html=True)
    st.markdown("### AI Analysis")

    progress = st.progress(0)
    status   = st.empty()

    # kick off
    api_post("/analyze/run", {
        "job_id":       st.session_state.job_id,
        "company_name": st.session_state.company,
        "focus_areas":  ["trend","anomaly","kpi_summary"],
        "audience":     st.session_state.audience,
    })

    # poll — handle 202 (still running) vs 200 (done) vs 400 (failed)
    for i in range(600):   # up to 10 minutes
        progress.progress(min(i / 400, 0.95))
        elapsed = i + 1
        status.markdown(f"*⏳ Analyzing with AI... {elapsed}s elapsed*")
        time.sleep(1)

        result = api_get(f"/analyze/result/{st.session_state.job_id}")

        # None = network error, keep waiting
        if result is None:
            continue

        # 202-style: still running
        if isinstance(result, dict) and result.get("status") in ("running","pending"):
            continue

        # failed
        if isinstance(result, dict) and result.get("status") == "failed":
            st.error(f"❌ Analysis failed: {result.get('message','Unknown error')}")
            break

        # done — must have summary key
        if isinstance(result, dict) and "summary" in result:
            st.session_state.analysis = result
            st.session_state.step     = 4
            progress.progress(1.0)
            status.markdown("*✅ Analysis complete!*")
            time.sleep(0.5)
            st.rerun()
            break

        # also check job status directly for failed state
        job = api_get(f"/ingest/jobs/{st.session_state.job_id}")
        if job and job.get("status") == "failed":
            st.error(f"❌ {job.get('error','Analysis failed')}")
            break
    else:
        st.warning("Analysis is taking very long. Click Refresh to check again.")
        if st.button("🔄 Refresh"):
            st.rerun()

# ── STEP 4: DASHBOARD ─────────────────────────────────────────────────────────

elif st.session_state.step == 4:
    analysis = st.session_state.analysis or {}
    if hasattr(analysis, "dict"):
        analysis = analysis.dict()
    report = st.session_state.report or {}
    df     = st.session_state.df
    co     = st.session_state.company

    st.markdown(f"## {co} — Business Intelligence Dashboard")

    # KPIs
    qs = report.get("quality_score", 0) if isinstance(report, dict) else getattr(report,"quality_score",0)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Data Quality",    f"{qs}/100")
    c2.metric("Rows Analyzed",   report.get("cleaned_rows",0) if isinstance(report,dict) else 0)
    c3.metric("Columns",         report.get("n_cols",0)       if isinstance(report,dict) else 0)
    c4.metric("Key Insights",    len(analysis.get("key_insights",[])))

    st.markdown("---")

    # Charts
    charts_cfg = analysis.get("charts_config", [])
    if charts_cfg and df is not None:
        cols = st.columns(min(len(charts_cfg), 2))
        for i, cfg in enumerate(charts_cfg[:4]):
            with cols[i % 2]:
                fig = make_chart(cfg, df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Insights / Anomalies / Recommendations
    tab1, tab2, tab3 = st.tabs(["💡 Key Insights", "⚠️ Anomalies", "🎯 Recommendations"])

    with tab1:
        for ins in analysis.get("key_insights", []):
            st.markdown(f'<div class="insight-card">💡 {ins}</div>', unsafe_allow_html=True)

    with tab2:
        anomalies = analysis.get("anomalies", [])
        if anomalies and anomalies[0] != "No anomalies detected":
            for a in anomalies:
                st.markdown(f'<div class="anomaly-card">⚠️ {a}</div>', unsafe_allow_html=True)
        else:
            st.success("No significant anomalies detected.")

    with tab3:
        for r in analysis.get("recommendations", []):
            st.markdown(f'<div class="rec-card">✅ {r}</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Export Reports")

    col_pdf, col_pptx = st.columns(2)

    with col_pdf:
        if st.button("📄 Export PDF"):
            with st.spinner("Generating PDF..."):
                r = requests.post(
                    f"{API_URL}/export/pdf/{st.session_state.job_id}",
                    params={"company_name": co}, timeout=60,
                )
            if r.status_code == 200:
                st.download_button(
                    "⬇️ Download PDF",
                    data=r.content,
                    file_name=f"BI_Report_{co.replace(' ','_')}.pdf",
                    mime="application/pdf",
                )
            else:
                st.error(f"❌ PDF failed: {r.text[:300]}")

    with col_pptx:
        if st.button("📊 Export PowerPoint"):
            with st.spinner("Generating PPTX (may take 15-30s)..."):
                r = requests.post(
                    f"{API_URL}/export/pptx/{st.session_state.job_id}",
                    params={"company_name": co, "industry": "general"},
                    timeout=90,
                )
            if r.status_code == 200:
                st.download_button(
                    "⬇️ Download PPTX",
                    data=r.content,
                    file_name=f"BI_Deck_{co.replace(' ','_')}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
            else:
                st.error(f"❌ PPTX failed: {r.text[:300]}")

    st.markdown("---")
    if st.expander("Raw AI Analysis JSON"):
        st.json(analysis)