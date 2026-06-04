import fs from "node:fs/promises";
import fsSync from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const SLIDES_DIR = path.join(ROOT, "defense", "slides");
const DEFENSE_ASSETS_DIR = path.join(ROOT, "defense", "assets", "deck_template");
const TOPIC_MAP = path.join(ROOT, "defense", "documents", "topic_slide_map.md");
const RUNTIME_NODE = "C:\\Users\\aliab\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe";
const RUNTIME_PYTHON = "C:\\Users\\aliab\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";
const SKILL_DIR = "C:\\Users\\aliab\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.601.10930\\skills\\presentations";
const THREAD_ID = process.env.CODEX_THREAD_ID || "manual-2026-06-04-defense-template";
const WORKSPACE = path.join(ROOT, "outputs", THREAD_ID, "presentations", "defense-template-package");
const WORKSPACE_SLIDES = path.join(WORKSPACE, "slides");
const WORKSPACE_PREVIEW = path.join(WORKSPACE, "preview");
const WORKSPACE_LAYOUT = path.join(WORKSPACE, "layout");
const WORKSPACE_QA = path.join(WORKSPACE, "qa");
const FINAL_PPTX = path.join(SLIDES_DIR, "defense_deck_template_samples.pptx");
const FINAL_PREVIEWS = path.join(SLIDES_DIR, "template_sample_previews");

const C = {
  white: "#FFFFFF",
  paper: "#F7F9FA",
  panel: "#EEF2F4",
  line: "#D8E0E5",
  ink: "#111820",
  graphite: "#27313A",
  muted: "#68737D",
  navy: "#142A3B",
  green: "#12864B",
  greenSoft: "#E7F3EC",
  red: "#B6121B",
  redSoft: "#F7E8E9",
  gold: "#D9A629",
  goldSoft: "#FBF3D8",
};

const assets = {
  robin: path.join(DEFENSE_ASSETS_DIR, "robin-logo.png"),
  guc: path.join(DEFENSE_ASSETS_DIR, "guc-logo.png"),
  rankAlignment: path.join(DEFENSE_ASSETS_DIR, "ch4-test-rank-alignment.png"),
  methodologyPipeline: path.join(DEFENSE_ASSETS_DIR, "methodology-pipeline-page16.png"),
  actorCritic: path.join(DEFENSE_ASSETS_DIR, "actor-critic-page22.png"),
  bucketMapping: path.join(DEFENSE_ASSETS_DIR, "bucket-mapping-page25.png"),
};

async function ensureDirs() {
  await fs.mkdir(DEFENSE_ASSETS_DIR, { recursive: true });
  await fs.mkdir(SLIDES_DIR, { recursive: true });
  await fs.mkdir(FINAL_PREVIEWS, { recursive: true });
  await fs.mkdir(WORKSPACE_SLIDES, { recursive: true });
  await fs.mkdir(WORKSPACE_PREVIEW, { recursive: true });
  await fs.mkdir(WORKSPACE_LAYOUT, { recursive: true });
  await fs.mkdir(WORKSPACE_QA, { recursive: true });
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, HOME: "C:\\Users\\aliab", ...options.env },
    timeout: options.timeout ?? 120000,
    maxBuffer: 10 * 1024 * 1024,
  });
  if (result.status !== 0) {
    throw new Error([
      `Command failed: ${command} ${args.join(" ")}`,
      result.error ? String(result.error) : "",
      result.stdout?.trim(),
      result.stderr?.trim(),
    ].filter(Boolean).join("\n"));
  }
  return result;
}

async function prepareAssets() {
  const sourceRobin = path.join(ROOT, "portfolio-simulator", "client", "public", "robin-logo.png");
  const sourceRank = path.join(ROOT, "thesis", "Bachelor Thesis Template", "images", "ch4_test_rank_alignment.png");
  await fs.copyFile(sourceRobin, assets.robin);
  await fs.copyFile(sourceRank, assets.rankAlignment);

  const derivedAssets = [
    assets.guc,
    assets.methodologyPipeline,
    assets.actorCritic,
    assets.bucketMapping,
  ];
  if (derivedAssets.every((assetPath) => fsSync.existsSync(assetPath))) {
    return;
  }

  const cropScript = String.raw`
from PIL import Image, ImageChops
import pathlib

root = pathlib.Path(r"${ROOT}")
out = pathlib.Path(r"${DEFENSE_ASSETS_DIR}")

def crop_white(src, dst, pad=16):
    img = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(img, bg).convert("L")
    bbox = diff.getbbox()
    if bbox:
        l, t, r, b = bbox
        l = max(0, l - pad); t = max(0, t - pad); r = min(img.width, r + pad); b = min(img.height, b + pad)
        img = img.crop((l, t, r, b))
    img.save(dst)

def render_page(page, name, crop):
    src = out / f"tmp-{name}-{page}.png"
    if not src.exists():
        raise FileNotFoundError(f"Missing pre-rendered source page PNG: {src}")
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    l, t, r, b = crop
    img.crop((int(w*l), int(h*t), int(w*r), int(h*b))).save(out / f"{name}.png")

crop_white(out / "tmp-guc.png", out / "guc-logo.png", 12)

render_page(16, "methodology-pipeline-page16", (0.11, 0.31, 0.96, 0.405))
render_page(22, "actor-critic-page22", (0.12, 0.43, 0.88, 0.58))
render_page(25, "bucket-mapping-page25", (0.12, 0.55, 0.88, 0.69))
`;
  run(RUNTIME_PYTHON, ["-c", cropScript], { timeout: 180000 });
}

function parseTopicMap(text) {
  const lines = text.split(/\r?\n/);
  const slides = [];
  let currentSection = "";
  for (const line of lines) {
    const section = line.match(/^##\s+\d+\.\s+(.+)$/);
    if (section) currentSection = section[1].trim();
    const slide = line.match(/^###\s+(Slide\s+\d+|Appendix\s+[A-Z])\s+-\s+(.+)$/);
    if (slide) {
      slides.push({
        id: slide[1],
        title: slide[2].trim(),
        section: currentSection || "Appendix Candidates",
      });
    }
  }
  return slides;
}

function chooseLayout(slide) {
  const id = slide.id;
  const title = slide.title.toLowerCase();
  if (id === "Slide 1") return "title";
  if (title.includes("roadmap")) return "roadmap";
  if (title.includes("references")) return "references";
  if (id.startsWith("Appendix")) return "appendix-dense";
  if (title.includes("scope") || title.includes("split") || title.includes("framework") || title.includes("feature") || title.includes("baseline")) return "table";
  if (title.includes("ranking quality") || title.includes("risk separation") || title.includes("economic")) return "result-callout";
  if (title.includes("pipeline") || title.includes("episode") || title.includes("masking") || title.includes("architecture") || title.includes("bucket") || title.includes("logic")) return "screenshot";
  return "claim-plus-visual";
}

function visualNeed(slide) {
  const title = slide.title.toLowerCase();
  if (slide.id === "Slide 5") return ["compact asset-universe table", "missing native table data finalization"];
  if (slide.id === "Slide 11") return ["methodology pipeline screenshot", assets.methodologyPipeline];
  if (slide.id === "Slide 19") return ["PPO episode tensor/mask figure", "MISSING: create or crop after final script structure is locked"];
  if (slide.id === "Slide 21") return ["actor-critic architecture screenshot", assets.actorCritic];
  if (slide.id === "Slide 23") return ["bucket mapping screenshot", assets.bucketMapping];
  if (slide.id === "Slide 28") return ["ranking quality metrics", "MISSING: final metric callout/table source"];
  if (slide.id === "Slide 29") return ["risk-bucket separation metrics", "MISSING: final result callout/table source"];
  if (slide.id === "Slide 30") return ["economic diagnostic metrics", "MISSING: final result callout/table source"];
  if (title.includes("references")) return ["five-reference list", "topic_slide_map.md"];
  if (slide.id.startsWith("Appendix")) return ["backup table or Q&A block", "WAITING_FOR_REVIEWED_SCRIPT"];
  return ["supporting icon/table/figure chosen during final deck pass", "WAITING_FOR_REVIEWED_SCRIPT"];
}

function riskLevel(slide) {
  const title = slide.title.toLowerCase();
  if (["Slide 16", "Slide 17", "Slide 18", "Slide 19", "Slide 20", "Slide 21", "Slide 22", "Slide 23", "Slide 28", "Slide 29", "Slide 30", "Slide 31"].includes(slide.id)) return "High";
  if (title.includes("literature") || title.includes("scope") || title.includes("questions") || slide.id.startsWith("Appendix")) return "Medium";
  return "Low";
}

async function writeFinalDocs(slides) {
  const designSystem = `# Defense Deck Template Design System

Status: template package, not final deck.

## Locked Visual Rules

- Format: 16:9 PowerPoint, 1280 x 720 render target.
- Style: quiet academic defense system with a symmetrical 12-column grid, cool white/gray surfaces, graphite text, and restrained accent bars.
- Palette: ROBIN green, GUC red, GUC gold, deep navy, graphite, white, and cool gray. No dominant gradients, blobs, or single-hue green wash.
- Logo chrome: ROBIN and GUC colored logos grouped in the top-right corner, ordered ROBIN then GUC, inside a fixed logo-safe area.
- Slide text: one visible claim line plus at most three short bullets on normal slides.
- Speaker notes: no final notes are injected from the current draft script; notes wait for the reviewed script.
- Figures: use high-resolution screenshots/crops and consistent white evidence frames with thin borders.
- Transitions: use subtle fade in PowerPoint when assembling the final full deck.

## Layout Set

| Layout | Use |
| --- | --- |
| Title | Opening slide with thesis title and identity chrome. |
| Roadmap | Talk structure and section navigation. |
| Section divider | Major chapter transitions. |
| Claim + visual | Standard slide with one claim, short bullets, and a proof object. |
| Table | Scope, splits, framework, feature, and baseline slides. |
| Screenshot | Thesis figure or result plot framed as visual evidence. |
| Result callout | Ranking quality, bucket separation, and economic diagnostics. |
| References | Five core references only. |
| Appendix dense | Backup slide with smaller but still readable information. |

## Quality Gates

- Minimum edge margin: 64 px; title/logos must not collide.
- Logo-safe zone: x >= 1016 px and y <= 88 px on normal slides.
- Normal body text target: 21-28 px; dense appendix minimum: 16 px.
- Every sample slide must include a proof object: table, screenshot, metric stack, or structured visual.
- Screenshot crops must avoid visible PDF page margins and blurry text.
- Layouts must feel horizontally balanced: no orphaned tiny panels, no accidental empty halves.
- No final script wording should be rewritten in this package.
`;

  const inventory = `# Defense Deck Visual And Asset Inventory

Status: prepared for template/sample deck; final deck assets remain open until the reviewed script is complete.

## Normalized Assets

| Asset | Prepared path | Source | Use |
| --- | --- | --- | --- |
| ROBIN logo | \`defense/assets/deck_template/robin-logo.png\` | \`portfolio-simulator/client/public/robin-logo.png\` | Top-right logo group. |
| GUC logo | \`defense/assets/deck_template/guc-logo.png\` | \`defense/assets/The_German_University_in_Cairo_Official_logo.jpg\` | Top-right logo group. |
| Test rank alignment plot | \`defense/assets/deck_template/ch4-test-rank-alignment.png\` | \`thesis/Bachelor Thesis Template/images/ch4_test_rank_alignment.png\` | Result/screenshot sample and possible Slide 28 support. |
| Methodology pipeline screenshot | \`defense/assets/deck_template/methodology-pipeline-page16.png\` | Page 16 of \`thesis/Bachelor Thesis Template/bachelor.pdf\` | Slide 11 and sample screenshot layout. |
| Actor-critic screenshot | \`defense/assets/deck_template/actor-critic-page22.png\` | Page 22 of \`thesis/Bachelor Thesis Template/bachelor.pdf\` | Slide 21 and sample screenshot layout. |
| Bucket mapping screenshot | \`defense/assets/deck_template/bucket-mapping-page25.png\` | Page 25 of \`thesis/Bachelor Thesis Template/bachelor.pdf\` | Slide 23 and possible appendix support. |

## Screenshot Rules

- Render/crop from thesis PDF at 220 dpi or higher.
- Crop to the figure/table only; avoid full-page margins.
- Use a white figure card with thin border inside the slide.
- Keep source captions out of the crop when the slide title already names the visual.
- If a crop is not readable at 16:9 slide size, replace it with a larger crop or split it across a backup slide.

## Missing Or Waiting Assets

- Slide 19 PPO episode tensor/mask visual: create or crop after the script structure is final.
- Slide 24 chronological split design: can be a native table, no screenshot required.
- Slides 28-31 result visuals: final metrics should be checked against the reviewed script before full deck generation.
- Speaker notes for all slides: \`WAITING_FOR_REVIEWED_SCRIPT\`.
`;

  const rows = slides.map((slide) => {
    const [need, source] = visualNeed(slide);
    return `| ${slide.id} | ${slide.title} | ${slide.section} | ${chooseLayout(slide)} | WAITING_FOR_REVIEWED_SCRIPT | ${need} | ${String(source).replaceAll("\\", "/")} | WAITING_FOR_REVIEWED_SCRIPT | ${riskLevel(slide)} |`;
  }).join("\n");
  const spec = `# Defense Slide Spec Scaffold

Status: scaffold only. It uses the current topic slide map as temporary structure and does not treat the current script as final.

| Slide | Title | Section | Intended layout | Visible claim | Visual / figure need | Source asset if known | Speaker-note status | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
${rows}
`;

  await fs.writeFile(path.join(SLIDES_DIR, "template_design_system.md"), designSystem, "utf8");
  await fs.writeFile(path.join(SLIDES_DIR, "visual_asset_inventory.md"), inventory, "utf8");
  await fs.writeFile(path.join(SLIDES_DIR, "slide_spec_scaffold.md"), spec, "utf8");
  const qaReport = `# Defense Deck Template QA Report

Status: redesigned sample template after visual rejection of the earlier pass.

## Rendered Artifacts

- PPTX: \`defense/slides/defense_deck_template_samples.pptx\`
- Preview images: \`defense/slides/template_sample_previews/slide-01.png\` through \`slide-08.png\`
- Contact sheet: \`defense/slides/template_sample_previews/contact-sheet.svg\`
- Generator: \`defense/slides/build_defense_template_package.mjs\`

## QA Checks Performed

- Rendered all 8 sample slides to PNG previews.
- Inspected title, roadmap, table, thesis figure, long-title diagram, metrics, references, and appendix layouts.
- Checked logo-safe zone, title wrapping, visual balance, table readability, metric alignment, and screenshot crop quality.

## Fixes From First Redesigned Render

- Replaced green-heavy old style with a controlled ROBIN/GUC/navy/graphite palette.
- Added a fixed top identity ribbon and consistent top-right logo group.
- Added a bottom metadata band to the title slide to remove dead lower space.
- Tightened result slide vertical rhythm and metric alignment.
- Cropped the actor-critic screenshot to remove the clipped thesis caption.
- Enlarged the actor-critic evidence area so the screenshot reads as evidence, not decoration.

## Remaining Intentional Limits

- Sample slide copy is representative only; final visible claims and speaker notes are \`WAITING_FOR_REVIEWED_SCRIPT\`.
- Result values are sample stress-test values and must be checked against the reviewed script before final deck generation.
- Figure crops are slide-ready examples; final deck may still need slide-specific crops once the reviewed script locks each figure.
`;
  await fs.writeFile(path.join(SLIDES_DIR, "template_qa_report.md"), qaReport, "utf8");

  const profilePlan = `task mode: create
primary deck-profile: engineering-platform
secondary gates: finance-ir for exact metrics and thesis-safe historical diagnostic wording
required proof objects: logo chrome, asset table, thesis figure screenshots, result callouts, reference list, appendix dense backup
source/asset requirements: only use existing ROBIN/GUC logos and thesis figure/result assets; do not invent identity marks
qa gates: render full sample PPTX, inspect contact sheet, fix at least one issue, rerender
known missing inputs: final reviewed script and final speaker notes
`;
  await fs.writeFile(path.join(WORKSPACE, "profile-plan.txt"), profilePlan, "utf8");
  await fs.writeFile(path.join(WORKSPACE, "source-notes.txt"), inventory, "utf8");
}

function commonModuleSource() {
  return `
export const COLORS = ${JSON.stringify(C)};
export const ASSETS = ${JSON.stringify(assets)};

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
`;
}

const slideModules = [
  `import { base, card, ASSETS, COLORS } from "./common.mjs";
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
  ctx.addText(slide, { text: "risk ranking\\nbefore\\nallocation", x: 914, y: 235, width: 170, height: 120, fontSize: 29, bold: true, color: COLORS.navy, align: "center" });
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
}`,
  `import { base, title, card, COLORS } from "./common.mjs";
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
}`,
  `import { base, title, claim, COLORS } from "./common.mjs";
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
}`,
  `import { base, title, card, ASSETS, COLORS, label } from "./common.mjs";
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
}`,
  `import { base, title, claim, card, bullets, ASSETS, COLORS } from "./common.mjs";
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
}`,
  `import { base, title, claim, metric, COLORS } from "./common.mjs";
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
}`,
  `import { base, title, COLORS } from "./common.mjs";
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
}`,
  `import { base, title, card, COLORS } from "./common.mjs";
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
}`
];

async function writeSlideModules() {
  await fs.writeFile(path.join(WORKSPACE_SLIDES, "common.mjs"), commonModuleSource(), "utf8");
  for (let i = 0; i < slideModules.length; i += 1) {
    await fs.writeFile(path.join(WORKSPACE_SLIDES, `slide-${String(i + 1).padStart(2, "0")}.mjs`), slideModules[i], "utf8");
  }
}

async function blobToBuffer(blob) {
  return Buffer.from(await blob.arrayBuffer());
}

async function buildDeck() {
  const utils = await import(pathToFileURL(path.join(SKILL_DIR, "scripts", "artifact_tool_utils.mjs")).href);
  const {
    createSlideContext,
    ensureArtifactToolWorkspace,
    importArtifactTool,
    importModuleFresh,
    resolveSlideFunction,
    saveBlobToFile,
  } = utils;

  await ensureArtifactToolWorkspace(WORKSPACE);
  const artifact = await importArtifactTool(WORKSPACE);
  const { Presentation, PresentationFile } = artifact;
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  const slideRecords = [];

  for (let i = 1; i <= slideModules.length; i += 1) {
    const slideModule = path.join(WORKSPACE_SLIDES, `slide-${String(i).padStart(2, "0")}.mjs`);
    const mod = await importModuleFresh(slideModule);
    const { name: exportName, fn } = resolveSlideFunction(mod, undefined, i);
    const ctx = createSlideContext(artifact, {
      slideSize: { width: 1280, height: 720 },
      slideNumber: i,
      outputDir: SLIDES_DIR,
      assetDir: DEFENSE_ASSETS_DIR,
      workspaceDir: WORKSPACE,
    });
    const beforeCount = presentation.slides.count;
    const returnedSlide = await fn(presentation, ctx);
    if (presentation.slides.count !== beforeCount + 1) {
      throw new Error(`${path.basename(slideModule)} must add exactly one slide.`);
    }
    const slide = returnedSlide || presentation.slides.getItem(presentation.slides.count - 1);
    slideRecords.push({ slideNumber: i, modulePath: slideModule, exportName, slide });
  }

  const finalLayoutDir = path.join(WORKSPACE_LAYOUT, "final");
  await fs.mkdir(finalLayoutDir, { recursive: true });
  const previewPaths = [];
  const layoutResults = [];
  for (const record of slideRecords) {
    const number = String(record.slideNumber).padStart(2, "0");
    const previewPath = path.join(WORKSPACE_PREVIEW, `slide-${number}.png`);
    const preview = await presentation.export({ slide: record.slide, format: "png", scale: 2 });
    await saveBlobToFile(preview, previewPath);
    previewPaths.push(previewPath);
    try {
      const layoutBlob = await presentation.export({ slide: record.slide, format: "layout" });
      const layoutPath = path.join(finalLayoutDir, `slide-${number}.layout.json`);
      await fs.writeFile(layoutPath, await layoutBlob.text(), "utf8");
      layoutResults.push({ layoutPath });
    } catch (error) {
      layoutResults.push({ layoutError: error.message || String(error) });
    }
  }

  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(FINAL_PPTX);
  const manifest = {
    output: FINAL_PPTX,
    outputBytes: (await fs.stat(FINAL_PPTX)).size,
    slideCount: presentation.slides.count,
    slideSize: { width: 1280, height: 720 },
    previewDir: WORKSPACE_PREVIEW,
    previewPaths,
    layoutDir: finalLayoutDir,
    layoutResults,
    slides: slideRecords.map((record) => ({
      index: record.slideNumber,
      requestedSlideNumber: record.slideNumber,
      modulePath: record.modulePath,
      exportName: record.exportName,
    })),
  };
  await fs.writeFile(path.join(WORKSPACE, "artifact-build-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
}

async function makeContactSheet() {
  const files = (await fs.readdir(WORKSPACE_PREVIEW))
    .filter((file) => /^slide-\d+\.png$/.test(file))
    .sort();
  if (files.length === 0) throw new Error("No preview PNGs found");
  const thumbW = 360;
  const thumbH = 203;
  const margin = 24;
  const gap = 18;
  const cols = 2;
  const rows = Math.ceil(files.length / cols);
  const width = margin * 2 + cols * thumbW + (cols - 1) * gap;
  const height = margin * 2 + rows * (thumbH + 30) + (rows - 1) * gap;
  const items = files.map((file, index) => {
    const x = margin + (index % cols) * (thumbW + gap);
    const y = margin + Math.floor(index / cols) * (thumbH + 30 + gap);
    return [
      `<image href="${file}" x="${x}" y="${y}" width="${thumbW}" height="${thumbH}" preserveAspectRatio="xMidYMid meet"/>`,
      `<rect x="${x}" y="${y}" width="${thumbW}" height="${thumbH}" fill="none" stroke="#D2DAE1" stroke-width="1"/>`,
      `<text x="${x}" y="${y + thumbH + 20}" font-family="Aptos, Arial" font-size="14" fill="#505A64">${file.replace(".png", "")}</text>`,
    ].join("\n");
  }).join("\n");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
<rect width="100%" height="100%" fill="#FFFFFF"/>
${items}
</svg>
`;
  await fs.writeFile(path.join(WORKSPACE_PREVIEW, "contact-sheet.svg"), svg, "utf8");
}

async function copyPreviews() {
  const files = await fs.readdir(WORKSPACE_PREVIEW);
  for (const file of files) {
    if (file.endsWith(".png") || file.endsWith(".svg")) {
      await fs.copyFile(path.join(WORKSPACE_PREVIEW, file), path.join(FINAL_PREVIEWS, file));
    }
  }
}

async function main() {
  await ensureDirs();
  await prepareAssets();
  const topic = await fs.readFile(TOPIC_MAP, "utf8");
  const slides = parseTopicMap(topic);
  await writeFinalDocs(slides);
  await writeSlideModules();
  await buildDeck();
  await makeContactSheet();
  await copyPreviews();
  await fs.writeFile(path.join(WORKSPACE_QA, "first-pass-notes.txt"), "Rendered sample deck for visual QA. Manual inspection/fix pass pending.\n", "utf8");
  console.log(JSON.stringify({
    finalPptx: FINAL_PPTX,
    previews: FINAL_PREVIEWS,
    assetDir: DEFENSE_ASSETS_DIR,
    workspace: WORKSPACE,
    slideCount: 8,
  }, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
