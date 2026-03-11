print("🔥 USING EXPORT.PY FROM:", __file__)
"""
routers/export.py
Full Consulting Pipeline Export

Pipeline:
  Data → AI Analysis → Story Builder → Slide Planner → slide_builder_v3.js→ PPTX

Endpoints:
  GET  /export/json/{job_id}
  POST /export/pdf/{job_id}
  POST /export/pptx/{job_id}          ← Full Consulting Story Engine
  POST /export/pptx-consulting/{job_id}
"""

import json, subprocess, tempfile
import pandas as pd
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from services.job_store import job_store

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _node() -> str:
    for p in ["/opt/homebrew/bin/node", "/usr/local/bin/node", "node"]:
        if Path(p).exists() or p == "node":
            return p
    return "node"

def _js(filename: str) -> str:
    here = Path(__file__).parent
    for c in [here/"services"/filename, here.parent/"services"/filename, Path("services")/filename]:
        if c.exists():
            return str(c)
    raise FileNotFoundError(f"{filename} not found in backend/services/")

def _safe_df(job: dict):
    df = job.get("clean_data")
    if df is None or (hasattr(df, "empty") and df.empty):
        df = job.get("data")
    if df is None or (hasattr(df, "empty") and df.empty):
        df = pd.DataFrame()
    return df

def _to_dict(obj):
    return obj.dict() if hasattr(obj, "dict") else (obj or {})

def _df_summary(df) -> dict:
    if df is None or (hasattr(df, "empty") and df.empty):
        return {"columns":[], "n_rows":0, "n_cols":0, "statistics":{}, "sample":[]}
    num = df.select_dtypes("number")
    return {
        "columns":    list(df.columns),
        "n_rows":     len(df),
        "n_cols":     len(df.columns),
        "statistics": num.describe().to_dict() if not num.empty else {},
        "sample":     df.head(8).to_dict(orient="records"),
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
    out = {"job_id": job_id, "report": _to_dict(job.get("report")), "analysis": _to_dict(job.get("analysis"))}
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
        path = build_pdf(analysis=analysis, report=report, df=df, company_name=company_name, output_path=tmp.name)
        fname = f"BI_Report_{company_name.replace(' ','_')}.pdf"
        return FileResponse(path, media_type="application/pdf", filename=fname,
                            headers={"Content-Disposition": f'attachment; filename="{fname}"'})
    except Exception as e:
        raise HTTPException(500, f"PDF failed: {e}")


# ── POST /pptx — Full Consulting Story Engine ─────────────────────────────────

@router.post("/pptx/{job_id}", summary="Full Consulting PPTX — Story Engine")
def export_pptx(job_id: str, company_name: str = "My Company", industry: str = "general"):
    """
    Full pipeline:
      1. Story Builder  — AI generates McKinsey-grade consulting story
                          with validated slides (quality check built-in)
      2. Slide Planner  — picks theme based on content
      3. slide_builder_v3.js — renders consulting-grade PPTX
         • 1 slide = 1 executive message
         • max 3 bullets, max 12 words each
         • chart left / insights right layout
         • strategic implication on every slide
         • consulting footer: Confidential | BI Agent | date
    """
    job      = _get_job(job_id)
    analysis = _to_dict(job["analysis"])
    report   = _to_dict(job.get("report"))
    df       = _safe_df(job)
    df_sum   = _df_summary(df)

    # ── Step 1: Story Builder ─────────────────────────────────────────────────
    story_dict = {}
    plan_dict  = {}

    try:
        from routers.analyze import call_ai
        from services.story_builder import build_story
        from services.slide_planner import build_slide_plan

        print(f"[export] running Story Builder for {company_name}...")
        deck = build_story(
            analysis     = analysis,
            report       = report,
            company_name = company_name,
            call_ai_fn   = call_ai,
        )
        story_dict = deck.__dict__.copy()
        # slides are dataclass objects — convert to dicts
        story_dict["slides"] = [s.__dict__ for s in deck.slides]

        # ── Step 2: Slide Planner ─────────────────────────────────────────────
        plan = build_slide_plan(
            analysis   = analysis,
            report     = report,
            df_summary = df_sum,
            story      = deck,
            industry   = industry,
        )
        plan_dict = {
            "theme_key":   plan.theme_key,
            "layout_key":  plan.layout_key,
            "theme":       plan.theme,
            "slide_order": plan.slide_order,
            "chart_plan":  plan.chart_plan,
            "n_slides":    plan.n_slides,
            "rationale":   plan.rationale,
        }
        print(f"[export] theme={plan.theme_key} layout={plan.layout_key}")

    except Exception as e:
        print(f"[export] Story Builder failed: {e} — using basic payload")
        import traceback; traceback.print_exc()

    # ── Build payload ─────────────────────────────────────────────────────────
    payload = {
        "company_name": company_name,
        "industry":     industry,
        "analysis":     analysis,
        "report":       report,
        "story":        story_dict,
        "plan":         plan_dict,
        "df_summary":   df_sum,
    }

    # ── Call Node.js slide_builder_v3.js ──────────────────────────────────────
    try:
        js_file = _js("slide_builder_v3.js")
    except FileNotFoundError:
        # fallback to v1
        try:
            js_file = _js("slide_builder_v3.js")
            print("[export] slide_builder_v3.js not found, using v1")
        except FileNotFoundError as e:
            raise HTTPException(500, str(e))

    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False, prefix=f"bi_{job_id[:8]}_")
    tmp.close()

    print(f"[export] calling {Path(js_file).name}...")
    result = subprocess.run(
        [_node(), js_file, tmp.name],
        input         = json.dumps(payload, default=str),
        capture_output= True,
        text          = True,
        timeout       = 120,
    )

    if result.returncode != 0:
        err = result.stderr or result.stdout
        print(f"[export] node error: {err[:300]}")
        raise HTTPException(500, f"PPTX failed: {err[:300]}")

    stdout = result.stdout.strip()
    path   = stdout[3:] if stdout.startswith("OK:") else tmp.name

    if not Path(path).exists():
        raise HTTPException(500, "PPTX file not created")

    fname = f"BI_Deck_{company_name.replace(' ','_')}.pptx"
    mime  = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    print(f"[export] ✅ PPTX ready: {path}")

    return FileResponse(path, media_type=mime, filename=fname,
                        headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@router.post("/pptx-consulting/{job_id}", summary="Alias → Full Consulting PPTX")
def export_pptx_consulting(job_id: str, company_name: str = "My Company", industry: str = "general"):
    return export_pptx(job_id, company_name, industry)