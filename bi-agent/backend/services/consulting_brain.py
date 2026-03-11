"""
services/consulting_brain.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Consulting Brain — AI thinks like a McKinsey/BCG consultant.

Takes raw AI analysis → produces structured consulting story:
  - SCR Framework (Situation / Complication / Resolution)
  - Impact quantification
  - Prioritized insights (Impact × Effort matrix)
  - Strategic recommendations (30/60/90 day roadmap)
  - Executive headline

Called by: consulting_pipeline.py
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Callable


# ─── Output Schema ────────────────────────────────────────────────────────────

@dataclass
class ConsultingStory:
    # Headline
    key_message:      str = ""          # 1-sentence conclusion-first headline
    headline_impact:  str = ""          # single metric: "+34% revenue opportunity"

    # SCR Framework
    situation:        str = ""          # what is the current state
    complication:     str = ""          # what is the core problem/tension
    resolution:       str = ""          # what should be done

    # Insights (ranked by impact)
    top_insights:     List[str] = field(default_factory=list)   # max 3
    root_causes:      List[str] = field(default_factory=list)
    opportunities:    List[str] = field(default_factory=list)

    # Recommendations (3 horizons)
    quick_wins:       List[str] = field(default_factory=list)   # 0-30 days
    medium_term:      List[str] = field(default_factory=list)   # 31-60 days
    long_term:        List[str] = field(default_factory=list)   # 61-90 days
    strategic_recs:   List[str] = field(default_factory=list)   # overall

    # Business Impact
    business_impacts: List[str] = field(default_factory=list)   # quantified
    risk_flags:       List[str] = field(default_factory=list)

    # Industry context
    industry:         str = "general"
    audience:         str = "executive"


# ─── Prompt Builder ───────────────────────────────────────────────────────────

def _build_consulting_prompt(
    analysis: dict,
    report: dict,
    df_summary: dict,
    company_name: str,
    industry: str,
    audience: str,
) -> str:
    qs       = report.get("quality_score", 0)
    n_rows   = df_summary.get("n_rows", 0)
    columns  = df_summary.get("columns", [])
    stats    = df_summary.get("statistics", {})
    insights = analysis.get("key_insights", [])
    anomalies= analysis.get("anomalies", [])
    recs     = analysis.get("recommendations", [])
    summary  = analysis.get("summary", "")

    return f"""You are a senior partner at McKinsey & Company with 20 years of experience.
Your job is to transform raw data analysis into a compelling consulting narrative.

COMPANY: {company_name}
INDUSTRY: {industry}
AUDIENCE: {audience} (tailor language and detail level accordingly)
DATA QUALITY: {qs}/100
DATASET: {n_rows} rows, columns: {', '.join(str(c) for c in columns[:10])}

RAW AI ANALYSIS:
Summary: {summary}

Key Insights:
{chr(10).join(f'- {i}' for i in insights)}

Anomalies:
{chr(10).join(f'- {a}' for a in anomalies)}

Recommendations:
{chr(10).join(f'- {r}' for r in recs)}

STATISTICS SAMPLE:
{json.dumps(stats, default=str, indent=2)[:800]}

YOUR TASK: Apply McKinsey consulting frameworks to produce a structured story.
Use the Pyramid Principle: conclusion first, then supporting evidence.
Be specific, quantified where possible, and action-oriented.

IMPORTANT: Return ONLY valid JSON. No markdown, no backticks, no extra text.

{{
  "key_message": "One powerful sentence — the single most important conclusion (conclusion-first)",
  "headline_impact": "Single metric that quantifies the opportunity or risk, e.g. '$2.4M revenue at risk' or '34% efficiency gain possible'",
  "situation": "2-3 sentences: current state of the business based on data",
  "complication": "2-3 sentences: the core tension, problem, or challenge revealed by the data",
  "resolution": "2-3 sentences: the strategic direction that resolves the complication",
  "top_insights": [
    "Insight 1 — most impactful, specific and quantified",
    "Insight 2 — second most impactful",
    "Insight 3 — third most impactful"
  ],
  "root_causes": [
    "Root cause 1 — underlying driver of the main problem",
    "Root cause 2"
  ],
  "opportunities": [
    "Opportunity 1 — specific, quantified value",
    "Opportunity 2",
    "Opportunity 3"
  ],
  "quick_wins": [
    "Action in 0-30 days — specific, owner, expected outcome"
  ],
  "medium_term": [
    "Action in 31-60 days"
  ],
  "long_term": [
    "Action in 61-90 days — strategic initiative"
  ],
  "strategic_recs": [
    "Strategic recommendation 1",
    "Strategic recommendation 2",
    "Strategic recommendation 3"
  ],
  "business_impacts": [
    "Quantified impact 1, e.g. '+18% revenue in 90 days'",
    "Quantified impact 2"
  ],
  "risk_flags": [
    "Risk that needs immediate attention"
  ]
}}"""


# ─── Response Parser ──────────────────────────────────────────────────────────

def _parse_consulting_response(raw: str, company_name: str, industry: str) -> ConsultingStory:
    try:
        text = raw.strip()
        # strip markdown fences
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
                raise ValueError("no valid JSON block")
        else:
            start = text.find("{")
            end   = text.rfind("}") + 1
            data  = json.loads(text[start:end])

        return ConsultingStory(
            key_message      = data.get("key_message", ""),
            headline_impact  = data.get("headline_impact", ""),
            situation        = data.get("situation", ""),
            complication     = data.get("complication", ""),
            resolution       = data.get("resolution", ""),
            top_insights     = data.get("top_insights", [])[:3],
            root_causes      = data.get("root_causes", [])[:3],
            opportunities    = data.get("opportunities", [])[:3],
            quick_wins       = data.get("quick_wins", [])[:3],
            medium_term      = data.get("medium_term", [])[:3],
            long_term        = data.get("long_term", [])[:3],
            strategic_recs   = data.get("strategic_recs", [])[:4],
            business_impacts = data.get("business_impacts", [])[:4],
            risk_flags       = data.get("risk_flags", [])[:3],
            industry         = industry,
            audience         = "executive",
        )

    except Exception as e:
        print(f"[consulting_brain] parse error: {e} — using fallback")
        # graceful fallback from raw analysis
        return ConsultingStory(
            key_message     = f"{company_name} data reveals critical business opportunities.",
            headline_impact = "Significant improvement potential identified",
            situation       = "Analysis of company data reveals patterns requiring strategic attention.",
            complication    = "Current performance trends indicate areas needing immediate intervention.",
            resolution      = "A structured 90-day action plan can address key challenges and capture opportunities.",
            top_insights    = [],
            strategic_recs  = [],
            industry        = industry,
        )


# ─── Public API ───────────────────────────────────────────────────────────────

def build_consulting_story(
    analysis:     dict,
    report:       dict,
    df_summary:   dict,
    company_name: str,
    call_ai_fn:   Callable[[str], str],
    industry:     str = "general",
    audience:     str = "executive",
) -> ConsultingStory:
    """
    Main entry point.

    Args:
        analysis:     dict from AI analysis (key_insights, anomalies, etc.)
        report:       dict from ETL pipeline (quality_score, n_rows, etc.)
        df_summary:   dict with columns, statistics, sample
        company_name: company name string
        call_ai_fn:   function(prompt: str) -> str  — your existing call_ai()
        industry:     industry hint for context
        audience:     executive / analyst / operations

    Returns:
        ConsultingStory dataclass
    """
    print(f"[consulting_brain] building story for {company_name}...")

    prompt = _build_consulting_prompt(
        analysis, report, df_summary,
        company_name, industry, audience
    )

    print(f"[consulting_brain] calling AI (prompt_len={len(prompt)})...")
    raw = call_ai_fn(prompt)
    print(f"[consulting_brain] got response (len={len(raw)})")

    story = _parse_consulting_response(raw, company_name, industry)
    print(f"[consulting_brain] done — key_message: {story.key_message[:60]}...")

    return story
