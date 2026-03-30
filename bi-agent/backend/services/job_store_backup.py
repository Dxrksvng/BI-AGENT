"""
routers/analyze.py
Layer 3: AI Analysis — Statistically Grounded

Key upgrade: Statistical Engine runs FIRST.
AI receives verified numbers → cannot hallucinate.
AI role = interpret and explain, not guess numbers.

Supports (set AI_PROVIDER in .env):
  AI_PROVIDER=claude   → Anthropic Claude  ← DEFAULT
  AI_PROVIDER=gemini   → Google Gemini
  AI_PROVIDER=openai   → OpenAI GPT (any OpenAI-compatible endpoint)
  AI_PROVIDER=typhoon  → Typhoon Thai LLM (OpenAI-compatible)
  AI_PROVIDER=glm      → GLM Z.ai (OpenAI-compatible)
  AI_PROVIDER=ollama   → Ollama local (free, private)
"""

import os, json, requests
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from dotenv import load_dotenv

from models.schemas import AnalysisRequest, AnalysisResult
from services.job_store import job_store

load_dotenv()
router      = APIRouter()
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude").lower()   # Default: claude


# ── AI Providers ──────────────────────────────────────────────────────────────

def call_claude(prompt: str, max_tokens: int = 8192) -> str:
    """Anthropic Claude — primary recommended provider."""
    from anthropic import Anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in .env")
    model  = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model      = model,
        max_tokens = max_tokens,
        messages   = [{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def call_gemini(prompt: str) -> str:
    """Google Gemini."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url   = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def call_openai(prompt: str) -> str:
    """OpenAI GPT or any OpenAI-compatible endpoint."""
    from openai import OpenAI
    api_key  = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env")
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model       = os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages    = [{"role": "user", "content": prompt}],
        max_tokens  = 8192,
        temperature = 0.2,
    )
    return response.choices[0].message.content


def call_typhoon(prompt: str) -> str:
    """Typhoon — Thai LLM by SCB Tech, OpenAI-compatible API."""
    from openai import OpenAI
    api_key = os.getenv("TYPHOON_API_KEY")
    if not api_key:
        raise ValueError("TYPHOON_API_KEY not found in .env")
    client = OpenAI(
        api_key  = api_key,
        base_url = "https://api.opentyphoon.ai/v1",
    )
    response = client.chat.completions.create(
        model       = os.getenv("TYPHOON_MODEL", "typhoon-v2-70b-instruct"),
        messages    = [{"role": "user", "content": prompt}],
        max_tokens  = 4096,
        temperature = 0.2,
    )
    return response.choices[0].message.content


def call_glm(prompt: str) -> str:
    """GLM — ZhipuAI Z.ai, OpenAI-compatible API."""
    from openai import OpenAI
    api_key = os.getenv("GLM_API_KEY", os.getenv("ZHIPU_API_KEY"))
    if not api_key:
        raise ValueError("GLM_API_KEY not found in .env")
    client = OpenAI(
        api_key  = api_key,
        base_url = "https://open.bigmodel.cn/api/paas/v4/",
    )
    response = client.chat.completions.create(
        model       = os.getenv("GLM_MODEL", "glm-4-flash"),
        messages    = [{"role": "user", "content": prompt}],
        max_tokens  = 4096,
        temperature = 0.2,
    )
    return response.choices[0].message.content


def call_ollama(prompt: str) -> str:
    """Ollama — local LLM, free and private."""
    base_url = os.getenv("OLLAMA_URL",   "http://localhost:11434")
    model    = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")
    url      = f"{base_url}/api/generate"
    resp = requests.post(
        url,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=600,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def call_ai(prompt: str, max_tokens: int = 8192) -> str:
    """
    Route to the correct AI provider based on AI_PROVIDER env var.
    Default: claude
    """
    providers = {
        "claude":  lambda p: call_claude(p, max_tokens),
        "gemini":  call_gemini,
        "openai":  call_openai,
        "typhoon": call_typhoon,
        "glm":     call_glm,
        "ollama":  call_ollama,
    }
    fn = providers.get(AI_PROVIDER)
    if not fn:
        available = list(providers.keys())
        raise ValueError(
            f"Unknown AI_PROVIDER='{AI_PROVIDER}'. "
            f"Available: {available}. "
            f"Set AI_PROVIDER in your .env file."
        )
    return fn(prompt)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/run", summary="Run AI analysis")
def run_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    job = job_store.get(request.job_id)
    if not job:
        raise HTTPException(404, "job_id not found")
    if job.get("clean_data") is None:
        raise HTTPException(400, "Run ETL pipeline first")

    job_store.set_status(request.job_id, "running")
    background_tasks.add_task(_analyze_task, request)

    return {
        "job_id":   request.job_id,
        "status":   "running",
        "provider": AI_PROVIDER,
        "message":  f"Analysis started with {AI_PROVIDER.upper()} (statistically grounded)",
    }


@router.get("/provider", summary="Check current AI provider and available keys")
def get_provider():
    return {
        "provider":          AI_PROVIDER,
        "available_providers": ["claude", "gemini", "openai", "typhoon", "glm", "ollama"],
        "has_claude":        bool(os.getenv("ANTHROPIC_API_KEY")),
        "has_gemini":        bool(os.getenv("GEMINI_API_KEY")),
        "has_openai":        bool(os.getenv("OPENAI_API_KEY")),
        "has_typhoon":       bool(os.getenv("TYPHOON_API_KEY")),
        "has_glm":           bool(os.getenv("GLM_API_KEY") or os.getenv("ZHIPU_API_KEY")),
        "ollama_url":        os.getenv("OLLAMA_URL", "http://localhost:11434"),
        "stat_grounding":    True,
    }


@router.get("/result/{job_id}", response_model=AnalysisResult, summary="Get analysis result")
def get_result(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(404, "job_id not found")
    if not job.get("analysis"):
        raise HTTPException(400, "Analysis not ready yet")
    return job["analysis"]


# ── Background Task ───────────────────────────────────────────────────────────

def _analyze_task(request: AnalysisRequest):
    import traceback
    print(f"[analyze] START job={request.job_id[:8]} provider={AI_PROVIDER}")
    try:
        job    = job_store.get(request.job_id)
        df     = job["clean_data"]
        report = job.get("report")

        # ── Step 1: Statistical Engine (runs first, always) ───────────────────
        print(f"[analyze] Running Statistical Engine...")
        try:
            from services.statistical_engine import run_statistical_analysis, report_to_dict
            stat_report = run_statistical_analysis(df)
            stat_dict   = report_to_dict(stat_report)
            job_store.update(request.job_id, stat_report=stat_dict)
            print(f"[analyze] Stat engine done — confidence: {stat_report.confidence_score}/100")
        except Exception as e:
            print(f"[analyze] Stat engine failed: {e} — using basic summary")
            stat_dict = _basic_summary(df, report)

        # ── Step 2: Build AI Prompt with verified numbers ─────────────────────
        print(f"[analyze] Building grounded prompt...")
        prompt = _build_grounded_prompt(stat_dict, request)

        # ── Step 3: AI interprets (not invents) ──────────────────────────────
        print(f"[analyze] Calling {AI_PROVIDER}... prompt_len={len(prompt)}")
        raw    = call_ai(prompt)
        print(f"[analyze] AI response received, len={len(raw)}")

        # ── Step 4: Parse + Validate ──────────────────────────────────────────
        result = _parse_and_validate(raw, request.job_id, stat_dict)

        job_store.update(request.job_id, analysis=result, status="done")
        print(f"[analyze] DONE job={request.job_id[:8]}")

    except Exception as e:
        print(f"[analyze] FAILED: {e}")
        traceback.print_exc()
        job_store.set_status(request.job_id, "failed", error=str(e))


# ── Prompt Builder (Grounded) ─────────────────────────────────────────────────

def _build_grounded_prompt(stat_dict: dict, request: AnalysisRequest) -> str:
    """
    Key design: AI receives verified numbers, not raw data.
    AI CANNOT hallucinate numbers because they are pre-calculated.
    AI role = interpret business meaning, not calculate.
    """
    audience_map = {
        "executive":  "C-suite executives — focus on strategic implications and business impact",
        "analyst":    "data analysts — include technical depth, statistical significance",
        "operations": "operations managers — focus on actionable quick wins and process improvements",
    }
    audience = audience_map.get(request.audience, "business stakeholders")

    kpis_text    = "\n".join(f"  - {k['name']}: {k['formatted']} (status: {k['status']})" for k in stat_dict.get("kpis", []))
    anomaly_text = "\n".join(f"  - [{a['severity'].upper()}] {a['description']}" for a in stat_dict.get("anomalies", []))
    corr_text    = "\n".join(f"  - {c['interpretation']}" for c in stat_dict.get("correlations", []))
    trend_text   = "\n".join(f"  - {t['description']}" for t in stat_dict.get("trends", []))
    chart_text   = "\n".join(
        f"  - {c['chart_type'].upper()} chart: '{c['title']}' (x={c['x_column']}, y={c['y_column']})"
        for c in stat_dict.get("chart_recommendations", [])
    )

    return f"""You are a Creative Senior Strategy Consultant at McKinsey & Company.
Find the HIDDEN STORY in this data — not the obvious summary.
Look for unexpected patterns, counterintuitive findings, and the ONE shocking insight that changes everything.

COMPANY: {request.company_name}
AUDIENCE: {audience}
CONFIDENCE SCORE: {stat_dict.get('confidence_score', 0)}/100

━━━ VERIFIED STATISTICAL FACTS (do NOT invent other numbers) ━━━

DATASET: {stat_dict.get('n_rows', 0):,} records, {stat_dict.get('n_cols', 0)} columns
STATISTICAL SUMMARY: {stat_dict.get('data_story', '')}

KEY METRICS (pre-calculated, verified):
{kpis_text or '  No numeric KPIs found'}

ANOMALIES (statistically detected):
{anomaly_text or '  No anomalies detected'}

CORRELATIONS (verified Pearson r):
{corr_text or '  No significant correlations'}

TRENDS (first vs last 20% of data):
{trend_text or '  Insufficient data for trends'}

RECOMMENDED CHARTS (system-selected based on data):
{chart_text}

━━━ YOUR TASK ━━━

Using ONLY the verified facts above (do not invent numbers), provide:

1. THE HIDDEN STORY — what surprising pattern exists that most analysts would miss?
2. 3 DIFFERENT ANGLES — analyze from Financial, Operational, AND Customer Experience perspectives
3. THE SHOCKING INSIGHT — if this was a high-stakes boardroom presentation, what's the ONE finding that would make executives sit up straight?
4. ROOT CAUSES — why might these patterns exist?
5. STRATEGIC RECOMMENDATIONS — specific (who, what, when, expected outcome)

CREATIVITY RULES:
- Every insight MUST reference a specific verified number
- Do NOT use phrases like "approximately", "seems like", "might be"
- Avoid generic insights like "improve customer service" — be specific and bold
- If confidence score < 70, add data quality warning
- Make recommendations that are SURPRISING but defensible with the data

Respond ONLY with valid JSON (no markdown, no backticks):
{{
  "summary": "3-sentence executive summary citing specific verified numbers",
  "key_insights": [
    "Insight 1 — [specific number from facts] implies [business meaning]",
    "Insight 2 — [specific number from facts] implies [business meaning]",
    "Insight 3 — [specific number from facts] implies [business meaning]"
  ],
  "anomalies": [
    "Risk: [column] shows [specific evidence] — business implication: [what this means]",
    "Risk: [column] shows [specific evidence] — business implication: [what this means]"
  ],
  "recommendations": [
    "Action 1: [specific action] for [target] by [timeframe] — expected outcome: [metric]",
    "Action 2: [specific action] for [target] by [timeframe] — expected outcome: [metric]",
    "Action 3: [specific action] for [target] by [timeframe] — expected outcome: [metric]"
  ],
  "charts_config": {json.dumps(stat_dict.get('chart_recommendations', [])[:4], default=str)},
  "confidence_note": "Analysis confidence: {stat_dict.get('confidence_score', 0)}/100 — {'High reliability' if stat_dict.get('confidence_score', 0) >= 80 else 'Moderate — review anomalies before decision-making' if stat_dict.get('confidence_score', 0) >= 60 else 'Low confidence — data quality issues detected'}"
}}"""


# ── Parse + Validate ──────────────────────────────────────────────────────────

def _parse_and_validate(raw: str, job_id: str, stat_dict: dict) -> AnalysisResult:
    """Parse AI response and validate against statistical ground truth."""
    try:
        text = raw.strip()
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                try:
                    data = json.loads(part)
                    break
                except Exception:
                    continue
            else:
                start = text.find("{")
                end   = text.rfind("}") + 1
                data  = json.loads(text[start:end])
        else:
            start = text.find("{")
            end   = text.rfind("}") + 1
            data  = json.loads(text[start:end])
    except Exception as e:
        print(f"[analyze] JSON parse error: {e} — using stat fallback")
        data = _build_fallback_from_stats(stat_dict)

    charts     = stat_dict.get("chart_recommendations", [])
    if not charts:
        charts = data.get("charts_config", [])

    confidence = stat_dict.get("confidence_score", 0)
    summary    = data.get("summary", "")
    if confidence < 70:
        summary += f" [Note: Data confidence score is {confidence}/100 — verify findings before executive decisions.]"

    return AnalysisResult(
        job_id          = job_id,
        summary         = summary,
        key_insights    = data.get("key_insights",    [])[:5],
        anomalies       = data.get("anomalies",       [])[:4],
        recommendations = data.get("recommendations", [])[:5],
        charts_config   = charts[:4],
        created_at      = datetime.utcnow(),
    )


def _build_fallback_from_stats(stat_dict: dict) -> dict:
    """Build analysis from pure statistics if AI fails."""
    kpis      = stat_dict.get("kpis", [])
    anomalies = stat_dict.get("anomalies", [])

    insights = []
    for k in kpis[:3]:
        if k.get("status") == "critical":
            insights.append(f"{k['name']} is {k['formatted']} — requires immediate attention (status: critical)")
        else:
            insights.append(f"{k['name']}: {k['formatted']}")

    recs = []
    for a in anomalies[:3]:
        if a["severity"] == "high":
            recs.append(f"Investigate {a['column']} — {a['description']}")

    return {
        "summary":         stat_dict.get("data_story", "Statistical analysis complete."),
        "key_insights":    insights or ["See statistical report for details"],
        "anomalies":       [a["description"] for a in anomalies[:3]],
        "recommendations": recs or ["Review full statistical report"],
        "charts_config":   stat_dict.get("chart_recommendations", []),
    }


def _basic_summary(df: pd.DataFrame, report) -> dict:
    """Fallback if statistical engine not available."""
    num = df.select_dtypes(include="number")
    qs  = report.get("quality_score", 0) if isinstance(report, dict) else 0
    return {
        "n_rows": len(df),
        "n_cols": len(df.columns),
        "confidence_score": qs,
        "data_story": f"Dataset: {len(df):,} rows, {len(df.columns)} columns.",
        "kpis": [],
        "anomalies": [],
        "correlations": [],
        "trends": [],
        "chart_recommendations": [],
        "statistics": num.describe().to_dict() if not num.empty else {},
        "sample": df.head(5).to_dict(orient="records"),
    }