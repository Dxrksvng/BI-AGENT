"""
services/slide_planner.py
━━━━━━━━━━━━━━━━━━━━━━━━━
Slide Planner — AI designs the presentation structure.

Given the consulting story + data, AI decides:
  - How many slides
  - What goes on each slide
  - Which charts to use and where
  - Visual theme and color palette
  - Narrative flow

Output feeds directly into slide_builder_consulting.js
"""

import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable


# ─── Theme Definitions ────────────────────────────────────────────────────────

THEMES = {
    "midnight_strategy": {
        "name":    "Midnight Strategy",
        "primary": "0D1B2A",
        "accent":  "4FC3F7",
        "gold":    "FFB300",
        "bg":      "F8FAFC",
        "text":    "1A1A2E",
        "best_for": ["sales", "revenue", "growth", "strategy"],
    },
    "clean_executive": {
        "name":    "Clean Executive",
        "primary": "1A1F5E",
        "accent":  "00AEAB",
        "gold":    "F0C040",
        "bg":      "FFFFFF",
        "text":    "1F2937",
        "best_for": ["general", "finance", "report"],
    },
    "forest_growth": {
        "name":    "Forest Growth",
        "primary": "1B4332",
        "accent":  "40916C",
        "gold":    "B7E4C7",
        "bg":      "F0FDF4",
        "text":    "1B4332",
        "best_for": ["sustainability", "growth", "environment", "health"],
    },
    "bold_indigo": {
        "name":    "Bold Indigo",
        "primary": "3730A3",
        "accent":  "818CF8",
        "gold":    "FCD34D",
        "bg":      "F5F3FF",
        "text":    "1E1B4B",
        "best_for": ["tech", "startup", "innovation", "product"],
    },
    "slate_tech": {
        "name":    "Slate Tech",
        "primary": "0F172A",
        "accent":  "38BDF8",
        "gold":    "FB923C",
        "bg":      "F1F5F9",
        "text":    "0F172A",
        "best_for": ["ai", "data", "engineering", "analytics"],
    },
    "crimson_risk": {
        "name":    "Crimson Risk",
        "primary": "7F1D1D",
        "accent":  "DC2626",
        "gold":    "FCA5A5",
        "bg":      "FFF5F5",
        "text":    "1C1917",
        "best_for": ["risk", "audit", "compliance", "crisis"],
    },
}

# ─── Layout Templates ─────────────────────────────────────────────────────────

LAYOUTS = {
    "pyramid": [
        "cover", "scr_summary", "situation_chart",
        "key_findings", "root_cause",
        "opportunity", "recommendations", "roadmap", "impact_close"
    ],
    "dashboard_first": [
        "cover", "kpi_wall", "situation_chart",
        "trend_analysis", "key_findings",
        "recommendations", "roadmap", "impact_close"
    ],
    "story_driven": [
        "cover", "key_message", "situation_chart",
        "complication_deep", "resolution",
        "recommendations", "roadmap", "impact_close"
    ],
    "risk_spotlight": [
        "cover", "risk_summary", "anomaly_wall",
        "root_cause", "impact_assessment",
        "mitigation", "roadmap", "impact_close"
    ],
    "data_intelligence": [
        "cover", "scr_summary", "kpi_wall",
        "trend_analysis", "key_findings",
        "opportunity", "recommendations", "impact_close"
    ],
}


# ─── Output Schema ────────────────────────────────────────────────────────────

@dataclass
class SlidePlan:
    theme_key:    str = "clean_executive"
    layout_key:   str = "pyramid"
    theme:        Dict = field(default_factory=dict)
    slide_order:  List[str] = field(default_factory=list)
    chart_plan:   List[Dict] = field(default_factory=list)   # which charts on which slides
    n_slides:     int = 9
    rationale:    str = ""     # why these choices were made


# ─── Deterministic Selector (no AI needed, fast) ─────────────────────────────

def _pick_theme_deterministic(analysis: dict, report: dict, industry: str) -> str:
    """Pick theme based on content — same data always gets same theme."""
    anomalies   = analysis.get("anomalies", [])
    qs          = report.get("quality_score", 100) if isinstance(report, dict) else 100
    summary     = (analysis.get("summary", "") + industry).lower()
    insights    = " ".join(analysis.get("key_insights", [])).lower()
    all_text    = summary + insights

    # Rule-based selection
    risk_words  = ["risk", "anomal", "declin", "loss", "fail", "critical", "urgent"]
    tech_words  = ["ai", "machine learn", "algorithm", "data science", "analytics", "engineer"]
    sales_words = ["revenue", "sales", "growth", "market", "customer", "profit"]
    green_words = ["sustainab", "environment", "green", "health", "wellness"]
    indigo_words= ["startup", "innovat", "product", "launch", "disrupt"]

    if qs < 60 or len([a for a in anomalies if "no anomal" not in a.lower()]) >= 2:
        return "crimson_risk"
    if any(w in all_text for w in risk_words):
        return "crimson_risk"
    if any(w in all_text for w in tech_words) or "tech" in industry.lower():
        return "slate_tech"
    if any(w in all_text for w in green_words):
        return "forest_growth"
    if any(w in all_text for w in indigo_words):
        return "bold_indigo"
    if any(w in all_text for w in sales_words):
        return "midnight_strategy"
    return "clean_executive"


def _pick_layout_deterministic(analysis: dict, df_summary: dict) -> str:
    """Pick layout based on data shape and content."""
    n_cols      = df_summary.get("n_cols", 0) if isinstance(df_summary, dict) else 0
    anomalies   = analysis.get("anomalies", [])
    all_text    = " ".join(analysis.get("key_insights", []) + [analysis.get("summary", "")]).lower()

    has_anomalies = len([a for a in anomalies if "no anomal" not in a.lower()]) >= 2
    has_many_cols = n_cols >= 5
    is_risk_focus = any(w in all_text for w in ["risk", "critical", "urgent", "decline", "loss"])
    is_data_rich  = n_cols >= 4 and has_many_cols

    if has_anomalies or is_risk_focus:
        return "risk_spotlight"
    if is_data_rich:
        return "dashboard_first"
    if "story" in all_text or "journey" in all_text:
        return "story_driven"
    if n_cols >= 3:
        return "data_intelligence"
    return "pyramid"


def _build_chart_plan(analysis: dict, df_summary: dict) -> List[Dict]:
    """Map AI chart suggestions to slide positions."""
    charts_cfg = analysis.get("charts_config", [])
    columns    = df_summary.get("columns", []) if isinstance(df_summary, dict) else []

    plan = []
    for i, cfg in enumerate(charts_cfg[:4]):
        x_col = cfg.get("x_column", "")
        y_col = cfg.get("y_column", "")
        # verify columns exist
        if x_col in columns and y_col in columns:
            plan.append({
                "slide_index": i + 2,   # start from slide 3
                "type":        cfg.get("type", "bar"),
                "title":       cfg.get("title", ""),
                "x_column":    x_col,
                "y_column":    y_col,
                "description": cfg.get("description", ""),
            })

    # ensure at least one chart
    if not plan and len(columns) >= 2:
        plan.append({
            "slide_index": 2,
            "type":        "bar",
            "title":       "Key Performance Overview",
            "x_column":    columns[0],
            "y_column":    columns[1] if len(columns) > 1 else columns[0],
            "description": "Overview of primary business metrics",
        })

    return plan


# ─── Public API ───────────────────────────────────────────────────────────────

def build_slide_plan(
    analysis:   dict,
    report:     dict,
    df_summary: dict,
    story,                      # ConsultingStory dataclass
    industry:   str = "general",
    call_ai_fn: Optional[Callable] = None,   # optional — uses deterministic if None
) -> SlidePlan:
    """
    Build the slide plan.

    Uses deterministic logic (fast, consistent) by default.
    If call_ai_fn is provided and story has enough content,
    AI can override theme/layout choices.

    Returns SlidePlan with theme, layout, chart plan.
    """
    print(f"[slide_planner] building plan — industry={industry}")

    # Deterministic picks (always run first)
    theme_key  = _pick_theme_deterministic(analysis, report, industry)
    layout_key = _pick_layout_deterministic(analysis, df_summary)
    theme      = THEMES.get(theme_key, THEMES["clean_executive"])
    layout     = LAYOUTS.get(layout_key, LAYOUTS["pyramid"])
    chart_plan = _build_chart_plan(analysis, df_summary)

    rationale = (
        f"Theme '{theme['name']}' selected based on content analysis. "
        f"Layout '{layout_key}' chosen for {len(df_summary.get('columns',[]))} columns dataset. "
        f"{len(chart_plan)} chart(s) planned."
    )

    print(f"[slide_planner] theme={theme_key} layout={layout_key} charts={len(chart_plan)}")

    return SlidePlan(
        theme_key   = theme_key,
        layout_key  = layout_key,
        theme       = theme,
        slide_order = layout,
        chart_plan  = chart_plan,
        n_slides    = len(layout),
        rationale   = rationale,
    )
