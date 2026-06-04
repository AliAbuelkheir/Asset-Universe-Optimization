
export const COLORS = {"white":"#FFFFFF","paper":"#F7F9FA","panel":"#EEF2F4","line":"#D8E0E5","ink":"#111820","graphite":"#27313A","muted":"#68737D","navy":"#142A3B","green":"#12864B","greenSoft":"#E7F3EC","red":"#B6121B","redSoft":"#F7E8E9","gold":"#D9A629","goldSoft":"#FBF3D8"};
export const ASSETS = {"robin":"C:\\Ali\\CS\\Bachelor thesis\\defense\\assets\\deck_template\\robin-logo.png","guc":"C:\\Ali\\CS\\Bachelor thesis\\defense\\assets\\deck_template\\guc-logo.png","rankAlignment":"C:\\Ali\\CS\\Bachelor thesis\\defense\\assets\\deck_template\\ch4-test-rank-alignment.png","methodologyPipeline":"C:\\Ali\\CS\\Bachelor thesis\\defense\\assets\\deck_template\\methodology-pipeline-page16.png","actorCritic":"C:\\Ali\\CS\\Bachelor thesis\\defense\\assets\\deck_template\\actor-critic-page22.png","bucketMapping":"C:\\Ali\\CS\\Bachelor thesis\\defense\\assets\\deck_template\\bucket-mapping-page25.png"};

export const GRID = {
  margin: 64,
  gutter: 24,
  col: 75,
  contentTop: 112,
  contentBottom: 632,
};

export async function base(slide, ctx, options = {}) {
  const C = COLORS;
  const dark = options.dark || false;
  ctx.addShape(slide, { x: 0, y: 0, width: 1280, height: 720, fill: dark ? C.navy : C.white, line: ctx.line() });
  if (!dark) {
    ctx.addShape(slide, { x: 0, y: 0, width: 1280, height: 96, fill: C.paper, line: ctx.line() });
    ctx.addShape(slide, { x: 0, y: 95, width: 1280, height: 1, fill: C.line, line: ctx.line() });
  }
  ctx.addShape(slide, { x: 0, y: 0, width: 430, height: 8, fill: C.green, line: ctx.line() });
  ctx.addShape(slide, { x: 430, y: 0, width: 175, height: 8, fill: C.gold, line: ctx.line() });
  ctx.addShape(slide, { x: 605, y: 0, width: 175, height: 8, fill: C.red, line: ctx.line() });
  ctx.addShape(slide, { x: 780, y: 0, width: 500, height: 8, fill: C.navy, line: ctx.line() });
  await ctx.addImage(slide, { path: ASSETS.robin, x: 1032, y: 26, width: 46, height: 46, fit: "contain", alt: "ROBIN logo" });
  await ctx.addImage(slide, { path: ASSETS.guc, x: 1094, y: 20, width: 116, height: 56, fit: "contain", alt: "GUC logo" });
  ctx.addText(slide, { text: options.footer || "Defense deck template package", x: 64, y: 686, width: 620, height: 18, fontSize: 12, color: dark ? C.white : C.muted });
  ctx.addText(slide, { text: String(options.slideNo || ""), x: 1136, y: 686, width: 58, height: 18, fontSize: 12, color: dark ? C.white : C.muted, align: "right" });
}

export function title(slide, ctx, text, section) {
  const C = COLORS;
  if (section) ctx.addText(slide, { text: section.toUpperCase(), x: 64, y: 30, width: 650, height: 18, fontSize: 11, color: C.green, bold: true });
  ctx.addText(slide, { text, x: 64, y: 50, width: 860, height: 40, fontSize: 26, bold: true, color: C.navy, typeface: "Aptos Display" });
}

export function claim(slide, ctx, text, y = 170) {
  const C = COLORS;
  ctx.addShape(slide, { x: 64, y, width: 8, height: 58, fill: C.green, line: ctx.line() });
  ctx.addText(slide, { text, x: 90, y: y - 1, width: 820, height: 60, fontSize: 24, bold: true, color: C.ink, typeface: "Aptos Display" });
}

export function bullets(slide, ctx, items, x, y, width) {
  const C = COLORS;
  items.forEach((item, index) => {
    const top = y + index * 52;
    ctx.addShape(slide, { x, y: top + 11, width: 9, height: 9, fill: index === 0 ? C.green : index === 1 ? C.gold : C.red, line: ctx.line() });
    ctx.addText(slide, { text: item, x: x + 24, y: top, width, height: 38, fontSize: 19, color: C.ink });
  });
}

export function metric(slide, ctx, value, label, x, y, w, color = COLORS.green) {
  const C = COLORS;
  ctx.addShape(slide, { x, y, width: w, height: 112, fill: C.white, line: ctx.line(C.line, 1) });
  ctx.addShape(slide, { x, y, width: w, height: 5, fill: color, line: ctx.line() });
  ctx.addText(slide, { text: value, x: x + 16, y: y + 18, width: w - 32, height: 38, fontSize: 31, bold: true, color });
  ctx.addText(slide, { text: label, x: x + 16, y: y + 62, width: w - 32, height: 38, fontSize: 14, color: C.muted });
}

export function card(slide, ctx, x, y, w, h, fill = COLORS.white) {
  ctx.addShape(slide, { x, y, width: w, height: h, fill, line: ctx.line(COLORS.line, 1) });
}

export function label(slide, ctx, text, x, y, color = COLORS.green) {
  ctx.addShape(slide, { x, y, width: 8, height: 8, fill: color, line: ctx.line() });
  ctx.addText(slide, { text, x: x + 18, y: y - 5, width: 260, height: 20, fontSize: 14, color: COLORS.muted });
}
