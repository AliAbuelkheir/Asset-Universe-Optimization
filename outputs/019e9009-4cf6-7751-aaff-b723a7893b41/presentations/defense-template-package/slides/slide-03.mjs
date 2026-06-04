import { base, title, claim, COLORS } from "./common.mjs";
export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  await base(slide, ctx, { slideNo: "03", footer: "Template sample - compact finance table" });
  title(slide, ctx, "Scope and asset universe", "Table stress test");
  claim(slide, ctx, "Finance tables should sit on a grid and use whitespace as structure.", 126);
  const rows = [
    ["Asset class", "Role in the universe", "Slide treatment"],
    ["Treasury bills", "Defensive money-market exposure", "short role"],
    ["Government bonds", "Fixed-income exposure", "short role"],
    ["EGX30 / stocks", "Equity growth and benchmark context", "grouped"],
    ["Gold / REIT", "Real-asset exposure", "grouped"],
    ["USD/EGP / CPI", "Macro context inputs, not selected assets", "note"]
  ];
  const x = 96, y = 248, widths = [230, 520, 234], rh = 50;
  rows.forEach((row, r) => {
    let cx = x;
    row.forEach((cell, c) => {
      ctx.addShape(slide, { x: cx, y: y + r * rh, width: widths[c], height: rh, fill: r === 0 ? COLORS.navy : (r % 2 ? COLORS.white : COLORS.paper), line: ctx.line(COLORS.line, 1) });
      ctx.addText(slide, { text: cell, x: cx + 15, y: y + r * rh + 12, width: widths[c] - 30, height: 30, fontSize: r === 0 ? 15 : 15, bold: r === 0, color: r === 0 ? COLORS.white : COLORS.ink });
      cx += widths[c];
    });
  });
  ctx.addShape(slide, { x: 96, y: 555, width: 984, height: 34, fill: COLORS.greenSoft, line: ctx.line(COLORS.line, 1) });
  ctx.addText(slide, { text: "Speaker notes and exact labels remain WAITING_FOR_REVIEWED_SCRIPT.", x: 112, y: 563, width: 760, height: 20, fontSize: 14, bold: true, color: COLORS.green });
  return slide;
}