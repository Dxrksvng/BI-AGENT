"""
services/auto_pipeline.py
Auto-Pipeline: runs automatically when Docker Agent pushes data

Flow:
  /ingest/push -> run_auto_pipeline(job_id)
    -> ETL (cleaner.py)
    -> AI Analysis (call_ai)
    -> consulting_pipeline (SCR story)
    -> PPTX Export (slide_builder_v3.js)
    -> Save to /reports/{date}/
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("auto_pipeline")

REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "./reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SLIDE_BUILDER = Path(__file__).parent / "slide_builder_v3.js"


def run_auto_pipeline(
    job_id: str,
    company_name: str = "Company",
    industry: str = "general",
    table_name: str = "data",
) -> dict:
    from services.job_store import job_store
    from services.cleaner import DataCleaner
    from services.consulting_pipeline import run_consulting_pipeline
    from routers.analyze import call_ai

    logger.info(f"[auto_pipeline] starting job_id={job_id} company={company_name}")
    result = {
        "job_id": job_id,
        "company_name": company_name,
        "table_name": table_name,
        "started_at": datetime.utcnow().isoformat(),
        "status": "running",
        "pptx_path": None,
        "error": None,
    }

    try:
        # Step 1: Get raw data
        job = job_store.get(job_id)
        if not job or job.get("data") is None:
            raise ValueError(f"job not found: {job_id}")
        df = job["data"]
        logger.info(f"[auto_pipeline] raw data: {len(df)} rows x {len(df.columns)} cols")

        # Step 2: ETL
        cleaner = DataCleaner(df, job_id)
        cleaned, clean_report = cleaner.run()
        clean_report_dict = clean_report.dict() if hasattr(clean_report, "dict") else vars(clean_report)
        quality_score = clean_report_dict.get("quality_score", 100)
        job_store.update(job_id, data=cleaned, status="cleaned")
        logger.info(f"[auto_pipeline] ETL done quality={quality_score}")

        # Step 3: AI Analysis
        cols_info = ", ".join([f"{c}({str(cleaned[c].dtype)})" for c in cleaned.columns])
        sample = cleaned.head(20).to_csv(index=False)
        ai_prompt = f"""Analyze this business dataset for {company_name} ({industry} industry).
Columns: {cols_info}
Quality score: {quality_score}/100
Sample data:
{sample}
Provide key insights, anomalies, and recommendations in English."""

        ai_response = call_ai(ai_prompt)
        logger.info(f"[auto_pipeline] AI done")

        # Step 4: Build consulting story
        job_dict = {
            "data":       cleaned,
            "clean_data": cleaned,
            "analysis":   {
                "summary":         ai_response,
                "key_insights":    [],
                "anomalies":       [],
                "recommendations": [],
            },
            "report": clean_report_dict,
        }
        story = run_consulting_pipeline(
            job=job_dict,
            company_name=company_name,
            call_ai_fn=call_ai,
            industry=industry,
        )
        logger.info(f"[auto_pipeline] story built")

        # Step 5: Save JSON + PPTX
        date_str = datetime.now().strftime("%Y-%m-%d")
        out_dir = REPORTS_DIR / date_str / company_name.replace(" ", "_")
        out_dir.mkdir(parents=True, exist_ok=True)

        pptx_path = str(out_dir / f"{table_name}_{date_str}.pptx")
        json_path = str(out_dir / f"{table_name}_{date_str}.json")

        story_out = story if isinstance(story, dict) else vars(story)
        story_out["company_name"]  = company_name
        story_out["industry"]      = industry
        story_out["quality_score"] = quality_score
        story_out["date"]          = datetime.now().strftime("%d %b %Y")

        with open(json_path, "w") as f:
            json.dump(story_out, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"[auto_pipeline] JSON saved -> {json_path}")

        # Step 6: Generate PPTX
        if SLIDE_BUILDER.exists():
            node_result = subprocess.run(
                ["node", str(SLIDE_BUILDER), pptx_path, json_path],
                capture_output=True, text=True, timeout=60,
            )
            if node_result.returncode == 0:
                result["pptx_path"] = pptx_path
                logger.info(f"[auto_pipeline] PPTX saved -> {pptx_path}")
            else:
                logger.warning(f"[auto_pipeline] PPTX failed: {node_result.stderr[:200]}")
        else:
            logger.warning("[auto_pipeline] slide_builder_v3.js not found")

        # Step 7: Update job
        job_store.update(job_id, status="exported", extra={
            "pptx_path":    pptx_path,
            "json_path":    json_path,
            "main_message": story_out.get("story", {}).get("key_message", ""),
        })

        result["status"] = "done"
        result["finished_at"] = datetime.utcnow().isoformat()
        logger.info(f"[auto_pipeline] complete")

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
