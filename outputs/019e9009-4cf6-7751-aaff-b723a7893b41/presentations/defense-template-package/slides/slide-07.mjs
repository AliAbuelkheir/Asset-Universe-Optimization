import { base, title, COLORS } from "./common.mjs";
export async function slide07(presentation, ctx) {
  const slide = presentation.slides.add();
  await base(slide, ctx, { slideNo: "07", footer: "Template sample - references" });
  title(slide, ctx, "Key references", "Five-reference limit");
  const refs = [
    "Markowitz (1952), Portfolio Selection",
    "Wang et al. (2020), Portfolio Formation with Preselection Using Deep Learning",
    "Ma et al. (2021), Portfolio Optimization with Return Prediction",
    "Chaweewanchon and Chaysiri (2022), Markowitz MVO with Predictive Selection",
    "Atta Mills and Anyomi (2022), Hybrid Two-Stage Robustness Approach"
  ];
  refs.forEach((ref, i) => {
    const y = 150 + i * 84;
    ctx.addShape(slide, { x: 96, y, width: 28, height: 28, fill: i % 2 ? COLORS.goldSoft : COLORS.greenSoft, line: ctx.line(COLORS.line, 1) });
    ctx.addText(slide, { text: String(i + 1), x: 96, y: y + 6, width: 28, height: 18, fontSize: 13, bold: true, color: i % 2 ? COLORS.gold : COLORS.green, align: "center" });
    ctx.addText(slide, { text: ref, x: 154, y: y + 2, width: 850, height: 34, fontSize: 20, color: COLORS.ink });
    ctx.addShape(slide, { x: 154, y: y + 50, width: 850, height: 1, fill: COLORS.line, line: ctx.line() });
  });
  return slide;
}