"""
services/story_builder.py  (v2 — merged + cached)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONSULTING STORY ENGINE — 1 AI call (was 2)

Changes vs original:
  • consulting_brain.py MERGED IN → delete that file, import from here
  • Prompt caching via SHA-256 → same data = 0 AI calls (saves ~$0.08/deck)
  • max_tokens: story needs ~2000 not 8192
  • Output schema: StoryDeck unchanged (backward compatible)

Cost:
  Before: story_builder + consulting_brain = ~$0.16/deck
  After:  1 merged call, cached           = ~$0.04 first run, $0 on cache hit
"""

import re
import json
import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from pathlib import Path

# ── Disk cache (6-hour TTL) ────────────────────────────────────────────────────
_CACHE_DIR = Path("/tmp/bi_agent_story_cache")
_CACHE_TTL  = 3600 * 6


def _cache_key(stat_dict: dict, analysis: dict, company_name: str) -> str:
    payload = json.dumps({"s": stat_dict, "a": analysis, "c": company_name},
                         sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _read_cache(key: str) -> Optional[dict]:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = _CACHE_DIR / f"{key}.json"
    if not p.exists(): return None
    if time.time() - p.stat().st_mtime > _CACHE_TTL:
        p.unlink(missing_ok=True); return None
    try:    return json.loads(p.read_text())
    except: return None


def _write_cache(key: str, data: dict) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_CACHE_DIR / f"{key}.json").write_text(json.dumps(data, default=str))


# ─── Output Schema ────────────────────────────────────────────────────────────

@dataclass
class SlideStory:
    slide_type:    str
    message:       str
    evidence:      str
    takeaways:     List[str] = field(default_factory=list)
    implication:   str = ""
    chart_type:    str = ""
    x_column:      str = ""
    y_column:      str = ""
    valid:         bool = True
    reject_reason: str = ""


@dataclass
class StoryDeck:
    company_name:      str
    main_message:      str
    headline_impact:   str
    situation:         str
    complication:      str
    resolution:        str
    slides:            List[SlideStory] = field(default_factory=list)
    supporting_points: List[str]        = field(default_factory=list)
    risks:             List[str]        = field(default_factory=list)
    opportunities:     List[str]        = field(default_factory=list)
    strategic_actions: List[str]        = field(default_factory=list)
    quick_wins:        List[str]        = field(default_factory=list)
    medium_term:       List[str]        = field(default_factory=list)
    long_term:         List[str]        = field(default_factory=list)
    business_impacts:  List[str]        = field(default_factory=list)
    risk_flags:        List[str]        = field(default_factory=list)
    theme_hint:        str  = "executive_light"
    from_cache:        bool = False


# ─── Title / text quality ─────────────────────────────────────────────────────

_GENERIC = {"key insights","insights","analysis","overview","summary","data analysis",
            "results","findings","report","slide","key findings","recommendations",
            "next steps","conclusion","introduction","background","agenda"}

def generate_executive_title(text: str, fallback: str = "") -> str:
    if not text: return fallback or "Strategic Finding Requires Attention"
    t = text.strip().rstrip(".,")
    for p in ("insight:","finding:","recommendation:","action:","note:","-","•","*"):
        if t.lower().startswith(p): t = t[len(p):].strip()
    if t.lower() in _GENERIC: return fallback or "Critical Business Finding Identified"
    if len(t) > 80:
        words = t[:80].split()
        t = " ".join(words[:-1]) + " — Key Implication"
    return t.title() if len(t.split()) <= 6 else t


def _ao(text: str) -> str:
    """Make text action-oriented."""
    patterns = [
        (r"^there (is|are) ", ""), (r"^it (is|was) (noted|observed|found) that ",""),
        (r"^the data (shows?|indicates?|suggests?) (that )?",""),
        (r"^analysis (shows?|indicates?|reveals?) (that )?",""),
        (r"\bshould consider\b","must"), (r"\bmight want to\b","should"),
        (r"\bcould potentially\b","can"), (r"\bit is recommended that\b",""),
        (r"\bwe recommend\b",""),
    ]
    r = text.strip()
    for pat, rep in patterns:
        r = re.sub(pat, rep, r, flags=re.IGNORECASE).strip()
    return r[0].upper() + r[1:] if r else r


def _validate(slide: SlideStory) -> SlideStory:
    if not slide.message or len(slide.message.strip()) < 5:
        slide.valid = False; slide.reject_reason = "no message"; return slide
    if slide.message.lower().strip() in _GENERIC:
        slide.valid = False; slide.reject_reason = f"generic"; return slide
    slide.takeaways = [
        " ".join(t.split()[:12]) + ("..." if len(t.split()) > 12 else "")
        for t in slide.takeaways[:3]
    ]
    slide.valid = True; return slide


# ─── MERGED Prompt ────────────────────────────────────────────────────────────

def _build_prompt(
    stat_dict: dict, analysis: dict, report: dict,
    company_name: str, industry: str, audience: str,
) -> str:
    """
    1 prompt = story_builder + consulting_brain combined.
    Sends only aggregated statistics, never raw CSV rows.
    """
    qs    = report.get("quality_score", 0) if isinstance(report, dict) else 0
    kpis  = "\n".join(
        f"  {k['name']}: {k['formatted']} [{k['status']}]"
        for k in stat_dict.get("kpis", [])[:6]
    )
    anom  = "\n".join(
        f"  [{a['severity'].upper()}] {a['description']}"
        for a in stat_dict.get("anomalies", [])[:4]
    )
    trend = "\n".join(t["description"] for t in stat_dict.get("trends", [])[:3])
    ins   = json.dumps(analysis.get("key_insights", [])[:4], ensure_ascii=False)
    recs  = json.dumps(analysis.get("recommendations", [])[:4], ensure_ascii=False)

    return f"""You are a Senior McKinsey Partner. Apply Pyramid Principle + SCR + 30/60/90-day planning.

VERIFIED DATA (do not invent numbers outside these):
Company: {company_name} | Industry: {industry} | Audience: {audience}
Quality: {qs}/100 | Rows: {stat_dict.get('n_rows',0):,} | Cols: {stat_dict.get('n_cols',0)}

KPIs:
{kpis or '  none'}
Anomalies:
{anom or '  none'}
Trends: {trend or 'none'}
Insights: {ins}
Recommendations: {recs}
Summary: {analysis.get('summary','')[:350]}

Respond ONLY with compact JSON (no markdown):
{{
  "main_message": "single most powerful conclusion",
  "headline_impact": "quantified metric e.g. '$2.4M at risk' or '34% efficiency gain'",
  "situation": "2 sentences: current state from data",
  "complication": "2 sentences: core problem the data reveals",
  "resolution": "2 sentences: strategic direction",
  "top_insights": ["specific insight with number", "insight 2", "insight 3"],
  "root_causes": ["root cause 1", "root cause 2"],
  "opportunities": ["opportunity with quantified value", "opportunity 2"],
  "quick_wins":  ["0-30 days: action → outcome"],
  "medium_term": ["31-60 days: action"],
  "long_term":   ["61-90 days: strategic initiative"],
  "strategic_recs": ["rec 1", "rec 2", "rec 3"],
  "business_impacts": ["quantified impact e.g. +18% revenue in 90 days"],
  "risk_flags": ["risk needing immediate attention"],
  "slides": [
    {{
      "slide_type": "key_message",
      "message": "conclusion-first title with specific number",
      "evidence": "which KPI/column supports this",
      "takeaways": ["data-backed point", "point 2", "point 3"],
      "implication": "business consequence — so what",
      "chart_type": "bar_vertical",
      "x_column": "exact_column_name",
      "y_column": "exact_column_name"
    }}
  ]
}}"""


# ─── Parser ───────────────────────────────────────────────────────────────────

def _parse(raw: str, analysis: dict, company_name: str, industry: str) -> StoryDeck:
    try:
        text = raw.strip()
        data: dict = {}
        if "```" in text:
            for part in text.split("```"):
                part = part.strip()
                if part.startswith("json"): part = part[4:].strip()
                try: data = json.loads(part); break
                except: continue
        if not data:
            s, e = text.find("{"), text.rfind("}") + 1
            data = json.loads(text[s:e])
    except Exception as ex:
        print(f"[story_builder] parse error: {ex} — fallback")
        return _fallback(analysis, company_name)

    slides = []
    for sd in data.get("slides", []):
        sl = _validate(SlideStory(
            slide_type  = sd.get("slide_type", "analysis"),
            message     = generate_executive_title(sd.get("message", "")),
            evidence    = sd.get("evidence", ""),
            takeaways   = [_ao(t) for t in sd.get("takeaways", [])],
            implication = _ao(sd.get("implication", "")),
            chart_type  = sd.get("chart_type", "none"),
            x_column    = sd.get("x_column", ""),
            y_column    = sd.get("y_column", ""),
        ))
        if sl.valid: slides.append(sl)

    print(f"[story_builder] {len(slides)}/{len(data.get('slides',[]))} slides OK")

    all_text = (data.get("main_message","") + " " + " ".join(data.get("risk_flags",[]))).lower()
    theme = (
        "crimson_risk"  if any(w in all_text for w in ("risk","decline","loss","crisis","critical")) else
        "midnight_tech" if any(w in all_text for w in ("ai","tech","saas","algorithm")) else
        "navy_consulting"if any(w in all_text for w in ("revenue","sales","growth","profit")) else
        "executive_light"
    )

    return StoryDeck(
        company_name      = company_name,
        main_message      = generate_executive_title(data.get("main_message",""),
                                                      f"{company_name}: Key Strategic Opportunities"),
        headline_impact   = data.get("headline_impact", ""),
        situation         = data.get("situation", ""),
        complication      = data.get("complication", ""),
        resolution        = data.get("resolution", ""),
        slides            = slides,
        supporting_points = data.get("top_insights", [])[:4],
        risks             = data.get("risk_flags", [])[:3],
        opportunities     = data.get("opportunities", [])[:3],
        strategic_actions = data.get("strategic_recs", [])[:4],
        quick_wins        = data.get("quick_wins", [])[:3],
        medium_term       = data.get("medium_term", [])[:3],
        long_term         = data.get("long_term", [])[:3],
        business_impacts  = data.get("business_impacts", [])[:4],
        risk_flags        = data.get("risk_flags", [])[:3],
        theme_hint        = theme,
    )


def _fallback(analysis: dict, company_name: str) -> StoryDeck:
    insights = analysis.get("key_insights", [])
    recs     = analysis.get("recommendations", [])
    slides   = []
    if insights:
        sl = _validate(SlideStory(
            slide_type="key_message",
            message=generate_executive_title(insights[0]) if insights else f"{company_name}: Key Finding",
            evidence="Statistical analysis", takeaways=[_ao(i) for i in insights[:3]],
            implication=recs[0] if recs else "Review and act on findings.",
            chart_type="bar_vertical",
        ))
        if sl.valid: slides.append(sl)
    return StoryDeck(
        company_name=company_name,
        main_message=f"{company_name}: Data Analysis Reveals Strategic Priorities",
        headline_impact="Significant improvement potential identified",
        situation=analysis.get("summary","")[:300],
        complication="Current patterns indicate areas requiring strategic attention.",
        resolution="A focused 90-day action plan will address key challenges.",
        slides=[s for s in slides if s.valid],
        supporting_points=insights[:3],
        opportunities=recs[:3], strategic_actions=recs[:3],
        quick_wins=recs[:1], medium_term=recs[1:2], long_term=recs[2:3],
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def build_story(
    analysis:     dict,
    report:       dict,
    company_name: str,
    call_ai_fn:   Callable[[str], str],
    stat_dict:    dict = None,
    industry:     str  = "general",
    audience:     str  = "executive",
    use_cache:    bool = True,
) -> StoryDeck:
    """
    1 AI call — merged story + consulting narrative.

    Args:
        analysis:     key_insights, anomalies, recommendations from analyze.py
        report:       quality_score, n_rows from ETL
        company_name: string
        call_ai_fn:   call_ai() from analyze.py
        stat_dict:    stat_report dict (adds KPI/trend context, reduces AI guessing)
        industry:     industry hint
        audience:     executive / analyst / operations
        use_cache:    True = reuse result if same inputs seen in last 6h
    """
    if stat_dict is None:
        stat_dict = {}

    print(f"[story_builder] {company_name} — merged story+brain call")

    # ── Cache check ────────────────────────────────────────────────────────────
    if use_cache:
        key    = _cache_key(stat_dict, analysis, company_name)
        cached = _read_cache(key)
        if cached:
            print(f"[story_builder] ✓ cache hit ({key}) — 0 tokens used")
            deck = _parse(json.dumps(cached), analysis, company_name, industry)
            deck.from_cache = True
            return deck

    # ── Single AI call ─────────────────────────────────────────────────────────
    prompt = _build_prompt(stat_dict, analysis, report, company_name, industry, audience)
    print(f"[story_builder] calling AI (prompt={len(prompt)} chars)")

    try:
        raw = call_ai_fn(prompt)
        print(f"[story_builder] response={len(raw)} chars")

        if use_cache:
            try:
                s, e = raw.find("{"), raw.rfind("}") + 1
                _write_cache(key, json.loads(raw[s:e]))
            except Exception:
                pass

        return _parse(raw, analysis, company_name, industry)
    except Exception as ex:
        print(f"[story_builder] failed: {ex} — fallback")
        return _fallback(analysis, company_name)


# ── Drop-in replacement for consulting_brain.build_consulting_story() ──────────

def build_consulting_story(
    analysis: dict, report: dict, df_summary: dict,
    company_name: str, call_ai_fn: Callable,
    industry: str = "general", audience: str = "executive",
) -> StoryDeck:
    """
    Backward-compat shim. Delete consulting_brain.py and use this.
    consulting_brain.py → this function does the same thing in 1 call.
    """
    stat_dict = {
        "kpis": [], "anomalies": [], "trends": [],
        "n_rows": df_summary.get("n_rows", 0),
        "n_cols": len(df_summary.get("columns", [])),
    }
    return build_story(
        analysis=analysis, report=report, company_name=company_name,
        call_ai_fn=call_ai_fn, stat_dict=stat_dict,
        industry=industry, audience=audience,
    )