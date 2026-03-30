"""
services/ai_deck_designer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AI Deck Designer — AI คิดออกแบบ PPTX ทั้งหมดเอง

ไม่มี hardcode template
AI อ่าน statistical report แล้วตัดสินใจ:
  - กี่ slides
  - แต่ละ slide ชื่ออะไร layout อะไร
  - กราฟชนิดใด columns อะไร
  - สีธีมอะไร
  - KPI อะไรสำคัญที่สุด
  - narrative flow อย่างไร

รองรับทุก dataset — sales, HR, finance, telco, healthcare, etc.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import os
from dotenv import load_dotenv
from services.design_agent import DesignSpec, generate_design_spec
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

VALID_LAYOUTS = {
    "cover", "executive_summary", "kpi_dashboard", "kpi_row",
    "split_chart_right", "split_chart_left", "full_chart",
    "three_column", "two_column", "bullets_only",
    "big_number", "timeline", "dark_close", "section_divider",
    "custom_text",  # legacy alias → sText
}


def _parse_json_safe(raw: str) -> dict:
    """Parse JSON from AI response, strip markdown fences."""
    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except Exception:
                continue
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    raise ValueError("No valid JSON found in AI response")


def _validate_chart_columns(
    ct: str, xc: str, yc: str,
    date_cols: set, num_cols: set, cat_cols: set, valid_cols: set,
) -> tuple:
    """
    Auto-correct chart type + column pairing.
    If columns don't match chart type → fix silently rather than crash.
    """
    # Strip invalid chart types
    allowed = {"bar_vertical","bar_horizontal","line","donut","scatter","area","none","kpi_card"}
    if ct not in allowed:
        ct = "bar_vertical"

    # pie → donut (always)
    if ct == "pie":
        ct = "donut"

    # Remove columns not in dataset
    if xc and xc not in valid_cols:
        xc = ""
    if yc and yc not in valid_cols:
        yc = ""

    # line/area MUST have datetime x
    if ct in ("line", "area"):
        if not date_cols:
            ct = "bar_vertical"  # no time axis — downgrade
        elif xc not in date_cols:
            xc = next(iter(date_cols), "")

    # scatter: both must be numeric
    if ct == "scatter":
        if xc not in num_cols and num_cols:
            xc = next(iter(num_cols), "")
        if yc not in num_cols and len(num_cols) > 1:
            yc = [c for c in num_cols if c != xc][0] if len(num_cols) > 1 else ""

    # donut: x=categorical, y=numeric
    if ct == "donut":
        if xc not in cat_cols and cat_cols:
            xc = next(iter(cat_cols), "")
        if yc not in num_cols and num_cols:
            yc = next(iter(num_cols), "")

    # bar_*: x=categorical, y=numeric
    if ct in ("bar_vertical", "bar_horizontal"):
        if xc not in cat_cols and cat_cols:
            xc = next(iter(cat_cols), "")
        if yc not in num_cols and num_cols:
            yc = next(iter(num_cols), "")

    return ct, xc, yc


# ─── Slide Plan Schema ────────────────────────────────────────────────────────

@dataclass
class SlideSpec:
    slide_num:    int
    slide_type:   str        # cover / executive_summary / kpi_dashboard / chart_analysis / comparison / findings / recommendations / roadmap / impact_close / custom
    title:        str        # conclusion-first title
    subtitle:     str        # supporting subtitle
    layout:       str        # full_chart / split_chart_right / split_chart_left / three_column / two_column / kpi_row / dark_close / cover
    chart_type:   str        # bar_vertical / bar_horizontal / line / pie / donut / scatter / none
    x_column:     str        # column name for x axis
    y_column:     str        # column name for y axis
    group_by:     str        # optional grouping column
    bullets:      List[str]  # key points (max 4)
    insight:      str        # bottom implication bar text
    theme_hint:   str        # primary / warning / danger / success / neutral
    kpis:         List[Dict] # [{name, value, unit, status}] for kpi slides


@dataclass
class DeckPlan:
    company_name:   str
    industry:       str
    main_message:   str      # one-sentence headline
    theme:          str      # navy_consulting / midnight_tech / crimson_risk / forest_growth / slate_minimal
    accent_color:   str      # hex color
    total_slides:   int
    slides:         List[SlideSpec]
    design_rationale: str    # why these choices were made
    design_spec: Optional[dict] = None

# ─── Theme Library ────────────────────────────────────────────────────────────

THEMES = {
    "ultra_premium": {
        "primary": "1A1A1A", "accent": "D4AF37", "gold": "FFD700",
        "success": "00C897", "danger": "FF4D4D", "bg": "0D0D0D",
        "surface": "1A1A1A", "text1": "FFFFFF", "text2": "E0E0E0",
        "chart_colors": ["D4AF37","FFD700","FFFFFF","00C897","FF4D4D","9A9A9A","4A4A4A","FDFBD4"],
    },
    "navy_consulting": {
        "primary": "0F172A", "accent": "22D3EE", "gold": "F59E0B",
        "success": "10B981", "danger": "EF4444", "bg": "FFFFFF",
        "surface": "F1F5F9", "text1": "0F172A", "text2": "475569",
        "chart_colors": ["0F172A","22D3EE","10B981","F59E0B","EF4444","94A3B8"],
    },
    "midnight_tech": {
        "primary": "0D1B2A", "accent": "4FC3F7", "gold": "FFB300",
        "success": "26C6DA", "danger": "EF5350", "bg": "F8FAFC",
        "surface": "E8EEF3", "text1": "0D1B2A", "text2": "37474F",
        "chart_colors": ["0D1B2A","4FC3F7","26C6DA","FFB300","EF5350","90A4AE"],
    },
    "crimson_risk": {
        "primary": "7F1D1D", "accent": "DC2626", "gold": "FCA5A5",
        "success": "16A34A", "danger": "991B1B", "bg": "FFF5F5",
        "surface": "FEE2E2", "text1": "1C1917", "text2": "44403C",
        "chart_colors": ["7F1D1D","DC2626","F97316","FCA5A5","16A34A","94A3B8"],
    },
    "forest_growth": {
        "primary": "1B4332", "accent": "40916C", "gold": "B7E4C7",
        "success": "2D6A4F", "danger": "D62828", "bg": "F0FDF4",
        "surface": "DCFCE7", "text1": "1B4332", "text2": "374151",
        "chart_colors": ["1B4332","40916C","74C69D","B7E4C7","D62828","94A3B8"],
    },
    "slate_minimal": {
        "primary": "1E293B", "accent": "6366F1", "gold": "FBBF24",
        "success": "10B981", "danger": "EF4444", "bg": "FFFFFF",
        "surface": "F1F5F9", "text1": "1E293B", "text2": "64748B",
        "chart_colors": ["1E293B","6366F1","8B5CF6","FBBF24","10B981","EF4444"],
    },
}


# ─── AI Prompt ────────────────────────────────────────────────────────────────

def _build_structure_prompt(
    stat_dict: dict,
    analysis: dict,
    company_name: str,
    industry: str,
    audience: str,
) -> str:
    """Call 1 — structure only. Small response, never truncates."""
    col_stats    = stat_dict.get("column_stats", [])
    num_cols     = [c["name"] for c in col_stats if c.get("dtype") == "numeric"]
    cat_cols     = [c["name"] for c in col_stats if c.get("dtype") == "categorical"]
    date_cols    = [c["name"] for c in col_stats if c.get("dtype") == "datetime"]
    kpis_text    = "\n".join(f"  {k['name']}: {k['formatted']} [{k['status']}]" for k in stat_dict.get("kpis", [])[:8])
    anom_high    = sum(1 for a in stat_dict.get("anomalies", []) if a["severity"] == "high")
    chart_recs   = stat_dict.get("chart_recommendations", [])
    chart_text   = "\n".join(
        f"  #{c['priority']} {c['chart_type'].upper()}: x={c['x_column']}, y={c['y_column']} — {c['title']}"
        for c in chart_recs[:8]
    )
    has_time     = len(date_cols) > 0

    return f"""You are a McKinsey CDO designing a board-level BI deck for {company_name}.

DATASET: {stat_dict.get('n_rows',0):,} rows × {stat_dict.get('n_cols',0)} cols | Quality: {stat_dict.get('confidence_score',0)}/100
Industry: {industry} | Audience: {audience}
Has time series: {"YES — " + ", ".join(date_cols) if has_time else "NO"}
Numeric columns: {", ".join(num_cols[:12]) or "none"}
Categorical columns: {", ".join(cat_cols[:8]) or "none"}

VERIFIED KPIs:
{kpis_text or "  none"}

STATISTICALLY RECOMMENDED CHARTS (engine-selected):
{chart_text or "  none"}

High-severity anomalies: {anom_high}

━━━ TASK: STRUCTURE ONLY ━━━

Design 10-16 slides. For each slide specify ONLY: slide_num, slide_type, title, layout, chart_type.
Do NOT write bullets/insight/kpis yet — those come in the detail pass.

LAYOUT RULES (variety is mandatory):
  - Never same layout twice in a row
  - Use at least 6 different layouts per deck
  - Available: cover, executive_summary, kpi_dashboard, kpi_row, split_chart_right,
    split_chart_left, full_chart, three_column, two_column, bullets_only,
    big_number, timeline, dark_close, section_divider

CHART TYPE RULES (hard constraints):
  - "line"          → ONLY if time column exists ({", ".join(date_cols) if date_cols else "none available"})
  - "scatter"       → ONLY for 2 numeric columns with real correlation
  - "bar_vertical"  → categorical ≤10 unique values
  - "bar_horizontal"→ categorical >10 unique values or ranked list
  - "donut"         → part-of-whole, 2-8 segments
  - "area"          → cumulative trend over time
  - "none"          → text-only slides
  - NEVER: "pie" (use donut instead), "histogram" (not supported)
  - chart columns MUST exist in: numeric={json.dumps(num_cols[:12])}, categorical={json.dumps(cat_cols[:8])}

THEME:
  - executive_light : default business
  - navy_consulting : finance/banking
  - crimson_risk    : if {anom_high} high anomalies OR quality<60
  - forest_growth   : healthcare/ESG
  - midnight_tech   : tech/SaaS/AI
  - slate_minimal   : startup/VC
  - ultra_premium   : luxury/premium brand

TITLE RULE: Every title = CONCLUSION not label.
  BAD: "Revenue Analysis"  GOOD: "Revenue Down 18% — 3 Products Drive 80% of Loss"

End with dark_close. Include section_divider if deck has >12 slides.

OUTPUT — compact JSON only, no markdown:
{{
  "company_name": "{company_name}",
  "industry": "{industry}",
  "main_message": "single most important finding in 1 sentence",
  "theme": "chosen_theme",
  "accent_color": "hex without #",
  "design_rationale": "why this theme and narrative arc (2 sentences)",
  "slides": [
    {{"slide_num": 1, "slide_type": "cover",       "title": "...", "layout": "cover",            "chart_type": "none"}},
    {{"slide_num": 2, "slide_type": "kpi_overview","title": "...", "layout": "kpi_dashboard",    "chart_type": "bar_vertical"}},
    {{"slide_num": 3, "slide_type": "trend",       "title": "...", "layout": "full_chart",       "chart_type": "line"}},
    ...
    {{"slide_num": N, "slide_type": "closing",     "title": "...", "layout": "dark_close",       "chart_type": "none"}}
  ]
}}"""


def _build_detail_prompt(
    slide_outlines: list,
    stat_dict: dict,
    analysis: dict,
    company_name: str,
) -> str:
    """Call 2 — fill detail for a batch of 3 slides. Small response, no truncation."""
    col_stats = stat_dict.get("column_stats", [])
    num_cols  = [c["name"] for c in col_stats if c.get("dtype") == "numeric"]
    cat_cols  = [c["name"] for c in col_stats if c.get("dtype") == "categorical"]
    date_cols = [c["name"] for c in col_stats if c.get("dtype") == "datetime"]
    kpis      = stat_dict.get("kpis", [])
    insights  = analysis.get("key_insights", [])
    recs      = analysis.get("recommendations", [])

    col_detail = []
    for c in col_stats[:20]:
        if c["dtype"] == "numeric":
            col_detail.append(f"  NUM  {c['name']}: mean={c.get('mean','?')}, min={c.get('min','?')}, max={c.get('max','?')}, null={c.get('null_pct',0):.0f}%")
        elif c["dtype"] == "categorical":
            top = ", ".join(f"{v[0]}({v[2]:.0f}%)" for v in (c.get("top_values") or [])[:4])
            col_detail.append(f"  CAT  {c['name']}: {c.get('n_unique',0)} unique — top: {top}")
        elif c["dtype"] == "datetime":
            col_detail.append(f"  DATE {c['name']}: {c.get('date_min','')} to {c.get('date_max','')}")

    kpis_json = json.dumps(
        [{"name": k["name"], "value": k["formatted"], "status": k["status"]} for k in kpis[:8]],
        ensure_ascii=False,
    )

    return f"""Fill slide details for {company_name}. Use ONLY verified column names below.

COLUMNS:
{chr(10).join(col_detail)}

VERIFIED KPIs: {kpis_json}
KEY INSIGHTS: {json.dumps(insights[:5], ensure_ascii=False)}
RECOMMENDATIONS: {json.dumps(recs[:4], ensure_ascii=False)}

SLIDES TO FILL:
{json.dumps(slide_outlines, ensure_ascii=False)}

CHART COLUMN RULES (strict — column must exist in list above):
  line/area   → x_column must be one of: {json.dumps(date_cols)}
  scatter     → x_column AND y_column must be numeric: {json.dumps(num_cols[:10])}
  bar_*       → x_column=categorical, y_column=numeric
  donut       → x_column=categorical(2-8 values), y_column=numeric
  kpi_card    → y_column=numeric col name, x_column=""
  none        → x_column="", y_column=""

FOR EACH SLIDE provide:
  subtitle    : 1 short sentence supporting the title
  bullets     : 2-4 bullets, each citing a real number from KPIs/stats
  insight     : 1 bold "so what" business implication (bottom bar)
  x_column    : exact column name from list (or "")
  y_column    : exact column name from list (or "")
  group_by    : optional categorical column for color grouping (or "")
  theme_hint  : primary / warning / danger / success / neutral
  kpis        : for kpi_dashboard/kpi_row/big_number ONLY — use verified KPIs list
  source_note : "source: column_name — formula used" (audit trail)

SPECIAL RULES:
  - cover, section_divider: bullets=[], insight="", kpis=[], x_column="", y_column=""
  - dark_close: 2-3 impact bullets, no chart
  - big_number: kpis=[exactly 1 KPI], chart_type=kpi_card

OUTPUT — compact JSON only (no markdown):
{{
  "slides": [
    {{
      "slide_num": N,
      "subtitle": "...",
      "bullets": ["bullet with specific number", "..."],
      "insight": "bold implication",
      "x_column": "exact_col",
      "y_column": "exact_col",
      "group_by": "",
      "theme_hint": "primary",
      "kpis": [],
      "source_note": "source: col_name"
    }}
  ]
}}"""


def _build_designer_prompt(
    stat_dict: dict,
    analysis: dict,
    company_name: str,
    industry: str,
    audience: str,
) -> str:
    """Legacy single-call prompt — kept for backward compat, now unused by design_deck()."""
    return _build_structure_prompt(stat_dict, analysis, company_name, industry, audience)

    return f"""You are a world-class data visualization designer and McKinsey strategy consultant combined.

TASK: Design a complete, professional PowerPoint presentation for {company_name}.
You have FULL CREATIVE FREEDOM — choose your own slide count, layouts, colors, chart types.

━━━ DATASET INFORMATION ━━━
Company: {company_name}
Industry: {industry}
Audience: {audience}
Dataset: {stat_dict.get('n_rows',0):,} rows × {stat_dict.get('n_cols',0)} columns
Confidence: {stat_dict.get('confidence_score',0)}/100

COLUMNS AVAILABLE:
{chr(10).join(col_summary)}

VERIFIED KPIs (use these exact numbers):
{kpis_text or '  No KPIs available'}

STATISTICAL ANOMALIES:
{anomalies_text or '  None detected'}

CORRELATIONS:
{correlations_text or '  None significant'}

AI INSIGHTS:
{insights_text}

RECOMMENDATIONS:
{recs_text}

━━━ YOUR DESIGN TASK ━━━

Design a complete deck. Think like a Big4 consultant designing for a Fortune 500 board meeting.

RULES:
1. Choose 8-15 slides based on data complexity
2. Every slide title must be a CONCLUSION, not a label
   BAD: "Revenue Analysis"  GOOD: "Revenue Declining 18% — Product C Drives 73% of Loss"
3. Choose chart types that BEST show the pattern:
   - bar_vertical: comparing categories (up to 8)
   - bar_horizontal: ranking (long labels)
   - line: trend over time or sequence
   - pie: composition (2-6 categories only, when parts-of-whole matters)
   - donut: same as pie but more modern
   - scatter: correlation between 2 numeric cols
   - none: text/bullets only
4. Choose x_column and y_column ONLY from the columns listed above
5. Choose theme based on data:
   - executive_light: DEFAULT for most business data — clean white, professional blue
   - navy_consulting: if finance/banking/investment data
   - crimson_risk: if anomaly count >= 3 or confidence < 60 (risk alert)
   - forest_growth: if healthcare/sustainability/environment
   - midnight_tech: if tech/AI/software/data science
   - slate_minimal: if startup/innovation
   IMPORTANT: Do NOT use ultra_premium. Always use white background themes.
6. CREATIVITY RULES (MUST FOLLOW):
   - NEVER use navy_consulting if crimson_risk or ultra_premium fits better
   - NO two consecutive slides with the same layout — vary every slide
   - Minimum 4 different layouts in one deck
   - Be BOLD — surprise the audience with unexpected but data-driven chart choices
   - Each slide must tell a different part of the story
7. Design rationale: explain WHY you made these choices

AVAILABLE LAYOUTS:
- cover: title slide with company name
- executive_summary: 3-column SCR cards
- kpi_dashboard: KPI numbers + chart below
- split_chart_right: chart left 65% + bullets right 35%
- split_chart_left: bullets left 35% + chart right 65%
- three_column: 3 equal content columns
- two_column: 2 equal columns
- full_chart: chart takes full content area
- dark_close: dark background closing slide
- custom_text: text-heavy, no chart

CRITICAL: Respond with ONLY valid JSON. No markdown, no backticks, no explanation.
Keep slide titles under 80 characters. Keep bullets under 100 characters each.
Maximum 12 slides to avoid token limits.

RESPOND WITH ONLY VALID JSON (no markdown):
{{
  "company_name": "{company_name}",
  "industry": "{industry}",
  "main_message": "one powerful sentence that IS the conclusion of the whole deck",
  "theme": "executive_light|navy_consulting|midnight_tech|crimson_risk|forest_growth|slate_minimal",
  "accent_color": "hex color without #",
  "total_slides": 10,
  "design_rationale": "why you chose this theme, structure, and visual approach",
  "slides": [
    {{
      "slide_num": 1,
      "slide_type": "cover",
      "title": "main message of entire deck",
      "subtitle": "supporting context",
      "layout": "cover",
      "chart_type": "none",
      "x_column": "",
      "y_column": "",
      "group_by": "",
      "bullets": [],
      "insight": "",
      "theme_hint": "primary",
      "kpis": []
    }},
    {{
      "slide_num": 2,
      "slide_type": "kpi_dashboard",
      "title": "conclusion about key metrics",
      "subtitle": "KPI Overview",
      "layout": "kpi_dashboard",
      "chart_type": "bar_vertical",
      "x_column": "column_name_from_dataset",
      "y_column": "numeric_column_from_dataset",
      "group_by": "",
      "bullets": ["insight 1 with real number", "insight 2"],
      "insight": "strategic implication",
      "theme_hint": "primary",
      "kpis": [
        {{"name": "KPI Name", "value": "formatted value", "unit": "%", "status": "critical|warning|good|neutral"}}
      ]
    }}
  ]
}}"""


# ─── Parser ───────────────────────────────────────────────────────────────────

def _parse_deck_plan(raw: str, company_name: str, stat_dict: dict) -> DeckPlan:
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
        print(f"[ai_designer] Parse error: {e} — trying partial parse")
        # Try to extract partial JSON
        try:
            start = raw.find('{')
            # Find last complete slide
            last_bracket = raw.rfind('}', 0, len(raw))
            if last_bracket > start:
                partial = raw[start:last_bracket+1]
                # Fix truncated JSON by closing arrays/objects
                partial = partial.rstrip(',').rstrip()
                # Count open brackets
                opens = partial.count('{') - partial.count('}')
                arrays = partial.count('[') - partial.count(']')
                partial += ']' * max(0, arrays) + '}' * max(0, opens)
                data = json.loads(partial)
                plan = _parse_deck_plan_from_data(data, company_name, stat_dict)
                if plan and plan.total_slides > 0:
                    print(f"[ai_designer] Partial parse OK — {plan.total_slides} slides")
                    return plan
        except Exception as e2:
            print(f"[ai_designer] Partial parse also failed: {e2}")
        return _fallback_plan(company_name, stat_dict)

    slides = []
    for sd in data.get("slides", []):
        slides.append(SlideSpec(
            slide_num   = sd.get("slide_num", len(slides)+1),
            slide_type  = sd.get("slide_type", "custom_text"),
            title       = sd.get("title", ""),
            subtitle    = sd.get("subtitle", ""),
            layout      = sd.get("layout", "split_chart_right"),
            chart_type  = sd.get("chart_type", "none"),
            x_column    = sd.get("x_column", ""),
            y_column    = sd.get("y_column", ""),
            group_by    = sd.get("group_by", ""),
            bullets     = sd.get("bullets", [])[:4],
            insight     = sd.get("insight", ""),
            theme_hint  = sd.get("theme_hint", "primary"),
            kpis        = sd.get("kpis", []),
        ))

    if not slides:
        return _fallback_plan(company_name, stat_dict)

    return DeckPlan(
        company_name     = data.get("company_name", company_name),
        industry         = data.get("industry", "general"),
        main_message     = data.get("main_message", ""),
        theme            = data.get("theme", "navy_consulting"),
        accent_color     = data.get("accent_color", "22D3EE"),
        total_slides     = len(slides),
        slides           = slides,
        design_rationale = data.get("design_rationale", ""),
    )


# ─── Fallback Plan ────────────────────────────────────────────────────────────

def _fallback_plan(company_name: str, stat_dict: dict) -> DeckPlan:
    """Rule-based fallback if AI fails."""
    kpis    = stat_dict.get("kpis", [])
    anom    = stat_dict.get("anomalies", [])
    insights= []
    cols    = stat_dict.get("column_stats", [])
    num_cols= [c["name"] for c in cols if c.get("dtype") == "numeric"]
    cat_cols= [c["name"] for c in cols if c.get("dtype") == "categorical"]

    theme = "crimson_risk" if len([a for a in anom if a.get("severity")=="high"]) >= 2 else "navy_consulting"

    slides = [
        SlideSpec(1,"cover","Business Intelligence Report","AI-Powered Analysis","cover","none","","","","","",theme,[]),
        SlideSpec(2,"kpi_dashboard","Key Metrics Overview","Performance Dashboard","kpi_dashboard",
                  "bar_vertical",cat_cols[0] if cat_cols else "",num_cols[0] if num_cols else "",
                  "","","primary",theme,kpis[:4]),
        SlideSpec(3,"findings","Key Findings","Critical Insights","split_chart_right",
                  "bar_horizontal",cat_cols[0] if cat_cols else "",num_cols[0] if num_cols else "",
                  "","","primary",theme,[]),
        SlideSpec(4,"recommendations","Strategic Recommendations","Priority Actions","three_column",
                  "none","","","","","primary",theme,[]),
        SlideSpec(5,"impact_close","Expected Business Impact","90-Day Roadmap","dark_close",
                  "none","","","","","primary",theme,[]),
    ]

    return DeckPlan(
        company_name=company_name, industry="general",
        main_message=f"{company_name}: Data Analysis Complete — Review Key Findings",
        theme=theme, accent_color="22D3EE",
        total_slides=len(slides), slides=slides,
        design_rationale="Fallback plan — AI design failed",
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def design_deck(
    stat_dict:    dict,
    analysis:     dict,
    company_name: str,
    industry:     str   = "general",
    audience:     str   = "executive",
    call_ai_fn          = None,
) -> DeckPlan:
    """
    2-call strategy — zero JSON truncation.

    Call 1 → structure (theme + slide outline, ~500 tokens response)
    Call 2 → details in batches of 3 slides (~400 tokens each)

    Both calls are small enough that Claude never truncates.
    """
    if call_ai_fn is None:
        print("[ai_designer] No AI function — using fallback")
        return _fallback_plan(company_name, stat_dict)

    # ── CALL 1: Structure ──────────────────────────────────────────────────────
    print(f"[ai_designer] Call 1/N — structure for {company_name}...")
    try:
        prompt1   = _build_structure_prompt(stat_dict, analysis, company_name, industry, audience)
        raw1      = call_ai_fn(prompt1)
        structure = _parse_json_safe(raw1)
        outlines  = structure.get("slides", [])
        print(f"[ai_designer] Structure: {len(outlines)} slides, theme={structure.get('theme','?')}")
    except Exception as e:
        print(f"[ai_designer] Call 1 failed: {e} — fallback")
        return _fallback_plan(company_name, stat_dict)

    if not outlines:
        return _fallback_plan(company_name, stat_dict)

    # ── CALL 2: Fill details in batches of 3 ──────────────────────────────────
    BATCH = 3
    details_map: dict = {}   # slide_num → detail dict

    for i in range(0, len(outlines), BATCH):
        batch = outlines[i : i + BATCH]
        nums  = [s.get("slide_num", i + j + 1) for j, s in enumerate(batch)]
        print(f"[ai_designer] Detail call — slides {nums}...")
        try:
            prompt2    = _build_detail_prompt(batch, stat_dict, analysis, company_name)
            raw2       = call_ai_fn(prompt2)
            detail_data = _parse_json_safe(raw2)
            for sd in detail_data.get("slides", []):
                n = sd.get("slide_num")
                if n is not None:
                    details_map[n] = sd
        except Exception as e:
            print(f"[ai_designer] Detail call slides {nums} failed: {e} — using empty details")

    # ── Merge + validate chart columns ────────────────────────────────────────
    col_stats = stat_dict.get("column_stats", [])
    valid_cols = {c["name"] for c in col_stats}
    date_cols  = {c["name"] for c in col_stats if c.get("dtype") == "datetime"}
    num_cols   = {c["name"] for c in col_stats if c.get("dtype") == "numeric"}
    cat_cols   = {c["name"] for c in col_stats if c.get("dtype") == "categorical"}

    slides = []
    for outline in outlines:
        num    = outline.get("slide_num", len(slides) + 1)
        detail = details_map.get(num, {})

        ct = outline.get("chart_type", "none")
        xc = detail.get("x_column", "")
        yc = detail.get("y_column", "")

        # Validate and auto-correct chart + column pairs
        ct, xc, yc = _validate_chart_columns(ct, xc, yc, date_cols, num_cols, cat_cols, valid_cols)

        layout = outline.get("layout", "split_chart_right")
        if layout not in VALID_LAYOUTS:
            layout = "split_chart_right"

        slides.append(SlideSpec(
            slide_num  = num,
            slide_type = outline.get("slide_type", "custom"),
            title      = outline.get("title", ""),
            subtitle   = detail.get("subtitle", ""),
            layout     = layout,
            chart_type = ct,
            x_column   = xc,
            y_column   = yc,
            group_by   = detail.get("group_by", ""),
            bullets    = detail.get("bullets", [])[:5],
            insight    = detail.get("insight", ""),
            theme_hint = detail.get("theme_hint", "primary"),
            kpis       = detail.get("kpis", [])[:6],
        ))

    if not slides:
        return _fallback_plan(company_name, stat_dict)

    # ── Generate visual design spec ──
    try:
        design = generate_design_spec(
            stat_dict=stat_dict,
            industry=industry,
            theme=structure.get("theme", "navy_consulting"),
            slide_count=len(slides),
        )
    except Exception as e:
        print("[ai_designer] design_agent failed:", e)
        design = None
    
    plan = DeckPlan(
        company_name     = structure.get("company_name", company_name),
        industry         = structure.get("industry", industry),
        main_message     = structure.get("main_message", ""),
        theme            = structure.get("theme", "navy_consulting"),
        accent_color     = structure.get("accent_color", "22D3EE"),
        total_slides     = len(slides),
        slides           = slides,
        design_rationale = structure.get("design_rationale", ""),
        design_spec      = design
    )
    print(f"[ai_designer] Plan done — {plan.total_slides} slides, theme={plan.theme}")
    return plan


def plan_to_dict(plan: DeckPlan) -> dict:
    """Serialize plan to dict for passing to slide_builder_v4.js"""
    theme = THEMES.get(plan.theme, THEMES["navy_consulting"])
    return {
        "company_name":    plan.company_name,
        "industry":        plan.industry,
        "main_message":    plan.main_message,
        "theme_name":      plan.theme,
        "theme":           theme,
        "accent_color":    plan.accent_color,
        "total_slides":    plan.total_slides,
        "design_rationale":plan.design_rationale,
        "slides": [
            {
                "slide_num":  s.slide_num,
                "slide_type": s.slide_type,
                "title":      s.title,
                "subtitle":   s.subtitle,
                "layout":     s.layout,
                "chart_type": s.chart_type,
                "x_column":   s.x_column,
                "y_column":   s.y_column,
                "group_by":   s.group_by,
                "bullets":    s.bullets,
                "insight":    s.insight,
                "theme_hint": s.theme_hint,
                "kpis":       s.kpis,
            }
            for s in plan.slides
        ],
        "design_spec": plan.design_spec,
    }