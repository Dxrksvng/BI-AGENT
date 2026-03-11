"""
services/consulting_pipeline.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Full Consulting Pipeline Orchestrator.

Runs after basic AI analysis:
  1. Consulting Brain  → McKinsey-style story (SCR)
  2. Slide Planner     → theme + layout + chart plan
  3. Returns payload ready for slide_builder_consulting.js

Usage in export.py:
    from services.consulting_pipeline import run_consulting_pipeline
    payload = run_consulting_pipeline(job, company_name, call_ai, industry)
    # then: node slide_builder_consulting.js < payload
"""

import pandas as pd
from typing import Callable, Optional

from services.consulting_brain import build_consulting_story, ConsultingStory
from services.slide_planner import build_slide_plan, SlidePlan


def _df_summary(df) -> dict:
    if df is None or (hasattr(df, "empty") and df.empty):
        return {"columns": [], "n_rows": 0, "n_cols": 0, "statistics": {}, "sample": []}
    num = df.select_dtypes("number")
    return {
        "columns":    list(df.columns),
        "n_rows":     len(df),
        "n_cols":     len(df.columns),
        "dtypes":     df.dtypes.astype(str).to_dict(),
        "statistics": num.describe().to_dict() if not num.empty else {},
        "sample":     df.head(5).to_dict(orient="records"),
    }


def run_consulting_pipeline(
    job:          dict,
    company_name: str,
    call_ai_fn:   Callable[[str], str],
    industry:     str = "general",
    audience:     str = "executive",
) -> dict:
    """
    Full pipeline: job dict → PPTX-ready payload dict.

    Args:
        job:          job_store entry with 'analysis', 'report', 'clean_data'
        company_name: company name
        call_ai_fn:   your existing call_ai() function
        industry:     industry hint (sales/tech/finance/general/etc.)
        audience:     executive / analyst / operations

    Returns:
        dict ready to JSON-serialize and pipe to slide_builder_consulting.js
    """
    print(f"[consulting_pipeline] starting for {company_name}")

    # ── Unpack job ────────────────────────────────────────────────────────────
    analysis_obj = job.get("analysis")
    report_obj   = job.get("report")
    df           = job.get("clean_data")
    if df is None or (hasattr(df, "empty") and df.empty):
        df = job.get("data")

    # Pydantic → dict
    analysis = analysis_obj.dict() if hasattr(analysis_obj, "dict") else (analysis_obj or {})
    report   = report_obj.dict()   if hasattr(report_obj,   "dict") else (report_obj   or {})
    df_sum   = _df_summary(df)

    # ── Step 1: Consulting Brain ──────────────────────────────────────────────
    try:
        story = build_consulting_story(
            analysis     = analysis,
            report       = report,
            df_summary   = df_sum,
            company_name = company_name,
            call_ai_fn   = call_ai_fn,
            industry     = industry,
            audience     = audience,
        )
    except Exception as e:
        print(f"[consulting_pipeline] consulting_brain failed: {e} — using fallback")
        story = ConsultingStory(
            key_message    = f"{company_name}: Key opportunities identified in data analysis.",
            situation      = analysis.get("summary", ""),
            strategic_recs = analysis.get("recommendations", []),
            top_insights   = analysis.get("key_insights", [])[:3],
        )

    # ── Step 2: Slide Planner ─────────────────────────────────────────────────
    try:
        plan = build_slide_plan(
            analysis   = analysis,
            report     = report,
            df_summary = df_sum,
            story      = story,
            industry   = industry,
        )
    except Exception as e:
        print(f"[consulting_pipeline] slide_planner failed: {e} — using defaults")
        from services.slide_planner import SlidePlan, THEMES, LAYOUTS
        plan = SlidePlan(
            theme_key  = "clean_executive",
            layout_key = "pyramid",
            theme      = THEMES["clean_executive"],
            slide_order= LAYOUTS["pyramid"],
            chart_plan = [],
            n_slides   = 9,
        )

    # ── Step 3: Build payload ─────────────────────────────────────────────────
    story_dict = story.__dict__ if hasattr(story, "__dict__") else {}
    plan_dict  = {
        "theme_key":   plan.theme_key,
        "layout_key":  plan.layout_key,
        "theme":       plan.theme,
        "slide_order": plan.slide_order,
        "chart_plan":  plan.chart_plan,
        "n_slides":    plan.n_slides,
        "rationale":   plan.rationale,
    }

    payload = {
        "company_name": company_name,
        "industry":     industry,
        "audience":     audience,
        "analysis":     analysis,
        "report":       report,
        "story":        story_dict,
        "plan":         plan_dict,
        "df_summary":   df_sum,
    }

    print(f"[consulting_pipeline] done — theme={plan.theme_key} layout={plan.layout_key} slides={plan.n_slides}")
    return payload
