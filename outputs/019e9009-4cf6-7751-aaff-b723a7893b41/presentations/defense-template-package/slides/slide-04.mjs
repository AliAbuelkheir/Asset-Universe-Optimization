import { base, title, card, ASSETS, COLORS, label } from "./common.mjs";
export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  await base(slide, ctx, { slideNo: "04", footer: "Template sample - thesis figure screenshot" });
  title(slide, ctx, "Contribution in one view", "Figure framing");
  ctx.addText(slide, { text: "The contribution slide should read as one evidence-led pipeline, not as a crowded explanation.", x: 64, y: 126, width: 840, height: 60, fontSize: 25, bold: true, color: COLORS.ink, typeface: "Aptos Display" });
  label(slide, ctx, "Data engineering", 96, 218, COLORS.green);
  label(slide, ctx, "Monthly ranking", 430, 218, COLORS.gold);
  label(slide, ctx, "Profile filtering", 746, 218, COLORS.red);
  card(slide, ctx, 88, 270, 1032, 238, COLORS.white);
  await ctx.addImage(slide, { path: ASSETS.methodologyPipeline, x: 118, y: 318, width: 972, height: 146, fit: "contain", alt: "Methodology pipeline screenshot" });
  ctx.addText(slide, { text: "Source crop: thesis methodology Figure 3.1", x: 104, y: 525, width: 420, height: 18, fontSize: 12, color: COLORS.muted });
  ctx.addShape(slide, { x: 848, y: 522, width: 272, height: 34, fill: COLORS.paper, line: ctx.line(COLORS.line, 1) });
  ctx.addText(slide, { text: "No final notes injected", x: 870, y: 531, width: 226, height: 18, fontSize: 13, bold: true, color: COLORS.graphite, align: "center" });
  return slide;
}