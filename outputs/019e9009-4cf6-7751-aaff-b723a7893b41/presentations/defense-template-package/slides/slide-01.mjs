import { base, card, ASSETS, COLORS } from "./common.mjs";
export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  await base(slide, ctx, { slideNo: "01", footer: "Template sample - title system" });
  ctx.addShape(slide, { x: 64, y: 140, width: 820, height: 1, fill: COLORS.line, line: ctx.line() });
  ctx.addText(slide, { text: "BACHELOR THESIS DEFENSE", x: 64, y: 168, width: 540, height: 20, fontSize: 12, bold: true, color: COLORS.green });
  ctx.addText(slide, { text: "Asset Universe Selection Based on Investor Profile", x: 64, y: 210, width: 760, height: 128, fontSize: 40, bold: true, color: COLORS.navy, typeface: "Aptos Display" });
  ctx.addText(slide, { text: "Portfolio optimization using AI risk-ranking before allocation", x: 66, y: 356, width: 640, height: 34, fontSize: 21, color: COLORS.graphite });
  ctx.addShape(slide, { x: 66, y: 426, width: 164, height: 4, fill: COLORS.green, line: ctx.line() });
  ctx.addShape(slide, { x: 238, y: 426, width: 76, height: 4, fill: COLORS.gold, line: ctx.line() });
  ctx.addShape(slide, { x: 322, y: 426, width: 76, height: 4, fill: COLORS.red, line: ctx.line() });
  card(slide, ctx, 874, 188, 250, 260, COLORS.paper);
  ctx.addText(slide, { text: "risk ranking\nbefore\nallocation", x: 914, y: 235, width: 170, height: 120, fontSize: 29, bold: true, color: COLORS.navy, align: "center" });
  ctx.addText(slide, { text: "Template only. Final wording waits for reviewed script.", x: 884, y: 376, width: 230, height: 42, fontSize: 14, color: COLORS.muted, align: "center" });
  ctx.addShape(slide, { x: 64, y: 540, width: 1048, height: 1, fill: COLORS.line, line: ctx.line() });
  [
    ["Presenter", "Ali Abuelkheir"],
    ["Institution", "German University in Cairo"],
    ["Project", "ROBIN portfolio research"]
  ].forEach((item, i) => {
    const x = 66 + i * 344;
    ctx.addText(slide, { text: item[0].toUpperCase(), x, y: 562, width: 240, height: 16, fontSize: 10, bold: true, color: i === 0 ? COLORS.green : i === 1 ? COLORS.gold : COLORS.red });
    ctx.addText(slide, { text: item[1], x, y: 586, width: 310, height: 24, fontSize: 16, color: COLORS.graphite });
  });
  return slide;
}