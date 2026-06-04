import { base, title, claim, card, bullets, ASSETS, COLORS } from "./common.mjs";
export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  await base(slide, ctx, { slideNo: "05", footer: "Template sample - long title and diagram" });
  title(slide, ctx, "Actor-critic architecture for variable active universes", "Long-title stress test");
  claim(slide, ctx, "The scorer combines asset-level rows with month-level context before PPO updates.", 126);
  card(slide, ctx, 80, 264, 640, 232, COLORS.white);
  await ctx.addImage(slide, { path: ASSETS.actorCritic, x: 104, y: 305, width: 592, height: 150, fit: "contain", alt: "Actor critic architecture screenshot" });
  ctx.addShape(slide, { x: 782, y: 264, width: 344, height: 5, fill: COLORS.green, line: ctx.line() });
  ctx.addText(slide, { text: "Use this layout when the slide needs a figure plus a short interpretation.", x: 782, y: 288, width: 342, height: 74, fontSize: 22, bold: true, color: COLORS.navy });
  bullets(slide, ctx, ["figure evidence on the left", "interpretation on the right", "talk track in notes later"], 782, 398, 312);
  return slide;
}