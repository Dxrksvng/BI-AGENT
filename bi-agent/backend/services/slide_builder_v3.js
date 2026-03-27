/**
 * slide_builder_v3.js
 * ─────────────────────────────────────────────────────────────
 * Reads JSON payload from stdin (sent by export.py via subprocess).
 * Builds a 9-slide McKinsey-style consulting PPTX using real data.
 *
 * Usage:
 *   echo '<json>' | node slide_builder_v3.js /output/path.pptx
 *   OR
 *   node slide_builder_v3.js /output/path.pptx   (reads stdin)
 */

const pptxgen = require("pptxgenjs");

// ─── DESIGN TOKENS ──────────────────────────────────────────────────────────
const C = {
  navy:    "0F172A",
  cyan:    "22D3EE",
  amber:   "F59E0B",
  green:   "10B981",
  danger:  "EF4444",
  white:   "FFFFFF",
  bg:      "FFFFFF",
  surface: "F1F5F9",
  border:  "E2E8F0",
  text1:   "0F172A",
  text2:   "475569",
  text3:   "334155",
  mute:    "94A3B8",
  chartK:  "0F172A",
  chartS:  "22D3EE",
  chartM:  "CBD5E1",
};

const G = {
  M: 0.42, HDR: 0.36, FTR: 0.22, FY: 5.405,
  CW: 9.16, CY: 0.54, GAP: 0.15,
  LW: 5.88, RW: 2.96, RX: 6.20,
};

const F = {
  TITLE: 32, SUB: 11, H3: 11, BODY: 10.5, BULLET: 10.5,
  KPI: 36, KPILBL: 9, CAP: 7.5, SECT: 7.5, IMPL: 10,
};

// ─── READ STDIN ──────────────────────────────────────────────────────────────
async function readStdin() {
  return new Promise((resolve) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", chunk => { data += chunk; });
    process.stdin.on("end", () => resolve(data));
    // if stdin closed immediately (no pipe), resolve empty
    setTimeout(() => { if (!data) resolve("{}"); }, 3000);
  });
}

// ─── HELPERS ─────────────────────────────────────────────────────────────────
function safe(arr, fallback = []) { return Array.isArray(arr) && arr.length ? arr : fallback; }
function safeStr(s, fallback = "") { return (typeof s === "string" && s.trim()) ? s.trim() : fallback; }
function truncate(s, max = 120) { return s && s.length > max ? s.slice(0, max) + "..." : (s || ""); }

function hdr(pres, s, section, D) {
  s.addShape("rect", { x:0,y:0,w:10,h:G.HDR, fill:{color:C.navy} });
  s.addText(section.toUpperCase(), {
    x:G.M,y:0,w:5,h:G.HDR,
    fontSize:F.SECT,color:C.cyan,bold:true,charSpacing:3,valign:"middle",margin:0,
  });
  s.addText(`${D.company}  ·  Confidential  ·  ${D.date}`, {
    x:5.5,y:0,w:4.3,h:G.HDR,
    fontSize:F.CAP,color:C.mute,align:"right",valign:"middle",margin:0,
  });
}

function ftr(s) {
  s.addText("BI Agent  ·  Auto-generated Analysis", {
    x:G.M,y:G.FY,w:5,h:G.FTR,
    fontSize:F.CAP-0.5,color:C.mute,valign:"middle",margin:0,
  });
}

function pgNum(s, pg, total) {
  s.addText(`${pg} / ${total}`, {
    x:8.5,y:G.FY,w:1.3,h:G.FTR,
    fontSize:F.CAP,color:C.mute,align:"right",valign:"middle",margin:0,
  });
}

function titl(s, main, sub) {
  const words = (main||"").split(" ").length;
  const fs = words > 9 ? 24 : words > 6 ? 28 : F.TITLE;
  s.addText(truncate(main, 100), {
    x:G.M,y:G.CY,w:G.CW,h:0.70,
    fontSize:fs,color:C.text1,bold:true,lineSpacingMultiple:1.05,margin:0,
  });
  if (sub) {
    s.addText(truncate(sub, 80), {
      x:G.M,y:G.CY+0.72,w:G.CW,h:0.24,
      fontSize:F.SUB,color:C.text2,margin:0,
    });
  }
  return G.CY + 0.72 + (sub ? 0.24 : 0) + G.GAP;
}

function rightPanel(s, heading, items, accentColor, y, h) {
  s.addShape("rect", { x:G.RX,y,w:G.RW,h, fill:{color:C.surface}, line:{color:C.border,pt:0.5} });
  s.addShape("rect", { x:G.RX,y,w:G.RW,h:0.04, fill:{color:accentColor} });
  s.addText((heading||"").toUpperCase(), {
    x:G.RX+0.14,y:y+0.10,w:G.RW-0.28,h:0.22,
    fontSize:F.SECT,color:accentColor,bold:true,charSpacing:2,margin:0,
  });
  s.addShape("rect", { x:G.RX+0.14,y:y+0.34,w:G.RW-0.28,h:0.015, fill:{color:C.border} });
  const slotH = (h - 0.42) / Math.min((items||[]).length || 1, 3);
  (items||[]).slice(0,3).forEach((item, i) => {
    const iy = y + 0.42 + i * slotH;
    s.addShape("ellipse", {
      x:G.RX+0.14,y:iy+0.12,w:0.14,h:0.14,
      fill:{color: i===0 ? accentColor : (i===1 ? C.amber : accentColor)},
    });
    s.addText(truncate(item, 80), {
      x:G.RX+0.36,y:iy,w:G.RW-0.48,h:slotH-0.06,
      fontSize:F.BULLET,color:C.text3,valign:"middle",lineSpacingMultiple:1.35,margin:0,
    });
    if (i < (items||[]).length-1 && i < 2) {
      s.addShape("rect", { x:G.RX+0.14,y:iy+slotH-0.04,w:G.RW-0.28,h:0.012, fill:{color:C.border} });
    }
  });
}

function impl(s, text, pg, total) {
  const y = G.FY - 0.46;
  s.addShape("rect", { x:G.M,y,w:0.06,h:0.36, fill:{color:C.cyan} });
  s.addText(truncate(text, 120), {
    x:G.M+0.14,y,w:G.CW-0.18,h:0.36,
    fontSize:F.IMPL,color:C.text1,bold:true,valign:"middle",margin:0,
  });
  ftr(s);
  pgNum(s, pg, total);
}

function barV(pres, s, labels, values, x, y, w, h) {
  if (!labels.length) return;
  const colors = values.map((_,i) => i===0 ? C.chartK : (i===1 ? C.chartS : C.chartM));
  s.addChart("bar", [{name:"Value", labels, values}], {
    x,y,w,h, barDir:"col",
    chartColors:colors, showTitle:false, showLegend:false, showValue:true,
    dataLabelFontSize:8,dataLabelColor:C.text1,
    valAxisLabelFontSize:8,catAxisLabelFontSize:8,
    valAxisLineShow:false,catAxisLineShow:false,
    chartArea:{fill:{color:C.bg}},plotArea:{fill:{color:C.bg}},
  });
}

function barH(pres, s, labels, values, x, y, w, h) {
  if (!labels.length) return;
  const colors = values.map((_,i) => i===0 ? C.chartK : (i===1 ? C.chartS : C.chartM));
  s.addChart("bar", [{name:"Value", labels, values}], {
    x,y,w,h, barDir:"bar",
    chartColors:colors, showTitle:false, showLegend:false, showValue:true,
    dataLabelFontSize:8,valAxisLabelFontSize:8,catAxisLabelFontSize:8,
    chartArea:{fill:{color:C.bg}},plotArea:{fill:{color:C.bg}},
  });
}

function lineC(pres, s, labels, values, x, y, w, h) {
  if (!labels.length) return;
  s.addChart("line", [{name:"Value", labels, values}], {
    x,y,w,h,
    chartColors:[C.chartK],lineSize:2.5,
    lineDataSymbol:"circle",lineDataSymbolSize:5,
    showTitle:false,showLegend:false,showValue:false,
    valAxisLabelFontSize:8,catAxisLabelFontSize:8,
    chartArea:{fill:{color:C.bg}},plotArea:{fill:{color:C.bg}},
  });
}

// ─── EXTRACT DATA FROM PAYLOAD ───────────────────────────────────────────────
function extractData(payload) {
  const analysis   = payload.analysis   || {};
  const report     = payload.report     || {};
  const story      = payload.story      || {};
  const df_summary = payload.df_summary || {};
  const company    = safeStr(payload.company_name, "My Company");
  const now        = new Date().toLocaleDateString("en-GB", {day:"2-digit",month:"short",year:"numeric"});

  // Core narrative — prefer story_builder output, fallback to analysis
  const mainMsg    = safeStr(story.main_message,   safeStr(analysis.summary, "Key Business Insights").slice(0,80));
  const headline   = safeStr(story.headline_impact, "Strategic opportunities identified");
  const situation  = safeStr(story.situation,  analysis.summary ? analysis.summary.slice(0,200) : "Current business state under review.");
  const complication = safeStr(story.complication, (analysis.anomalies||[])[0] || "Key challenges identified in data.");
  const resolution = safeStr(story.resolution,  (analysis.recommendations||[])[0] || "Targeted actions recommended.");

  // Key content
  const insights   = safe(analysis.key_insights,   ["Key finding identified from data analysis"]);
  const anomalies  = safe(analysis.anomalies,       []).filter(a => !/no anomal/i.test(a));
  const recs       = safe(analysis.recommendations, ["Review findings and implement recommendations"]);
  const quickWins  = safe(story.quick_wins,  recs.slice(0,1));
  const medTerm    = safe(story.medium_term, recs.slice(1,2));
  const longTerm   = safe(story.long_term,   recs.slice(2,3));

  // Report stats
  const qs      = report.quality_score || 0;
  const origRows= report.original_rows || df_summary.n_rows || 0;
  const cleanRows=report.cleaned_rows  || df_summary.n_rows || 0;
  const nCols   = report.n_cols        || df_summary.n_cols || 0;

  // Chart data — extract from df_summary.sample
  const sample   = safe(df_summary.sample, []);
  const cols     = safe(df_summary.columns, []);
  const stats    = df_summary.statistics || {};

  // Find numeric columns for charts
  const numCols  = cols.filter(c => stats[c] && stats[c].mean !== undefined);
  const catCols  = cols.filter(c => !numCols.includes(c));

  // Build chart data from charts_config first, fallback to sample data
  const chartsConfig = safe(analysis.charts_config, []);
  let chartLabels = [], chartValues = [], chartTitle = "Key Performance Overview";
  let trendLabels = [], trendValues = [];

  if (chartsConfig.length > 0 && sample.length > 0) {
    const cfg = chartsConfig[0];
    const xCol = cfg.x_column || catCols[0] || cols[0];
    const yCol = cfg.y_column || numCols[0] || cols[1];
    chartTitle  = safeStr(cfg.title, chartTitle);
    if (xCol && yCol) {
      // Aggregate by x column
      const agg = {};
      sample.forEach(row => {
        const k = String(row[xCol] ?? "Unknown");
        const v = parseFloat(row[yCol]) || 0;
        agg[k] = (agg[k] || 0) + v;
      });
      chartLabels = Object.keys(agg).slice(0, 8);
      chartValues = chartLabels.map(k => Math.round(agg[k] * 100) / 100);
    }

    // Trend chart — use second chart config or first numeric col
    if (chartsConfig.length > 1) {
      const cfg2 = chartsConfig[1];
      const xCol2 = cfg2.x_column || cols[0];
      const yCol2 = cfg2.y_column || numCols[0];
      if (xCol2 && yCol2) {
        trendLabels = sample.slice(0,10).map(r => String(r[xCol2] ?? ""));
        trendValues = sample.slice(0,10).map(r => parseFloat(r[yCol2]) || 0);
      }
    }
  }

  // Fallback chart data from raw sample
  if (!chartLabels.length && sample.length > 0 && catCols.length && numCols.length) {
    const agg = {};
    sample.forEach(row => {
      const k = String(row[catCols[0]] ?? "Unknown");
      const v = parseFloat(row[numCols[0]]) || 0;
      agg[k] = (agg[k] || 0) + v;
    });
    chartLabels = Object.keys(agg).slice(0,8);
    chartValues = chartLabels.map(k => Math.round(agg[k]*100)/100);
  }
  if (!trendLabels.length && sample.length > 1 && numCols.length) {
    trendLabels = sample.slice(0,10).map((r,i) => String(r[cols[0]] ?? `Row ${i+1}`));
    trendValues = sample.slice(0,10).map(r => parseFloat(r[numCols[0]]) || 0);
  }

  // Roadmap from story or recs
  const roadmap = [
    { phase:"30 DAYS", color:C.cyan,  item: safeStr(quickWins[0], recs[0] || "Audit and review key findings") },
    { phase:"60 DAYS", color:C.navy,  item: safeStr(medTerm[0],   recs[1] || "Implement priority recommendations") },
    { phase:"90 DAYS", color:C.green, item: safeStr(longTerm[0],  recs[2] || "Evaluate outcomes and scale wins") },
  ];

  // Impact metrics from story
  const bizImpacts = safe(story.business_impacts, []);
  const impacts    = bizImpacts.slice(0,3);
  while (impacts.length < 3) impacts.push("Improvement opportunity identified");

  // Supporting evidence for cover/summary
  const supporting = safe(story.supporting_points, insights.slice(0,3));

  // KPI stats for slide 3
  const kpiStats = numCols.slice(0,3).map((col,i) => {
    const s = stats[col] || {};
    const avg = s.mean ? (Math.round(s.mean*10)/10) : 0;
    return { val: String(avg), lbl: col + " avg" };
  });
  while (kpiStats.length < 3) kpiStats.push({ val:"—", lbl:"metric" });

  return {
    company, date: now,
    mainMsg, headline, situation, complication, resolution,
    qs, rows: String(origRows), cols: String(nCols),
    insights, anomalies, recs, supporting,
    chartLabels, chartValues, chartTitle,
    trendLabels, trendValues,
    kpiStats, roadmap, impacts,
    recImplication: safeStr((story.strategic_actions||[])[0], recs[0] || "Executive sign-off required to proceed"),
    nextStep: "NEXT STEP: Schedule executive review to approve implementation roadmap",
  };
}

// ─── BUILD ───────────────────────────────────────────────────────────────────
async function build() {
  const raw     = await readStdin();
  let payload   = {};
  try { payload = JSON.parse(raw); } catch(e) { console.error("JSON parse error:", e.message); }

  const D     = extractData(payload);
  const pres  = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "BI Agent";
  pres.title  = `${D.company} — Business Intelligence Report`;

  const TOTAL = 9;

  // ═══ SLIDE 1 — COVER ═════════════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    s.addShape("rect", {x:0,y:0,w:6.3,h:5.625, fill:{color:C.navy}});

    s.addText(D.company.toUpperCase(), {
      x:0.5,y:0.55,w:5.5,h:0.28,
      fontSize:9,color:C.cyan,bold:true,charSpacing:3.5,margin:0,
    });
    s.addText(truncate(D.mainMsg, 100), {
      x:0.5,y:0.95,w:5.5,h:2.30,
      fontSize:30,color:C.white,bold:true,lineSpacingMultiple:1.08,margin:0,
    });
    s.addShape("rect", {x:0.5,y:3.4,w:5.5,h:0.48, fill:{color:C.cyan}});
    s.addText(truncate(D.headline, 70), {
      x:0.5,y:3.4,w:5.5,h:0.48,
      fontSize:12,color:C.navy,bold:true,valign:"middle",margin:{left:14},
    });
    s.addText(`${D.company}  ·  Confidential  ·  BI Agent`, {
      x:0.5,y:5.30,w:5.2,h:0.24,
      fontSize:F.CAP,color:"334155",margin:0,
    });

    // Right panel
    s.addText("BUSINESS INTELLIGENCE REPORT", {
      x:6.6,y:0.5,w:3.1,h:0.22,
      fontSize:7,color:C.text2,bold:true,charSpacing:1.5,margin:0,
    });
    s.addText(D.date, { x:6.6,y:0.78,w:3.1,h:0.22,fontSize:10,color:C.text3,margin:0 });

    const kpis = [
      { val:String(D.qs), lbl:"Data Quality  /100" },
      { val:D.rows,        lbl:"Records Analyzed" },
      { val:D.cols,        lbl:"Columns  fields" },
    ];
    kpis.forEach(({val,lbl}, i) => {
      const y = 1.18 + i * 1.22;
      s.addShape("rect", {x:6.6,y,w:3.1,h:1.08, fill:{color:C.bg}, line:{color:C.border,pt:0.5}});
      s.addShape("rect", {x:6.6,y,w:0.06,h:1.08, fill:{color:C.cyan}});
      s.addText(val, {x:6.80,y:y+0.08,w:2.8,h:0.58, fontSize:F.KPI,color:C.cyan,bold:true,margin:0});
      s.addText(lbl, {x:6.80,y:y+0.66,w:2.8,h:0.28, fontSize:F.KPILBL,color:C.text2,margin:0});
    });
  }

  // ═══ SLIDE 2 — EXECUTIVE SUMMARY (SCR) ═══════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Executive Summary", D);

    titl(s, truncate(D.mainMsg.split(",")[0], 70) + " — Strategic Priority", "SCR Framework — Situation · Complication · Resolution");

    const scr = [
      { letter:"S", label:"SITUATION",    body:D.situation,    color:C.cyan,  bg:"EFF9FF" },
      { letter:"C", label:"COMPLICATION", body:D.complication, color:C.amber, bg:"FFFBEB" },
      { letter:"R", label:"RESOLUTION",   body:D.resolution,   color:C.green, bg:"F0FDF4" },
    ];
    const cY = G.CY + 1.10, cH = 2.62;
    scr.forEach(({letter,label,body,color,bg}, i) => {
      const x = G.M + i * 3.06;
      s.addShape("rect", {x,y:cY,w:2.94,h:cH, fill:{color:bg}, line:{color:C.border,pt:0.5}});
      s.addShape("rect", {x,y:cY,w:2.94,h:0.04, fill:{color:color}});
      s.addShape("ellipse", {x:x+0.14,y:cY+0.12,w:0.36,h:0.36, fill:{color:color}});
      s.addText(letter, {x:x+0.14,y:cY+0.12,w:0.36,h:0.36, fontSize:13,color:C.white,bold:true,align:"center",valign:"middle",margin:0});
      s.addText(label,  {x:x+0.58,y:cY+0.14,w:2.24,h:0.30, fontSize:F.SECT,color:color,bold:true,charSpacing:1.5,valign:"middle",margin:0});
      s.addText(truncate(body,180), {x:x+0.14,y:cY+0.60,w:2.66,h:cH-0.72, fontSize:F.BODY+0.5,color:C.text3,lineSpacingMultiple:1.55,valign:"top",margin:0});
    });

    // Supporting evidence row
    const evY = cY + cH + 0.14;
    s.addText("KEY SUPPORTING EVIDENCE", {x:G.M,y:evY,w:G.CW,h:0.22, fontSize:F.SECT,color:C.text2,bold:true,charSpacing:2,margin:0});
    D.supporting.slice(0,3).forEach((ev, i) => {
      const x = G.M + i * 3.06;
      s.addShape("ellipse", {x,y:evY+0.32,w:0.14,h:0.14, fill:{color:C.cyan}});
      s.addText(truncate(ev, 70), {x:x+0.22,y:evY+0.28,w:2.72,h:0.26, fontSize:F.BODY,color:C.text3,valign:"middle",margin:0});
    });

    ftr(s); pgNum(s, 2, TOTAL);
  }

  // ═══ SLIDE 3 — CURRENT SITUATION (KPI + chart) ════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Current Situation", D);
    titl(s, truncate(D.mainMsg, 70), "Key Performance Indicators & Data Overview");

    const kpiY = G.CY + 1.10;
    D.kpiStats.slice(0,3).forEach(({val,lbl}, i) => {
      const x = G.M + i * 3.06;
      s.addShape("rect", {x,y:kpiY,w:2.94,h:0.78, fill:{color:C.bg}, line:{color:C.border,pt:0.4}});
      s.addShape("rect", {x,y:kpiY,w:0.05,h:0.78, fill:{color:[C.text1,C.cyan,C.green][i]}});
      s.addText(String(val), {x:x+0.18,y:kpiY+0.04,w:2.5,h:0.46, fontSize:F.KPI-2,color:[C.text1,C.cyan,C.green][i],bold:true,margin:0});
      s.addText(lbl, {x:x+0.18,y:kpiY+0.52,w:2.5,h:0.22, fontSize:F.KPILBL,color:C.text2,margin:0});
    });

    const chartY = kpiY + 0.78 + G.GAP;
    const chartH = G.FY - 0.52 - chartY;
    if (D.chartLabels.length) barV(pres, s, D.chartLabels, D.chartValues, G.M, chartY, G.LW, chartH);
    rightPanel(s, "Key Takeaways", D.insights.slice(0,3), C.cyan, chartY, chartH);
    impl(s, truncate(D.situation, 110), 3, TOTAL);
  }

  // ═══ SLIDE 4 — KEY FINDINGS ═══════════════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Key Findings", D);
    titl(s, truncate(D.insights[0] || "Key business findings identified", 70));

    const cY = G.CY + 0.82;
    const cH = G.FY - 0.52 - cY;
    if (D.chartLabels.length) barH(pres, s, D.chartLabels, D.chartValues, G.M, cY, G.LW, cH);
    rightPanel(s, "Critical Findings", D.insights, C.cyan, cY, cH);
    impl(s, `▶  ${truncate(D.recs[0] || "Implement priority recommendations", 100)}`, 4, TOTAL);
  }

  // ═══ SLIDE 5 — ROOT CAUSE ANALYSIS ═══════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Root Cause Analysis", D);
    const anomalyMsg = D.anomalies[0] || D.insights[1] || "Data patterns reveal underlying drivers";
    titl(s, truncate(anomalyMsg, 70), "Anomaly Deep-Dive");

    const cY = G.CY + 1.06;
    const cH = G.FY - 0.52 - cY;
    if (D.trendLabels.length) lineC(pres, s, D.trendLabels, D.trendValues, G.M, cY, G.LW, cH);
    else if (D.chartLabels.length) barV(pres, s, D.chartLabels, D.chartValues, G.M, cY, G.LW, cH);
    rightPanel(s, "Anomalies Detected", D.anomalies.length ? D.anomalies : D.insights, C.amber, cY, cH);
    impl(s, `▶  ${D.anomalies.length} anomaly/anomalies identified — root cause investigation required`, 5, TOTAL);
  }

  // ═══ SLIDE 6 — OPPORTUNITY & IMPACT ══════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Opportunity & Impact", D);
    titl(s, truncate(D.headline, 70), "Business Value Assessment");

    const cY = G.CY + 1.10, cH = 2.80;
    const opps = D.recs.slice(0,3).map((r,i) => ({
      num: String(i+1).padStart(2,"0"),
      title: truncate(r, 60),
      color: [C.cyan, C.navy, C.green][i],
    }));
    opps.forEach(({num,title,color}, i) => {
      const x = G.M + i * 3.06;
      s.addShape("rect", {x,y:cY,w:2.94,h:cH, fill:{color:C.bg}, line:{color:C.border,pt:0.5}});
      s.addShape("rect", {x,y:cY,w:2.94,h:0.05, fill:{color:color}});
      s.addText(num, {x:x+0.14,y:cY+0.14,w:0.6,h:0.42, fontSize:22,color:color,bold:true,margin:0});
      s.addText(title, {x:x+0.14,y:cY+0.66,w:2.66,h:0.72, fontSize:F.BODY+1,color:C.text3,lineSpacingMultiple:1.4,valign:"top",margin:0});
    });

    const evY = cY + cH + 0.18;
    D.recs.slice(0,3).forEach((dot, i) => {
      const x = G.M + i * 3.06;
      s.addShape("ellipse", {x,y:evY+0.06,w:0.14,h:0.14, fill:{color:C.cyan}});
      s.addText(truncate(dot, 55), {x:x+0.22,y:evY,w:2.72,h:0.26, fontSize:F.BODY,color:C.text3,valign:"middle",margin:0});
    });

    impl(s, `▶  ${D.company}: ${truncate(D.headline, 80)}`, 6, TOTAL);
  }

  // ═══ SLIDE 7 — STRATEGIC RECOMMENDATIONS ═════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Strategic Recommendations", D);
    titl(s, "Three Priority Actions Required", "Prioritized by Impact × Feasibility");

    const cY = G.CY + 1.06;
    const cH = G.FY - 0.52 - cY;
    // Priority score chart (1st=3.0, 2nd=2.5, 3rd=2.0)
    const recLabels = D.recs.slice(0,3).map((r,i) => `R${i+1}: ${r.slice(0,20)}...`);
    const recScores = [3.0, 2.5, 2.0].slice(0, D.recs.length);
    if (recLabels.length) barV(pres, s, recLabels, recScores, G.M, cY, G.LW, cH);
    rightPanel(s, "Priority Actions", D.recs, C.cyan, cY, cH);
    impl(s, `▶  ${truncate(D.recImplication, 100)}`, 7, TOTAL);
  }

  // ═══ SLIDE 8 — IMPLEMENTATION ROADMAP ════════════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.bg}});
    hdr(pres, s, "Implementation Roadmap", D);
    titl(s, "90-Day Action Plan", "Phase-by-Phase Delivery Timeline");

    const cY = G.CY + 1.06;
    const cH = G.FY - 0.52 - cY;
    D.roadmap.forEach(({phase,color,item}, i) => {
      const x = G.M + i * 3.06;
      s.addShape("rect", {x,y:cY,w:2.94,h:0.44, fill:{color:color}});
      s.addText(phase, {x:x+0.14,y:cY,w:2.66,h:0.44, fontSize:11,color:C.white,bold:true,valign:"middle",margin:0});
      s.addShape("rect", {x,y:cY+0.44,w:2.94,h:cH-0.44, fill:{color:C.bg}, line:{color:C.border,pt:0.5}});
      s.addShape("ellipse", {x:x+0.14,y:cY+0.64,w:0.14,h:0.14, fill:{color:color}});
      s.addText(truncate(item, 80), {x:x+0.36,y:cY+0.54,w:2.44,h:cH-0.70, fontSize:F.BODY+0.5,color:C.text3,lineSpacingMultiple:1.45,valign:"top",margin:0});
    });

    impl(s, `▶  EXPECTED OUTCOME: ${truncate(D.headline, 80)}`, 8, TOTAL);
  }

  // ═══ SLIDE 9 — EXPECTED IMPACT (dark close) ═══════════════════════════════
  {
    const s = pres.addSlide();
    s.addShape("rect", {x:0,y:0,w:10,h:5.625, fill:{color:C.navy}});
    s.addText("EXPECTED IMPACT", {x:G.M,y:0.28,w:G.CW,h:0.26, fontSize:F.SECT,color:C.cyan,bold:true,charSpacing:3,margin:0});
    s.addText(truncate(D.mainMsg, 90), {x:G.M,y:0.65,w:G.CW,h:0.78, fontSize:22,color:C.white,bold:true,lineSpacingMultiple:1.1,margin:0});

    // 3 impact cards
    D.impacts.slice(0,3).forEach((val, i) => {
      const x = G.M + i * 3.06;
      const y = 1.70;
      s.addShape("rect", {x,y,w:2.94,h:1.70, fill:{color:"FFFFFF",transparency:90}, line:{color:"334155",pt:0.6}});
      s.addShape("rect", {x,y,w:0.05,h:1.70, fill:{color:[C.cyan,C.amber,C.green][i]}});
      s.addText(truncate(val, 30), {x:x+0.12,y:y+0.14,w:2.68,h:0.78, fontSize:13,color:C.amber,bold:true,align:"center",lineSpacingMultiple:1.2,margin:0});
    });

    const ctaY = 3.62;
    s.addShape("rect", {x:G.M,y:ctaY,w:G.CW,h:0.54, fill:{color:C.cyan}});
    s.addText(D.nextStep, {x:G.M+0.14,y:ctaY,w:G.CW-0.28,h:0.54, fontSize:F.IMPL,color:C.navy,bold:true,valign:"middle",margin:0});
    s.addText(`${D.company}  ·  Confidential  ·  BI Agent  ·  ${D.date}`, {
      x:G.M,y:G.FY,w:G.CW,h:G.FTR,
      fontSize:F.CAP,color:"334155",align:"center",valign:"middle",margin:0,
    });
  }

  // ─── WRITE ────────────────────────────────────────────────────────────────
  const out = process.argv[2] || "/tmp/output.pptx";
  await pres.writeFile({ fileName: out });
  console.log("OK:" + out);
}

build().catch(e => {
  console.error("ERROR: " + e.message + "\n" + e.stack);
  process.exit(1);
});
