"""
routers/export.py
Full Pipeline Export — Statistically Grounded + AI-Designed Deck

Pipeline:
  1. Statistical Engine  — calculates real numbers (no hallucination)
  2. Story Builder       — McKinsey SCR narrative
  3. AI Deck Designer    — AI designs slides (2-call, no JSON truncation)
  4. slide_builder_v4.js — renders any layout AI specifies

Endpoints:
  GET  /export/json/{job_id}
  POST /export/pdf/{job_id}
  POST /export/pptx/{job_id}
  POST /export/pptx-consulting/{job_id}  ← alias
"""

import json, subprocess, tempfile
import pandas as pd
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from services.job_store import job_store

router = APIRouter()

SLIDE_BUILDER_PATH = Path('/Users/jswvn/Desktop/missj/My-project/BI-AGENT/bi-agent/backend/services/slide_builder_v4.js')


# ── helpers ───────────────────────────────────────────────────────────────────

def _node() -> str:
    for p in ["/opt/homebrew/bin/node", "/usr/local/bin/node", "node"]:
        if Path(p).exists() or p == "node":
            return p
    return "node"


def _safe_df(job: dict):
    df = job.get("clean_data")
    if df is None or (hasattr(df, "empty") and df.empty):
        df = job.get("data")
    if df is None or (hasattr(df, "empty") and df.empty):
        df = pd.DataFrame()
    return df


def _to_dict(obj):
    if obj is None:
        return {}
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return {}


def _df_summary(df) -> dict:
    if df is None or (hasattr(df, "empty") and df.empty):
        return {"columns": [], "n_rows": 0, "n_cols": 0, "statistics": {}, "sample": []}
    num = df.select_dtypes("number")
    return {
        "columns":    list(df.columns),
        "n_rows":     len(df),
        "n_cols":     len(df.columns),
        "statistics": num.describe().to_dict() if not num.empty else {},
        "sample":     df.to_dict(orient="records"),   # full dataset for chart accuracy
    }


def _get_job(job_id: str) -> dict:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "job_id not found")
    if not job.get("analysis"):
        raise HTTPException(400, "Run /analyze/run first")
    return job


# ── GET /json ─────────────────────────────────────────────────────────────────

@router.get("/json/{job_id}")
def export_json(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "job_id not found")
    out = {
        "job_id":      job_id,
        "report":      _to_dict(job.get("report")),
        "analysis":    _to_dict(job.get("analysis")),
        "stat_report": job.get("stat_report", {}),
    }
    return JSONResponse(json.loads(json.dumps(out, default=str)))


# ── POST /pdf ─────────────────────────────────────────────────────────────────

@router.post("/pdf/{job_id}", summary="Generate PDF report")
def export_pdf(job_id: str, company_name: str = "My Company"):
    job      = _get_job(job_id)
    analysis = _to_dict(job["analysis"])
    report   = _to_dict(job.get("report"))
    df       = _safe_df(job)
    try:
        from services.report_builder import build_pdf
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, prefix=f"bi_{job_id[:8]}_")
        tmp.close()
        path  = build_pdf(analysis=analysis, report=report, df=df,
                          company_name=company_name, output_path=tmp.name)
        fname = f"BI_Report_{company_name.replace(' ','_')}.pdf"
        return FileResponse(path, media_type="application/pdf", filename=fname,
                            headers={"Content-Disposition": f'attachment; filename="{fname}"'})
    except Exception as e:
        raise HTTPException(500, f"PDF failed: {e}")


# ── POST /pptx ────────────────────────────────────────────────────────────────

@router.post("/pptx/{job_id}", summary="AI-Designed PPTX — Full Pipeline")
def export_pptx(job_id: str, company_name: str = "My Company", industry: str = "general"):
    """
    Full pipeline:
    1. Statistical Engine  — calculates real KPIs, anomalies, correlations
    2. Story Builder       — McKinsey SCR narrative
    3. AI Deck Designer    — 2-call strategy (structure → details), no JSON truncation
    4. slide_builder_v4.js — renders the AI plan
    """
    job      = _get_job(job_id)
    analysis = _to_dict(job["analysis"])
    report   = _to_dict(job.get("report"))
    df       = _safe_df(job)
    df_sum   = _df_summary(df)

    # ── Step 1: Statistical Engine ────────────────────────────────────────────
    stat_dict = job.get("stat_report") or {}
    if not stat_dict:
        try:
            from services.statistical_engine import run_statistical_analysis, report_to_dict
            print(f"[export] Running Statistical Engine...")
            stat_report = run_statistical_analysis(df)
            stat_dict   = report_to_dict(stat_report)
            job_store.update(job_id, stat_report=stat_dict)
            print(f"[export] Stat engine done — confidence: {stat_dict.get('confidence_score',0)}/100")
        except Exception as e:
            print(f"[export] Stat engine failed: {e}")

    # ── Step 2: Story Builder ─────────────────────────────────────────────────
    story_dict = {}
    try:
        from routers.analyze import call_ai
        from services.story_builder import build_story
        print(f"[export] Running Story Builder...")
        deck = build_story(
            analysis     = analysis,
            report       = report,
            company_name = company_name,
            call_ai_fn   = call_ai,
        )
        story_dict = deck.__dict__.copy()
        story_dict["slides"] = [s.__dict__ for s in deck.slides]
    except Exception as e:
        print(f"[export] Story Builder failed: {e}")

    # ── Step 3: AI Deck Designer (2-call, no truncation) ─────────────────────
    deck_plan_dict = {}
    try:
        from routers.analyze import call_ai
        from services.ai_deck_designer import design_deck, plan_to_dict
        print(f"[export] Running AI Deck Designer (2-call strategy)...")
        plan = design_deck(
            stat_dict    = stat_dict,
            analysis     = analysis,
            company_name = company_name,
            industry     = industry,
            audience     = "executive",
            call_ai_fn   = call_ai,
        )
        deck_plan_dict = plan_to_dict(plan)
        print(f"[export] Deck plan: {plan.total_slides} slides, theme: {plan.theme}")
        print(f"[export] Rationale: {plan.design_rationale[:80]}...")
    except Exception as e:
        print(f"[export] AI Deck Designer failed: {e} — using fallback")
        import traceback; traceback.print_exc()

    # ── Step 4: Build payload ─────────────────────────────────────────────────
    payload = {
        "company_name": company_name,
        "industry":     industry,
        "analysis":     analysis,
        "report":       report,
        "story":        story_dict,
        "stat_report":  stat_dict,
        "deck_plan":    deck_plan_dict,
        "df_summary":   df_sum,
    }

    # ── Step 5: Call slide_builder_v4.js ──────────────────────────────────────
    if not SLIDE_BUILDER_PATH.exists():
        raise HTTPException(500, f"slide_builder_v4.js not found at {SLIDE_BUILDER_PATH}")

    print(f"[export] Using slide_builder_v4.js")
    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False, prefix=f"bi_{job_id[:8]}_")
    tmp.close()

    result = subprocess.run(
        [_node(), str(SLIDE_BUILDER_PATH), tmp.name],
        input          = json.dumps(payload, default=str),
        capture_output = True,
        text           = True,
        timeout        = 180,
    )

    if result.returncode != 0:
        err = result.stderr or result.stdout
        print(f"[export] Node error: {err[:400]}")
        raise HTTPException(500, f"PPTX failed: {err[:400]}")

    stdout = result.stdout.strip()
    path   = stdout[3:] if stdout.startswith("OK:") else tmp.name

    if not Path(path).exists():
        raise HTTPException(500, "PPTX file not created")

    fname = f"BI_Deck_{company_name.replace(' ','_')}.pptx"
    mime  = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    print(f"[export] PPTX ready: {path}")

    # ── Notify ────────────────────────────────────────────────────────────────
    try:
        from services.notifier import notify_analysis_complete
        notify_analysis_complete(
            company_name = company_name,
            analysis     = analysis,
            report       = report,
            pptx_path    = path,
        )
    except Exception as e:
        print(f"[export] Notification failed (non-critical): {e}")

    return FileResponse(path, media_type=mime, filename=fname,
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.post("/pptx-consulting/{job_id}", summary="Alias → AI-Designed PPTX")
def export_pptx_consulting(job_id: str, company_name: str = "My Company", industry: str = "general"):
    return export_pptx(job_id, company_name, industry)