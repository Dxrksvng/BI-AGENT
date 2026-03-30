"""
services/auto_pipeline.py
Auto-Pipeline: runs automatically when Docker Agent pushes data

Flow:
  /ingest/push -> run_auto_pipeline(job_id)
    -> ETL (cleaner.py)
    -> Statistical Engine (statistical_engine.py)
    -> AI Analysis (call_ai)
    -> AI Deck Designer (ai_deck_designer.py)  ← 2-call strategy, no truncation
    -> PPTX Export (slide_builder_v4.js)
    -> Save to /reports/{date}/
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("auto_pipeline")

REPORTS_DIR   = Path(os.getenv("REPORTS_DIR", "./reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SLIDE_BUILDER = Path(__file__).parent / "slide_builder_v4.js"


def _node() -> str:
    for p in ["/opt/homebrew/bin/node", "/usr/local/bin/node", "node"]:
        if Path(p).exists() or p == "node":
            return p
    return "node"


def run_auto_pipeline(
    job_id: str,
    company_name: str = "Company",
    industry: str     = "general",
    table_name: str   = "data",
) -> dict:
    from services.job_store import job_store
    from services.cleaner import DataCleaner
    from routers.analyze import call_ai

    logger.info(f"[auto_pipeline] starting job_id={job_id} company={company_name}")
    result = {
        "job_id":       job_id,
        "company_name": company_name,
        "table_name":   table_name,
        "started_at":   datetime.utcnow().isoformat(),
        "status":       "running",
        "pptx_path":    None,
        "error":        None,
    }

    try:
        # ── Step 1: Get raw data ───────────────────────────────────────────────
        job = job_store.get(job_id)
        if not job or job.get("data") is None:
            raise ValueError(f"job not found: {job_id}")
        df = job["data"]
        logger.info(f"[auto_pipeline] raw data: {len(df)} rows x {len(df.columns)} cols")

        # ── Step 2: ETL ────────────────────────────────────────────────────────
        cleaner = DataCleaner(df, job_id)
        cleaned, clean_report = cleaner.run()
        clean_report_dict = clean_report.dict() if hasattr(clean_report, "dict") else vars(clean_report)
        quality_score = clean_report_dict.get("quality_score", 100)
        job_store.update(job_id, data=cleaned, clean_data=cleaned, status="cleaned")
        logger.info(f"[auto_pipeline] ETL done quality={quality_score}")

        # ── Step 3: Statistical Engine ─────────────────────────────────────────
        stat_dict = {}
        try:
            from services.statistical_engine import run_statistical_analysis, report_to_dict
            logger.info("[auto_pipeline] Running Statistical Engine...")
            stat_report = run_statistical_analysis(cleaned)
            stat_dict   = report_to_dict(stat_report)
            job_store.update(job_id, stat_report=stat_dict)
            logger.info(f"[auto_pipeline] Stat engine done — confidence: {stat_dict.get('confidence_score',0)}/100")
        except Exception as e:
            logger.warning(f"[auto_pipeline] Stat engine failed: {e}")
            stat_dict = {
                "n_rows": len(cleaned), "n_cols": len(cleaned.columns),
                "confidence_score": quality_score, "data_story": f"Dataset: {len(cleaned):,} rows",
                "kpis": [], "anomalies": [], "correlations": [], "trends": [],
                "chart_recommendations": [], "column_stats": [],
            }

        # ── Step 4: AI Analysis ────────────────────────────────────────────────
        logger.info("[auto_pipeline] Running AI Analysis...")
        cols_info = ", ".join([f"{c}({str(cleaned[c].dtype)})" for c in cleaned.columns])
        sample    = cleaned.head(20).to_csv(index=False)
        ai_prompt = f"""Analyze this business dataset for {company_name} ({industry} industry).
Columns: {cols_info}
Quality score: {quality_score}/100
Sample data:
{sample}
Provide key insights, anomalies, and recommendations.

Respond ONLY with valid JSON:
{{
  "summary": "3-sentence executive summary",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "anomalies": ["risk 1", "risk 2"],
  "recommendations": ["action 1", "action 2", "action 3"]
}}"""

        try:
            ai_raw  = call_ai(ai_prompt)
            text    = ai_raw.strip()
            start   = text.find("{")
            end     = text.rfind("}") + 1
            analysis_dict = json.loads(text[start:end]) if start >= 0 else {}
        except Exception as e:
            logger.warning(f"[auto_pipeline] AI Analysis failed: {e} — using stat summary")
            analysis_dict = {
                "summary":         stat_dict.get("data_story", ""),
                "key_insights":    [k["formatted"] for k in stat_dict.get("kpis", [])[:3]],
                "anomalies":       [a["description"] for a in stat_dict.get("anomalies", [])[:2]],
                "recommendations": ["Review full statistical report"],
            }
        logger.info("[auto_pipeline] AI Analysis done")

        # ── Step 5: AI Deck Designer (2-call, no truncation) ──────────────────
        logger.info("[auto_pipeline] Running AI Deck Designer...")
        deck_plan_dict = {}
        try:
            from services.ai_deck_designer import design_deck, plan_to_dict
            plan = design_deck(
                stat_dict    = stat_dict,
                analysis     = analysis_dict,
                company_name = company_name,
                industry     = industry,
                audience     = "executive",
                call_ai_fn   = call_ai,
            )
            deck_plan_dict = plan_to_dict(plan)
            logger.info(f"[auto_pipeline] Deck plan: {plan.total_slides} slides, theme: {plan.theme}")
        except Exception as e:
            logger.warning(f"[auto_pipeline] AI Deck Designer failed: {e} — will use fallback in slide_builder")

        # ── Step 5.5: Validation Engine (ตรวจสอบข้อมูลไม่มั่ว) ───────────────
        logger.info("[auto_pipeline] Running Validation Engine...")
        validation_result = {"is_valid": False, "confidence": 0, "errors": [], "warnings": []}
        try:
            from services.validation_engine import validate_deck_plan, apply_corrections
            validation = validate_deck_plan(stat_dict, deck_plan_dict)
            validation_result = {
                "is_valid": validation.is_valid,
                "confidence": validation.confidence,
                "errors": validation.errors,
                "warnings": validation.warnings,
            }

            if not validation.is_valid:
                logger.error(f"[auto_pipeline] Validation FAILED with {len(validation.errors)} errors")
                for err in validation.errors[:5]:
                    logger.error(f"  - {err}")
                # Apply auto-corrections
                deck_plan_dict = apply_corrections(deck_plan_dict, validation)
            else:
                logger.info(f"[auto_pipeline] Validation PASSED (confidence: {validation.confidence}%)")
                if validation.warnings:
                    for warn in validation.warnings[:5]:
                        logger.warning(f"  - {warn}")
        except Exception as e:
            logger.warning(f"[auto_pipeline] Validation Engine failed: {e} — proceeding without validation")

        # ── Step 6: Save JSON + generate PPTX ────────────────────────────────
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_dir  = REPORTS_DIR / date_str / company_name.replace(" ", "_")
        out_dir.mkdir(parents=True, exist_ok=True)

        pptx_path = str(out_dir / f"{table_name}_{date_str}.pptx")
        json_path = str(out_dir / f"{table_name}_{date_str}.json")

        payload = {
            "company_name": company_name,
            "industry":     industry,
            "analysis":     analysis_dict,
            "report":       clean_report_dict,
            "stat_report":  stat_dict,
            "deck_plan":    deck_plan_dict,
            "quality_score": quality_score,
            "validation":   validation_result,
            "date":         datetime.now().strftime("%d %b %Y"),
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"[auto_pipeline] JSON saved -> {json_path}")

        # ── Step 7: Run slide_builder_v4.js ───────────────────────────────────
        if not SLIDE_BUILDER.exists():
            raise FileNotFoundError(f"slide_builder_v4.js not found at {SLIDE_BUILDER}")

        node_result = subprocess.run(
            [_node(), str(SLIDE_BUILDER), pptx_path],
            input          = json.dumps(payload, default=str),
            capture_output = True,
            text           = True,
            timeout        = 180,
        )

        if node_result.returncode == 0:
            stdout = node_result.stdout.strip()
            final_path = stdout[3:] if stdout.startswith("OK:") else pptx_path
            result["pptx_path"] = final_path
            logger.info(f"[auto_pipeline] PPTX saved -> {final_path}")
        else:
            err = node_result.stderr or node_result.stdout
            logger.warning(f"[auto_pipeline] PPTX failed: {err[:200]}")

        # ── Step 8: Update job store ───────────────────────────────────────────
        job_store.update(job_id, status="exported", analysis=analysis_dict, extra={
            "pptx_path":    pptx_path,
            "json_path":    json_path,
            "main_message": deck_plan_dict.get("main_message", ""),
        })

        result["status"]      = "done"
        result["finished_at"] = datetime.utcnow().isoformat()
        logger.info("[auto_pipeline] complete")

    except Exception as e:
        logger.error(f"[auto_pipeline] failed: {e}", exc_info=True)
        try:
            from services.job_store import job_store
            job_store.set_status(job_id, "failed", error=str(e))
        except Exception:
            pass
        result["status"] = "failed"
        result["error"]  = str(e)

    return result