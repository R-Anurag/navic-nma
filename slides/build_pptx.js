// Builds slides/navic-nma.pptx from results/*.csv. Charts are native PowerPoint charts.
// Run: NODE_PATH=<dir with pptxgenjs> node slides/build_pptx.js [path/to/apply_theme.js]
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const OUT = path.join(__dirname, "navic-nma.pptx");

const THEME = {
  name: "NavIC NMA",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "13212C", lt1: "FFFFFF", dk2: "566977", lt2: "EAF0F3",
    accent1: "A3146F", accent2: "EB6834", accent3: "2A78D6", accent4: "1BAF7A",
    accent5: "B42323", accent6: "16794A", hlink: "2A78D6", folHlink: "A3146F",
  },
};
const HEX = { ink: "13212C", muted: "566977", bg: "EAF0F3", line: "C8D4DC", panel: "FBFCFD",
  naive: "EB6834", tesla: "2A78D6", hardened: "1BAF7A", accent: "A3146F", grid: "D9E1E7" };

// ---------- data ----------
function csv(name) {
  const [head, ...rows] = fs.readFileSync(path.join(ROOT, "results", name), "utf8").trim().split("\n");
  const keys = head.split(",");
  return rows.map((r) => Object.fromEntries(r.split(",").map((v, i) => [keys[i], v])));
}
const M = csv("attack_matrix.csv");
const P = Object.fromEntries(csv("performance.csv").map((r) => [r.metric, r.value]));
const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
const fooled = (attack, sev, mode) =>
  Math.round(100 * mean(M.filter((r) => r.attack === attack && +r.severity === sev && r.mode === mode).map((r) => +r.fooled_frac)));
const sevs = (attack) => [...new Set(M.filter((r) => r.attack === attack).map((r) => +r.severity))].sort((a, b) => a - b);
const MODES = [["naive", "Naive receiver"], ["tesla", "TESLA only"], ["hardened", "Hardened (ours)"]];

// ---------- deck ----------
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.author = "Anurag Rai";
pres.title = "A NavIC receiver that refuses spoofed positions";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.333, X0 = 0.6, CW = W - 2 * X0;

pres.defineSlideMaster({
  title: "Dark title",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: X0, y: 1.6, w: CW, h: 0.4, fontSize: 14, bold: true, color: "E36BBD", charSpacing: 2, valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 2.1, w: 10.5, h: 2.2, fontSize: 48, bold: true, color: C.background2, valign: "top", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: X0, y: 4.5, w: 10, h: 1.6, fontSize: 22, color: "B8C6D0", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Content",
  background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: X0, y: 0.45, w: CW, h: 0.35, fontSize: 13, bold: true, color: C.accent1, charSpacing: 2, valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: X0, y: 0.82, w: CW, h: 1.05, fontSize: 30, bold: true, color: C.text1, valign: "top", align: "left", margin: 0 }, text: "" } },
    { text: { text: "NavIC spoofing-resistant receiver · simulation only", options: { x: X0, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: C.text2, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: HEX.muted, align: "right" },
});

let section = "";
function slide(kind, kicker, title, sectionTitle) {
  if (sectionTitle !== section) { pres.addSection({ title: sectionTitle }); section = sectionTitle; }
  const s = pres.addSlide({ masterName: kind, sectionTitle });
  if (kicker) s.addText(kicker.toUpperCase(), { placeholder: "kicker" });
  if (title) s.addText(title, { placeholder: "title" });
  return s;
}
function card(s, x, y, w, h, name) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: HEX.line, width: 1 }, objectName: name });
}
function text(s, t, o) { s.addText(t, { isTextBox: true, margin: 0, valign: "top", color: C.text1, fontSize: 16, ...o }); }
function bullets(s, items, o) {
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
    { isTextBox: true, margin: 0, valign: "top", fontSize: 18, color: C.text1, paraSpaceAfter: 10, ...o });
}
function stat(s, x, y, w, h, num, unit, label, name) {
  card(s, x, y, w, h, name);
  s.addText([{ text: num, options: { fontSize: 54, bold: true, color: C.text1 } }, { text: unit ? " " + unit : "", options: { fontSize: 20, color: C.text2 } }],
    { isTextBox: true, x: x + 0.3, y: y + 0.3, w: w - 0.6, h: 1.0, margin: 0, valign: "top", fontFace: THEME.headFontFace });
  text(s, label, { x: x + 0.3, y: y + 1.4, w: w - 0.6, h: h - 1.6, fontSize: 16, color: C.text2 });
}
const chartStyle = (title, yTitle) => ({
  showTitle: true, title, titleFontSize: 14, titleColor: HEX.ink, titleFontFace: "+mn-lt",
  chartColors: [HEX.naive, HEX.tesla, HEX.hardened],
  showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: "+mn-lt", legendColor: HEX.ink,
  catAxisLabelColor: HEX.muted, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25,
  valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" },
  showValAxisTitle: true, valAxisTitle: yTitle, valAxisTitleFontSize: 11, valAxisTitleColor: HEX.muted, valAxisTitleFontFace: "+mn-lt",
  showCatAxisTitle: true, catAxisTitleFontSize: 11, catAxisTitleColor: HEX.muted, catAxisTitleFontFace: "+mn-lt",
});
function lineChart(s, attack, x, y, w, h, title, xTitle, modes = MODES) {
  const xs = sevs(attack);
  const data = modes.map(([m, name]) => ({ name, labels: xs.map(String), values: xs.map((v) => fooled(attack, v, m)) }));
  s.addChart(pres.charts.LINE, data, {
    x, y, w, h, ...chartStyle(title, "Time fooled (%)"), catAxisTitle: xTitle,
    chartColors: modes.map(([m]) => HEX[m]), lineSize: 2.5, lineDataSymbol: "circle", lineDataSymbolSize: 8,
    objectName: `${attack} chart`,
  });
}

// 1 ----- title
let s = slide("Dark title", "INS CCA · Network and Information Security", "A NavIC receiver that refuses spoofed positions", "Introduction");
s.addText("Two TESLA authentication schemes, signed internet time, and a replay check. Tested against eight attacks in simulation.", { placeholder: "body" });
text(s, "Anurag Rai · November 2026 · simulation only, no radio transmission", { x: X0, y: 6.3, w: 10, h: 0.4, fontSize: 16, color: "B8C6D0" });
s.addNotes("Introduce the problem in one line: aircraft near Delhi were shown false positions. This project builds a receiver that refuses them.");

// 2 ----- incident
s = slide("Content", "The incident", "Delhi, November 2025: a week of GPS spoofing", "The problem");
stat(s, X0, 2.2, 3.85, 2.9, "7", "", "flights diverted to Jaipur in one night after airlines reported spoofed positions near IGI airport", "Stat diversions");
stat(s, X0 + 4.1, 2.2, 3.85, 2.9, "465", "", "interference and spoofing incidents in India's border regions, Nov 2023 to Feb 2025", "Stat incidents");
stat(s, X0 + 8.2, 2.2, 3.85, 2.9, "10", "min", "DGCA's new deadline for reporting a spoofing event", "Stat DGCA");
text(s, "Aviation, telecom network timing and AIS-140 fleet trackers all trust whatever position and time the satellite receiver reports.", { x: X0, y: 5.5, w: 10, h: 0.8, fontSize: 18, color: C.text2 });

// 3 ----- how spoofing works (diagram)
s = slide("Content", "How spoofing works", "Civil satellite signals carry no signature", "The problem");
const sats = [[0.9, 2.3], [3.0, 2.0], [5.1, 2.3]];
for (const [sx, sy] of sats) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: sx, y: sy, w: 0.7, h: 0.35, rectRadius: 0.05, fill: { color: C.accent3 }, line: { color: C.accent3 }, objectName: "Satellite" });
  s.addShape(pres.shapes.LINE, { x: Math.min(sx + 0.35, 3.45), y: sy + 0.35, w: Math.abs(3.45 - (sx + 0.35)) || 0.01, h: 5.6 - sy - 0.35, flipH: sx + 0.35 > 3.45, line: { color: C.accent3, width: 1.5, dashType: "dash" }, objectName: "Real signal" });
}
text(s, "real signals,\nvery weak", { x: 5.5, y: 3.3, w: 1.6, h: 0.4, fontSize: 14, color: C.accent3 });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.9, y: 5.2, w: 1.0, h: 0.6, rectRadius: 0.08, fill: { color: C.accent2 }, line: { color: C.accent2 }, objectName: "Spoofer" });
text(s, "spoofer", { x: 0.9, y: 5.9, w: 1.4, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
s.addShape(pres.shapes.LINE, { x: 1.9, y: 5.5, w: 1.1, h: 0.25, line: { color: C.accent2, width: 5, endArrowType: "triangle" }, objectName: "Fake signal" });
text(s, "fake signals, stronger", { x: 0.6, y: 4.55, w: 2.4, h: 0.35, fontSize: 14, color: C.accent2 });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.05, y: 5.6, w: 0.8, h: 0.5, rectRadius: 0.08, fill: { color: C.text1 }, line: { color: C.text1 }, objectName: "Receiver" });
text(s, "receiver", { x: 3.0, y: 6.2, w: 1.2, h: 0.35, fontSize: 14, bold: true });
text(s, "locks onto the louder one", { x: 4.0, y: 5.7, w: 2.6, h: 0.35, fontSize: 14, color: C.text2 });
[["Jamming", "Noise drowns the signal. The receiver knows it has no fix."],
 ["Spoofing", "Forged signals with false data. The receiver shows a confident, wrong position."],
 ["Meaconing (replay)", "Real signals recorded and rebroadcast late. Every bit is genuine, only the timing is wrong."]]
  .forEach(([h, b], i) => {
    text(s, h, { x: 7.4, y: 2.1 + i * 1.5, w: 5.3, h: 0.45, fontSize: 22, bold: true, fontFace: THEME.headFontFace });
    text(s, b, { x: 7.4, y: 2.6 + i * 1.5, w: 5.3, h: 0.8, fontSize: 16, color: C.text2 });
  });

// 4 ----- gap
s = slide("Content", "The gap", "What exists, and what's missing", "The problem");
bullets(s, [
  "Galileo OSNMA authenticates navigation data. Initial service since 24 July 2025.",
  "ISRO designed TESLA authentication for NavIC and test-transmitted it from IRNSS-1D and 1I in 2023. Not a launched service.",
  "NavIC is down to 3 working satellites. A position needs 4, so NavIC alone can't give one.",
], { x: X0, y: 2.2, w: 5.7, h: 4.2 });
card(s, 6.9, 2.2, 5.8, 3.2, "Contribution card");
text(s, "So \"add TESLA to NavIC\" is not new.", { x: 7.2, y: 2.5, w: 5.2, h: 0.9, fontSize: 22, bold: true, fontFace: THEME.headFontFace });
text(s, "The contribution is the receiver: one trust policy across two constellations, a TESLA clock that can't be dragged, and a check for the replay attack TESLA can't see.",
  { x: 7.2, y: 3.5, w: 5.2, h: 1.8, fontSize: 17 });

// 5 ----- borrowed crypto
s = slide("Content", "Borrowed crypto", "Two ideas from internet security", "Approach");
[["TESLA", "Broadcast authentication from multicast networking research. A cheap MAC now, the key disclosed later. Adopted by Galileo OSNMA and ISRO's NavIC proposal.",
  "Weakness: secure only if the receiver knows the time well enough to reject a key that is already public."],
 ["Roughtime", "Signed time from internet security. The client sends a random nonce. The server signs nonce + time + uncertainty with Ed25519.",
  "Gives TESLA the trusted clock it assumes, from a source the radio attacker can't touch."]]
  .forEach(([h, b, n], i) => {
    const x = X0 + i * 6.15;
    card(s, x, 2.2, 5.9, 4.1, `${h} card`);
    text(s, h, { x: x + 0.3, y: 2.5, w: 5.3, h: 0.6, fontSize: 26, bold: true, fontFace: THEME.headFontFace });
    text(s, b, { x: x + 0.3, y: 3.2, w: 5.3, h: 1.6, fontSize: 17 });
    text(s, n, { x: x + 0.3, y: 4.9, w: 5.3, h: 1.2, fontSize: 15, color: C.text2 });
  });

// 6 ----- TESLA picture
s = slide("Content", "TESLA in one picture", "Sign now with a secret key, reveal the key 96 s later", "Approach");
text(s, "K(i) = SHA-256(K(i+1)), 128 bits. Anyone can hash forward to check. Nobody can go backward.", { x: X0, y: 2.05, w: CW, h: 0.4, fontSize: 15, color: C.text2, align: "center" });
const keys = ["K0 root", "K1", "K2", "K3", "… Kn (seed)"];
keys.forEach((k, i) => {
  const x = X0 + i * 2.5;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.6, w: 1.7, h: 0.7, rectRadius: 0.08, fill: { color: i === 0 ? C.accent1 : C.background1 }, line: { color: i === 0 ? C.accent1 : C.text1, width: 1 }, objectName: `Key ${k}` });
  text(s, k, { x, y: 2.6, w: 1.7, h: 0.7, fontSize: 18, bold: i === 0, color: i === 0 ? C.background1 : C.text1, align: "center", valign: "middle" });
  if (i > 0) s.addShape(pres.shapes.LINE, { x: x - 0.75, y: 2.95, w: 0.7, h: 0, flipH: true, line: { color: C.text2, width: 1.5, endArrowType: "triangle" }, objectName: "Hash arrow" });
});
text(s, "signed with Ed25519", { x: X0, y: 3.4, w: 2.5, h: 0.35, fontSize: 14, color: C.accent1 });
card(s, 3.1, 4.3, 4.3, 0.6, "Tag box");
text(s, "t = 48 s: nav data + tag = HMAC(K1)[:32]", { x: 3.25, y: 4.3, w: 4.1, h: 0.6, fontSize: 15, valign: "middle" });
s.addShape(pres.shapes.LINE, { x: 7.5, y: 4.6, w: 1.3, h: 0, line: { color: C.accent1, width: 2, endArrowType: "triangle" }, objectName: "Delay arrow" });
text(s, "96 s", { x: 7.5, y: 4.95, w: 1.3, h: 0.35, fontSize: 14, color: C.accent1, align: "center" });
card(s, 8.9, 4.3, 3.8, 0.6, "Disclosure box");
text(s, "t = 144 s: K1 disclosed → verify tag", { x: 9.05, y: 4.3, w: 3.6, h: 0.6, fontSize: 15, valign: "middle" });
text(s, "Security condition: accept a tag only if local time + clock uncertainty < its key's disclosure time.", { x: X0, y: 5.6, w: CW, h: 0.5, fontSize: 18, bold: true });
text(s, "32-bit tag vs 512-bit Ed25519 signature per message: TESLA is 16× cheaper on a 25 bit/s channel. Parameters: ISRO ICG-17 (2023), L5/S chain.", { x: X0, y: 6.4, w: CW, h: 0.4, fontSize: 12, color: C.text2 });

// 7 ----- architecture
s = slide("Content", "Architecture", "Four inputs, four checks, one trust policy", "Approach");
text(s, "attacker can tamper with", { x: X0, y: 1.95, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
const ins = ["NavIC NMA (msg 10)", "Galileo OSNMA", "Pseudoranges", "Roughtime reply"];
const checks = ["Root key signature (Ed25519)", "Key chain + tag (HMAC)", "Replay: signal vs signed time", "Clock jump + signed time"];
ins.forEach((t, i) => {
  const y = 2.4 + i * 0.95;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X0, y, w: 2.7, h: 0.7, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.accent2, width: 1.5 }, objectName: `Input ${t}` });
  text(s, t, { x: X0 + 0.15, y, w: 2.5, h: 0.7, fontSize: 15, valign: "middle" });
  s.addShape(pres.shapes.LINE, { x: X0 + 2.7, y: y + 0.35, w: 0.8, h: 0, line: { color: C.text2, width: 1.25 }, objectName: "Wire" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.1, y, w: 3.3, h: 0.7, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.text1, width: 1 }, objectName: `Check ${checks[i]}` });
  text(s, checks[i], { x: 4.25, y, w: 3.1, h: 0.7, fontSize: 15, valign: "middle" });
  s.addShape(pres.shapes.LINE, { x: 7.4, y: y + 0.35, w: 0.4, h: 0, line: { color: C.text2, width: 1.25 }, objectName: "Wire" });
});
s.addShape(pres.shapes.LINE, { x: 7.8, y: 2.75, w: 0, h: 2.85, line: { color: C.text2, width: 1.25 }, objectName: "Bus" });
s.addShape(pres.shapes.LINE, { x: 7.8, y: 4.15, w: 0.5, h: 0, line: { color: C.text2, width: 1.25, endArrowType: "triangle" }, objectName: "Wire" });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.3, y: 3.6, w: 2.3, h: 1.1, rectRadius: 0.1, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: "Trust policy" });
text(s, [{ text: "Trust policy", options: { bold: true, fontSize: 18, breakLine: true } }, { text: "per-satellite state", options: { fontSize: 13 } }], { x: 8.3, y: 3.6, w: 2.3, h: 1.1, color: C.background1, align: "center", valign: "middle" });
s.addShape(pres.shapes.LINE, { x: 10.6, y: 4.15, w: 0.4, h: 0, line: { color: C.text2, width: 1.25, endArrowType: "triangle" }, objectName: "Wire" });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 11.0, y: 3.6, w: 1.7, h: 1.1, rectRadius: 0.1, fill: { color: C.text1 }, line: { color: C.text1 }, objectName: "Position output" });
text(s, [{ text: "Position", options: { fontSize: 17, breakLine: true } }, { text: "+ trust level", options: { fontSize: 13 } }], { x: 11.0, y: 3.6, w: 1.7, h: 1.1, color: C.background2, align: "center", valign: "middle" });
text(s, [
  { text: "Authenticated: ≥4 authenticated satellites, clock OK", options: { color: C.accent6, breakLine: true } },
  { text: "Degraded: 1 to 3 authenticated satellites", options: { color: "8A5A00", breakLine: true } },
  { text: "Untrusted: clock jump, replay, or none", options: { color: C.accent5 } },
], { x: 8.3, y: 5.0, w: 4.6, h: 1.1, fontSize: 13, paraSpaceAfter: 4 });
text(s, "Only satellites the trust policy marks authenticated reach the least-squares position solver.", { x: X0, y: 6.4, w: CW, h: 0.4, fontSize: 13, color: C.text2 });

// 8 ----- what's new
s = slide("Content", "What's new", "Three pieces the existing designs don't have", "Approach");
[["1 · Dual-TESLA receiver", "Galileo (40-bit tags) and NavIC (32-bit) verified side by side. Position from authenticated satellites only, reported with a trust level."],
 ["2 · Signed-time bootstrap", "Roughtime at cold start and every 30 s. A free-running oscillator flags any sudden clock jump."],
 ["3 · Replay detection", "MACs prove who wrote the data, not when it arrived. Flag signals whose time disagrees with signed time by more than 1 s."]]
  .forEach(([h, b], i) => {
    const x = X0 + i * 4.1;
    card(s, x, 2.2, 3.85, 3.6, h);
    text(s, h, { x: x + 0.3, y: 2.5, w: 3.25, h: 0.9, fontSize: 21, bold: true, fontFace: THEME.headFontFace });
    text(s, b, { x: x + 0.3, y: 3.5, w: 3.25, h: 2.1, fontSize: 16 });
  });

// 9 ----- results summary (native grouped bar)
s = slide("Content", `Results · ${M.length.toLocaleString("en")} simulated runs`, "The hardened receiver was never fooled", "Results");
const HEAD = [["A1", 50, "Data tampering"], ["A2", 1, "Forged key"], ["A3", 10, "Fake root key"], ["A4", 5, "Old-key reuse"], ["A5", 10, "Clock drag"], ["A6", 5, "Replay (5 s)"], ["A7", 1, "Downgrade"]];
s.addChart(pres.charts.BAR, MODES.map(([m, name]) => ({ name, labels: HEAD.map((h) => h[2]), values: HEAD.map(([a, v]) => fooled(a, v, m)) })), {
  x: X0, y: 1.95, w: CW, h: 4.9, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
  ...chartStyle("Time spent showing a wrong position as valid (%)", "Time fooled (%)"), showCatAxisTitle: false,
  showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: HEX.muted, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "0",
  objectName: "Attack summary chart",
});

// 10 ----- clock matters
s = slide("Content", "Why the clock matters", "TESLA alone falls to a 5 s clock error", "Results");
lineChart(s, "A4", X0, 1.95, 5.95, 4.3, "A4 Old-key reuse", "Receiver clock running slow by (s)");
lineChart(s, "A5", X0 + 6.2, 1.95, 5.95, 4.3, "A5 Clock drag", "Clock drag applied by attacker (s)");
text(s, "A slow clock (A4) or a dragged clock (A5) lets an attacker reuse already-disclosed keys. Signed time keeps the error under ~1 s, below what the forgery needs.", { x: X0, y: 6.35, w: CW, h: 0.5, fontSize: 13, color: C.text2 });

// 11 ----- replay
s = slide("Content", "Expected loss", "Replays under 1 s still get through", "Results");
lineChart(s, "A6", X0, 1.95, CW, 4.3, "A6 Replay (meaconing)", "Replay delay d (s)");
const det = (sev) => Math.round(100 * mean(M.filter((r) => r.attack === "A6" && +r.severity === sev && r.mode === "hardened").map((r) => +r.detected)));
text(s, `Hardened detection: ${det(0.3)}% at 0.3 s, ${det(1)}% at 1 s, ${det(1.5)}% from 1.5 s (40 seeds). Internet time is only good to about a second. Closing the gap needs spreading-code authentication.`,
  { x: X0, y: 6.35, w: CW, h: 0.5, fontSize: 13, color: C.text2 });

// 12 ----- cost
s = slide("Content", "Cost", "Cheap enough for a low-cost receiver", "Results");
stat(s, X0, 2.2, 3.85, 3.2, (+P.cpu_per_tag_verify).toFixed(1), "µs", "to verify one tag on a laptop (HMAC-SHA-256)", "Stat CPU");
stat(s, X0 + 4.1, 2.2, 3.85, 3.2, (+P.navic_auth_bits_per_second_per_sat).toFixed(1), "bit/s", "NavIC authentication bits per satellite (32-bit tag + 128-bit key every 48 s)", "Stat bandwidth");
stat(s, X0 + 8.2, 2.2, 3.85, 3.2, String(Math.round(+P.navic_ttfaf_warm)), "s", `until NavIC satellites are authenticated, matching ISRO's figure. Galileo: ${Math.round(+P.time_to_first_authenticated_fix_warm)} s warm, ${Math.round(+P.time_to_first_authenticated_fix_cold)} s cold (median)`, "Stat TTFAF");

// 13 ----- limits
s = slide("Content", "Limits", "What this does not stop", "Close");
text(s, "Attacks", { x: X0, y: 2.0, w: 5.7, h: 0.5, fontSize: 22, bold: true, fontFace: THEME.headFontFace });
bullets(s, ["Jamming. No cryptography helps against noise.", "Replay under ~1 s (shown before).", "Downgrade works if the pilot ignores the Degraded warning.", "Pseudorange spoofing with genuine data: needs spreading-code authentication."], { x: X0, y: 2.6, w: 5.7, h: 3.8 });
text(s, "Model", { x: 6.9, y: 2.0, w: 5.8, h: 0.5, fontSize: 22, bold: true, fontFace: THEME.headFontFace });
bullets(s, ["NavIC message layout is modelled. ISRO's spec is not public.", "Simulated orbits are circular. No real RF.", "Future work: spreading-code authentication, post-quantum root keys."], { x: 6.9, y: 2.6, w: 5.8, h: 3.8 });

// 14 ----- demo
s = slide("Content", "Live demo · under 5 minutes", "Watch the attacks happen", "Close");
const steps = ["Clean sky: trust level Authenticated", "A1 tampering: naive jumps 3.4 km, hardened drops NavIC and holds", "A5 clock drag: signed-time check fires", "A6 replay 5 s: caught", "A6 replay 0.3 s: missed, and why"];
steps.forEach((t, i) => {
  const y = 2.15 + i * 0.85;
  s.addShape(pres.shapes.OVAL, { x: X0, y, w: 0.55, h: 0.55, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: `Step ${i + 1}` });
  text(s, String(i + 1), { x: X0, y, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" });
  text(s, t, { x: X0 + 0.8, y, w: 5.6, h: 0.55, fontSize: 17, valign: "middle" });
});
card(s, 7.6, 2.15, 5.1, 3.4, "Demo card");
text(s, "Open demo/demo.html (works offline), or run", { x: 7.9, y: 2.45, w: 4.5, h: 0.8, fontSize: 17 });
text(s, "make demo", { x: 7.9, y: 3.35, w: 4.5, h: 0.6, fontSize: 24, fontFace: "Courier New", bold: true, color: C.accent1 });
text(s, "for the same five steps in the terminal.", { x: 7.9, y: 4.1, w: 4.5, h: 0.8, fontSize: 16, color: C.text2 });

// 15 ----- questions
s = slide("Dark title", "Questions", "Authenticate the data, then authenticate the time", "Close");
s.addText("Code, tests, experiments and figures: one command each. make test · make experiments · make figures", { placeholder: "body" });
text(s, "github.com/R-Anurag/navic-nma", { x: X0, y: 6.3, w: 10, h: 0.4, fontSize: 16, color: "B8C6D0" });

(async () => {
  await pres.writeFile({ fileName: OUT });
  const applyPath = process.argv[2];
  if (applyPath) await require(applyPath).applyTheme(OUT, THEME);
  console.log("wrote " + OUT);
})();
