import { base, title, claim, metric, COLORS } from "./common.mjs";
export async function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  await base(slide, ctx, { slideNo: "06", footer: "Template sample - result metrics" });
  title(slide, ctx, "Profile-universe risk separation", "Metric callout");
  claim(slide, ctx, "The result slide should show bucket separation before any return discussion.", 126);
  const y = 258;
  metric(slide, ctx, "0.239", "Low-risk bucket mean realized risk", 96, y, 238, COLORS.green);
  metric(slide, ctx, "0.536", "Medium bucket mean realized risk", 360, y, 238, COLORS.navy);
  metric(slide, ctx, "0.688", "High-risk bucket mean realized risk", 624, y, 238, COLORS.red);
  metric(slide, ctx, "11/11", "Monthly monotonicity on test", 888, y, 190, COLORS.gold);
  ctx.addShape(slide, { x: 96, y: 474, width: 984, height: 20, fill: COLORS.panel, line: ctx.line() });
  ctx.addShape(slide, { x: 96, y: 474, width: 314, height: 20, fill: COLORS.green, line: ctx.line() });
  ctx.addShape(slide, { x: 410, y: 474, width: 322, height: 20, fill: COLORS.navy, line: ctx.line() });
  ctx.addShape(slide, { x: 732, y: 474, width: 348, height: 20, fill: COLORS.red, line: ctx.line() });
  ctx.addText(slide, { text: "Low", x: 96, y: 508, width: 90, height: 18, fontSize: 14, color: COLORS.muted });
  ctx.addText(slide, { text: "Medium", x: 580, y: 508, width: 110, height: 18, fontSize: 14, color: COLORS.muted, align: "center" });
  ctx.addText(slide, { text: "High", x: 990, y: 508, width: 80, height: 18, fontSize: 14, color: COLORS.muted, align: "right" });
  return slide;
}