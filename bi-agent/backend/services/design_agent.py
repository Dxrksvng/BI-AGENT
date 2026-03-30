"""
services/design_agent.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dynamic Consulting Presentation Designer

AI เลือก layout + theme + visual style ใหม่ทุกครั้ง
ตามลักษณะของ dataset และ business context
"""
import time # เพิ่มสิ่งนี้
import random
import hashlib
from dataclasses import dataclass, field
from typing import List
import pandas as pd

@dataclass
class ColorPalette:
    name: str
    primary: str
    secondary: str
    accent: str
    background: str
    surface: str
    text: str
    text_light: str
    success: str
    warning: str
    danger: str


@dataclass
class LayoutSpec:
    name: str
    kpi_position: str    # "top" | "grid" | "left" | "right"
    chart_style: str     # "full_width" | "split" | "sidebar" | "stacked"
    insight_style: str   # "cards" | "numbered" | "callout" | "timeline"
    rec_style: str       # "columns" | "steps" | "matrix" | "bullets"
    use_dividers: bool
    use_section_icons: bool


@dataclass
class DesignSpec:
    palette: ColorPalette
    layout: LayoutSpec
    font_size_h1: int = 22
    font_size_h2: int = 14
    font_size_body: int = 10
    font_size_kpi: int = 26
    font_size_label: int = 8
    design_seed: int = 0


# ── 7 Palettes ──────────────────────────────────────────
PALETTES = [
    ColorPalette("EY Navy",       "1A1F5E","2E4DA3","00AEAB","FFFFFF","F5F6FA","1F2937","6B7280","059669","D97706","DC2626"),
    ColorPalette("McKinsey Slate","0F172A","334155","3B82F6","FFFFFF","F8FAFC","0F172A","64748B","10B981","F59E0B","EF4444"),
    ColorPalette("BCG Forest",    "064E3B","065F46","34D399","FFFFFF","F0FDF4","1F2937","6B7280","059669","D97706","DC2626"),
    ColorPalette("Deloitte Teal", "006B6B","008080","FFB300","FFFFFF","F0FAFA","1A2E2E","5C7A7A","2DD4BF","FBBF24","F87171"),
    ColorPalette("KPMG Cobalt",   "00338D","005EB8","00A3E0","FFFFFF","EFF6FF","1E3A5F","6B7280","059669","D97706","DC2626"),
    ColorPalette("Bain Crimson",  "8B0000","B91C1C","F59E0B","FFFFFF","FFF7F7","1F2937","6B7280","059669","D97706","B91C1C"),
    ColorPalette("PwC Garnet",    "D04A02","EB6000","FFB600","FFFFFF","FFF9F5","2D2D2D","6B7280","059669","D97706","DC2626"),
]

# ── 6 Layouts ────────────────────────────────────────────
LAYOUTS = [
    LayoutSpec("Executive Briefing", "top",   "full_width", "callout",  "columns", True,  False),
    LayoutSpec("Dashboard Heavy",    "grid",  "split",      "cards",    "steps",   False, True ),
    LayoutSpec("Strategy Story",     "left",  "sidebar",    "numbered", "matrix",  True,  False),
    LayoutSpec("Risk Analysis",      "top",   "stacked",    "callout",  "steps",   True,  True ),
    LayoutSpec("Growth Report",      "right", "full_width", "timeline", "columns", False, True ),
    LayoutSpec("Minimal Exec",       "top",   "full_width", "numbered", "bullets", False, False),
]


def choose_design(analysis: dict, report: dict, df: pd.DataFrame, company_name: str = "") -> DesignSpec:
    # Deterministic seed per dataset
    summary  = analysis.get("summary", "")[:100]
    insights = str(analysis.get("key_insights", []))[:100]
    rows_val = str(report.get("original_rows", 0) if isinstance(report, dict) else "")
    raw      = f"{company_name}|{summary}|{insights}|{rows_val}"
    seed     = int(hashlib.md5(raw.encode()).hexdigest(), 16) % 10000
    rng      = random.Random(seed)

    # Data characteristics
    n_cols    = report.get("n_cols", 0)         if isinstance(report, dict) else getattr(report, "n_cols", 0)
    n_rows    = report.get("original_rows", 0)  if isinstance(report, dict) else getattr(report, "original_rows", 0)
    quality   = report.get("quality_score", 80) if isinstance(report, dict) else getattr(report, "quality_score", 80)
    anomalies = len(analysis.get("anomalies", []))
    n_insights= len(analysis.get("key_insights", []))
    cols_lower = [c.lower() for c in df.columns]
    has_revenue = any(k in c for c in cols_lower for k in ["revenue","sales","income","profit"])
    has_time    = any(k in c for c in cols_lower for k in ["date","time","month","year","week"])

    # Layout rules
    if anomalies >= 2:
        layout = LAYOUTS[3]            # Risk Analysis
    elif n_cols >= 8 or n_rows >= 500:
        layout = LAYOUTS[1]            # Dashboard Heavy
    elif has_time and has_revenue:
        layout = LAYOUTS[4]            # Growth Report
    elif n_insights <= 2:
        layout = LAYOUTS[5]            # Minimal Exec
    else:
        layout = rng.choice([LAYOUTS[0], LAYOUTS[2], LAYOUTS[4]])

    # Palette rules
    if anomalies >= 2:
        palette = rng.choice([PALETTES[1], PALETTES[5]])
    elif has_revenue:
        palette = rng.choice([PALETTES[0], PALETTES[4]])
    elif quality < 70:
        palette = PALETTES[5]
    else:
        palette = PALETTES[seed % len(PALETTES)]

    sizes = [(20,13,9,24),(22,14,10,26),(24,15,10,28)][seed % 3]

    return DesignSpec(
        palette=palette, layout=layout,
        font_size_h1=sizes[0], font_size_h2=sizes[1],
        font_size_body=sizes[2], font_size_kpi=sizes[3],
        design_seed=seed,
    )
# services/design_agent.py
def get_design_spec(df: pd.DataFrame, report: dict, analysis: dict) -> DesignSpec:
    # เปลี่ยนจากเดิมที่ใช้ hashlib.md5(...) เป็น:
    # ถ้าอยากให้กดใหม่ได้ใหม่เสมอ ใช้ time.time_ns()
    # ถ้าอยากให้เปลี่ยนตามอารมณ์ AI ให้รับ seed มาจากข้างนอก
    current_seed = int(time.time() * 1000) % (2**32)
    rng = random.Random(current_seed) 
    
    # เพิ่มความหลากหลายให้ Palette
    # แทนที่จะ if/else แข็งๆ ให้ใช้การถ่วงน้ำหนัก (Weights)
    if has_revenue:
        # มีโอกาส 70% ได้ Midnight, 30% ได้สีอื่นเพื่อให้ดูแปลกใหม่
        palette = rng.choices(PALETTES, weights=[50, 10, 10, 10, 10, 10], k=1)[0]

def generate_design_spec(stat_dict, industry, theme, slide_count):

    seed = int(hashlib.md5(
        f"{industry}-{theme}-{slide_count}".encode()
    ).hexdigest(),16) % 10_000

    random.seed(seed)

    palette = random.choice(PALETTES)

    layout = LayoutSpec(
        name=random.choice([
            "consulting_modern",
            "executive_clean",
            "data_storytelling",
            "minimal_boardroom"
        ]),
        kpi_position=random.choice(["top","grid"]),
        chart_style=random.choice(["full_width","split"]),
        insight_style=random.choice(["callout","cards"]),
        rec_style=random.choice(["steps","columns"]),
        use_dividers=slide_count>10,
        use_section_icons=random.choice([True,False]),
    )

    return {
        "palette": palette.__dict__,
        "layout": layout.__dict__,
        "seed": seed
    }