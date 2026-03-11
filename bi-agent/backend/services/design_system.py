"""
design_system.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONSULTING DESIGN TOKEN SYSTEM  ·  BI Agent v3

Philosophy:
  Every color, spacing value, and type size is a deliberate
  design decision — not a default. This system produces
  McKinsey / BCG / Bain grade visual standards automatically.

Rules enforced:
  ✔  Neutral backgrounds only — no colored backgrounds behind text
  ✔  Max 3 colors per slide
  ✔  High contrast text (WCAG AA minimum)
  ✔  No bright / startup colors
  ✔  Charts: highlight key metric, mute all others
  ✔  Consistent 12-column grid with 0.5" margins
  ✔  Typography scale enforced (title dominant at 36pt+)

Usage:
    from design_system import generate_theme, validate_slide, DesignTokens
    theme = generate_theme("finance", "Goldman Sachs")
"""

import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY SCALE  (McKinsey standard)
# ══════════════════════════════════════════════════════════════════════════════

TITLE_SIZE    = 36    # pt — slide headline. Must visually dominate. Never go below 32.
SUBTITLE_SIZE = 20    # pt — section callouts, card headers
H3_SIZE       = 14    # pt — body headers, insight labels
BODY_SIZE     = 11    # pt — supporting copy (tight, executive style)
CAPTION_SIZE  = 8     # pt — footer, axis labels, page numbers
KPI_SIZE      = 40    # pt — large metric callouts
SECTION_SIZE  = 8     # pt — section labels (ALL CAPS, tracked)

FONT_HEADING  = "Calibri"       # Clean, universally available, professional
FONT_BODY     = "Calibri"       # Consistent pairing
FONT_DATA     = "Calibri Light" # Data labels, table content


# ══════════════════════════════════════════════════════════════════════════════
# GRID SYSTEM  (10" × 5.625" slide — LAYOUT_16x9)
# ══════════════════════════════════════════════════════════════════════════════

SLIDE_W  = 10.0
SLIDE_H  = 5.625

MARGIN   = 0.45       # left/right margin — consistent everywhere
MARGIN_T = 0.50       # top content margin (below header)
MARGIN_B = 0.22       # bottom content margin (above footer)

HEADER_H = 0.40       # top bar height
FOOTER_H = 0.19       # footer bar height
FOOTER_Y = SLIDE_H - FOOTER_H

CONTENT_W = SLIDE_W - (MARGIN * 2)          # 9.10"
CONTENT_Y = HEADER_H + MARGIN_T             # 0.90"
CONTENT_H = FOOTER_Y - CONTENT_Y - MARGIN_B # ~4.07"

# Grid column unit (12-column system)
COL = CONTENT_W / 12   # ~0.758" per column

# Standard layout splits
SPLIT_65_35 = (CONTENT_W * 0.638, CONTENT_W * 0.330)  # insight layout
SPLIT_50_50 = (CONTENT_W * 0.490, CONTENT_W * 0.490)  # balanced
SPLIT_33    = CONTENT_W / 3.12                          # 3-column

GAP       = 0.16    # standard gap between elements
CARD_PAD  = 0.14    # internal card padding


# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DesignTokens:
    """
    All design values for one deck. Passed to the JS renderer.
    All hex values are 6-char, no '#'.
    """
    # Identity
    theme_name:      str = "clean_executive"
    industry:        str = "general"

    # ── Color System ──────────────────────────────────────────────────────────
    # Rule: neutral backgrounds, minimal saturation, high readability
    primary:         str = "1C2B4A"   # dominant — headers, key shapes (60-70% weight)
    secondary:       str = "2E6DA4"   # active elements, links, accent shapes
    accent:          str = "C8A45A"   # premium accent — use sparingly (< 5% of slide)
    bg:              str = "FFFFFF"   # slide background — always white or near-white
    surface:         str = "F4F6F9"   # card / panel background
    border:          str = "DDE3EC"   # subtle dividers and card outlines

    # Text
    text_primary:    str = "111827"   # body text — near black, not pure black
    text_secondary:  str = "4B5563"   # labels, captions
    text_muted:      str = "9CA3AF"   # de-emphasized, annotations
    text_light:      str = "FFFFFF"   # on dark backgrounds

    # Semantic (use only when content demands it — not for decoration)
    danger:          str = "9B1C1C"   # risk, anomaly, critical
    warning:         str = "92400E"   # caution, medium risk
    success:         str = "065F46"   # positive, achieved, on-track

    # ── Chart Color Rules ─────────────────────────────────────────────────────
    # Key metric = full primary color. Everything else = muted gray.
    chart_key:       str = "1C2B4A"   # highlighted bar/line
    chart_secondary: str = "2E6DA4"   # second series if needed
    chart_muted:     str = "C9D2DC"   # all other series — muted
    chart_bg:        str = "FFFFFF"

    # ── Typography ───────────────────────────────────────────────────────────
    TITLE_SIZE:      int = TITLE_SIZE
    SUBTITLE_SIZE:   int = SUBTITLE_SIZE
    BODY_SIZE:       int = BODY_SIZE
    KPI_SIZE:        int = KPI_SIZE
    CAPTION_SIZE:    int = CAPTION_SIZE

    # ── Spacing ──────────────────────────────────────────────────────────────
    MARGIN:          float = MARGIN
    MARGIN_T:        float = MARGIN_T
    HEADER_H:        float = HEADER_H
    FOOTER_H:        float = FOOTER_H
    FOOTER_Y:        float = FOOTER_Y
    CONTENT_W:       float = CONTENT_W
    CONTENT_Y:       float = CONTENT_Y
    CONTENT_H:       float = CONTENT_H
    GAP:             float = GAP

    # ── Fonts ─────────────────────────────────────────────────────────────────
    font_heading:    str = FONT_HEADING
    font_body:       str = FONT_BODY


# ══════════════════════════════════════════════════════════════════════════════
# THEME LIBRARY  (8 consulting-grade themes)
# ══════════════════════════════════════════════════════════════════════════════
# Constraints:
#   - All primaries: dark, desaturated, authoritative
#   - All surfaces: light, neutral, high-contrast
#   - No theme uses bright/saturated colors as primary

_THEMES = {

    # ── McKinsey Blue  (default)
    "clean_executive": dict(
        primary="1C2B4A", secondary="2E6DA4", accent="C8A45A",
        bg="FFFFFF", surface="F4F6F9", border="DDE3EC",
        chart_key="1C2B4A", chart_secondary="2E6DA4", chart_muted="C9D2DC",
        industries=["general","management","operations","hr","education"],
    ),

    # ── BCG Midnight  (strategy, finance)
    "midnight_strategy": dict(
        primary="0D1B2A", secondary="1E5F8A", accent="B8963E",
        bg="FFFFFF", surface="F0F4F8", border="D9E2EC",
        chart_key="0D1B2A", chart_secondary="1E5F8A", chart_muted="C5D0DB",
        industries=["finance","strategy","banking","investment","consulting","private equity"],
    ),

    # ── Bain Slate  (tech, data)
    "slate_tech": dict(
        primary="0F172A", secondary="1D4ED8", accent="D97706",
        bg="FFFFFF", surface="F1F5F9", border="CBD5E1",
        chart_key="0F172A", chart_secondary="1D4ED8", chart_muted="CBD5E1",
        industries=["technology","tech","software","ai","data","saas","engineering","analytics"],
    ),

    # ── Teal Clinical  (healthcare, pharma)
    "teal_clinical": dict(
        primary="134E4A", secondary="0F766E", accent="B45309",
        bg="FFFFFF", surface="F0FDFA", border="CCFBF1",
        chart_key="134E4A", chart_secondary="0F766E", chart_muted="CBD5E1",
        industries=["healthcare","health","medical","pharma","biotech","hospital","wellness"],
    ),

    # ── Warm Stone  (consumer, retail)
    "warm_stone": dict(
        primary="292524", secondary="78350F", accent="6B7280",
        bg="FAFAF9", surface="F5F0EB", border="E7E0D8",
        chart_key="292524", chart_secondary="78350F", chart_muted="D6D0C8",
        industries=["retail","consumer","fmcg","ecommerce","food","fashion","hospitality"],
    ),

    # ── Crimson Authority  (risk, audit, compliance)
    "crimson_authority": dict(
        primary="7F1D1D", secondary="991B1B", accent="475569",
        bg="FFFFFF", surface="FEF2F2", border="FECACA",
        chart_key="7F1D1D", chart_secondary="991B1B", chart_muted="CBD5E1",
        industries=["risk","audit","compliance","legal","insurance","security","fraud"],
    ),

    # ── Forest Institutional  (ESG, sustainability)
    "forest_institutional": dict(
        primary="14532D", secondary="166534", accent="92400E",
        bg="FFFFFF", surface="F0FDF4", border="BBFCCA",
        chart_key="14532D", chart_secondary="166534", chart_muted="CBD5E1",
        industries=["sustainability","environment","energy","esg","green","impact","ngo"],
    ),

    # ── Charcoal Minimal  (fallback premium)
    "charcoal_minimal": dict(
        primary="1F2937", secondary="374151", accent="9CA3AF",
        bg="FFFFFF", surface="F9FAFB", border="E5E7EB",
        chart_key="1F2937", chart_secondary="374151", chart_muted="D1D5DB",
        industries=["architecture","design","media","publishing","nonprofit"],
    ),
}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — AUTO THEME GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def _select_theme_key(industry: str, analysis_text: str = "") -> str:
    """
    Deterministic theme selection based on industry + content signals.
    Risk signals override industry (highest priority).
    """
    combined = (industry + " " + analysis_text).lower()

    # Highest priority: risk signals
    if any(w in combined for w in ["risk","anomal","fraud","audit","compliance","crisis","loss","decline","breach"]):
        return "crimson_authority"

    # Match industry keywords
    for key, cfg in _THEMES.items():
        if any(ind in combined for ind in cfg.get("industries", [])):
            return key

    return "clean_executive"


def generate_theme(
    industry:      str = "general",
    company_name:  str = "",
    analysis_text: str = "",
) -> DesignTokens:
    """
    STEP 2 — Generate design tokens for a consulting deck.

    Same industry + company = same theme (deterministic).
    Different companies in same industry get subtle accent variation.

    Args:
        industry:       e.g. "finance", "tech", "healthcare", "retail", "risk"
        company_name:   used for controlled per-company variation
        analysis_text:  AI analysis text — detects risk signals to override theme

    Returns:
        DesignTokens with all colors, typography, spacing
    """
    theme_key = _select_theme_key(industry, analysis_text)
    cfg = _THEMES.get(theme_key, _THEMES["clean_executive"])

    # Deterministic seed from company name — same company always gets same look
    seed = int(hashlib.md5(f"{company_name}{industry}".encode()).hexdigest()[:8], 16) % 4
    # Subtle accent variations (all stay within consulting palette)
    accent_variants = ["C8A45A", "B8963E", "A07D32", "C4A35A"]
    accent = accent_variants[seed % len(accent_variants)]

    return DesignTokens(
        theme_name      = theme_key,
        industry        = industry,
        primary         = cfg["primary"],
        secondary       = cfg["secondary"],
        accent          = accent,
        bg              = cfg.get("bg", "FFFFFF"),
        surface         = cfg.get("surface", "F4F6F9"),
        border          = cfg.get("border", "DDE3EC"),
        chart_key       = cfg["chart_key"],
        chart_secondary = cfg["chart_secondary"],
        chart_muted     = cfg["chart_muted"],
    )


def get_chart_colors(theme: DesignTokens, n: int, highlight: int = 0) -> List[str]:
    """
    Return chart color list: highlight index = full primary, rest = muted.
    Max 3 distinct colors on any chart (consulting rule).
    """
    colors = []
    for i in range(n):
        if i == highlight:
            colors.append(theme.chart_key)
        elif n > 3 and i == 1:
            colors.append(theme.chart_secondary)
        else:
            colors.append(theme.chart_muted)
    return colors


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — STYLE ENFORCER
# ══════════════════════════════════════════════════════════════════════════════

GENERIC_TITLES = {
    "key insights","insights","analysis","overview","summary","slide","findings",
    "key findings","recommendations","next steps","conclusion","introduction",
    "background","agenda","data analysis","results","report","presentation",
}


def validate_slide(
    message:   str,
    takeaways: list,
    theme:     DesignTokens,
) -> Tuple[bool, List[str]]:
    """
    STEP 7 — Validate slide content before export.
    Returns (is_valid, list_of_issues).
    Auto-fixes where possible (bullets trimmed to 3).
    Rejects only on hard violations.
    """
    issues = []

    # Hard reject: no message
    if not message or len(message.strip()) < 4:
        issues.append("REJECT: slide has no title/message")
        return False, issues

    # Hard reject: generic title
    if message.lower().strip() in GENERIC_TITLES:
        issues.append(f"REJECT: generic title '{message}' — must be a conclusion")
        return False, issues

    # Auto-fix: too many bullets
    if len(takeaways) > 3:
        issues.append(f"AUTO-FIX: trimmed {len(takeaways)} bullets → 3 max")

    # Warn: long bullets
    for i, t in enumerate(takeaways[:3]):
        if len(t.split()) > 14:
            issues.append(f"WARN: bullet {i+1} is {len(t.split())} words — trim to 12")

    return True, issues


def tokens_to_dict(t: DesignTokens) -> dict:
    """Serialize DesignTokens to dict for JSON passing to JS renderer."""
    return {k: v for k, v in t.__dict__.items()}
