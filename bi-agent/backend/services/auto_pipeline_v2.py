"""
services/auto_pipeline_v2.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI Fully Autonomous Pipeline with Data Verification

NEW Flow:
  1. Upload → DataCleaner (ETL)
  2. Data Profiler → Full context + sample (1000 rows)
  3. Single AI Call → Complete deck with query instructions
  4. Verification Engine → Validate ALL claims against source data
  5. Generate PPTX + Audit Report

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import pandas as pd

logger = logging.getLogger("auto_pipeline")

REPORTS_DIR   = Path(os.getenv("REPORTS_DIR", "./reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SLIDE_BUILDER = Path(__file__).parent / "slide_builder_v4.js"


def _node() -> str:
    for p in ["/opt/homebrew/bin/node", "/usr/local/bin/node", "node"]:
        if Path(p).exists() or p == "node":
            return p
    return "node"


def run_fully_autonomous_pipeline(
    job_id: str,
    company_name: str = "Company",
    industry: str     = "general",
    table_name: str   = "data",
) -> dict:
    """
    AI Fully Autonomous Pipeline - Zero human intervention.

    AI decides EVERYTHING:
      - Slide count (dynamic based on data complexity)
      - Layout for each slide
      - Chart type and columns
      - Theme and colors
      - All text content

    Verification Engine validates ALL claims against source data.
    """
    from services.job_store import job_store
    from services.cleaner import DataCleaner
    from services.data_profiler import profile_dataset
    from services.verifier import verify_dataset
    from routers.analyze import call_ai

    logger.info(f"[auto_pipeline_v2] starting job_id={job_id} company={company_name}")
    result = {
        "job_id":       job_id,
        "company_name": company_name,
        "table_name":   table_name,
        "started_at":   datetime.utcnow().isoformat(),
        "status":       "running",
        "pptx_path":    None,
        "error":        None,
        "verification_report": None,
    }

    try:
        # ── Step 1: Get raw data ───────────────────────────────────────────────
        job = job_store.get(job_id)
        if not job or job.get("data") is None:
            raise ValueError(f"job not found: {job_id}")
        df = job["data"]
        logger.info(f"[auto_pipeline_v2] raw data: {len(df)} rows x {len(df.columns)} cols")

        # ── Step 2: ETL ────────────────────────────────────────────────────────
        cleaner = DataCleaner(df, job_id)
        cleaned, clean_report = cleaner.run()
        clean_report_dict = clean_report.dict() if hasattr(clean_report, "dict") else vars(clean_report)
        quality_score = clean_report_dict.get("quality_score", 100)
        job_store.update(job_id, data=cleaned, clean_data=cleaned, status="cleaned")
        logger.info(f"[auto_pipeline_v2] ETL done quality={quality_score}")

        # ── Step 3: Data Profiler (NEW) ───────────────────────────────────────
        logger.info("[auto_pipeline_v2] Running Data Profiler...")
        profile_dict = profile_dataset(cleaned, max_sample=1000)
        job_store.update(job_id, data_profile=profile_dict)
        logger.info(f"[auto_pipeline_v2] Profile: {profile_dict['n_rows']:,} rows, "
                    f"{len(profile_dict['columns'])} cols, "
                    f"quality={profile_dict['quality_score']}/100")

        # ── Step 4: Single AI Call (Full Autonomous) ───────────────────────────────
        logger.info("[auto_pipeline_v2] Running AI Full Autonomous...")

        cols_info = ", ".join([
            f"{c['name']}({c['dtype']})"
            for c in profile_dict["columns"][:20]
        ])
        sample_json = json.dumps(profile_dict["sample_data"][:50], ensure_ascii=False, default=str)

        ai_prompt = f"""You are a McKinsey Partner designing a complete board-level BI presentation for {company_name} ({industry} industry).

DATASET OVERVIEW:
  Rows: {profile_dict['n_rows']:,}
  Columns: {profile_dict['n_cols']}
  Data Quality: {quality_score}/100

NUMERIC COLUMNS (for calculations):
  {json.dumps(profile_dict['numeric_columns'][:12], ensure_ascii=False)}

CATEGORICAL COLUMNS:
  {json.dumps(profile_dict['categorical_columns'][:8], ensure_ascii=False)}

DATETIME COLUMNS:
  {json.dumps(profile_dict['datetime_columns'], ensure_ascii=False)}

HIGH CORRELATIONS (|r| > 0.7):
{chr(10).join([f"  - {c['col1']} × {c['col2']}: {c['correlation']}" for c in profile_dict['high_correlations'][:5]])}

SAMPLE DATA (first 50 rows):
{sample_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULLY AUTONOMOUS DESIGN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have FULL CREATIVE FREEDOM and COMPLETE DATA CONTEXT.
Design a professional consulting presentation based on the data above.

KEY REQUIREMENTS:
1. DYNAMIC SLIDE COUNT: Decide optimal slide count based on data complexity
   - Small dataset (<100 rows, <5 cols): 8-12 slides
   - Medium dataset (100-1000 rows, 5-10 cols): 12-18 slides
   - Large dataset (1000+ rows, 10+ cols): 15-25 slides
   - Complex patterns (many correlations, anomalies): 18-30 slides

2. EVERY SLIDE MUST HAVE:
   - Unique layout (no repeats if possible)
   - Chart with VERIFIED columns from the dataset
   - Data-backed insights with REAL numbers
   - Clear "so what" business implication

3. SLIDE TYPES AVAILABLE:
  - cover: Title slide with company name
  - executive_summary: 3-column SCR (Situation, Complication, Resolution)
  - kpi_dashboard: 4-6 key metrics + chart
  - kpi_row: Horizontal KPI cards + bullets below
  - split_chart_right: Chart 65% left, bullets 35% right
  - split_chart_left: Bullets 35% left, chart 65% right
  - full_chart: Chart fills content area
  - three_column: 3 equal content columns
  - two_column: 2 equal columns
  - bullets_only: Numbered bullets list
  - big_number: Single large KPI + insights
  - timeline: Timeline/roadmap view
  - section_divider: Section break slide
  - dark_close: Closing slide with impact

4. CHART TYPES (must use verified columns):
  - bar_vertical: categorical ≤10 unique values
  - bar_horizontal: categorical >10 values or ranking
  - line: time series (MUST use datetime column)
  - donut: composition (2-8 segments)
  - area: cumulative trend
  - scatter: 2 numeric columns with correlation
  - none: text-only slides

5. TITLE RULE: Every title = CONCLUSION with SPECIFIC NUMBER
   BAD: "Revenue Analysis"
   GOOD: "Revenue Down 18% — Product C Drives 73% of Loss"

6. NUMBERS MUST BE REAL: All percentages, counts, averages must be calculable from the data

7. THEME SELECTION (ALL WHITE BACKGROUND):
  - executive_light: Default (white, blue accents)
  - navy_consulting: Finance/banking (white, navy accents)
  - forest_growth: Healthcare/ESG (white, green accents)
  - slate_minimal: Modern tech (white, purple accents)
  - crimson_risk: Risk alert (white, red accents - ONLY if many anomalies)
  - midnight_tech: Tech/SaaS (white, dark blue accents)
  - ultra_premium: NEVER USE (dark backgrounds)
  - slate_minimal: Startup/VC

8. LAYOUT VARIETY: Use minimum 8 different layouts in one deck

9. FOR EACH SLIDE, OUTPUT (JSON only, no markdown):
{{
  "slide_num": N,
  "slide_type": "cover|executive_summary|kpi_dashboard|kpi_row|split_chart_right|split_chart_left|full_chart|three_column|two_column|bullets_only|big_number|timeline|section_divider|dark_close",
  "title": "CONCLUSION with specific number (under 80 chars)",
  "subtitle": "1 short supporting sentence (under 100 chars)",
  "layout": "cover|executive_summary|kpi_dashboard|kpi_row|split_chart_right|split_chart_left|full_chart|three_column|two_column|bullets_only|big_number|timeline|section_divider|dark_close",
  "chart_type": "bar_vertical|bar_horizontal|line|donut|area|scatter|none|kpi_card",
  "x_column": "EXACT column name from dataset (or empty)",
  "y_column": "EXACT column name from dataset (or empty)",
  "bullets": ["2-4 data-backed bullets with real numbers", ...],
  "insight": "So what? Business impact (under 120 chars)",
  "theme_hint": "primary|warning|danger|success|neutral",
  "kpis": [
    {{"name": "KPI Name", "value": "EXACT value from data", "unit": "%", "status": "good|warning|critical|neutral"}}
  ]  # Only for kpi_dashboard, kpi_row, big_number
}}

IMPORTANT:
- End with dark_close slide
- Include section_divider if deck has >15 slides
- Never use ultra_premium (dark background)
- All chart columns must exist in the dataset list above
- All numbers in titles/bullets must be calculable from the data

OUTPUT — complete JSON only (no markdown):
{{
  "company_name": "{company_name}",
  "industry": "{industry}",
  "main_message": "single most powerful finding in 1 sentence (under 100 chars)",
  "theme": "executive_light|navy_consulting|forest_growth|slate_minimal|midnight_tech|crimson_risk",
  "accent_color": "hex color (without #) matching the theme",
  "total_slides": N,
  "design_rationale": "Why you chose this theme, structure, and approach (2 sentences)",
  "slides": [ ... all slide objects ... ]
}}"""

        try:
            ai_raw = call_ai(ai_prompt)
            text = ai_raw.strip()
            start   = text.find("{")
            end     = text.rfind("}") + 1
            deck_plan_dict = json.loads(text[start:end]) if start >= 0 else {}
            logger.info(f"[auto_pipeline_v2] AI Response: {len(text)} chars, {len(deck_plan_dict.get('slides', []))} slides")
        except Exception as e:
            logger.error(f"[auto_pipeline_v2] AI call failed: {e}")
            raise

        # ── Step 5: Verification Engine (NEW) ───────────────────────────────────────
        logger.info("[auto_pipeline_v2] Running Verification Engine...")
        verification_report = verify_dataset(cleaned, deck_plan_dict)
        logger.info(f"[auto_pipeline_v2] Verification: {verification_report['verified_claims']}/{verification_report['total_claims']} claims verified, "
                    f"confidence={verification_report['verification_rate']}%")

        # ── Step 6: Save JSON + generate PPTX ────────────────────────────────
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_dir  = REPORTS_DIR / date_str / company_name.replace(" ", "_")
        out_dir.mkdir(parents=True, exist_ok=True)

        pptx_path = str(out_dir / f"{table_name}_{date_str}.pptx")
        json_path = str(out_dir / f"{table_name}_{date_str}.json")

        payload = {
            "company_name": company_name,
            "industry": industry,
            "analysis": {
                "summary": f"AI Fully Autonomous - {verification_report['verification_rate']}% verification",
                "key_insights": [f"{verification_report['verified_claims']} verified claims"],
                "anomalies": verification_report['unverified_claims'][:3],
                "recommendations": ["Review audit report for details"],
            },
            "report": clean_report_dict,
            "data_profile": profile_dict,
            "deck_plan": deck_plan_dict,
            "verification": verification_report,
            "quality_score": quality_score,
            "date": datetime.now().strftime("%d %b %Y"),
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"[auto_pipeline_v2] JSON saved -> {json_path}")

        # ── Step 7: Run slide_builder_v4.js ───────────────────────────────────────
        if not SLIDE_BUILDER.exists():
            raise FileNotFoundError(f"slide_builder_v4.js not found at {SLIDE_BUILDER}")

        node_result = subprocess.run(
            [_node(), str(SLIDE_BUILDER), pptx_path],
            input = json.dumps(payload, default=str),
            capture_output = True,
            text = True,
            timeout = 300,  # Increased timeout for larger decks
        )

        if node_result.returncode == 0:
            stdout = node_result.stdout.strip()
            final_path = stdout[3:] if stdout.startswith("OK:") else pptx_path
            result["pptx_path"] = final_path
            logger.info(f"[auto_pipeline_v2] PPTX saved -> {final_path}")
        else:
            err = node_result.stderr or node_result.stdout
            logger.warning(f"[auto_pipeline_v2] PPTX failed: {err[:200]}")

        # ── Step 8: Update job store ───────────────────────────────────────────
        job_store.update(job_id, status="exported", extra={
            "pptx_path": pptx_path,
            "json_path": json_path,
            "main_message": deck_plan_dict.get("main_message", ""),
            "total_slides": deck_plan_dict.get("total_slides", 0),
            "verification_rate": verification_report.get("verification_rate", 0),
        })

        result["verification_report"] = verification_report
        result["status"] = "done"
        result["finished_at"] = datetime.utcnow().isoformat()
        logger.info("[auto_pipeline_v2] complete")

    except Exception as e:
        logger.error(f"[auto_pipeline_v2] failed: {e}", exc_info=True)
        try:
            from services.job_store import job_store
            job_store.set_status(job_id, "failed", error=str(e))
        except Exception:
            pass
        result["status"] = "failed"
        result["error"] = str(e)

    return result


# Convenience wrapper for easy import
def run_auto_pipeline(job_id: str, company_name: str = "Company",
                       industry: str = "general", table_name: str = "data",
                       use_v2: bool = True) -> dict:
    """Wrapper to run pipeline, choosing v2 or original."""
    if use_v2:
        return run_fully_autonomous_pipeline(job_id, company_name, industry, table_name)
    else:
        # Import original pipeline
        from services.auto_pipeline import run_auto_pipeline as run_original
        return run_original(job_id, company_name, industry, table_name)
