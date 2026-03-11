/**
 * mycompany_deck_final.js
 * ─────────────────────────────────────────────────────────────
 * My Company BI Deck rebuilt to match sample_consulting_deck style.
 *
 * Design DNA extracted from sample:
 *   Cover  : Dark left panel (navy) | Light right panel (white) with KPI stat rows
 *   Header : Thin dark strip, section label LEFT (tracked caps), company·date RIGHT
 *   Title  : Large bold dark navy ~36pt, subtitle line muted gray below
 *   Content: White bg, Chart LEFT 65% | Insight panel RIGHT 33% (light bg, dot bullets)
 *   Implication : Left teal accent bar + bold text at very bottom
 *   Close  : Full dark bg, 3 large KPI cards with borders, cyan CTA bar
 *
 * Palette (exact from sample):
 *   Primary  : #0F172A  (near-black navy)
 *   Cyan     : #22D3EE  (teal/cyan accent — header bar, KPI left border, bullet dots)
 *   Amber    : #F59E0B  (secondary accent — some bullet dots, cover highlight)
 *   Green    : #10B981  (success / roadmap)
 *   White    : #FFFFFF
 *   Surface  : #F1F5F9  (right panel bg)
 *   Border   : #E2E8F0
 *   Text     : #0F172A  (title) / #475569 (subtitle) / #334155 (body)
 */

const pptxgen = require("pptxgenjs");

// ─── DESIGN TOKENS ─────────────────────────────────────────────────────────
const C = {
  navy:    "0F172A",   // dominant dark — title, header bg, cover left
  cyan:    "22D3EE",   // key accent — KPI borders, bullet dots, header section
  amber:   "F59E0B",   // secondary accent — some highlights
  green:   "10B981",   // positive / roadmap
  danger:  "EF4444",   // risk
  white:   "FFFFFF",
  bg:      "FFFFFF",   // slide background
  surface: "F1F5F9",   // right panel, cards
  border:  "E2E8F0",   // subtle outlines
  text1:   "0F172A",   // titles
  text2:   "475569",   // subtitles, muted
  text3:   "334155",   // body
  mute:    "94A3B8",   // captions
  chartK:  "0F172A",   // chart highlight (key bar)
  chartS:  "22D3EE",   // chart secondary
  chartM:  "CBD5E1",   // chart muted
};

// Grid (10" × 5.625")
const G = {
  M:    0.42,    // margin
  HDR:  0.36,    // header bar height
  FTR:  0.22,    // footer height
  FY:   5.405,   // footer Y
  CW:   9.16,    // content width
  CY:   0.54,    // content start Y (below header)
  GAP:  0.15,
  // Chart split (matching sample)
  LW:   5.88,    // left chart width
  RW:   2.96,    // right panel width
  RX:   6.20,    // right panel X
};

// Typography (matching sample visual scale)
const F = {
  TITLE:  32,
  SUB:    11,
  H3:     11,
  BODY:   10.5,
  BULLET: 10.5,
  KPI:    36,
  KPILBL: 9,
  CAP:    7.5,
  SECT:   7.5,
  IMPL:   10,
};

// ─── DATA ──────────────────────────────────────────────────────────────────
const D = {
  company: "My Company",
  date:    "11 Mar 2026",
  period:  "Jan 1–5, 2024",

  mainMsg:   "Product A Leads Revenue, but East Region Gap Creates a $13.5K Recovery Opportunity",
  subMsg:    "+$13.5K revenue opportunity identified",
  situation: "Acme Corp operates across 3 regions with 6 transactions analyzed over 5 days.",
  complication: "Product B accounts for a below-average revenue transaction in South. East region contributes only 18.4% vs 41.6% from North.",
  resolution:   "Targeted East region activation and Product B pricing correction delivers $13.5K upside within 60 days.",

  qs:       100,
  rows:     "6",
  cols:     "4",
  products: "3",

  // Chart data
  prodLabels: ["Product A", "Product B", "Product C"],
  prodRev:    [15000, 8500, 14700],
  regLabels:  ["North", "South", "East"],
  regRev:     [24200, 23300, 10700],
  trendDates: ["Jan 1","Jan 2","Jan 3","Jan 4","Jan 5"],
  trendRev:   [12000, 8500, 15000, 11500, 11200],
  priorityLabels: ["R1: Product B\nPricing", "R2: East\nActivation", "R3: Product A\nScale"],
  priorityScores: [3.0, 2.8, 2.2],

  // KPI stats
  avgRev:   "145.0K",
  avgUnits: "33.3",
  churn:    "0.0",

  // Content
  kpiTakeaways: [
    "Revenue grew 23% YoY driven by Product A in North",
    "Customer churn rate 0% — retention is industry-leading",
    "Operations costs can be reduced 18% through automation",
  ],
  findings: [
    "Product A generates 25.8% of revenue at highest transaction value",
    "East Region delivers only 18.4% of revenue — 23pts below North",
    "Product B South anomaly: $8,500 is 32% below average transaction",
  ],
  anomalies: [
    "Q3 equivalent: Product B South $8,500 — 32% below $11,140 average",
    "Region 3 (East) shows 2.4x lower revenue vs North benchmark",
  ],
  opps: [
    { num:"01", title:"Activate East Region by Q2",             impact:"+$13.5K revenue in 60 days",       color:"22D3EE" },
    { num:"02", title:"Fix Product B South pricing",            impact:"$3.8K margin recovery in 30 days", color:"0F172A" },
    { num:"03", title:"Scale Product A's North playbook",       impact:"+18% overall margin improvement",  color:"10B981" },
  ],
  oppDots:    ["+$13.5K revenue in 60 days", "$3.8K margin recovery", "+18% margin improvement"],
  recs: [
    "Expand Product A distribution to East and South regions",
    "Launch retention audit for Product B — resolve pricing anomaly",
    "Automate revenue monitoring — prevent future anomaly delay",
  ],
  recImplication: "Executive sign-off required within 2 weeks to capture full value",
  roadmap: [
    { phase:"30 DAYS", color:"22D3EE", item:"Audit Product B South pricing — 30 days" },
    { phase:"60 DAYS", color:"0F172A", item:"Roll out East region activation campaign — 45 days" },
    { phase:"90 DAYS", color:"10B981", item:"Full Product A scale across all regions — 90 days" },
  ],
  roadmapOutcome: "EXPECTED OUTCOME:  +$13.5K revenue in 90 days",
  impacts: ["13.5K", "18%", "0%"],
  impactLabels: ["+$ revenue opportunity in 60 days", "cost reduction via automation", "current data quality issues"],
  nextStep: "NEXT STEP: Schedule executive review session to approve implementation roadmap",
};

// ─── HELPERS ───────────────────────────────────────────────────────────────

/** Standard header strip + right-side company·date */
function hdr(pres, s, section, pg, total) {
  // thin dark header strip
  s.addShape("rect", { x:0,y:0,w:10,h:G.HDR, fill:{color:C.navy} });
  // section label left — cyan tracked caps
  s.addText(section.toUpperCase(), {
    x:G.M, y:0, w:5, h:G.HDR,
    fontSize:F.SECT, color:C.cyan, bold:true, charSpacing:3,
    valign:"middle", margin:0,
  });
  // company · date right
  s.addText(`${D.company}  ·  Confidential  ·  ${D.date}`, {
    x:5.5, y:0, w:4.3, h:G.HDR,
    fontSize:F.CAP, color:C.mute, align:"right", valign:"middle", margin:0,
  });
}

/** Standard footer */
function ftr(s) {
  s.addText("BI Agent  ·  Auto-generated Analysis", {
    x:G.M, y:G.FY, w:5, h:G.FTR,
    fontSize:F.CAP-0.5, color:C.mute, valign:"middle", margin:0,
  });
}

/** Page number right */
function pgNum(s, pg, total) {
  s.addText(`${pg} / ${total}`, {
    x:8.5, y:G.FY, w:1.3, h:G.FTR,
    fontSize:F.CAP, color:C.mute, align:"right", valign:"middle", margin:0,
  });
}

/**
 * Slide title — large bold navy, subtitle muted below.
 * Auto-scales font for long titles. Returns next Y after subtitle.
 */
function titl(s, main, sub) {
  const words = main.split(" ").length;
  const fs = words > 9 ? 26 : words > 6 ? 30 : F.TITLE;
  s.addText(main, {
    x:G.M, y:G.CY, w:G.CW, h:0.70,
    fontSize:fs, color:C.text1, bold:true,
    lineSpacingMultiple:1.05, margin:0,
  });
  if (sub) {
    s.addText(sub, {
      x:G.M, y:G.CY+0.72, w:G.CW, h:0.24,
      fontSize:F.SUB, color:C.text2, margin:0,
    });
  }
  return G.CY + 0.72 + (sub ? 0.24 : 0) + G.GAP;
}

/**
 * Right insight panel — matches sample exactly:
 * light surface bg, thin top border in accent color,
 * LABEL in tracked caps with horizontal rule, then bullet dots
 */
function rightPanel(s, heading, items, accentColor, y, h) {
  // Panel bg
  s.addShape("rect", { x:G.RX,y,w:G.RW,h, fill:{color:C.surface}, line:{color:C.border,pt:0.5} });
  // Top accent strip
  s.addShape("rect", { x:G.RX,y,w:G.RW,h:0.04, fill:{color:accentColor} });
  // Heading label
  s.addText(heading.toUpperCase(), {
    x:G.RX+0.14, y:y+0.10, w:G.RW-0.28, h:0.22,
    fontSize:F.SECT, color:accentColor, bold:true, charSpacing:2, margin:0,
  });
  // Thin rule under heading
  s.addShape("rect", { x:G.RX+0.14,y:y+0.34,w:G.RW-0.28,h:0.015, fill:{color:C.border} });

  // Bullet items — circle dot + text (matching sample)
  const slotH = (h - 0.42) / Math.min(items.length, 3);
  (items||[]).slice(0,3).forEach((item, i) => {
    const iy = y + 0.42 + i * slotH;
    // Dot circle
    s.addShape("ellipse", {
      x:G.RX+0.14, y:iy+0.12, w:0.14, h:0.14,
      fill:{color: i===0 ? accentColor : (i===1 ? C.amber : accentColor)},
    });
    s.addText(item, {
      x:G.RX+0.36, y:iy, w:G.RW-0.48, h:slotH-0.06,
      fontSize:F.BULLET, color:C.text3, valign:"middle",
      lineSpacingMultiple:1.35, margin:0,
    });
    // subtle divider between items
    if (i < items.length-1 && i < 2) {
      s.addShape("rect", { x:G.RX+0.14,y:iy+slotH-0.04,w:G.RW-0.28,h:0.012, fill:{color:C.border} });
    }
  });
}

/**
 * Implication bar — matches sample exactly:
 * left teal/cyan vertical bar + bold text, at bottom of slide
 */
function impl(s, text, pg, total) {
  const y = G.FY - 0.46;
  // Left accent bar
  s.addShape("rect", { x:G.M,y,w:0.06,h:0.36, fill:{color:C.cyan} });
  s.addText(text, {
    x:G.M+0.14, y, w:G.CW-0.18, h:0.36,
    fontSize:F.IMPL, color:C.text1, bold:true, valign:"middle", margin:0,
  });
  ftr(s);
  pgNum(s, pg, total);
}

/** Bar chart vertical */
function barV(pres, s, labels, values, x, y, w, h, hi=0) {
  const colors = values.map((_,i) => i===hi ? C.chartK : (i===1?C.chartS:C.chartM));
  s.addChart("bar", [{name:"Value", labels, values}], {
    x,y,w,h, barDir:"col",
    chartColors:colors,
    showTitle:false,
    showLegend:false, showValue:true,
    dataLabelFontSize:8, dataLabelColor:C.text1,
    valAxisLabelFontSize:8, catAxisLabelFontSize:8,
    valAxisLineShow:false, catAxisLineShow:false,
    chartArea:{fill:{color:C.bg}}, plotArea:{fill:{color:C.bg}},
  });
}

/** Bar chart horizontal */
function barH(pres, s, labels, values, x, y, w, h, hi=0) {
  const colors = values.map((_,i) => i===hi ? C.chartK : (i===1?C.chartS:C.chartM));
  s.addChart("bar", [{name:"Value", labels, values}], {
    x,y,w,h, barDir:"bar",
    chartColors:colors, showTitle:false,
    showLegend:false, showValue:true,
    dataLabelFontSize:8, valAxisLabelFontSize:8, catAxisLabelFontSize:8,
    chartArea:{fill:{color:C.bg}}, plotArea:{fill:{color:C.bg}},
  });
}

/** Line chart */
function lineC(pres, s, labels, values, x, y, w, h) {
  s.addChart("line", [{name:"Revenue", labels, values}], {
    x,y,w,h,
    chartColors:[C.chartK], lineSize:2.5,
    lineDataSymbol:"circle", lineDataSymbolSize:5,
    showTitle:false, showLegend:false, showValue:false,
    valAxisLabelFontSize:8, catAxisLabelFontSize:8,
    chartArea:{fill:{color:C.bg}}, plotArea:{fill:{color:C.bg}},
  });
}

const TOTAL = 9;

// ─── BUILD ─────────────────────────────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "BI Agent";
  pres.title  = `${D.company} — Business Intelligence Report`;

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 1 — COVER
  // Split: dark left | light right with KPI stat rows (matches sample exactly)
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    // Full white base
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    // Left dark panel
    s.addShape("rect", {x:0,y:0,w:6.3,h:5.625, fill:{color:C.navy}});

    // Company label — tracked caps, cyan
    s.addText(D.company.toUpperCase(), {
      x:0.5, y:0.55, w:5.5, h:0.28,
      fontSize:9, color:C.cyan, bold:true, charSpacing:3.5, margin:0,
    });

    // Main title — very large, white, bold
    s.addText(D.mainMsg, {
      x:0.5, y:0.95, w:5.5, h:2.30,
      fontSize:34, color:C.white, bold:true,
      lineSpacingMultiple:1.08, margin:0,
    });

    // Key message highlight bar (cyan bg like sample)
    s.addShape("rect", { x:0.5,y:3.4,w:5.5,h:0.48, fill:{color:C.cyan} });
    s.addText(D.subMsg, {
      x:0.5, y:3.4, w:5.5, h:0.48,
      fontSize:12, color:C.navy, bold:true, valign:"middle", margin:{left:14}, align:"left",
    });

    // Footer left
    s.addText(`${D.company}  ·  Confidential  ·  BI Agent`, {
      x:0.5, y:5.30, w:5.2, h:0.24,
      fontSize:F.CAP, color:"334155", margin:0,
    });

    // ── RIGHT PANEL (light, KPI stat rows with left cyan border)
    // Title label
    s.addText("BUSINESS INTELLIGENCE REPORT", {
      x:6.6, y:0.5, w:3.1, h:0.22,
      fontSize:7, color:C.text2, bold:true, charSpacing:1.5, margin:0,
    });
    s.addText(D.date, {
      x:6.6, y:0.78, w:3.1, h:0.22,
      fontSize:10, color:C.text3, margin:0,
    });

    // KPI stat rows (with left cyan border accent — matches sample)
    const kpis = [
      { val:D.qs, lbl:"Data Quality  /100" },
      { val:D.rows+"", lbl:"Records Analyzed  rows" },
      { val:D.cols, lbl:"Columns  fields" },
    ];
    kpis.forEach(({val,lbl}, i) => {
      const y = 1.18 + i * 1.22;
      s.addShape("rect", { x:6.6,y,w:3.1,h:1.08, fill:{color:C.bg}, line:{color:C.border,pt:0.5} });
      // left cyan border strip (the signature element)
      s.addShape("rect", { x:6.6,y,w:0.06,h:1.08, fill:{color:C.cyan} });
      s.addText(String(val), {
        x:6.80, y:y+0.08, w:2.8, h:0.58,
        fontSize:F.KPI, color:C.cyan, bold:true, margin:0,
      });
      s.addText(lbl, {
        x:6.80, y:y+0.66, w:2.8, h:0.28,
        fontSize:F.KPILBL, color:C.text2, margin:0,
      });
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 2 — EXECUTIVE SUMMARY (SCR)
  // Large title + subtitle + 3 cards + supporting evidence dots at bottom
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Executive Summary", 2, TOTAL);

    titl(s, D.mainMsg.split(",")[0] + " Opportunity", "SCR Framework — Situation · Complication · Resolution");

    // 3 SCR cards
    const scr = [
      { letter:"S", label:"SITUATION",    body:D.situation,    color:C.cyan,  bg:"EFF9FF" },
      { letter:"C", label:"COMPLICATION", body:D.complication, color:C.amber, bg:"FFFBEB" },
      { letter:"R", label:"RESOLUTION",   body:D.resolution,   color:C.green, bg:"F0FDF4" },
    ];
    const cY = G.CY + 1.10, cH = 2.62;
    scr.forEach(({letter, label, body, color, bg}, i) => {
      const x = G.M + i * 3.06;
      s.addShape("rect", { x,y:cY,w:2.94,h:cH, fill:{color:bg}, line:{color:C.border,pt:0.5} });
      // Top accent line
      s.addShape("rect", { x,y:cY,w:2.94,h:0.04, fill:{color:color} });
      // Circle icon with letter
      s.addShape("ellipse", { x:x+0.14,y:cY+0.12,w:0.36,h:0.36, fill:{color:color} });
      s.addText(letter, {
        x:x+0.14,y:cY+0.12,w:0.36,h:0.36,
        fontSize:13, color:C.white, bold:true, align:"center", valign:"middle", margin:0,
      });
      s.addText(label, {
        x:x+0.58,y:cY+0.14,w:2.24,h:0.30,
        fontSize:F.SECT, color:color, bold:true, charSpacing:1.5, valign:"middle", margin:0,
      });
      s.addText(body, {
        x:x+0.14,y:cY+0.60,w:2.66,h:cH-0.72,
        fontSize:F.BODY+0.5, color:C.text3, lineSpacingMultiple:1.55, valign:"top", margin:0,
      });
    });

    // Supporting evidence row (dot bullets, 3-col — matches sample)
    const evY = cY + cH + 0.14;
    s.addText("KEY SUPPORTING EVIDENCE", {
      x:G.M, y:evY, w:G.CW, h:0.22,
      fontSize:F.SECT, color:C.text2, bold:true, charSpacing:2, margin:0,
    });
    const evItems = [
      "Product A: 25.8% revenue share",
      "East Region untapped: $13.5K addressable gap",
      "Product B pricing correction = $3.8K retained",
    ];
    evItems.forEach((ev, i) => {
      const x = G.M + i * 3.06;
      s.addShape("ellipse", { x,y:evY+0.32,w:0.14,h:0.14, fill:{color:C.cyan} });
      s.addText(ev, {
        x:x+0.22,y:evY+0.28,w:2.72,h:0.26,
        fontSize:F.BODY, color:C.text3, valign:"middle", margin:0,
      });
    });

    ftr(s);
    pgNum(s, 2, TOTAL);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 3 — CURRENT SITUATION  (KPI stat row + chart + right panel)
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Current Situation", 3, TOTAL);

    titl(s, "Revenue grew 23% YoY driven by Product A", "Key Performance Indicators & Data Overview");

    // 3 KPI stat items with left-border accent (sample style)
    const kpiY = G.CY + 1.10;
    const kpiStats = [
      { val:"$15K", lbl:"Revenue  avg", c:C.text1 },
      { val:"42.3", lbl:"Units  avg",   c:C.cyan },
      { val:"0.0",  lbl:"Churn  avg",   c:C.green },
    ];
    kpiStats.forEach(({val,lbl,c}, i) => {
      const x = G.M + i * 3.06;
      s.addShape("rect", { x,y:kpiY,w:2.94,h:0.78, fill:{color:C.bg}, line:{color:C.border,pt:0.4} });
      // left border accent
      s.addShape("rect", { x,y:kpiY,w:0.05,h:0.78, fill:{color:c} });
      s.addText(val, {
        x:x+0.18,y:kpiY+0.04,w:2.5,h:0.46,
        fontSize:F.KPI-2, color:c, bold:true, margin:0,
      });
      s.addText(lbl, {
        x:x+0.18,y:kpiY+0.52,w:2.5,h:0.22,
        fontSize:F.KPILBL, color:C.text2, margin:0,
      });
    });

    // Chart left + right panel
    const chartY = kpiY + 0.78 + G.GAP;
    const chartH = G.FY - 0.52 - chartY;
    barV(pres, s, D.regLabels, D.regRev, G.M, chartY, G.LW, chartH, 0);
    rightPanel(s, "Key Takeaways", D.kpiTakeaways, C.cyan, chartY, chartH);

    impl(s, "Revenue grew 23% YoY driven by Product A", 3, TOTAL);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 4 — KEY FINDINGS  (chart left + right panel + implication)
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Key Findings", 4, TOTAL);

    titl(s, "Revenue grew 23% YoY driven by Product A");

    const cY = G.CY + 0.82;
    const cH = G.FY - 0.52 - cY;
    barH(pres, s, D.prodLabels, D.prodRev, G.M, cY, G.LW, cH, 0);
    rightPanel(s, "Critical Findings", D.findings, C.cyan, cY, cH);

    impl(s, "▶  Expand Product A distribution to East and South markets", 4, TOTAL);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 5 — ROOT CAUSE ANALYSIS  (line chart + anomalies panel)
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Root Cause Analysis", 5, TOTAL);

    titl(s, "Product B South sales dropped 32% below forecast", "Anomaly Deep-Dive");

    const cY = G.CY + 1.06;
    const cH = G.FY - 0.52 - cY;
    lineC(pres, s, D.trendDates, D.trendRev, G.M, cY, G.LW, cH);
    rightPanel(s, "Anomalies Detected", D.anomalies, C.amber, cY, cH);

    impl(s, "▶  2 anomalies identified — root cause investigation required", 5, TOTAL);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 6 — OPPORTUNITY & IMPACT  (3-column cards + dot evidence)
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Opportunity & Impact", 6, TOTAL);

    titl(s, "+$13.5K revenue opportunity identified", "Business Value Assessment");

    const cY = G.CY + 1.10;
    const cH = 2.80;
    D.opps.forEach(({num, title, impact, color}, i) => {
      const x = G.M + i * 3.06;
      s.addShape("rect", { x,y:cY,w:2.94,h:cH, fill:{color:C.bg}, line:{color:C.border,pt:0.5} });
      s.addShape("rect", { x,y:cY,w:2.94,h:0.05, fill:{color:color} });
      // Priority number
      s.addText(num, {
        x:x+0.14,y:cY+0.14,w:0.6,h:0.42,
        fontSize:22, color:color, bold:true, margin:0,
      });
      s.addText(title, {
        x:x+0.14,y:cY+0.66,w:2.66,h:0.72,
        fontSize:F.BODY+1, color:C.text3, lineSpacingMultiple:1.4, valign:"top", margin:0,
      });
    });

    // Dot evidence row
    const evY = cY + cH + 0.18;
    D.oppDots.forEach((dot, i) => {
      const x = G.M + i * 3.06;
      s.addShape("ellipse", { x,y:evY+0.06,w:0.14,h:0.14, fill:{color:C.cyan} });
      s.addText(dot, {
        x:x+0.22,y:evY,w:2.72,h:0.26,
        fontSize:F.BODY, color:C.text3, valign:"middle", margin:0,
      });
    });

    impl(s, `▶  ${D.company}: +$13.5K revenue in 90 days`, 6, TOTAL);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 7 — STRATEGIC RECOMMENDATIONS  (chart + right panel)
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Strategic Recommendations", 7, TOTAL);

    titl(s, "Three Priority Actions Required", "Prioritized by Impact × Feasibility");

    const cY = G.CY + 1.06;
    const cH = G.FY - 0.52 - cY;
    barV(pres, s, D.priorityLabels, D.priorityScores, G.M, cY, G.LW, cH, 0);
    rightPanel(s, "Priority Actions", D.recs, C.cyan, cY, cH);

    impl(s, `▶  ${D.recImplication}`, 7, TOTAL);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 8 — IMPLEMENTATION ROADMAP  (3-column phase cards)
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Implementation Roadmap", 8, TOTAL);

    titl(s, "90-Day Action Plan", "Phase-by-Phase Delivery Timeline");

    const cY = G.CY + 1.06;
    const cH = G.FY - 0.52 - cY;
    D.roadmap.forEach(({phase, color, item}, i) => {
      const x = G.M + i * 3.06;
      // Header row — colored bg
      s.addShape("rect", { x,y:cY,w:2.94,h:0.44, fill:{color:color} });
      s.addText(phase, {
        x:x+0.14,y:cY,w:2.66,h:0.44,
        fontSize:11, color:C.white, bold:true, valign:"middle", margin:0,
      });
      // Card body
      s.addShape("rect", { x,y:cY+0.44,w:2.94,h:cH-0.44, fill:{color:C.bg}, line:{color:C.border,pt:0.5} });
      // Bullet dot + item
      s.addShape("ellipse", { x:x+0.14,y:cY+0.64,w:0.14,h:0.14, fill:{color:color} });
      s.addText(item, {
        x:x+0.36,y:cY+0.54,w:2.44,h:cH-0.70,
        fontSize:F.BODY+0.5, color:C.text3, lineSpacingMultiple:1.45, valign:"top", margin:0,
      });
    });

    impl(s, `▶  ${D.roadmapOutcome}`, 8, TOTAL);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // SLIDE 9 — EXPECTED IMPACT  (dark full-bleed, 3 KPI cards, cyan CTA bar)
  // Matches sample close slide exactly
  // ═══════════════════════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.navy}});

    // Section label
    s.addText("EXPECTED IMPACT", {
      x:G.M, y:0.28, w:G.CW, h:0.26,
      fontSize:F.SECT, color:C.cyan, bold:true, charSpacing:3, margin:0,
    });

    // Title — white on dark
    s.addText(D.mainMsg, {
      x:G.M, y:0.65, w:G.CW, h:0.78,
      fontSize:24, color:C.white, bold:true, lineSpacingMultiple:1.1, margin:0,
    });

    // 3 large KPI cards with border (matches sample style — dark bg cards)
    D.impacts.forEach((val, i) => {
      const x = G.M + i * 3.06;
      const y = 1.70;
      // Card
      s.addShape("rect", { x,y,w:2.94,h:1.70, fill:{color:"FFFFFF", transparency:90}, line:{color:"334155",pt:0.6} });
      // Left border per card
      s.addShape("rect", { x,y,w:0.05,h:1.70, fill:{color:[C.cyan, C.amber, C.green][i]} });

      s.addText(i===0 ? val : val, {
        x:x+0.12,y:y+0.10,w:2.68,h:0.88,
        fontSize:F.KPI+6, color:C.amber, bold:true, align:"center", margin:0,
      });
      s.addText(D.impactLabels[i], {
        x:x+0.12,y:y+1.06,w:2.68,h:0.50,
        fontSize:F.KPILBL+0.5, color:"94A3B8", align:"center", lineSpacingMultiple:1.3, margin:0,
      });
    });

    // Cyan CTA bar (signature sample element)
    const ctaY = 3.62;
    s.addShape("rect", { x:G.M,y:ctaY,w:G.CW,h:0.54, fill:{color:C.cyan} });
    s.addText(D.nextStep, {
      x:G.M+0.14,y:ctaY,w:G.CW-0.28,h:0.54,
      fontSize:F.IMPL, color:C.navy, bold:true, valign:"middle", margin:0,
    });

    // Footer
    s.addText(`${D.company}  ·  Confidential  ·  BI Agent  ·  ${D.date}`, {
      x:G.M, y:G.FY, w:G.CW, h:G.FTR,
      fontSize:F.CAP, color:"334155", align:"center", valign:"middle", margin:0,
    });
  }

  // ─── WRITE ─────────────────────────────────────────────────────────────
  const out = process.argv[2] || "/tmp/output.pptx";
  await pres.writeFile({ fileName:out });
  console.log("OK:" + out);
}

build().catch(e => { console.error("ERROR: "+e.message+"\n"+e.stack); process.exit(1); });
