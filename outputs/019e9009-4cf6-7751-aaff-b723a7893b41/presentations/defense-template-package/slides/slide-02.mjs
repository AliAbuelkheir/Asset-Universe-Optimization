import { base, title, card, COLORS } from "./common.mjs";
export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  await base(slide, ctx, { slideNo: "02", footer: "Template sample - roadmap" });
  title(slide, ctx, "Talk roadmap", "Navigation");
  const items = [
    ["01", "Problem", "Why profile-based universe selection matters"],
    ["02", "Gap", "What existing portfolio selection misses"],
    ["03", "Design", "How ranking becomes pre-allocation filtering"],
    ["04", "Method", "Data, environment, PPO setup"],
    ["05", "Results", "Risk separation and diagnostics"],
    ["06", "Close", "Research claims and limitations"]
  ];
  items.forEach((item, i) => {
    const x = 64 + (i % 3) * 392;
    const y = 154 + Math.floor(i / 3) * 176;
    card(slide, ctx, x, y, 336, 122, i === 3 ? COLORS.greenSoft : COLORS.white);
    ctx.addShape(slide, { x, y, width: 336, height: 5, fill: i % 3 === 0 ? COLORS.green : i % 3 === 1 ? COLORS.gold : COLORS.red, line: ctx.line() });
    ctx.addText(slide, { text: item[0], x: x + 22, y: y + 26, width: 52, height: 36, fontSize: 24, bold: true, color: COLORS.navy });
    ctx.addText(slide, { text: item[1], x: x + 90, y: y + 24, width: 230, height: 30, fontSize: 22, bold: true, color: COLORS.ink });
    ctx.addText(slide, { text: item[2], x: x + 90, y: y + 58, width: 238, height: 42, fontSize: 14, color: COLORS.muted });
  });
  return slide;
}