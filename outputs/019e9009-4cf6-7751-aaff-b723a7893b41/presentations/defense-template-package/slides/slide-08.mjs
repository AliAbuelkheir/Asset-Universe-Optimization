import { base, title, card, COLORS } from "./common.mjs";
export async function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  await base(slide, ctx, { slideNo: "08", footer: "Template sample - appendix dense" });
  title(slide, ctx, "Appendix backup: feature families", "Dense backup");
  const groups = [
    ["Risk / downside", "egarch_vol, downside_dev, max_drawdown, downside_tail_ratio_3m"],
    ["Liquidity", "volume"],
    ["Technical state", "atr_pct_20, price_to_sma20, rsi_14, distance_to_3m_high"],
    ["Market sensitivity", "beta_to_egx30"],
    ["Macro context", "usd_vol, cpi_trajectory"],
    ["Review gate", "WAITING_FOR_REVIEWED_SCRIPT"]
  ];
  groups.forEach((g, i) => {
    const x = 80 + (i % 2) * 520;
    const y = 142 + Math.floor(i / 2) * 118;
    const accent = i % 3 === 0 ? COLORS.green : i % 3 === 1 ? COLORS.gold : COLORS.red;
    card(slide, ctx, x, y, 450, 86, i === 5 ? COLORS.paper : COLORS.white);
    ctx.addShape(slide, { x, y, width: 5, height: 86, fill: accent, line: ctx.line() });
    ctx.addText(slide, { text: g[0], x: x + 20, y: y + 13, width: 410, height: 22, fontSize: 18, bold: true, color: COLORS.navy });
    ctx.addText(slide, { text: g[1], x: x + 20, y: y + 42, width: 410, height: 30, fontSize: 14, color: COLORS.muted });
  });
  ctx.addText(slide, { text: "Appendix slides may be denser, but still use grouped meaning instead of log-dump prose.", x: 82, y: 560, width: 840, height: 24, fontSize: 16, color: COLORS.green, bold: true });
  return slide;
}