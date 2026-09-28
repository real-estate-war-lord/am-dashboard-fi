/* AM Dashboard — Finland Edition · chartsvg.js   (v2.2 W5)

   The Charts view's drawing half: the self-contained SVG the chart card shows on screen and the
   ⤓ PNG rasterises, in its three shapes — line, bars and the (dormant) dwelling distribution —
   plus the title block, the measuring/clipping helpers W1 added and the source footer.

   Why it is a file of its own: `src/app.js` ended W4 at 470 931 B of a 471 040 B budget, 109 bytes
   short of the ceiling, and W5 has seven features to land. W4 scoped this move in PROGRESS.md and
   W5 carries it out unchanged — the block from `chartSvg` down to the end of `chartSvgLine`, whose
   only names used elsewhere are the four exported below. Everything else it declares (`CH_FONT`,
   `CH_W`, `chTextW`, `chClip`, `chTitleBlock`, `chFoot`, `chartSvgBar`, `chartSvgDist`,
   `DIST_COLORS` …) was only ever used inside it.

   Like `src/present.js` and `src/testprop.js` this is a feature module, not a pure `*_core.js`:
   it reads `CH`, `D`, `IND`, `MUNI`, `OSA` and calls `chartSeries()`, `chartInd()`, `esc()`,
   `fmtOf()` and friends by name out of the one global lexical scope the build inlines every
   script into. What is pure in W5 lives in `src/w5_core.js` and is node-tested there.

   Inlined into dist/index.html by scripts/build_dashboard.py as {{CHARTSVG_JS}}, **before**
   app.js, which aliases the four exported names so every call site reads as it did.
*/
"use strict";

var CHARTSVG = (function () {

/* the pure half this file leans on — `src/w5_core.js`, inlined before it and node-tested */
const WC = (typeof window !== "undefined" && window.W5_CORE) || {};

/* self-contained SVG (inline styles, title, legend) so the same markup renders on screen and rasterises to PNG */
function chartSvg(withTitle) {
  const mode = chartMode();
  if (mode === "dist") return chartSvgDist(withTitle);
  if (mode === "bar") return chartSvgBar(withTitle);
  return chartSvgLine(withTitle);
}
const CH_FONT = "Inter, 'Helvetica Neue', Arial, sans-serif", CH_MONO = "'IBM Plex Mono', Menlo, monospace";
/* The chart is 1 200 units wide and is rasterised straight to PNG from a string, so a title or a
   sub-title that is too long cannot be measured in the document and cannot wrap by itself: an
   indicator description simply ran off the right edge and into the downloaded file. One canvas
   measures the same font here, the line is cut on a word and gets an ellipsis, and the full text
   stays in the element's <title> — hover on screen, and nothing is lost from the export either. */
const CH_W = 1200, CH_PAD = 24;
let CH_MEAS = null;
function chTextW(s, font) {
  if (CH_MEAS === null) { try { CH_MEAS = document.createElement("canvas").getContext("2d"); } catch (e) { CH_MEAS = false; } }
  if (!CH_MEAS) return String(s).length * 7;     /* no canvas: assume a wide-ish character */
  CH_MEAS.font = font;
  return CH_MEAS.measureText(String(s)).width;
}
function chClip(s, maxW, font) {
  s = String(s == null ? "" : s);
  if (!s || chTextW(s, font) <= maxW) return s;
  let lo = 0, hi = s.length;
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (chTextW(s.slice(0, mid) + "…", font) <= maxW) lo = mid; else hi = mid - 1; }
  if (!lo) return "…";
  const cut = s.slice(0, lo), sp = cut.lastIndexOf(" ");
  return (sp > lo * .6 ? cut.slice(0, sp) : cut).replace(/[\s·,;:—–-]+$/, "") + "…";
}
const chTitleFont = () => "600 24px " + CH_FONT, chSubFont = () => "12px " + CH_MONO;
const chTextMax = L0 => CH_W - L0 - CH_PAD;
function chTitleBlock(withTitle, ind, L0, sub) {
  if (!withTitle) return "";
  const t = CH.title || chartAutoTitle(), s = sub != null ? sub : (ind.desc || ""), max = chTextMax(L0);
  return `<text x="${L0}" y="40" font-family="${CH_FONT}" font-size="24" font-weight="600" fill="#16170F" id="chsvgtitle">${esc(chClip(t, max, chTitleFont()))}<title>${esc(t)}</title></text>`
    + `<text x="${L0}" y="64" font-family="${CH_MONO}" font-size="12" fill="#8A8C81" id="chsvgsub">${esc(chClip(s, max, chSubFont()))}<title>${esc(s)}</title></text>`;
}
/* the title box is typed into, live, without redrawing the chart — so it is re-clipped here too */
function chTitleLive() {
  const el = document.getElementById("chsvgtitle"); if (!el) return;
  const full = CH.title || chartAutoTitle();
  el.textContent = chClip(full, chTextMax(Number(el.getAttribute("x")) || 96), chTitleFont());
  const t = document.createElementNS("http://www.w3.org/2000/svg", "title");
  t.textContent = full; el.appendChild(t);
}
/* W6 — the footer is measured like the title block above it, and a note gets a line of its own.
   The source line alone fits the 1 200-unit canvas (≈163 characters at 11 px mono); a note beside
   it does not — W5's climate-pair note is 160 characters on its own — so the two ran together off
   the right edge and were cut by the viewBox, on screen and in the downloaded PNG. Both lines are
   clipped on a word as a last resort and both keep the full string in their <title>. */
const chFootFont = () => "11px " + CH_MONO;
function chFoot(L0, H, ind, extra) {
  const src = (ind.source || ""); const short = src.length > 90 ? src.slice(0, 88) + "…" : src;
  const max = chTextMax(L0), font = chFootFont();
  const line = `Source: ${short} · Macro Dashboard — Finland, open data · built ${(D.meta && D.meta.built) || ""}`;
  const note = String(extra || "").replace(/^[\s·]+/, "");
  const t = (s, y) => `<text data-testid="chart-foot" x="${L0}" y="${y}" font-family="${CH_MONO}" font-size="11" fill="#8A8C81">${esc(chClip(s, max, font))}<title>${esc(s)}</title></text>`;
  return t(line, H - 14) + (note ? t(note, H - 30) : "");
}
/* bars: latest value per selected area, sorted, median as a dashed marker */
function chartSvgBar(withTitle) {
  const ind = chartInd(); const ents = CH.areas.map(chEntity).filter(Boolean);
  /* W5 §6 — a Climate indicator draws BOTH return periods side by side. The publisher maps a
     1-in-100 and a 1-in-1000 chance as two separate rasters and this build keeps them as two
     indicators (D13), so a bar chart of one of them answered half the question a reader has:
     "how much worse does it get in the rarer event?" `W5C.rpRows()` pairs the family per area,
     sorted by the commoner period, and the rarer one is drawn in a lighter tint of the same
     area colour so a pair reads as one area, not two. */
  const fam = (WC.rpFamilyOf ? WC.rpFamilyOf(PC, ind.key) : []);
  const rows = fam.length > 1 ? rpBarRows(ents, fam) : ents.map((e, k) => { const own = e.inds.some(i => i.key === ind.key); const v = own ? (V(e.o, ind.key) ?? (e.type === "postinumero" && e.muni ? V(e.muni, ind.key) : null)) : null;
    return { name: e.name, color: CH_COLORS[k % CH_COLORS.length], v, inh: own && V(e.o, ind.key) == null && v != null }; }).filter(r => r.v != null).sort((a, b) => b.v - a.v);
  const W = 1200, L0 = 96, R = 170, T0 = withTitle ? 96 : 30, B = 70;
  /* W6 — the canvas is as tall as its bars need. A fixed 640 units left ~300 px of white between
     a two-area chart and its source line, on screen and in the PNG; a row is 52 units until the
     rows stop fitting, so from nine areas up this is the old geometry exactly. */
  const H = Math.min(640, T0 + Math.max(rows.length, 1) * 52 + B + 26);
  if (!rows.length) return `<svg class="chart" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" id="chsvg"><rect width="${W}" height="${H}" fill="#FFFFFF"/><text x="${W / 2}" y="${H / 2}" text-anchor="middle" font-family="${CH_FONT}" font-size="18" fill="#8A8C81">Add areas with the search box — nothing to plot yet</text></svg>`;
  const pool = ents.length && ents.every(e => e.type === "osa_alue") ? OSA.areas : MUNI;
  /* two return periods on one axis are two measurements: a single "median" tick could only belong
     to one of them, so the pair mode draws none and says so under the chart instead */
  const med = CH.median && fam.length <= 1 ? median(pool.map(p => V(p, ind.key))) : null;
  const vals = rows.map(r => r.v).concat(med != null ? [med] : []);
  /* W2 §3a — the value axis ends on a round number and always contains 0: a bar is read from the
     zero line out, so that line is part of the scale, not a decoration */
  const bax = chSpan(Math.min(0, ...vals), Math.max(0, ...vals), fmtTight(ind), 6) || SCL.niceTicks(Math.min(0, ...vals), Math.max(0, ...vals), 6);
  const lo = bax.lo, hi = bax.hi;
  const labW = 260; const x0 = L0 + labW, x1 = W - R; const x = v => x0 + (v - lo) / (hi - lo || 1) * (x1 - x0);
  const grid = bax.ticks.map(t => `<line x1="${x(t).toFixed(1)}" x2="${x(t).toFixed(1)}" y1="${T0 - 4}" y2="${T0 + rows.length * Math.min(52, (H - T0 - B) / rows.length)}" stroke="#EFEFEA"/><text x="${x(t).toFixed(1)}" y="${(T0 + rows.length * Math.min(52, (H - T0 - B) / rows.length) + 18).toFixed(1)}" text-anchor="middle" font-family="${CH_MONO}" font-size="11" fill="#8A8C81">${esc(fmtTight(ind)(t))}</text>`).join("");
  const rowH = Math.min(52, (H - T0 - B) / rows.length), bh = rowH * .62;
  const bars = rows.map((r, i) => { const y = T0 + i * rowH + (rowH - bh) / 2; return `<text x="${x0 - 12}" y="${(y + bh / 2 + 5).toFixed(1)}" text-anchor="end" font-family="${CH_FONT}" font-size="15" fill="#16170F">${esc(r.name)}${r.inh ? " (kunta)" : ""}</text>
    <rect ${r.rp ? `data-testid="chart-rp-bar" data-rp="${esc(r.rp)}" ` : ""}x="${x(Math.min(0, r.v)).toFixed(1)}" y="${y.toFixed(1)}" width="${Math.abs(x(r.v) - x(0)).toFixed(1)}" height="${bh.toFixed(1)}" fill="${r.color}" rx="3"/>
    <text x="${(x(Math.max(0, r.v)) + 8).toFixed(1)}" y="${(y + bh / 2 + 5).toFixed(1)}" font-family="${CH_MONO}" font-size="14" fill="#16170F">${esc(fmtOf(ind)(r.v))}</text>`; }).join("");
  const medLine = med != null ? `<line x1="${x(med).toFixed(1)}" x2="${x(med).toFixed(1)}" y1="${T0 - 8}" y2="${T0 + rows.length * rowH}" stroke="#5C5F52" stroke-width="2" stroke-dasharray="7 5"/><text x="${(x(med) + 6).toFixed(1)}" y="${T0 - 12}" font-family="${CH_MONO}" font-size="12" fill="#5C5F52">${pool === MUNI ? "Finland median" : "Osa-alue median"} ${esc(fmtOf(ind)(med))}</text>` : "";
  const asof = asofText(ind);
  const extra = fam.length > 1
    ? " · both return periods per area; a return period is a probability, not a date, and no median tick is drawn because the two are separate measurements"
    : (rows.some(r => r.inh) ? " · (kunta) = the kunta's figure, shown where the area publishes none" : "");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" id="chsvg"><rect width="${W}" height="${H}" fill="#FFFFFF"/>${chTitleBlock(withTitle, ind, L0, `${ind.desc || ""}${asof ? " · as of " + asof : ""}`)}
    ${grid}<line ${chSigned(ind) ? 'data-testid="chart-zero" ' : ""}x1="${x(0).toFixed(1)}" x2="${x(0).toFixed(1)}" y1="${T0}" y2="${T0 + rows.length * rowH}" stroke="#4A4C43" stroke-width="1.5"/>${bars}${medLine}${chFoot(L0, H, ind, extra)}</svg>`;
}
/* W5 §6 — one row per (area × return period), the pairs kept together and ordered by the commoner
   period, so reading down the chart is reading areas and reading across a pair is reading the two
   probabilities. The rarer period keeps the area's colour, mixed 45 % toward white. */
function rpBarRows(ents, fam) {
  const out = [];
  ents.map((e, k) => {
    const cells = fam.map((f, j) => {
      const own = e.inds.some(i => i.key === f.key);
      const v = own ? (V(e.o, f.key) ?? (e.type === "postinumero" && e.muni ? V(e.muni, f.key) : null)) : null;
      return { name: `${e.name} · ${f.label}`, rp: f.rp, color: WC.tint(CH_COLORS[k % CH_COLORS.length], j * .45), v,
               inh: own && V(e.o, f.key) == null && v != null };
    }).filter(r => r.v != null);
    return { lead: cells.length ? cells[0].v : null, cells };
  }).filter(g => g.cells.length).sort((a, b) => b.lead - a.lead).forEach(g => out.push(...g.cells));
  return out;
}
/* distributions from the building register: one donut per area */
const DIST_DEFS = { size: ["Dwelling size", ["< 50 m²", "50–79 m²", "80–119 m²", "120+ m²"]], rooms: ["Rooms", ["1 room", "2 rooms", "3 rooms", "4+ rooms"]],
                    built: ["Year built", ["before 1950", "1950–79", "1980–2009", "2010+"]], type: ["Building type", ["houses", "row houses", "multi-dwelling", "other"]] };
const DIST_COLORS = ["#C9DCD6", "#7FB0A4", "#3E8A78", "#1C6B5C"];
function chartSvgDist(withTitle) {
  const ents = CH.areas.map(chEntity).filter(Boolean).filter(e => e.o.bbr && e.o.bbr.dist); const [dl, labels] = DIST_DEFS[CH.dist] || DIST_DEFS.size;
  const W = 1200, H = 640, L0 = 96, T0 = withTitle ? 96 : 30;
  const ind = { label: `${dl} — share of dwellings`, unit: "", desc: "Distribution of current dwellings from the building register, placed by building coordinate.", source: "the building register" };
  if (!ents.length) return `<svg class="chart" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" id="chsvg"><rect width="${W}" height="${H}" fill="#FFFFFF"/>${chTitleBlock(withTitle, ind, L0, "")}<text x="${W / 2}" y="${H / 2}" text-anchor="middle" font-family="${CH_FONT}" font-size="18" fill="#8A8C81">No area here carries a dwelling distribution — Ryhti publishes none</text></svg>`;
  const perRow = Math.min(4, ents.length), cw = (W - L0 * 2) / perRow, rows = Math.ceil(ents.length / perRow), avail = H - T0 - 110, rh = avail / rows, r0 = Math.min(cw, rh) * .34, r1 = r0 * .55;
  const arc = (cx, cy, a0, a1, R0, R1) => { const p = (a, r) => [cx + r * Math.cos(a), cy + r * Math.sin(a)]; const [x0, y0] = p(a0, R0), [x1, y1] = p(a1, R0), [x2, y2] = p(a1, R1), [x3, y3] = p(a0, R1); const big = a1 - a0 > Math.PI ? 1 : 0;
    return `M${x0.toFixed(1)},${y0.toFixed(1)}A${R0},${R0} 0 ${big} 1 ${x1.toFixed(1)},${y1.toFixed(1)}L${x2.toFixed(1)},${y2.toFixed(1)}A${R1},${R1} 0 ${big} 0 ${x3.toFixed(1)},${y3.toFixed(1)}Z`; };
  const donuts = ents.map((e, k) => { const cx = L0 + (k % perRow) * cw + cw / 2, cy = T0 + Math.floor(k / perRow) * rh + rh / 2 - 10; const d = e.o.bbr.dist[CH.dist] || [0, 0, 0, 0]; const tot = d.reduce((a, b) => a + b, 0) || 1; let a = -Math.PI / 2;
    const slices = d.map((v, i) => { const a1 = a + v / tot * 2 * Math.PI - 1e-6; const path = `<path d="${arc(cx, cy, a, a1, r0, r1)}" fill="${DIST_COLORS[i]}"><title>${esc(labels[i])}: ${nf(v / tot * 100, 0)} % (${nf(v, 0)})</title></path>`; const mid = (a + a1) / 2; const lab = v / tot >= .07 ? `<text x="${(cx + (r0 + r1) / 2 * Math.cos(mid)).toFixed(1)}" y="${(cy + (r0 + r1) / 2 * Math.sin(mid) + 5).toFixed(1)}" text-anchor="middle" font-family="${CH_MONO}" font-size="13" font-weight="600" fill="${i >= 2 ? "#FFFFFF" : "#16170F"}">${nf(v / tot * 100, 0)} %</text>` : ""; a = a1 + 1e-6; return path + lab; }).join("");
    return slices + `<text x="${cx}" y="${(cy + r0 + 26).toFixed(1)}" text-anchor="middle" font-family="${CH_FONT}" font-size="15" font-weight="600" fill="#16170F">${esc(e.name)}</text><text x="${cx}" y="${(cy + r0 + 46).toFixed(1)}" text-anchor="middle" font-family="${CH_MONO}" font-size="12" fill="#8A8C81">${nf(e.o.bbr.n, 0)} dwellings</text>`; }).join("");
  const legY = H - 52; const legend = labels.map((l, i) => `<rect x="${L0 + i * 220}" y="${legY - 12}" width="14" height="14" fill="${DIST_COLORS[i]}" rx="2"/><text x="${L0 + i * 220 + 22}" y="${legY}" font-family="${CH_FONT}" font-size="14" fill="#16170F">${esc(l)}</text>`).join("");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" id="chsvg"><rect width="${W}" height="${H}" fill="#FFFFFF"/>${chTitleBlock(withTitle, ind, L0, ind.desc)}${donuts}${legend}${chFoot(L0, H, ind)}</svg>`;
}
/* "2026K2" → "2026 Q2" for display; years pass through */
const fmtP = p => String(p).replace(/K(\d)$/, " Q$1");
function chartSvgLine(withTitle) {
  const { ind, inds, ys, series } = chartSeries(); const q = isQuarter(ys[0] || "");
  /* W6 — the "(kunta)" note is a second footer line now (see chFoot), so the bottom band is 16
     units taller when there is one: the legend, the year labels and the note all live in B. */
  const footNote = series.some(s_ => s_.inherited) ? " · (kunta) = the kunta's figure, shown where the area publishes none" : "";
  const W = 1200, H = 640, L0 = 96, R = 30, T0 = withTitle ? 84 : 24, B = 150 + (footNote ? 16 : 0);
  const all = series.flatMap(s_ => s_.pts.map(p => p.v)).filter(v => v != null);
  const F = "Inter, 'Helvetica Neue', Arial, sans-serif", M = "'IBM Plex Mono', Menlo, monospace";
  if (!all.length) return `<svg class="chart" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg"><rect width="${W}" height="${H}" fill="#FFFFFF"/><text x="${W / 2}" y="${H / 2}" text-anchor="middle" font-family="${F}" font-size="18" fill="#8A8C81">Add areas with the search box — nothing to plot yet</text></svg>`;
  /* W2 §3 — nice ticks, the range off the years every series covers, a value outside it clipped and
     marked. The 8 % padding this replaced could not put a tick on a round number and could not keep
     one series' pre-merger spike from flattening every other line in the card. */
  const ax = chAxis(series, ys, ind);
  const lo = ax.lo, hi = ax.hi, sp = (hi - lo) || 1;
  const x = i => L0 + i / Math.max(1, ys.length - 1) * (W - L0 - R), y = v => T0 + (1 - (v - lo) / sp) * (H - T0 - B);
  const yc = v => y(Math.max(lo, Math.min(hi, v)));
  const outOf = v => v > hi + 1e-9 ? "▲" : v < lo - 1e-9 ? "▼" : "";
  const ticks = ax.ticks;
  const paths = series.map(s_ => { let d = "", open = false; s_.pts.forEach((p, i) => { if (p.v == null) { open = false; return; } d += (open ? "L" : "M") + x(i).toFixed(1) + "," + yc(p.v).toFixed(1); open = true; });
    return `<path d="${d}" fill="none" stroke="${s_.color}" stroke-width="${s_.dash ? 2 : 3}" ${s_.dash ? 'stroke-dasharray="7 5"' : ""} stroke-linejoin="round"/>` +
      s_.pts.map((p, i) => { if (p.v == null) return ""; const o = outOf(p.v);
        if (o) return `<text data-testid="chart-clip" x="${x(i).toFixed(1)}" y="${(yc(p.v) + (o === "▲" ? 14 : -5)).toFixed(1)}" text-anchor="middle" font-family="${M}" font-size="13" fill="${s_.color}">${o}<title>${esc(s_.name)} ${fmtP(p.y)}: ${fmtOf(ind)(p.v)} — off the scale</title></text>`;
        return s_.dash ? "" : `<circle cx="${x(i).toFixed(1)}" cy="${yc(p.v).toFixed(1)}" r="${q ? 2.2 : 4}" fill="${s_.color}"><title>${esc(s_.name)} ${fmtP(p.y)}: ${fmtOf(ind)(p.v)}</title></circle>`; }).join(""); }).join("");
  /* §3a — the zero line a signed indicator needs: darker than a gridline, drawn under the series */
  const zeroLine = chSigned(ind) && lo <= 0 && hi >= 0
    ? `<line data-testid="chart-zero" x1="${L0}" x2="${W - R}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}" stroke="#4A4C43" stroke-width="1.5"/>` : "";
  const clipNote = chClipNote(ax, inds);
  /* series breaks: thin dotted marker, short label, the registry text as tooltip */
  const brks = chartBreaks(inds, ys).map(b => `<g><line x1="${x(b.idx).toFixed(1)}" x2="${x(b.idx).toFixed(1)}" y1="${T0}" y2="${H - B}" stroke="#8A8C81" stroke-width="1" stroke-dasharray="2 3"/>
    <text x="${(x(b.idx) + 5).toFixed(1)}" y="${T0 + 12}" font-family="${M}" font-size="11" fill="#8A8C81">break ${esc(fmtP(b.at))}</text>
    <line x1="${x(b.idx).toFixed(1)}" x2="${x(b.idx).toFixed(1)}" y1="${T0}" y2="${H - B}" stroke="transparent" stroke-width="12"><title>${esc(b.text)}</title></line></g>`).join("");
  /* the clipped-years note sits between the year labels and the legend, and pushes the legend down */
  const legY = H - B + 46 + (clipNote ? 16 : 0); const perRow = 3, colW = (W - L0 - R) / perRow;
  const legend = series.map((s_, k) => { const lx = L0 + (k % perRow) * colW, ly = legY + Math.floor(k / perRow) * 24; const last = [...s_.pts].reverse().find(p => p.v != null);
    return `<line x1="${lx}" x2="${lx + 26}" y1="${ly - 4}" y2="${ly - 4}" stroke="${s_.color}" stroke-width="${s_.dash ? 2 : 3}" ${s_.dash ? 'stroke-dasharray="7 5"' : ""}/><text x="${lx + 34}" y="${ly}" font-family="${F}" font-size="14" fill="#16170F">${esc(s_.name)}${s_.inherited ? " (kunta)" : ""}${last ? ` <tspan font-family="${M}" fill="#4A4C43">${esc(fmtOf(ind)(last.v))} (${fmtP(last.y)})</tspan>` : ""}</text>`; }).join("");
  const title = chTitleBlock(withTitle, ind, L0);
  const foot = chFoot(L0, H, ind, footNote);
  /* the clipped years are named on the chart itself, so the downloaded PNG carries the caveat too */
  const note = clipNote ? `<text data-testid="chart-scale-note" x="${L0}" y="${H - B + 38}" font-family="${M}" font-size="11" fill="#8A8C81">${esc(chClip(clipNote, CH_W - L0 - CH_PAD, "11px " + CH_MONO))}<title>${esc(clipNote)}</title></text>` : "";
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" id="chsvg"><rect width="${W}" height="${H}" fill="#FFFFFF"/>${title}
    ${ticks.map(t => `<line x1="${L0}" x2="${W - R}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}" stroke="#EFEFEA"/><text x="${L0 - 10}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end" font-family="${M}" font-size="12" fill="#8A8C81">${esc(fmtTight(ind)(t))}</text>`).join("")}
    ${zeroLine}
    ${ys.map((yy, i) => q && !yy.endsWith("K1") ? "" : `<text x="${x(i).toFixed(1)}" y="${H - B + 22}" text-anchor="middle" font-family="${M}" font-size="12" fill="#8A8C81">${q ? yy.slice(0, 4) : yy}</text>`).join("")}
    ${brks}${paths}${legend}${note}${foot}</svg>`;
}

return { chartSvg, chTitleLive, DIST_DEFS, fmtP };
})();

if (typeof window !== "undefined") window.CHARTSVG = CHARTSVG;
