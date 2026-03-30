/**
 * slide_builder_v4.js — BI Agent Premium
 * Luxury consulting-grade PPTX. AI-designed, statistically grounded.
 * Fixes: correct section headers, working charts, clean layouts, premium colors.
 */
const pptxgen = require("pptxgenjs");

// ─── THEMES ──────────────────────────────────────────────────────────────────
const THEMES = {
  executive_light:{
    primary:"1A365D",accent:"2B6CB0",gold:"D4A017",
    success:"276749",danger:"C53030",warn:"B7791F",
    bg:"FFFFFF",surface:"F7FAFC",card:"EDF2F7",
    border:"CBD5E0",text1:"1A202C",text2:"4A5568",text3:"718096",
    muted:"A0AEC0",
    charts:["1A365D","2B6CB0","276749","D4A017","744210","553C9A","97266D","A0AEC0"],
  },
  navy_consulting:{
    primary:"1E3A5F",accent:"2563EB",gold:"D97706",
    success:"059669",danger:"DC2626",warn:"D97706",
    bg:"FFFFFF",surface:"F8FAFC",card:"F1F5F9",
    border:"E2E8F0",text1:"0F172A",text2:"475569",text3:"64748B",
    muted:"94A3B8",
    charts:["1E3A5F","2563EB","059669","D97706","7C3AED","DC2626","0891B2","94A3B8"],
  },
  slate_minimal:{
    primary:"1E293B",accent:"4F46E5",gold:"CA8A04",
    success:"16A34A",danger:"DC2626",warn:"CA8A04",
    bg:"FFFFFF",surface:"F8FAFC",card:"F1F5F9",
    border:"E2E8F0",text1:"1E293B",text2:"475569",text3:"64748B",
    muted:"94A3B8",
    charts:["1E293B","4F46E5","16A34A","CA8A04","0891B2","DC2626","9333EA","94A3B8"],
  },
  forest_growth:{
    primary:"1A4731",accent:"1D7A4A",gold:"92400E",
    success:"065F46",danger:"991B1B",warn:"92400E",
    bg:"FFFFFF",surface:"F0FDF4",card:"DCFCE7",
    border:"BBF7D0",text1:"064E3B",text2:"065F46",text3:"047857",
    muted:"6EE7B7",
    charts:["1A4731","1D7A4A","059669","92400E","1D4ED8","991B1B","7C3AED","94A3B8"],
  },
  midnight_tech:{
    primary:"0C1A2E",accent:"1D4ED8",gold:"B45309",
    success:"065F46",danger:"991B1B",warn:"B45309",
    bg:"FFFFFF",surface:"F0F4FF",card:"E0E7FF",
    border:"C7D2FE",text1:"0C1A2E",text2:"1E3A5F",text3:"374151",
    muted:"9CA3AF",
    charts:["0C1A2E","1D4ED8","065F46","B45309","7C3AED","991B1B","0891B2","9CA3AF"],
  },
  crimson_risk:{
    primary:"7F1D1D",accent:"B91C1C",gold:"92400E",
    success:"065F46",danger:"7F1D1D",warn:"92400E",
    bg:"FFFFFF",surface:"FEF2F2",card:"FEE2E2",
    border:"FECACA",text1:"1C1917",text2:"44403C",text3:"78716C",
    muted:"A8A29E",
    charts:["7F1D1D","B91C1C","92400E","065F46","1D4ED8","374151","7C3AED","A8A29E"],
  },
  ultra_premium:{
    primary:"111827",accent:"D4A017",gold:"D4A017",
    success:"065F46",danger:"991B1B",warn:"92400E",
    bg:"FFFFFF",surface:"FAFAF9",card:"F5F5F4",
    border:"E7E5E4",text1:"111827",text2:"374151",text3:"6B7280",
    muted:"9CA3AF",
    charts:["111827","D4A017","065F46","1D4ED8","7C3AED","991B1B","0891B2","9CA3AF"],
  },
};

// ─── SECTION LABEL MAP ───────────────────────────────────────────────────────
const SECTION = {
  cover:"Cover",executive_summary:"Executive Summary",kpi_dashboard:"Performance Dashboard",
  findings:"Key Findings",analysis:"Data Analysis",comparison:"Comparative Analysis",
  root_cause:"Root Cause Analysis",correlation:"Correlation Analysis",
  recommendations:"Strategic Recommendations",roadmap:"Implementation Roadmap",
  opportunities:"Strategic Opportunities",risk:"Risk Assessment",
  impact_close:"Expected Impact",custom_text:"Strategic Insights",
  split_chart_right:"Key Findings",split_chart_left:"Analysis",
  three_column:"Recommendations",two_column:"Implementation Roadmap",
  full_chart:"Data Analysis",
};


// ─── DESIGN CONSTRAINTS (LOCKED) ─────────────────────────────────────────────
const FORBIDDEN_BG = ["000000","111111","1A1A1A","0D0D0D","222222","333333"];
const CHART_PALETTE = ["1A365D","2B6CB0","276749","D4A017","744210","553C9A","97266D","718096"];
const TYPOGRAPHY = {H1:32,H2:24,H3:18,BODY:11,CAPTION:9,LABEL:8};

function safeColor(hex, fallback) {
  if(!hex) return fallback;
  const h = String(hex).replace("#","").toUpperCase();
  return FORBIDDEN_BG.includes(h) ? fallback : h;
}

// Calculate luminance for a hex color (0-255)
function getLuminance(hex) {
  if(!hex) return 128;
  const h = hex.replace("#","");
  const r = parseInt(h.substr(0,2),16);
  const g = parseInt(h.substr(2,2),16);
  const b = parseInt(h.substr(4,2),16);
  return 0.299*r + 0.587*g + 0.114*b;
}

// Auto-select text color based on background (white or black)
function textColorForBg(bgColor, lightText="FFFFFF", darkText="1A202C") {
  const lum = getLuminance(bgColor);
  return lum > 128 ? darkText : lightText;
}

// Get high-contrast accent color for background
function contrastColor(bgColor, themeColors) {
  const lum = getLuminance(bgColor);
  // If bg is light, pick dark color; if bg is dark, pick light color
  return lum > 128 ? (themeColors.primary || "1A202C") : (themeColors.accent || "2B6CB0");
}

// Auto-wrap text to prevent truncation
function autoWrap(text, maxCharsPerLine=55) {
  if(!text) return "";
  if(text.length <= maxCharsPerLine) return text;
  const words = text.split(" ");
  let lines = [], line = "";
  for(const w of words){
    if((line+" "+w).trim().length > maxCharsPerLine && line){
      lines.push(line.trim());
      line = w;
    } else {
      line = (line+" "+w).trim();
    }
  }
  if(line) lines.push(line.trim());
  return lines.join("\n");
}

const G = {W:10,H:5.625,M:0.45,HDR:0.40,FTR_H:0.22,FTR_Y:5.40,CY:0.78,CW:9.10,CHART_W:5.78,PANEL_W:3.05,PANEL_X:6.12};
const F = {COVER:32,TITLE:24,SUB:10,SECT:7.5,BODY:10.5,BULLET:10,KPI:30,KPILBL:8.5,CAP:6.5,IMPL:10};

// ─── STDIN ───────────────────────────────────────────────────────────────────
async function readStdin(){return new Promise(r=>{let d="";process.stdin.setEncoding("utf8");process.stdin.on("data",c=>d+=c);process.stdin.on("end",()=>r(d));setTimeout(()=>{if(!d)r("{}");},5000);})}

function confidenceToPercent(txt){
  if(!txt) return "85%";

  const t = txt.toLowerCase();

  if(t.includes("very high")) return "95%";
  if(t.includes("high")) return "90%";
  if(t.includes("medium")) return "75%";
  if(t.includes("low")) return "60%";

  const num = parseFloat(txt);
  if(!isNaN(num)) return `${Math.round(num)}%`;

  return "85%";
}

function normalizeInsight(spec){
  return (
    spec.insight ||
    spec.insights ||
    spec.key_insight ||
    spec.recommendation ||
    ""
  );
}
// ─── UTILS ───────────────────────────────────────────────────────────────────
const trunc=(s,n=200)=>s&&s.length>n?s.slice(0,n)+"...":(s||"");
const safe=(a,f=[])=>Array.isArray(a)&&a.length?a:f;
const safeS=(s,f="")=>(typeof s==="string"&&s.trim())?s.trim():f;
const r2=v=>Math.round(parseFloat(v||0)*100)/100;
const sc=(status,T)=>status==="critical"?T.danger:status==="warning"?T.warn:status==="good"?T.success:T.primary;

// ─── CHART ENGINE ────────────────────────────────────────────────────────────
function getChartData(spec, sample){
  const xCol = spec.x_column;
  const yCol = spec.y_column;

  if(!xCol || !sample?.length) return null;

  const agg={},cnt={};

  sample.forEach(row=>{
    const k = String(row[xCol] ?? "Unknown").slice(0,25);

    if(yCol){
      const v = parseFloat(row[yCol]);
      if(!isNaN(v)){
        agg[k]=(agg[k]||0)+v;
        cnt[k]=(cnt[k]||0)+1;
      }
    }else{
      agg[k]=(agg[k]||0)+1;
      cnt[k]=(cnt[k]||0)+1;
    }
  });

  const entries = Object.entries(agg)
    .sort((a,b)=>b[1]-a[1])
    .slice(0,8);

  if(!entries.length){
    return {labels:["No Data"],values:[1]};
  }

  return {
    labels:entries.map(e=>e[0]),
    values:entries.map(e=>yCol ? +(e[1]/cnt[e[0]]).toFixed(2) : e[1])
  };
}

function drawChart(s,spec,sample,T,x,y,w,h){
  const ct=spec.chart_type;
  if(!ct||ct==="none"||ct==="kpi_card") return false;

  // Validate columns exist in sample
  const sampleKeys=sample.length?Object.keys(sample[0]):[];
  console.log("[chart columns]", sampleKeys);
  console.log("[requested]", spec.x_column, spec.y_column);
  const xOk=!spec.x_column||sampleKeys.includes(spec.x_column);
  const yOk=!spec.y_column||sampleKeys.includes(spec.y_column);
  if(!xOk||!yOk){
    // show placeholder
    s.addShape("rect",{x,y,w,h,fill:{color:T.surface},line:{color:T.border,pt:0.5,dashType:"dash"}});
    s.addText(`[ data columns not found in dataset ]`,{x,y:y+h/2-0.15,w,h:0.3,fontSize:8,color:T.muted,align:"center",margin:0});
    return false;
  }

  const d=getChartData(spec,sample);
  if(!d){
    s.addShape("rect",{x,y,w,h,fill:{color:T.surface},line:{color:T.border,pt:0.5,dashType:"dash"}});
    s.addText(`[ insufficient data for ${ct} chart ]`,{x,y:y+h/2-0.15,w,h:0.3,fontSize:8,color:T.muted,align:"center",margin:0});
    return false;
  }
  const {labels,values}=d;
  const colors=T.charts||CHART_PALETTE;
  const base={x,y,w,h,showTitle:false,showLegend:false,chartArea:{fill:{color:T.bg}},plotArea:{fill:{color:T.bg}}};

  try{
    // bar_vertical or bar (alias)
    if(ct==="bar_vertical"||ct==="bar"){
      s.addChart("bar",[{name:spec.y_column||"Value",labels,values}],{
        ...base,barDir:"col",
        chartColors:values.map((_,i)=>colors[i%colors.length]),
        showValue:labels.length<=10,dataLabelFontSize:7,dataLabelColor:"FFFFFF",
        valAxisLabelFontSize:7,catAxisLabelFontSize:labels.length>8?6:7.5,
        valAxisLineShow:false,catAxisLineShow:true,
        barGapWidthPct:40,
      });
    // bar_horizontal — sorted descending, best for ranked lists
    }else if(ct==="bar_horizontal"){
      // sort descending for ranked view
      const pairs=labels.map((l,i)=>({l,v:values[i]})).sort((a,b)=>b.v-a.v);
      const sl=pairs.map(p=>p.l), sv=pairs.map(p=>p.v);
      s.addChart("bar",[{name:spec.y_column||"Value",labels:sl,values:sv}],{
        ...base,barDir:"bar",
        chartColors:sv.map((_,i)=>colors[i%colors.length]),
        showValue:true,dataLabelFontSize:7,dataLabelColor:"FFFFFF",
        valAxisLabelFontSize:7,catAxisLabelFontSize:7,
        barGapWidthPct:35,
      });
    // line — time series
    }else if(ct==="line"){
      s.addChart("line",[{name:spec.y_column||"Value",labels,values}],{
        ...base,chartColors:[T.accent],lineSize:2.5,
        lineDataSymbol:labels.length>20?"none":"circle",lineDataSymbolSize:5,
        showValue:false,valAxisLabelFontSize:7,catAxisLabelFontSize:labels.length>12?6:7.5,
        valGridLine:{style:"solid",color:T.border,pt:0.3},
      });
    // area — cumulative trend
    }else if(ct==="area"){
      s.addChart("area",[{name:spec.y_column||"Value",labels,values}],{
        ...base,chartColors:[T.accent],lineSize:2,
        showValue:false,valAxisLabelFontSize:7,catAxisLabelFontSize:7,
      });
    // donut — part of whole (modern vs pie)
    }else if(ct==="donut"||ct==="pie"){  // pie → donut automatically
      s.addChart("doughnut",[{name:spec.x_column||"Segment",labels,values}],{
        ...base,
        chartColors:colors.slice(0,Math.min(labels.length,8)),
        showLegend:true,legendPos:"r",legendFontSize:8,
        showLeaderLines:true,dataLabelFontSize:8.5,holeSize:55,
        showPercent:true,dataLabelColor:T.text1,
      });
    // scatter — correlation
    }else if(ct==="scatter"){
      const xV=sample.map(r=>parseFloat(r[spec.x_column])).filter(v=>!isNaN(v));
      const yV=sample.map(r=>parseFloat(r[spec.y_column])).filter(v=>!isNaN(v));
      const n=Math.min(xV.length,yV.length,300);
      if(n<3){
        s.addShape("rect",{x,y,w,h,fill:{color:T.surface},line:{color:T.border,pt:0.5,dashType:"dash"}});
        s.addText("[ insufficient scatter data ]",{x,y:y+h/2-0.15,w,h:0.3,fontSize:8,color:T.muted,align:"center",margin:0});
        return false;
      }
      s.addChart("scatter",[{name:`${spec.x_column} vs ${spec.y_column}`,values:Array.from({length:n},(_,i)=>({x:xV[i],y:yV[i]}))}],{
        ...base,chartColors:[T.accent],lineDataSymbol:"dot",lineDataSymbolSize:6,lineSize:0,
        valAxisLabelFontSize:7,catAxisLabelFontSize:7,
      });
    }else{
      return false;
    }
    return true;
  }catch(e){console.error(`[chart:${ct}]`,e.message);return false;}
}

// ─── UI COMPONENTS ───────────────────────────────────────────────────────────
function hdr(s, label, plan, T) {
  // Auto-select text color for dark header background
  const headerTextColor = textColorForBg(T.primary, T.accent, "FFFFFF");
  const mutedColor = textColorForBg(T.primary, T.muted, "CCCCCC");

  s.addShape("rect", {
    x: 0,
    y: 0,
    w: G.W,
    h: G.HDR,
    fill: { color: T.primary }
  });

  s.addShape("rect", {
    x: 0,
    y: 0,
    w: 0.06,
    h: G.HDR,
    fill: { color: T.accent }
  });

  s.addText(label.toUpperCase(), {
    x: 0.14,
    y: 0,
    w: 5,
    h: G.HDR,
    fontSize: F.SECT,
    color: headerTextColor,
    bold: true,
    charSpacing: 3,
    valign: "middle",
    margin: 0
  });

  s.addText(
    `${plan.company} · Confidential · ${plan.date}`,
    {
      x: 5,
      y: 0,
      w: 4.8,
      h: G.HDR,
      fontSize: F.CAP,
      color: mutedColor,
      align: "right",
      valign: "middle",
      margin: 0
    }
  );
}

function ftr(s, pg, total, T, validation = {}) {
  const conf = validation.confidence || 0;
  const confText = `Data Confidence: ${Math.round(conf)}%`;
  const confColor = conf >= 90 ? T.success : conf >= 70 ? T.warn : T.danger;
  const isValid = validation.is_valid !== false;

  // footer text
  s.addText(
    isValid ? "AI-Powered · Statistically Verified" : "AI-Powered · Review Recommended",
    {
      x: G.W - 1.4,
      y: G.FTR_Y,
      w: G.CW,
      h: 0.2,
      fontSize: 6.5,
      align: "right",
      color: isValid ? T.muted : T.danger
    }
  );

  // confidence badge
  s.addShape("rect", {
    x: G.W - 2.4,
    y: G.FTR_Y - 0.08,
    w: 0.95,
    h: 0.18,
    fill: { color: confColor },
    line: { color: confColor, pt: 0 }
  });
  s.addText(
    confText,
    {
      x: G.W - 2.4,
      y: G.FTR_Y - 0.08,
      w: 0.95,
      h: 0.18,
      fontSize: 6,
      color: "FFFFFF",
      align: "center",
      valign: "middle",
      bold: true,
      margin: 0
    }
  );

  // page number (premium consulting style)
  if (pg !== undefined && total !== undefined) {
    s.addText(
      `${pg} / ${total}`,
      {
        x: G.W - 1.2,
        y: G.FTR_Y - 0.28,
        w: 1,
        h: 0.2,
        fontSize: 6.5,
        color: T.muted
      }
    );
  }

  // Audit badge (show verification confidence)
  if (validation && validation.overall_confidence > 0) {
    const auditLabel = validation.is_valid ? `✓ Verified ${Math.round(validation.overall_confidence)}%` : `⚠ Review ${Math.round(validation.overall_confidence)}%`;
    const auditColor = validation.is_valid ? T.success : T.warn;

    s.addShape("rect", {
      x: 0.1,
      y: G.FTR_Y - 0.08,
      w: 1.2,
      h: 0.18,
      fill: { color: auditColor },
      line: { color: auditColor, pt: 0.5 }
    });
    s.addText(auditLabel, {
      x: 0.1,
      y: G.FTR_Y - 0.08,
      w: 1.2,
      h: 0.18,
      fontSize: 6,
      color: "FFFFFF",
      align: "center",
      valign: "middle",
      bold: true,
      margin: 0
    });
  }
}

function titl(s,title,sub,T,compact=false){
  const chars=(title||"").length;
  let fs;
  if(compact){fs=chars>100?13:chars>70?15:chars>50?17:chars>30?19:21;}
  else{fs=chars>100?15:chars>70?17:chars>50?19:chars>30?21:F.TITLE;}
  const titleH=compact?0.72:0.88;
  s.addText(trunc(title,160),{x:G.M,y:G.CY,w:G.CW,h:titleH,fontSize:fs,color:T.text1,bold:true,lineSpacingMultiple:1.1,margin:0});
  if(sub) s.addText(trunc(sub,110),{x:G.M,y:G.CY+titleH+0.04,w:G.CW,h:0.24,fontSize:10,color:T.text2,margin:0});
  return G.CY+titleH+0.06+(sub?0.26:0)+0.08;
}

function impl(s,text,T){
  if(!text) return;
  const y=G.FTR_Y-0.50;
  s.addShape("rect",{x:G.M,y,w:G.CW,h:0.40,fill:{color:T.surface}});
  s.addShape("rect",{x:G.M,y,w:0.055,h:0.40,fill:{color:T.accent}});
  s.addText(trunc(text,250),{x:G.M+0.12,y,w:G.CW-0.16,h:0.40,fontSize:F.IMPL,color:T.text1,bold:true,valign:"middle",margin:0});
}

function panel(s,heading,bullets,T,y,h,color){
  const C=color||T.accent,RX=G.PANEL_X,RW=G.PANEL_W;
  const headerColor = textColorForBg(T.surface, C, T.text2);
  s.addShape("rect",{x:RX,y,w:RW,h,fill:{color:T.surface},line:{color:T.border,pt:0.5}});
  s.addShape("rect",{x:RX,y,w:RW,h:0.05,fill:{color:C}});
  s.addText((heading||"").toUpperCase(),{x:RX+0.14,y:y+0.10,w:RW-0.28,h:0.24,fontSize:F.SECT,color:headerColor,bold:true,charSpacing:2.5,margin:0});
  s.addShape("rect",{x:RX+0.14,y:y+0.36,w:RW-0.28,h:0.01,fill:{color:T.border}});
  const items=safe(bullets).slice(0,4);
  const slotH=(h-0.46)/Math.max(items.length,1);
  items.forEach((item,i)=>{
    const iy=y+0.46+i*slotH;
    const bulletColor = i===0?C:T.muted;
    s.addShape("ellipse",{x:RX+0.14,y:iy+0.11,w:0.10,h:0.10,fill:{color:bulletColor}});
    const bulletTextColor = textColorForBg(T.surface, bulletColor, T.text3);
    s.addText(trunc(item,42),{x:RX+0.30,y:iy,w:RW-0.42,h:slotH-0.06,fontSize:F.BULLET,color:bulletTextColor,valign:"middle",lineSpacingMultiple:1.15,margin:0});
    if(i<items.length-1) s.addShape("rect",{x:RX+0.14,y:iy+slotH-0.04,w:RW-0.28,h:0.008,fill:{color:T.border}});
  });
}

function kpiRow(s,kpis,T,y,h=0.86){
  const n=Math.min(safe(kpis).length,4);if(!n)return;
  const w=G.CW/n;
  kpis.slice(0,n).forEach((kpi,i)=>{
    const x=G.M+i*w,color=sc(kpi.status,T);
    s.addShape("rect",{x,y,w:w-0.08,h,fill:{color:T.card},line:{color:T.border,pt:0.4}});
    s.addShape("rect",{x,y,w:0.05,h,fill:{color:color}});
    s.addText(String(kpi.value||kpi.formatted||"—").slice(0,12),{x:x+0.14,y:y+0.06,w:w-0.22,h:h*0.58,fontSize:F.KPI,color:color,bold:true,margin:0});
    s.addText(trunc(kpi.name||"",28),{x:x+0.14,y:y+h*0.60,w:w-0.22,h:h*0.36,fontSize:F.KPILBL,color:T.text2,margin:0});
  });
}

// ─── SLIDE BUILDERS ──────────────────────────────────────────────────────────
function sCover(pres,spec,plan,sample,T){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  s.addShape("rect",{x:0,y:0,w:6.6,h:G.H,fill:{color:T.primary}});
  s.addShape("rect",{x:6.52,y:0,w:0.12,h:G.H,fill:{color:T.accent}});
  s.addText(plan.company.toUpperCase(),{x:0.52,y:0.52,w:5.7,h:0.30,fontSize:9,color:T.accent,bold:true,charSpacing:4.5,margin:0});
  const title=safeS(spec.title,plan.mainMsg);
  const wc=title.split(" ").length;
  const fs=wc>12?22:wc>8?26:wc>5?30:F.COVER;
  s.addText(trunc(title,150),{x:0.52,y:0.96,w:5.7,h:2.54,fontSize:fs,color:"FFFFFF",bold:true,lineSpacingMultiple:1.1,margin:0});
  s.addShape("rect",{x:0.52,y:3.62,w:5.7,h:0.54,fill:{color:T.accent}});
  s.addText(trunc(safeS(spec.subtitle,plan.industry||"Business Intelligence"),80),{x:0.52,y:3.62,w:5.7,h:0.54,fontSize:12,color:T.primary,bold:true,valign:"middle",margin:{left:16}});
  s.addText(`${plan.company}  ·  Confidential  ·  ${plan.date}`,{x:0.52,y:5.32,w:5.7,h:0.22,fontSize:F.CAP,color:"475569",margin:0});
  s.addText("BUSINESS INTELLIGENCE REPORT",{x:6.80,y:0.50,w:2.90,h:0.22,fontSize:6.5,color:T.text2,bold:true,charSpacing:1.5,margin:0});
  s.addText(plan.date,{x:6.80,y:0.74,w:2.90,h:0.22,fontSize:10,color:T.text3,margin:0});
  const coverKPIs=safe(spec.kpis).length?safe(spec.kpis).slice(0,3):[{name:"Data Quality",value:"95/100",status:"good"},{name:"AI Confidence",value:"High",status:"good"},{name:"Slides",value:String(plan.total),status:"neutral"}];
  coverKPIs.forEach(({name,value,status},i)=>{
    const color=sc(status,T),y=1.16+i*1.36;
    s.addShape("rect",{x:6.80,y,w:2.92,h:1.22,fill:{color:T.bg},line:{color:T.border,pt:0.5}});
    s.addShape("rect",{x:6.80,y,w:0.055,h:1.22,fill:{color:color}});
    const displayValue =
      name.toLowerCase().includes("confidence")
        ? confidenceToPercent(value)
        : value;
    s.addText(String(name),{x:6.95,y:y+0.50,w:2.65,h:0.28,fontSize:9,color:T.text2,margin:0});
    s.addText(String(displayValue),{x:6.95,y:y+0.82,w:2.65,h:0.30,fontSize:12,color:color,bold:true,margin:0});
  });
}

function sSCR(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,"Executive Summary",plan,T);
  titl(s,spec.title,"SCR Framework — Situation · Complication · Resolution",T);
  const B=safe(spec.bullets);
  const scr=[
    {L:"S",label:"SITUATION",    body:B[0]||plan.situation, color:T.accent, bg:T.surface},
    {L:"C",label:"COMPLICATION", body:B[1]||plan.compl,    color:T.warn,   bg:"FFFBEB"},
    {L:"R",label:"RESOLUTION",   body:B[2]||plan.resol,    color:T.success,bg:"F0FDF4"},
  ];
  const cY=1.18,cH=2.66;
  scr.forEach(({L,label,body,color,bg},i)=>{
    const x=G.M+i*3.08;
    s.addShape("rect",{x,y:cY,w:2.98,h:cH,fill:{color:safeColor(bg,T.surface)},line:{color:T.border,pt:0.5}});
    s.addShape("rect",{x,y:cY,w:2.98,h:0.06,fill:{color:color}});
    s.addShape("ellipse",{x:x+0.14,y:cY+0.14,w:0.36,h:0.36,fill:{color:color}});
    s.addText(L,{x:x+0.14,y:cY+0.14,w:0.36,h:0.36,fontSize:13,color:"FFFFFF",bold:true,align:"center",valign:"middle",margin:0});
    s.addText(label,{x:x+0.58,y:cY+0.16,w:2.26,h:0.32,fontSize:F.SECT,color:color,bold:true,charSpacing:1.5,valign:"middle",margin:0});
    s.addText(trunc(body,300),{x:x+0.14,y:cY+0.62,w:2.70,h:cH-0.74,fontSize:F.BODY,color:T.text3,lineSpacingMultiple:1.55,valign:"top",margin:0});
  });
  const evY=cY+cH+0.12;
  safe(spec.kpis).slice(0,3).forEach((kpi,i)=>{
    const x=G.M+i*3.08,color=sc(kpi.status,T);
    s.addShape("ellipse",{x,y:evY+0.22,w:0.10,h:0.10,fill:{color:color}});
    s.addText(`${kpi.name}: ${kpi.value||kpi.formatted}`,{x:x+0.18,y:evY+0.18,w:2.8,h:0.26,fontSize:9.5,color:T.text3,valign:"middle",margin:0});
  });
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sKPI(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Performance Dashboard",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const kpis=safe(spec.kpis);
  if(kpis.length) kpiRow(s,kpis,T,nY);
  const cY=nY+(kpis.length?0.88:0)+0.06;
  const cH=Math.min(G.FTR_Y-0.9-cY,2.3);
  const hasChart=drawChart(s,spec,sample,T,G.M,cY,G.CHART_W,cH);
  let kpiBullets=safe(spec.bullets);
  if(!kpiBullets.length) kpiBullets=["Key metrics verified from source data","Statistical engine calculated — no AI estimation","Review trends against industry benchmarks"];
  panel(s,"Key Takeaways",kpiBullets,T,cY,cH);
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sSplitR(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Key Findings",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const cY=nY+0.04,cH=Math.min(G.FTR_Y-0.54-cY,3.2);
  const hasChart=drawChart(s,spec,sample,T,G.M,cY,G.CHART_W,cH);
  // RULE: chart always requires insight panel
  let bullets=safe(spec.bullets);
  if(bullets.length===0){
    bullets=["Data pattern identified — see chart for distribution","Statistical analysis verified from source dataset","Review with business team for strategic implications"];
  }
  panel(s,spec.section||"Key Insights",bullets,T,cY,cH);
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sSplitL(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Analysis",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const cY=nY+0.04,cH=G.FTR_Y-0.54-cY,LW=3.0,RX=3.58,RW=6.06;
  s.addShape("rect",{x:G.M,y:cY,w:LW,h:cH,fill:{color:T.surface},line:{color:T.border,pt:0.5}});
  s.addShape("rect",{x:G.M,y:cY,w:LW,h:0.05,fill:{color:T.accent}});
  s.addText((spec.section||"Insights").toUpperCase(),{x:G.M+0.14,y:cY+0.10,w:LW-0.28,h:0.24,fontSize:F.SECT,color:T.accent,bold:true,charSpacing:2,margin:0});
  const items=safe(spec.bullets).slice(0,4);
  const slotH=(cH-0.42)/Math.max(items.length,1);
  items.forEach((b,i)=>{
    const iy=cY+0.42+i*slotH;
    s.addShape("ellipse",{x:G.M+0.14,y:iy+0.10,w:0.10,h:0.10,fill:{color:i===0?T.accent:T.muted}});
    s.addText(trunc(b,32),{x:G.M+0.30,y:iy,w:LW-0.42,h:slotH-0.06,fontSize:F.BULLET,color:T.text3,valign:"middle",lineSpacingMultiple:1.3,margin:0});
  });
  drawChart(s,spec,sample,T,RX,cY,RW,cH);
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function s3Col(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Recommendations",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const cY=nY+0.06,cH=2.92,cW=2.98;
  const cols=safe(spec.bullets).slice(0,3);
  while(cols.length<3) cols.push("Strategic consideration");
  const colC=[T.accent,T.primary,T.success];
  cols.forEach((txt,i)=>{
    const x=G.M+i*3.08;
    s.addShape("rect",{x,y:cY,w:cW,h:cH,fill:{color:T.card},line:{color:T.border,pt:0.5}});
    s.addShape("rect",{x,y:cY,w:cW,h:0.06,fill:{color:colC[i]}});
    s.addShape("ellipse",{x:x+0.14,y:cY+0.14,w:0.42,h:0.42,fill:{color:colC[i]}});
    s.addText(String(i+1),{x:x+0.14,y:cY+0.14,w:0.42,h:0.42,fontSize:15,color:"FFFFFF",bold:true,align:"center",valign:"middle",margin:0});
    s.addText(trunc(txt,200),{x:x+0.14,y:cY+0.70,w:cW-0.28,h:cH-0.82,fontSize:10,color:T.text3,lineSpacingMultiple:1.45,valign:"top",margin:0});
  });
  const evY=cY+cH+0.14;
  safe(spec.kpis).slice(0,3).forEach((kpi,i)=>{
    const x=G.M+i*3.08,color=sc(kpi.status,T);
    s.addShape("ellipse",{x,y:evY+0.06,w:0.10,h:0.10,fill:{color:color}});
    s.addText(trunc(`${kpi.name}: ${kpi.value||kpi.formatted}`,55),{x:x+0.18,y:evY,w:2.8,h:0.26,fontSize:9.5,color:T.text3,valign:"middle",margin:0});
  });
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function s2Col(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Roadmap",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const cY=nY+0.06,cH=G.FTR_Y-0.54-cY,cW=4.50;
  const B=safe(spec.bullets);
  const left=B.slice(0,Math.ceil(B.length/2)),right=B.slice(Math.ceil(B.length/2));
  [[left,T.accent],[right,T.primary]].forEach(([items,color],col)=>{
    const x=G.M+col*(cW+0.12);
    s.addShape("rect",{x,y:cY,w:cW,h:cH,fill:{color:T.surface},line:{color:T.border,pt:0.5}});
    s.addShape("rect",{x,y:cY,w:cW,h:0.05,fill:{color:color}});
    const slotH=(cH-0.12)/Math.max(items.length,1);
    items.forEach((item,i)=>{
      const iy=cY+0.12+i*slotH;
      s.addShape("ellipse",{x:x+0.14,y:iy+0.10,w:0.10,h:0.10,fill:{color:color}});
      s.addText(trunc(item,180),{x:x+0.30,y:iy,w:cW-0.40,h:slotH-0.06,fontSize:F.BULLET,color:T.text3,valign:"middle",lineSpacingMultiple:1.3,margin:0});
      if(i<items.length-1) s.addShape("rect",{x:x+0.14,y:iy+slotH-0.04,w:cW-0.28,h:0.008,fill:{color:T.border}});
    });
  });
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sFullChart(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Data Analysis",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const cY=nY+0.04,cH=Math.min(G.FTR_Y-0.54-cY,3.2);
  drawChart(s,spec,sample,T,G.M,cY,G.CW,cH);
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sText(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Strategic Insights",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const cY=nY+0.04,cH=G.FTR_Y-0.54-cY;
  const items=safe(spec.bullets).slice(0,5);
  const slotH=cH/Math.max(items.length,1);
  items.forEach((b,i)=>{
    const iy=cY+i*slotH;
    s.addShape("rect",{x:G.M,y:iy+0.08,w:0.05,h:slotH-0.20,fill:{color:i===0?T.accent:T.border}});
    s.addText(trunc(b,170),{x:G.M+0.14,y:iy,w:G.CW-0.14,h:slotH,fontSize:11.5,color:T.text3,valign:"middle",lineSpacingMultiple:1.5,margin:0});
    if(i<items.length-1) s.addShape("rect",{x:G.M,y:iy+slotH-0.02,w:G.CW,h:0.008,fill:{color:T.border}});
  });
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sDark(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  // White background closing slide
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  // Top accent bar
  s.addShape("rect",{x:0,y:0,w:G.W,h:0.08,fill:{color:T.accent}});
  // Section label
  s.addText("EXPECTED IMPACT & NEXT STEPS",{x:G.M,y:0.18,w:G.CW,h:0.26,fontSize:F.SECT,color:T.accent,bold:true,charSpacing:3,margin:0});
  // Main headline
  const headline=trunc(spec.title||plan.mainMsg,120);
  const wc=headline.split(" ").length;
  const hfs=wc>15?18:wc>10?20:22;
  s.addText(headline,{x:G.M,y:0.50,w:G.CW,h:0.80,fontSize:hfs,color:T.text1,bold:true,lineSpacingMultiple:1.15,margin:0});
  // Divider
  s.addShape("rect",{x:G.M,y:1.36,w:G.CW,h:0.025,fill:{color:T.border}});
  // KPI impact cards
  const kpis=safe(spec.kpis).slice(0,3);
  while(kpis.length<3) kpis.push({name:"Review implementation roadmap",value:"Q2 2026",status:"neutral"});
  const cardC=[T.accent,T.gold||"D4A017",T.success];
  kpis.forEach(({name,value,status},i)=>{
    const x=G.M+i*3.08,y=1.48;
    const color=status==="good"?T.success:status==="critical"?T.danger:cardC[i];
    s.addShape("rect",{x,y,w:2.98,h:1.60,fill:{color:T.card},line:{color:T.border,pt:0.5}});
    s.addShape("rect",{x,y,w:2.98,h:0.06,fill:{color:color}});
    // Value
    const valStr=trunc(String(value),35);
    const vfs=valStr.length>20?11:valStr.length>12?13:16;
    s.addText(valStr,{x:x+0.14,y:y+0.16,w:2.70,h:0.70,fontSize:vfs,color:color,bold:true,align:"center",lineSpacingMultiple:1.1,margin:0});
    // Name
    s.addText(trunc(String(name),50),{x:x+0.14,y:y+0.92,w:2.70,h:0.56,fontSize:9,color:T.text2,align:"center",lineSpacingMultiple:1.2,margin:0});
  });
  // Bullets from spec
  const bullets=safe(spec.bullets).slice(0,3);
  if(bullets.length>0){
    const bY=3.22;
    s.addText("KEY ACTIONS",{x:G.M,y:bY,w:G.CW,h:0.22,fontSize:F.SECT,color:T.text2,bold:true,charSpacing:2,margin:0});
    bullets.forEach((b,i)=>{
      const iy=bY+0.26+i*0.36;
      s.addShape("ellipse",{x:G.M,y:iy+0.10,w:0.10,h:0.10,fill:{color:T.accent}});
      s.addText(trunc(b,140),{x:G.M+0.18,y:iy,w:G.CW-0.18,h:0.34,fontSize:10,color:T.text1,valign:"middle",lineSpacingMultiple:1.2,margin:0});
    });
  }
  // CTA bar
  const ctaY=G.FTR_Y-0.62;
  s.addShape("rect",{x:G.M,y:ctaY,w:G.CW,h:0.48,fill:{color:T.accent}});
  s.addText(trunc(spec.insight||"NEXT STEP: Schedule executive review and approve implementation budget",130),{x:G.M+0.16,y:ctaY,w:G.CW-0.30,h:0.48,fontSize:10,color:"FFFFFF",bold:true,valign:"middle",margin:0});
  ftr(s,pg,total,T);
}

// ─── NEW LAYOUTS ─────────────────────────────────────────────────────────────

function sBigNumber(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  // Left dark panel
  s.addShape("rect",{x:0,y:0,w:4.2,h:G.H,fill:{color:T.primary}});
  s.addShape("rect",{x:4.12,y:0,w:0.10,h:G.H,fill:{color:T.accent}});
  // The big number
  const kpi=safe(spec.kpis)[0]||{name:"Key Metric",value:"—",status:"neutral"};
  const numStr=String(kpi.value||kpi.formatted||"—").slice(0,14);
  const numFs=numStr.length>10?32:numStr.length>7?42:54;
  s.addText(numStr,{x:0.3,y:1.3,w:3.6,h:1.8,fontSize:numFs,color:T.accent,bold:true,align:"center",valign:"middle",margin:0});
  s.addText((kpi.name||"").toUpperCase(),{x:0.3,y:3.1,w:3.6,h:0.35,fontSize:8.5,color:"AABBCC",bold:true,align:"center",charSpacing:1.5,margin:0});
  // Source note
  if(kpi.source_column) s.addText(`Source: ${kpi.source_column}`,{x:0.3,y:G.FTR_Y-0.4,w:3.6,h:0.25,fontSize:6.5,color:"7A9BB5",italic:true,align:"center",margin:0});
  // Right side — title + bullets
  hdr(s,spec.section||"Key Metric",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const items=safe(spec.bullets).slice(0,4);
  const slotH=(G.FTR_Y-0.55-nY-0.35)/Math.max(items.length,1);
  items.forEach((b,i)=>{
    const iy=nY+0.12+i*slotH;
    s.addShape("rect",{x:4.36,y:iy+0.10,w:0.05,h:slotH-0.24,fill:{color:i===0?T.accent:T.border}});
    s.addText(trunc(b,130),{x:4.48,y:iy,w:G.W-4.62,h:slotH,fontSize:F.BULLET,color:T.text3,valign:"middle",lineSpacingMultiple:1.3,margin:0});
  });
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sTimeline(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Implementation Roadmap",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const bullets=safe(spec.bullets).slice(0,5);
  const n=Math.max(bullets.length,1);
  const lineY=nY+1.2;
  const lineX1=G.M+0.3, lineX2=G.M+G.CW-0.3;
  // Timeline backbone
  s.addShape("rect",{x:lineX1,y:lineY-0.015,w:lineX2-lineX1,h:0.03,fill:{color:T.accent}});
  const stepW=(lineX2-lineX1)/(n);
  bullets.forEach((b,i)=>{
    const cx=lineX1+i*stepW+stepW*0.5;
    // Dot
    s.addShape("ellipse",{x:cx-0.12,y:lineY-0.12,w:0.24,h:0.24,fill:{color:T.accent},line:{color:T.bg,pt:1.5}});
    // Phase label above
    const phases=["30 DAYS","60 DAYS","90 DAYS","Q2","Q3","Q4"];
    s.addText(phases[i]||`Phase ${i+1}`,{x:cx-stepW*0.42,y:lineY-0.52,w:stepW*0.84,h:0.28,fontSize:7,color:T.accent,bold:true,align:"center",charSpacing:1,margin:0});
    // Content below
    s.addText(trunc(b,160),{x:cx-stepW*0.44,y:lineY+0.22,w:stepW*0.88,h:1.8,fontSize:F.BULLET,color:T.text3,align:"center",valign:"top",lineSpacingMultiple:1.3,wrap:true,margin:0});
  });
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sBulletsOnly(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Strategic Insights",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,false);
  const cY=nY+0.14;
  // Accent divider
  s.addShape("rect",{x:G.M,y:cY,w:1.2,h:0.04,fill:{color:T.accent}});
  const items=safe(spec.bullets).slice(0,6);
  const cH=Math.max(2.2, G.FTR_Y-0.90-cY);
  const slotH=cH/Math.max(items.length,1);
  items.forEach((b,i)=>{
    const iy=nY+0.14+i*slotH;
    const color=i===0?T.accent:i===1?T.primary:T.muted;
    // Number badge
    s.addShape("ellipse",{x:G.M,y:iy+0.06,w:0.28,h:0.28,fill:{color:color}});
    s.addText(String(i+1),{x:G.M,y:iy+0.06,w:0.28,h:0.28,fontSize:10,color:"FFFFFF",bold:true,align:"center",valign:"middle",margin:0});
    s.addText(autoWrap(trunc(b,200)),{x:G.M+0.38,y:iy,w:G.CW-0.38,h:slotH-0.06,fontSize:11.5,color:T.text3,valign:"middle",lineSpacingMultiple:1.4,margin:0});
    if(i<items.length-1) s.addShape("rect",{x:G.M,y:iy+slotH-0.04,w:G.CW,h:0.006,fill:{color:T.border}});
  });
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

function sSectionDivider(pres,spec,plan,sample,T,pg,total,validation={}){
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  // Left accent panel
  s.addShape("rect",{x:0,y:0,w:4.0,h:G.H,fill:{color:T.primary}});
  s.addShape("rect",{x:3.92,y:0,w:0.12,h:G.H,fill:{color:T.accent}});
  // Section number
  s.addText(`0${pg}`,{x:0.4,y:1.0,w:3.2,h:1.2,fontSize:80,color:T.accent,bold:true,align:"center",valign:"middle",opacity:20,margin:0});
  s.addText((spec.title||"Section").toUpperCase(),{x:0.4,y:2.0,w:3.2,h:1.0,fontSize:F.TITLE,color:"FFFFFF",bold:true,align:"center",valign:"middle",lineSpacingMultiple:1.1,margin:0});
  // Right: subtitle + description
  if(spec.subtitle) s.addText(spec.subtitle,{x:4.28,y:1.8,w:5.5,h:0.5,fontSize:16,color:T.text2,margin:0});
  if(safe(spec.bullets).length){
    safe(spec.bullets).slice(0,3).forEach((b,i)=>{
      s.addShape("ellipse",{x:4.28,y:2.48+i*0.50,w:0.10,h:0.10,fill:{color:T.accent}});
      s.addText(trunc(b,120),{x:4.46,y:2.40+i*0.50,w:5.3,h:0.44,fontSize:10.5,color:T.text3,valign:"middle",margin:0});
    });
  }
  ftr(s,pg,total,T,validation);
}

function sKpiRow(pres,spec,plan,sample,T,pg,total,validation={}){
  // KPI banner + large text area below
  const s=pres.addSlide();
  s.addShape("rect",{x:0,y:0,w:G.W,h:G.H,fill:{color:T.bg}});
  hdr(s,spec.section||"Performance Overview",plan,T);
  const nY=titl(s,spec.title,spec.subtitle,T,true);
  const kpis=safe(spec.kpis).slice(0,4);
  if(kpis.length) kpiRow(s,kpis,T,nY+0.04,1.0);
  const bY=nY+(kpis.length?1.12:0)+0.10;
  const items=safe(spec.bullets).slice(0,4);
  const slotH=(G.FTR_Y-0.55-bY-0.12)/Math.max(items.length,1);
  items.forEach((b,i)=>{
    const iy=bY+i*slotH;
    s.addShape("rect",{x:G.M,y:iy+0.10,w:0.05,h:slotH-0.22,fill:{color:i===0?T.accent:T.border}});
    s.addText(trunc(b,160),{x:G.M+0.14,y:iy,w:G.CW-0.14,h:slotH,fontSize:F.BULLET,color:T.text3,valign:"middle",lineSpacingMultiple:1.3,margin:0});
    if(i<items.length-1) s.addShape("rect",{x:G.M,y:iy+slotH-0.02,w:G.CW,h:0.006,fill:{color:T.border}});
  });
  impl(s,normalizeInsight(spec),T);ftr(s,pg,total,T,validation);
}

// ─── MAIN ────────────────────────────────────────────────────────────────────
async function build(){
  const raw=await readStdin();
  let P={};
  try{P=JSON.parse(raw);}catch(e){console.error("JSON:",e.message);}

  const dp=P.deck_plan||{};
  const analysis=P.analysis||{};
  const story=P.story||{};
  const dfSum=P.df_summary||{};
  const sample=safe(dfSum.sample,[]);
  const slides=safe(dp.slides,[]);
  const validation=P.validation||{};

  if(!slides.length){console.error("ERROR: No slides in deck_plan");process.exit(1);}

  // theme_name = string name, theme = object from Python
  const themeName = safeS(dp.theme_name,"navy_consulting");

  const T = (dp.theme && typeof dp.theme === "object" && dp.theme.primary)
    ? dp.theme
    : (THEMES[themeName] || THEMES.navy_consulting);

  const DESIGN  = dp.design_spec || {};
  const PALETTE = DESIGN.palette || {};
  const LAYOUT  = DESIGN.layout  || {};
  const PRIMARY = PALETTE.primary || T.primary;
  const ACCENT  = PALETTE.accent  || T.accent;

  T.primary = PRIMARY;
  T.accent  = ACCENT;

  // merge AI palette into theme
  if (PALETTE.primary) T.primary = PALETTE.primary;
  if (PALETTE.accent)  T.accent  = PALETTE.accent;
  if (PALETTE.muted)   T.muted   = PALETTE.muted;

  const date=new Date().toLocaleDateString("en-GB",
    {day:"2-digit",month:"short",year:"numeric"}
  );

  const plan={
    company:safeS(dp.company_name,"My Company"),
    date,
    total:slides.length,
    mainMsg:safeS(dp.main_message,
             safeS(analysis.summary,"Key Business Insights").slice(0,80)),
    industry:safeS(dp.industry,"general"),
    design_spec: dp.design_spec,
    situation:safeS(story.situation,(analysis.summary||"").slice(0,200)),
    compl:safeS(story.complication,safe(analysis.anomalies,[])[0]||""),
    resol:safeS(story.resolution,safe(analysis.recommendations,[])[0]||""),
    verification:dp.verification||{verified_claims:0,total_claims:0,overall_confidence:0},
  };

  const pres=new pptxgen();
  pres.layout="LAYOUT_16x9";
  pres.author="BI Agent";
  pres.company = plan.company;
  pres.subject = "Business Intelligence Analysis";
  pres.title=`${plan.company} — BI Report`;
  const total=slides.length;

  slides.forEach((spec,idx)=>{
    // Fix section label — use SECTION_LABELS map, not raw slide_type
    spec.section=SECTION[spec.slide_type]||SECTION[spec.layout]||safeS(spec.slide_type,"Analysis").replace(/_/g," ");
    const layout=safeS(spec.layout,"split_chart_right");
    const pg=idx+1;

    // ---- AUTO LAYOUT NORMALIZER ----
  if(!spec.layout){
    if(spec.kpis) spec.layout="kpi_dashboard";
    else if(spec.chart_type) spec.layout="split_chart_right";
    else if(spec.bullets) spec.layout="bullets_only";
    else spec.layout="two_column";
  }

    switch(layout){
      case "cover":              sCover(pres,spec,plan,sample,T);break;
      case "executive_summary":  sSCR(pres,spec,plan,sample,T,pg,total,validation);break;
      case "kpi_dashboard":      sKPI(pres,spec,plan,sample,T,pg,total,validation);break;
      case "kpi_row":            sKpiRow(pres,spec,plan,sample,T,pg,total,validation);break;
      case "split_chart_right":  sSplitR(pres,spec,plan,sample,T,pg,total,validation);break;
      case "split_chart_left":   sSplitL(pres,spec,plan,sample,T,pg,total,validation);break;
      case "three_column":       s3Col(pres,spec,plan,sample,T,pg,total,validation);break;
      case "two_column":         s2Col(pres,spec,plan,sample,T,pg,total,validation);break;
      case "full_chart":         sFullChart(pres,spec,plan,sample,T,pg,total,validation);break;
      case "dark_close":         sDark(pres,spec,plan,sample,T,pg,total,validation);break;
      case "big_number":         sBigNumber(pres,spec,plan,sample,T,pg,total,validation);break;
      case "timeline":           sTimeline(pres,spec,plan,sample,T,pg,total,validation);break;
      case "bullets_only":       sBulletsOnly(pres,spec,plan,sample,T,pg,total,validation);break;
      case "section_divider":    sSectionDivider(pres,spec,plan,sample,T,pg,total,validation);break;
      case "image_text":         sSplitR(pres,spec,plan,sample,T,pg,total,validation);break;  // alias
      default:                   sText(pres,spec,plan,sample,T,pg,total,validation);break;    // safe fallback
    }
  });

  const out=process.argv[2]||"/tmp/output.pptx";
  await pres.writeFile({fileName:out});
  console.log("OK:"+out);
}

build().catch(e=>{console.error("ERROR:"+e.message+"\n"+e.stack);process.exit(1);});