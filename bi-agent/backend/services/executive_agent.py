"""
services/executive_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Consulting AI Layer — แปลง Analytics → Strategy Narrative
ใช้ pattern เดียวกับ McKinsey / BCG / Big4

Output structure:
  executive_message   — 1 headline sentence (conclusion)
  situation           — Current state (fact-based)
  complication        — Key problem / tension
  resolution          — What should be done
  impact_metrics      — Quantified business impact
  prioritized_actions — Top 3 only (Impact vs Effort)
  roadmap             — 30/60/90 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional


# ─── Output schema ─────────────────────────────────────────────────

@dataclass
class PrioritizedAction:
    action:    str
    impact:    str          # High / Medium / Low
    effort:    str          # High / Medium / Low
    priority:  int          # 1 = highest
    timeframe: str          # "30 days" / "60 days" / "90 days"

@dataclass
class ImpactMetric:
    label:     str          # "Cost Saving", "Time Saved", etc.
    value:     str          # "$120,000 / year"
    direction: str          # "positive" / "negative" / "neutral"

@dataclass
class ExecutiveNarrative:
    # SCR (Situation-Complication-Resolution) — McKinsey standard
    executive_message:   str
    situation:           str
    complication:        str
    resolution:          str
    # Business impact
    impact_metrics:      List[ImpactMetric]    = field(default_factory=list)
    # Prioritized actions (Impact vs Effort)
    prioritized_actions: List[PrioritizedAction] = field(default_factory=list)
    # Roadmap
    roadmap_30d:         List[str]             = field(default_factory=list)
    roadmap_60d:         List[str]             = field(default_factory=list)
    roadmap_90d:         List[str]             = field(default_factory=list)
    # Slide headline (conclusion-first style)
    slide_headlines:     List[str]             = field(default_factory=list)


# ─── Prompt builder ────────────────────────────────────────────────

def _build_executive_prompt(
    analysis: dict,
    report:   dict,
    company_name: str,
    industry: str = "general",
) -> str:
    qs        = report.get("quality_score", 0)
    orig      = report.get("original_rows", 0)
    insights  = analysis.get("key_insights", [])
    anomalies = analysis.get("anomalies", [])
    recs      = analysis.get("recommendations", [])
    summary   = analysis.get("summary", "")

    return f"""You are a Senior Strategy Consultant at a Big4 firm (McKinsey / BCG / Bain level).
You MUST respond entirely in English.
Use professional business English suitable for C-suite executives.

Your client is: {company_name} ({industry} industry)

ANALYSIS DATA:
- Data quality score: {qs}/100
- Records analyzed: {orig}
- Key insights: {json.dumps(insights, ensure_ascii=False)}
- Anomalies: {json.dumps(anomalies, ensure_ascii=False)}
- Recommendations: {json.dumps(recs, ensure_ascii=False)}
- Summary: {summary}

YOUR TASK:
Create an executive-level consulting narrative using SCR framework:
- Situation: What is the current state (facts only)
- Complication: What tension/problem exists
- Resolution: What the client must do

CONSULTING RULES:
1. executive_message = 1 sentence that IS the conclusion (not a topic)
   BAD:  "Sales Analysis Report"
   GOOD: "Immediate action on Segment B churn will recover 30% of lost revenue"
2. Each slide headline must be the insight, not a label
   BAD:  "Revenue Trend"
   GOOD: "Revenue declining 18% — driven by Product C underperformance"
3. Impact metrics must be quantified (estimate if needed)
4. Prioritize actions by Impact vs Effort (top 3 only)
5. Roadmap must be concrete 30/60/90 day actions

RESPOND IN JSON ONLY (no markdown, no backticks):
{{
  "executive_message": "one powerful sentence conclusion",
  "situation": "2-3 sentences: current state facts",
  "complication": "2-3 sentences: the key tension/problem",
  "resolution": "2-3 sentences: what must be done",
  "impact_metrics": [
    {{"label": "metric name", "value": "quantified value", "direction": "positive"}},
    {{"label": "metric name", "value": "quantified value", "direction": "negative"}}
  ],
  "prioritized_actions": [
    {{"action": "specific action", "impact": "High", "effort": "Low", "priority": 1, "timeframe": "30 days"}},
    {{"action": "specific action", "impact": "High", "effort": "Medium", "priority": 2, "timeframe": "60 days"}},
    {{"action": "specific action", "impact": "Medium", "effort": "Low", "priority": 3, "timeframe": "90 days"}}
  ],
  "roadmap_30d": ["action 1", "action 2"],
  "roadmap_60d": ["action 1", "action 2"],
  "roadmap_90d": ["action 1", "action 2"],
  "slide_headlines": [
    "Slide 2 headline: situation in one sentence",
    "Slide 3 headline: key finding as conclusion",
    "Slide 4 headline: root cause identified",
    "Slide 5 headline: opportunity quantified",
    "Slide 6 headline: recommended action"
  ]
}}"""


# ─── Response parser ───────────────────────────────────────────────

def _parse_executive_response(raw: str) -> ExecutiveNarrative:
    try:
        text = raw.strip()
        # strip markdown code blocks if any
        text = re.sub(r"```(?:json)?", "", text).strip()
        data = json.loads(text)
    except json.JSONDecodeError:
        # fallback
        return ExecutiveNarrative(
            executive_message="Analysis complete — review insights below",
            situation=raw[:200],
            complication="Data anomalies detected requiring attention",
            resolution="Review recommendations and implement prioritized actions",
        )

    impact_metrics = [
        ImpactMetric(
            label=m.get("label", ""),
            value=m.get("value", ""),
            direction=m.get("direction", "neutral"),
        )
        for m in data.get("impact_metrics", [])
    ]

    prioritized_actions = [
        PrioritizedAction(
            action=a.get("action", ""),
            impact=a.get("impact", "Medium"),
            effort=a.get("effort", "Medium"),
            priority=a.get("priority", i+1),
            timeframe=a.get("timeframe", "30 days"),
        )
        for i, a in enumerate(data.get("prioritized_actions", []))
    ]

    return ExecutiveNarrative(
        executive_message=data.get("executive_message", ""),
        situation=data.get("situation", ""),
        complication=data.get("complication", ""),
        resolution=data.get("resolution", ""),
        impact_metrics=impact_metrics,
        prioritized_actions=prioritized_actions,
        roadmap_30d=data.get("roadmap_30d", []),
        roadmap_60d=data.get("roadmap_60d", []),
        roadmap_90d=data.get("roadmap_90d", []),
        slide_headlines=data.get("slide_headlines", []),
    )


# ─── Main function ─────────────────────────────────────────────────

def generate_executive_narrative(
    analysis:     dict,
    report:       dict,
    company_name: str,
    industry:     str = "general",
    call_ai_fn    = None,   # inject analyze.py call_ai function
) -> ExecutiveNarrative:
    """
    Generate McKinsey-style executive narrative from analysis data.

    Usage in export.py:
        from services.executive_agent import generate_executive_narrative
        from routers.analyze import call_ai

        narrative = generate_executive_narrative(
            analysis=analysis_dict,
            report=report_dict,
            company_name=company_name,
            call_ai_fn=call_ai,
        )
    """
    if call_ai_fn is None:
        # fallback: basic narrative without AI
        return _fallback_narrative(analysis, report, company_name)

    prompt = _build_executive_prompt(analysis, report, company_name, industry)

    try:
        raw = call_ai_fn(prompt)
        return _parse_executive_response(raw)
    except Exception as e:
        return _fallback_narrative(analysis, report, company_name)


def _fallback_narrative(analysis: dict, report: dict, company_name: str) -> ExecutiveNarrative:
    """ใช้เมื่อ AI call ล้มเหลว — generate จาก rule-based"""
    qs       = report.get("quality_score", 0)
    insights = analysis.get("key_insights", [])
    recs     = analysis.get("recommendations", [])
    anomalies= analysis.get("anomalies", [])

    q_label = "excellent" if qs >= 80 else "acceptable" if qs >= 50 else "poor"
    msg = (
        f"{company_name} data shows {q_label} quality ({qs}/100) — "
        f"{len(insights)} key insights identified requiring immediate review"
    )

    actions = [
        PrioritizedAction(r, "High", "Low", i+1, f"{(i+1)*30} days")
        for i, r in enumerate(recs[:3])
    ]
    metrics = [
        ImpactMetric("Data Quality Score", f"{qs}/100",
                     "positive" if qs >= 70 else "negative"),
        ImpactMetric("Records Processed",
                     f"{report.get('cleaned_rows',0):,}", "neutral"),
        ImpactMetric("Issues Detected", str(len(anomalies)),
                     "negative" if anomalies else "positive"),
    ]

    return ExecutiveNarrative(
        executive_message=msg,
        situation=analysis.get("summary", "")[:300],
        complication="; ".join(anomalies[:2]) if anomalies else "No critical anomalies detected",
        resolution="; ".join(recs[:2]) if recs else "Continue monitoring key metrics",
        impact_metrics=metrics,
        prioritized_actions=actions,
        roadmap_30d=[recs[0]] if recs else ["Review data quality"],
        roadmap_60d=[recs[1]] if len(recs)>1 else ["Implement monitoring"],
        roadmap_90d=[recs[2]] if len(recs)>2 else ["Evaluate outcomes"],
        slide_headlines=[
            f"{company_name}: Data analysis reveals {len(insights)} actionable insights",
            f"Data quality at {qs}% — {q_label} foundation for decision-making",
            insights[0] if insights else "Key performance metrics reviewed",
            anomalies[0] if anomalies else "No critical anomalies detected",
            recs[0] if recs else "Continue strategic monitoring",
        ],
    )
