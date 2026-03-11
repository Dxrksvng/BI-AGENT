"""
services/story_builder.py
━━━━━━━━━━━━━━━━━━━━━━━━━
CONSULTING STORY ENGINE — Step 1 + 2

Core principle:
  A consulting slide is NOT information.
  A consulting slide is a MESSAGE supported by evidence.

Transforms raw AI analysis into:
  - ONE dominant executive message per slide
  - Decision-oriented language
  - Executive titles (conclusion-first)
  - Quality-checked slide objects

Usage:
    from services.story_builder import build_story, StoryDeck
    deck = build_story(analysis, report, company_name, call_ai_fn)
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Optional, Callable


# ─── Slide Object (Step 3) ────────────────────────────────────────────────────

@dataclass
class SlideStory:
    slide_type:   str          # cover / executive_summary / key_message / analysis / recommendation / roadmap / impact
    message:      str          # THE ONE executive message (title = conclusion)
    evidence:     str          # chart config or supporting data reference
    takeaways:    List[str] = field(default_factory=list)   # MAX 3, MAX 12 words each
    implication:  str = ""     # strategic implication (bottom of slide)
    chart_type:   str = ""     # bar / line / pie / scatter / table / none
    x_column:     str = ""
    y_column:     str = ""
    valid:        bool = True   # quality check result
    reject_reason:str = ""


@dataclass
class StoryDeck:
    company_name:    str
    main_message:    str          # THE headline for the whole deck
    headline_impact: str          # "+34% revenue opportunity"
    situation:       str
    complication:    str
    resolution:      str
    slides:          List[SlideStory] = field(default_factory=list)
    supporting_points: List[str] = field(default_factory=list)
    risks:           List[str]   = field(default_factory=list)
    opportunities:   List[str]   = field(default_factory=list)
    strategic_actions: List[str] = field(default_factory=list)
    quick_wins:      List[str]   = field(default_factory=list)
    medium_term:     List[str]   = field(default_factory=list)
    long_term:       List[str]   = field(default_factory=list)
    business_impacts: List[str]  = field(default_factory=list)
    theme_hint:      str = "clean_executive"   # for slide planner


# ─── Step 2: Executive Title Generator ───────────────────────────────────────

# Bad title patterns to reject
_GENERIC_TITLES = {
    "key insights", "insights", "analysis", "overview", "summary",
    "data analysis", "results", "findings", "report", "slide",
    "key findings", "recommendations", "next steps", "conclusion",
    "introduction", "background", "agenda",
}

def generate_executive_title(text: str, fallback: str = "") -> str:
    """
    Generate a consulting-grade executive title.

    Rules:
    - Must contain a conclusion (not just a topic)
    - No generic titles like "Insights" or "Analysis"
    - Should sound like a McKinsey slide title
    - Max ~12 words

    Examples:
      BAD:  "Key Insights"
      GOOD: "East Region Drives High Revenue Despite Lower Sales Volume"

      BAD:  "Sales Analysis"
      GOOD: "Product B Underperforms in Q3 — Immediate Action Required"
    """
    if not text:
        return fallback or "Strategic Finding Requires Executive Attention"

    # clean up
    title = text.strip().rstrip(".").rstrip(",")

    # strip leading labels
    for prefix in ["insight:", "finding:", "recommendation:", "action:", "note:", "-", "•", "*"]:
        if title.lower().startswith(prefix):
            title = title[len(prefix):].strip()

    # check if generic
    if title.lower() in _GENERIC_TITLES:
        return fallback or "Critical Business Finding Identified"

    # truncate to ~80 chars but keep at word boundary
    if len(title) > 80:
        words = title[:80].split(" ")
        title = " ".join(words[:-1]) if len(words) > 1 else words[0]
        title += " — Key Implication"

    # capitalize properly (title case for short, sentence case for long)
    if len(title.split()) <= 6:
        title = title.title()

    return title


# ─── Step 3+4: Slide Validator (Quality Check) ───────────────────────────────

def _validate_slide(slide: SlideStory) -> SlideStory:
    """
    STEP 7 — Quality check before export.
    Reject slide if:
      - no message exists
      - more than 3 bullets
      - title is generic
    """
    # Check: message exists
    if not slide.message or len(slide.message.strip()) < 5:
        slide.valid = False
        slide.reject_reason = "no message"
        return slide

    # Check: generic title
    if slide.message.lower().strip() in _GENERIC_TITLES:
        slide.valid = False
        slide.reject_reason = f"generic title: '{slide.message}'"
        return slide

    # Check: max 3 bullets
    if len(slide.takeaways) > 3:
        slide.takeaways = slide.takeaways[:3]   # auto-trim (don't reject, just fix)

    # Enforce: max 12 words per bullet
    trimmed = []
    for t in slide.takeaways:
        words = t.split()
        if len(words) > 12:
            t = " ".join(words[:12]) + "..."
        trimmed.append(t)
    slide.takeaways = trimmed

    slide.valid = True
    return slide


def _make_action_oriented(text: str) -> str:
    """Convert passive/generic text to action-oriented consulting language."""
    replacements = [
        (r"^there (is|are) ", ""),
        (r"^it (is|was) (noted|observed|found) that ", ""),
        (r"^the data (shows?|indicates?|suggests?) (that )?", ""),
        (r"^analysis (shows?|indicates?|reveals?) (that )?", ""),
        (r"\bshould consider\b", "must"),
        (r"\bmight want to\b", "should"),
        (r"\bcould potentially\b", "can"),
        (r"\bit is recommended that\b", ""),
        (r"\bwe recommend\b", ""),
        (r"\bplease note\b", ""),
    ]
    result = text.strip()
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE).strip()
    # capitalize first letter
    if result:
        result = result[0].upper() + result[1:]
    return result


# ─── AI Prompt ────────────────────────────────────────────────────────────────

def _build_story_prompt(analysis: dict, report: dict, company_name: str) -> str:
    qs       = report.get("quality_score", 0) if isinstance(report, dict) else 0
    insights = analysis.get("key_insights", [])
    anomalies= analysis.get("anomalies", [])
    recs     = analysis.get("recommendations", [])
    summary  = analysis.get("summary", "")
    charts   = analysis.get("charts_config", [])

    chart_cols = []
    for c in charts:
        chart_cols.append(f"{c.get('type','bar')}: {c.get('x_column','?')} vs {c.get('y_column','?')}")

    return f"""You are a Senior McKinsey Engagement Manager creating a C-suite presentation.

COMPANY: {company_name}
DATA QUALITY: {qs}/100

RAW ANALYSIS:
Summary: {summary[:600]}

Key Insights:
{chr(10).join(f'{i+1}. {ins}' for i, ins in enumerate(insights))}

Anomalies:
{chr(10).join(f'- {a}' for a in anomalies if 'no anomal' not in a.lower())}

Recommendations:
{chr(10).join(f'- {r}' for r in recs)}

Available Charts: {', '.join(chart_cols) if chart_cols else 'bar chart available'}

YOUR TASK: Transform this into a McKinsey consulting story.

CRITICAL RULES:
1. Every message must be a CONCLUSION, not a topic
2. Use decision-oriented language
3. Remove ALL generic wording ("data shows", "it is noted", "we recommend considering")
4. Each takeaway MAX 12 words, action-oriented
5. Implication must say WHAT TO DO, not what was found
6. Titles must sound like consulting headlines (conclusion-first)
7. Respond ONLY with valid JSON

{{
  "main_message": "Single most important conclusion for the CEO — must contain a specific insight or recommendation",
  "headline_impact": "Quantified opportunity or risk e.g. '$2.4M at risk' or '28% efficiency gain available'",
  "situation": "2 sentences: current state, specific and factual",
  "complication": "2 sentences: the core tension or problem revealed by data",
  "resolution": "2 sentences: what strategic action resolves this",
  "supporting_points": [
    "Specific supporting fact 1 — quantified",
    "Specific supporting fact 2",
    "Specific supporting fact 3"
  ],
  "risks": [
    "Specific risk with business consequence"
  ],
  "opportunities": [
    "Specific opportunity with estimated value"
  ],
  "strategic_actions": [
    "Concrete action with owner and timeline"
  ],
  "quick_wins": ["0-30 day action — specific"],
  "medium_term": ["31-60 day initiative — specific"],
  "long_term": ["61-90 day strategic move — specific"],
  "business_impacts": ["Quantified impact e.g. '+18% revenue in 90 days'"],
  "slides": [
    {{
      "slide_type": "executive_summary",
      "message": "Executive title — must be conclusion-first, not generic",
      "evidence": "What data/chart supports this message",
      "takeaways": ["Action-oriented point (max 12 words)", "Point 2", "Point 3"],
      "implication": "What decision-maker must do next",
      "chart_type": "bar",
      "x_column": "column_name_from_data",
      "y_column": "column_name_from_data"
    }},
    {{
      "slide_type": "key_message",
      "message": "Most critical single finding",
      "evidence": "Supporting data reference",
      "takeaways": ["Takeaway 1", "Takeaway 2"],
      "implication": "Strategic implication",
      "chart_type": "none",
      "x_column": "",
      "y_column": ""
    }},
    {{
      "slide_type": "analysis",
      "message": "What the data reveals — specific conclusion",
      "evidence": "Chart or table reference",
      "takeaways": ["Data-backed point 1", "Data-backed point 2", "Data-backed point 3"],
      "implication": "What this means for the business",
      "chart_type": "bar",
      "x_column": "column_name",
      "y_column": "column_name"
    }},
    {{
      "slide_type": "recommendation",
      "message": "Specific strategic recommendation — conclusion first",
      "evidence": "Why this recommendation (data reference)",
      "takeaways": ["Action 1 — owner, timeline", "Action 2", "Action 3"],
      "implication": "Expected outcome if implemented",
      "chart_type": "none",
      "x_column": "",
      "y_column": ""
    }},
    {{
      "slide_type": "roadmap",
      "message": "90-Day Plan Delivers [specific outcome]",
      "evidence": "Key milestones",
      "takeaways": ["30 days: [specific action]", "60 days: [specific action]", "90 days: [specific outcome]"],
      "implication": "Total expected business impact",
      "chart_type": "none",
      "x_column": "",
      "y_column": ""
    }},
    {{
      "slide_type": "impact",
      "message": "Expected business impact of recommended actions",
      "evidence": "Quantified projections",
      "takeaways": ["Impact metric 1", "Impact metric 2", "Impact metric 3"],
      "implication": "Call to action for leadership",
      "chart_type": "none",
      "x_column": "",
      "y_column": ""
    }}
  ]
}}"""


# ─── Parser ───────────────────────────────────────────────────────────────────

def _parse_story_response(raw: str, analysis: dict, company_name: str) -> StoryDeck:
    """Parse AI response into StoryDeck with quality validation."""
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
                raise ValueError("no JSON block found")
        else:
            start = text.find("{")
            end   = text.rfind("}") + 1
            data  = json.loads(text[start:end])

    except Exception as e:
        print(f"[story_builder] parse error: {e} — building fallback story")
        return _build_fallback_story(analysis, company_name)

    # Build slides with quality checks
    raw_slides = data.get("slides", [])
    validated_slides = []

    for sd in raw_slides:
        slide = SlideStory(
            slide_type  = sd.get("slide_type", "analysis"),
            message     = generate_executive_title(sd.get("message", "")),
            evidence    = sd.get("evidence", ""),
            takeaways   = [_make_action_oriented(t) for t in sd.get("takeaways", [])],
            implication = _make_action_oriented(sd.get("implication", "")),
            chart_type  = sd.get("chart_type", "none"),
            x_column    = sd.get("x_column", ""),
            y_column    = sd.get("y_column", ""),
        )
        slide = _validate_slide(slide)
        if slide.valid:
            validated_slides.append(slide)
        else:
            print(f"[story_builder] rejected slide '{slide.slide_type}': {slide.reject_reason}")

    print(f"[story_builder] {len(validated_slides)}/{len(raw_slides)} slides passed quality check")

    return StoryDeck(
        company_name     = company_name,
        main_message     = generate_executive_title(data.get("main_message", ""), f"{company_name}: Key Strategic Opportunities Identified"),
        headline_impact  = data.get("headline_impact", ""),
        situation        = data.get("situation", ""),
        complication     = data.get("complication", ""),
        resolution       = data.get("resolution", ""),
        slides           = validated_slides,
        supporting_points= data.get("supporting_points", [])[:4],
        risks            = data.get("risks", [])[:3],
        opportunities    = data.get("opportunities", [])[:3],
        strategic_actions= data.get("strategic_actions", [])[:4],
        quick_wins       = data.get("quick_wins", [])[:3],
        medium_term      = data.get("medium_term", [])[:3],
        long_term        = data.get("long_term", [])[:3],
        business_impacts = data.get("business_impacts", [])[:4],
        theme_hint       = _detect_theme(data, analysis),
    )


def _detect_theme(data: dict, analysis: dict) -> str:
    """Detect appropriate theme from story content."""
    all_text = (
        data.get("main_message", "") + " " +
        data.get("situation", "") + " " +
        " ".join(data.get("risks", []))
    ).lower()

    if any(w in all_text for w in ["risk", "decline", "loss", "crisis", "urgent", "critical"]):
        return "crimson_risk"
    if any(w in all_text for w in ["ai", "tech", "data science", "algorithm", "analytics"]):
        return "slate_tech"
    if any(w in all_text for w in ["revenue", "sales", "growth", "market", "profit"]):
        return "midnight_strategy"
    return "clean_executive"


def _build_fallback_story(analysis: dict, company_name: str) -> StoryDeck:
    """Graceful fallback using raw analysis when AI parsing fails."""
    insights = analysis.get("key_insights", [])
    recs     = analysis.get("recommendations", [])
    anomalies= [a for a in analysis.get("anomalies", []) if "no anomal" not in a.lower()]

    slides = []

    if insights:
        slides.append(_validate_slide(SlideStory(
            slide_type  = "key_message",
            message     = generate_executive_title(insights[0]) if insights else f"{company_name}: Key Finding",
            evidence    = "AI analysis output",
            takeaways   = [_make_action_oriented(i) for i in insights[:3]],
            implication = recs[0] if recs else "Review and act on findings above.",
            chart_type  = "bar",
        )))

    if recs:
        slides.append(_validate_slide(SlideStory(
            slide_type  = "recommendation",
            message     = generate_executive_title(recs[0]) if recs else "Immediate Action Required",
            evidence    = "Based on data analysis",
            takeaways   = [_make_action_oriented(r) for r in recs[:3]],
            implication = "Implement within 30 days for maximum impact.",
            chart_type  = "none",
        )))

    return StoryDeck(
        company_name      = company_name,
        main_message      = f"{company_name}: Data Analysis Reveals Strategic Priorities",
        headline_impact   = "Multiple improvement opportunities identified",
        situation         = analysis.get("summary", "")[:300],
        complication      = "Current data patterns indicate areas requiring strategic attention.",
        resolution        = "A focused 90-day action plan will address key challenges.",
        slides            = [s for s in slides if s.valid],
        supporting_points = insights[:3],
        risks             = anomalies[:2],
        opportunities     = recs[:3],
        strategic_actions = recs[:3],
        quick_wins        = recs[:1],
        medium_term       = recs[1:2],
        long_term         = recs[2:3],
        business_impacts  = [],
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def build_story(
    analysis:     dict,
    report:       dict,
    company_name: str,
    call_ai_fn:   Callable[[str], str],
) -> StoryDeck:
    """
    Main entry point — Build full consulting story from raw analysis.

    Args:
        analysis:     dict with key_insights, anomalies, recommendations, etc.
        report:       dict with quality_score, n_rows, etc.
        company_name: string
        call_ai_fn:   your existing call_ai() function

    Returns:
        StoryDeck with validated slides, messages, and consulting narrative
    """
    print(f"[story_builder] building consulting story for {company_name}...")

    prompt = _build_story_prompt(analysis, report, company_name)
    print(f"[story_builder] calling AI (prompt_len={len(prompt)})...")

    try:
        raw = call_ai_fn(prompt)
        print(f"[story_builder] response received (len={len(raw)})")
        deck = _parse_story_response(raw, analysis, company_name)
    except Exception as e:
        print(f"[story_builder] AI call failed: {e} — using fallback")
        deck = _build_fallback_story(analysis, company_name)

    print(f"[story_builder] done — main_message: '{deck.main_message[:60]}...'")
    print(f"[story_builder] slides: {len(deck.slides)} validated")

    return deck
