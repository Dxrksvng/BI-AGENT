import { computeLayout } from "./layout_engine.js";

const layout = computeLayout(spec);

export function computeLayout(slide){

  const density =
    (slide.bullets?.length || 0) +
    (slide.insight?.length || 0)/120;

  if(slide.chart_type && density > 6){
    return "chart_left_text_right";
  }

  if(slide.chart_type){
    return "chart_focus";
  }

  return "text_focus";
}

function autoFontSize(text){
  const len=text.length;

  if(len<80) return 20;
  if(len<160) return 16;
  if(len<260) return 13;
  return 11;
}
fontSize:autoFontSize(spec.insight)