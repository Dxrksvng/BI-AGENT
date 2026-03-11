"""
routers/analyze.py
Layer 3: AI Analysis — English output

Supports 3 providers via .env:
  AI_PROVIDER=gemini   → Google Gemini (free 1,500 req/day)
  AI_PROVIDER=claude   → Anthropic Claude
  AI_PROVIDER=ollama   → Ollama local (Mac, 100% free)

.env example:
  AI_PROVIDER=gemini
  GEMINI_API_KEY=AIza...

  AI_PROVIDER=claude
  ANTHROPIC_API_KEY=sk-ant-...

  AI_PROVIDER=ollama
  OLLAMA_MODEL=llama3.2
  OLLAMA_URL=http://localhost:11434
"""

import os, json, requests
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from dotenv import load_dotenv

from models.schemas import AnalysisRequest, AnalysisResult
from services.job_store import job_store

load_dotenv()
router     = APIRouter()
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()


# ── AI provider functions ─────────────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url   = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
    }
    resp = requests.post(url, json=payload, timeout=1000)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def call_claude(prompt: str) -> str:
    from anthropic import Anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in .env")
    client  = Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def call_ollama(prompt: str) -> str:
    base_url = os.getenv("OLLAMA_URL",   "http://localhost:11434")
    model    = os.getenv("OLLAMA_MODEL", "llama3.2")
    url      = f"{base_url}/api/generate"
    resp = requests.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=600)
    resp.raise_for_status()
    return resp.json().get("response", "")


def call_ai(prompt: str) -> str:
    providers = {"gemini": call_gemini, "claude": call_claude, "ollama": call_ollama}
    if AI_PROVIDER not in providers:
        raise ValueError(f"Unknown AI_PROVIDER '{AI_PROVIDER}'. Use: gemini / claude / ollama")
    return providers[AI_PROVIDER](prompt)


# ── endpoints ────────────────────────────────────────────────────────────────

@router.post("/run", summary="Run AI analysis")
def run_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    job = job_store.get(request.job_id)
    if not job:
        raise HTTPException(404, "job_id not found")
    if job["clean_data"] is None:
        raise HTTPException(400, "Run ETL pipeline first")

    job_store.set_status(request.job_id, "running")
    background_tasks.add_task(_analyze_task, request)

    return {
        "job_id":   request.job_id,
        "status":   "running",
        "provider": AI_PROVIDER,
        "message":  f"Analysis started with {AI_PROVIDER.upper()}",
    }


@router.get("/provider", summary="Check current AI provider")
def get_provider():
    return {
        "provider":   AI_PROVIDER,
        "has_gemini": bool(os.getenv("GEMINI_API_KEY")),
        "has_claude": bool(os.getenv("ANTHROPIC_API_KEY")),
        "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
    }


@router.get("/result/{job_id}", response_model=AnalysisResult, summary="Get analysis result")
def get_result(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "job_id not found")
    if not job["analysis"]:
        raise HTTPException(400, "Analysis not ready yet — check /analyze/run status")
    return job["analysis"]


# ── background task ───────────────────────────────────────────────────────────

def _analyze_task(request: AnalysisRequest):
    import traceback
    print(f"[analyze] START job={request.job_id[:8]} provider={AI_PROVIDER}")
    try:
        job     = job_store.get(request.job_id)
        df      = job["clean_data"]
        report  = job.get("report")
        print(f"[analyze] building prompt...")
        summary = _build_data_summary(df, report)
        prompt  = _build_prompt(summary, request)
        print(f"[analyze] calling {AI_PROVIDER}... prompt_len={len(prompt)}")
        raw     = call_ai(prompt)
        print(f"[analyze] got response len={len(raw)}")
        result  = _parse_response(raw, request.job_id)
        job_store.update(request.job_id, analysis=result, status="done")
        print(f"[analyze] DONE job={request.job_id[:8]}")
    except Exception as e:
        print(f"[analyze] FAILED: {e}")
        traceback.print_exc()
        job_store.set_status(request.job_id, "failed", error=str(e))


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_data_summary(df: pd.DataFrame, report) -> dict:
    num = df.select_dtypes(include="number")
    s = {
        "shape":       list(df.shape),
        "columns":     list(df.columns),
        "dtypes":      df.dtypes.astype(str).to_dict(),
        "sample_rows": df.head(5).to_dict(orient="records"),
        "statistics":  num.describe().to_dict() if not num.empty else {},
        "null_counts": df.isna().sum().to_dict(),
    }
    if report:
        s["quality_score"]  = report.quality_score
        s["issues_summary"] = report.issues_summary
    return s


def _build_prompt(summary: dict, request: AnalysisRequest) -> str:
    focus = ", ".join(request.focus_areas)
    audience_map = {
        "executive":  "C-suite executives who need big-picture strategic insight",
        "analyst":    "data analysts who need detailed findings and patterns",
        "operations": "operations team who need actionable tasks and quick wins",
    }
    audience = audience_map.get(request.audience, request.audience)

    return f"""You are a senior strategy consultant (McKinsey / Big4 level).
Analyze the business data for {request.company_name} and produce an executive-grade report.

IMPORTANT: Respond ENTIRELY in English. Professional business English only.

Data summary:
{json.dumps(summary, ensure_ascii=False, indent=2, default=str)}

Focus areas: {focus}
Target audience: {audience}

Respond with ONLY valid JSON (no markdown, no backticks, no commentary):
{{
  "summary": "2-3 paragraph executive overview highlighting the most critical business findings",
  "key_insights": [
    "Insight 1 — specific, quantified where possible",
    "Insight 2",
    "Insight 3"
  ],
  "anomalies": [
    "Anomaly or risk flag 1",
    "Anomaly or risk flag 2"
  ],
  "recommendations": [
    "Strategic recommendation 1 — specific action",
    "Strategic recommendation 2",
    "Strategic recommendation 3"
  ],
  "charts_config": [
    {{
      "type": "bar",
      "title": "Chart title — phrased as a conclusion",
      "x_column": "column_name",
      "y_column": "column_name",
      "description": "What this chart shows and why it matters"
    }}
  ]
}}"""


def _parse_response(raw: str, job_id: str) -> AnalysisResult:
    try:
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        data = {
            "summary":         raw,
            "key_insights":    [],
            "anomalies":       [],
            "recommendations": [],
            "charts_config":   [],
        }

    return AnalysisResult(
        job_id           = job_id,
        summary          = data.get("summary", ""),
        key_insights     = data.get("key_insights", []),
        anomalies        = data.get("anomalies", []),
        recommendations  = data.get("recommendations", []),
        charts_config    = data.get("charts_config", []),
        created_at       = datetime.utcnow(),
    )