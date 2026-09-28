/* AM Dashboard — Finland Edition · present.js   (v2.2 W4 — package D)

   The three things that make this dashboard usable in a meeting rather than only at a desk:

     1. **Present mode** — `present=1` in the link, the top bar's `Present` button, or `P`. The
        sidebar goes, every toolbar collapses into one thin line (indicator · period · area), the
        headline numbers grow a quarter, the mini-map legends open, and a one-line source footer is
        pinned to the bottom of the window. Esc leaves. Only *controls* are hidden: every figure,
        caveat and section that was on the page is still on it.
     2. **The study row's ⤓ PNG** — the chart and the mini map side by side at 2×, with the title,
        the map's own legend and the same source footer. The basemap is drawn from the live tiles
        when the canvas will accept them, and is **omitted, and said to be omitted**, when they are
        cross-origin — which is the normal case for tile.openstreetmap.org, whose tiles carry no
        CORS header. Nothing is fetched and no library is loaded: the picture is made out of the
        elements already on the page.
     3. **The print sheet** — A4 landscape, in `src/style.css` under the same heading.

   This file is the W4 half of app.js, not a pure core. It reads `S`, `UI`, `MK`, `D` and calls
   `renderTop()`, `syncHash()`, `esc()` and friends by name, the same way app.js and testprop.js
   share the one global lexical scope the build inlines them into. What *is* pure — the footer
   line, the composite's geometry and its file name — takes its inputs as arguments and is
   exported for `node --test tests/present.test.js`.

   Inlined into dist/index.html by scripts/build_dashboard.py **before** app.js, because its
   document listeners must run before app.js's: that is what lets `P` and Esc be answered here
   first, without touching the key handling three earlier phases wrote.
*/
"use strict";

var PRESENT = (function () {

/* where a reader who is handed the printed page or the PNG finds the live thing */
const SITE = "real-estate-war-lord.github.io/am-dashboard-fi";
const PAPER = "#E8EDE7", INK = "#16170F", MUTED = "#8A8C81", LINE = "#D7DCD4", CARD = "#FBFCFA";
const FONT = "Inter, 'Helvetica Neue', Arial, sans-serif";
const MONO = "'IBM Plex Mono', Menlo, monospace";

/* ======================================================================== pure */

function uniq(list) {
  const out = [];
  (list || []).forEach(v => { const s = String(v == null ? "" : v).trim(); if (s && out.indexOf(s) < 0) out.push(s); });
  return out;
}

/* "Source: Tilastokeskus, Aluesarjat … · as of 2025Q4 · real-estate-war-lord.github.io/…"
   One line, and the same line in present mode, in print and inside the PNG — a picture that
   leaves this machine has to say what it is a picture of. A publisher's parenthetical
   ("Tilastokeskus (Paavo)") is dropped before the list is de-duplicated, so the same body is
   never named twice; anything past `max` is counted rather than listed. */
function footerText(o) {
  o = o || {};
  const pubs = uniq((o.publishers || []).map(p => String(p == null ? "" : p).replace(/\s*\([^)]*\)\s*$/, "")));
  const max = o.max || 4;
  const head = pubs.length
    ? pubs.slice(0, max).join(", ") + (pubs.length > max ? " and " + (pubs.length - max) + " more" : "")
    : "open data";
  const parts = ["Source: " + head];
  if (o.asof) parts.push("as of " + o.asof);
  if (o.note) parts.push(o.note);
  parts.push(o.site || SITE);
  return parts.join(" · ");
}

/* the newest as-of any source in the build carries. Sorting the strings is right for every shape
   this field takes here ("2024", "2025Q4", "2025-06-01") because each is already big-endian. */
function newestAsof(sources) {
  return uniq((sources || []).map(s => s && s.asof)).sort().pop() || "";
}

/* The composite's geometry, in CSS pixels before the 2× scale is applied.

   The chart is drawn at **its own aspect ratio** and never stretched to fill a box — a line chart
   squeezed vertically is a chart whose slopes lie. Its series legend goes under it, in the same
   column. The map takes the rest of the width and the **full** height of the body beside it, and
   the body has a floor (`minBody`): the area page's panel chart is a 900 × 240 strip, and at that
   ratio alone the map would come out as a 100-px band of colour with nothing readable in it. */
function layout(o) {
  o = o || {};
  const W = o.width || 1600;
  const pad = o.pad == null ? 28 : o.pad;
  const gap = o.gap == null ? 20 : o.gap;
  const titleH = o.titleH == null ? 62 : o.titleH;
  const footH = o.footH == null ? 30 : o.footH;
  const minBody = o.minBody == null ? 360 : o.minBody;
  const legH = o.legH || 0;
  const inner = W - pad * 2;
  const chartW = Math.round((inner - gap) * (o.split || 0.64));
  const mapW = inner - gap - chartW;
  const chartH = Math.round(chartW * (o.chartH || 640) / (o.chartW || 1200));
  const bodyH = Math.max(chartH + legH, minBody);
  const H = pad * 2 + titleH + bodyH + footH;
  return {
    W, H, pad, gap, bodyH,
    title: { x: pad, y: pad, w: inner, h: titleH },
    chart: { x: pad, y: pad + titleH, w: chartW, h: chartH },
    legend: { x: pad, y: pad + titleH + chartH, w: chartW, h: legH },
    map: { x: pad + chartW + gap, y: pad + titleH, w: mapW, h: bodyH },
    foot: { x: pad, y: H - pad, w: inner },
  };
}

/* a file name someone can still read a month later: what, where, which period */
function fileName(parts, ext) {
  const s = (parts || []).map(p => String(p == null ? "" : p)
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, ""))
    .filter(Boolean).join("_");
  return (s || "export") + (ext || ".png");
}

/* ==================================================================== the page */
/* everything below this line needs a document; in node the module stops here */

const hasDom = typeof document !== "undefined" && typeof window !== "undefined";

const on = () => !!(typeof UI !== "undefined" && UI.present);

/* The live footer line. The publishers are the ones **Data › Sources** names, through the very
   function that fills that table and writes the sources CSV (`sourceRecords()`), so a picture that
   leaves this machine cannot credit a different body than the page does. It is build metadata and
   never changes, so it is worked out once — `apply()` asks for it on every render. */
let FOOT = null;
function footLine() {
  if (FOOT != null) return FOOT;
  let rows = [];
  try { rows = typeof sourceRecords === "function" ? sourceRecords() : []; } catch (e) { rows = []; }
  FOOT = footerText({ publishers: rows.map(r => r.publisher),
                      asof: newestAsof(rows.map(r => ({ asof: r.as_of }))) });
  return FOOT;
}

/* ---------- present mode ---------- */

/* the one thin line the four toolbars collapse into: what is being read, over which period, for
   which area. The three things a toolbar was saying; the controls that set them are one Esc away. */
function line() {
  let i = {}, per = "", area = "";
  try {
    i = (typeof S !== "undefined" && S.view === "charts" ? chartInd() : curInd()) || {};
    per = period(i);
    area = presentArea();
  } catch (e) { /* a half-loaded view still gets a bar, just a shorter one */ }
  return `<div class="presentline" data-testid="present-line">`
    + `<b>${esc(i.short || i.label || "")}</b>`
    + (per ? `<span class="pdim">${esc(per)}</span>` : "")
    + (area ? `<span class="pdim">${esc(area)}</span>` : "") + `</div>`;
}

function presentArea() {
  const c = crumbs();
  return [c.c.length > 1 ? c.c[c.c.length - 1][0] : "", c.tail].filter(Boolean).join(" › ");
}

/* the period the view is actually showing — the chart's year span, the panel's series, or the
   selected year. `panelPeriod()` is the area page's own answer, so the bar cannot contradict it. */
function period(i) {
  if (typeof S === "undefined") return "";
  /* `chartSeries().ys`, not `chartYears()`: W2 §3c trims the leading periods nothing is published
     for, and the bar must not claim a span the chart is not drawing */
  if (S.view === "charts") { const ys = chartSeries().ys || []; return ys.length ? fmtP(ys[0]) + "–" + fmtP(ys[ys.length - 1]) : ""; }
  if (S.view === "area") { const e = areaEntity(); if (e) return panelPeriod(e, i); }
  if (S.view === "property") {
    const r = typeof anRes === "function" ? anRes() : null;
    const e = r && !r.error ? tpEntity(r) : null;
    if (e) return panelPeriod(e, i);
  }
  return (typeof asofShortOf === "function" ? asofShortOf(i) : "") || (typeof MK !== "undefined" ? MK.year : "") || "";
}

function btn() {
  const v = on();
  return `<button class="tbtn ${v ? "on" : ""}" data-testid="present-btn" data-present aria-pressed="${v}"`
    + ` title="Present mode (P) — sidebar and toolbars away, bigger numbers, one source line. Esc leaves.">`
    + `${v ? "✕ Leave present" : "▶ Present"}</button>`;
}

const pngBtn = () => `<button class="tbtn pngbtn" data-testid="study-png" data-studypng`
  + ` title="Download the chart and the mini map beside it as one image, at 2×">⤓ PNG</button>`;

/* called at the end of every render(): the body class, the footer line and the mini maps' legends,
   which present mode opens (they live behind a `Legend ▾` pill since W2 §2). */
function apply() {
  if (!hasDom) return;
  const v = on();
  document.body.classList.toggle("present", v);
  const f = document.getElementById("srcfoot");
  if (f) f.textContent = footLine();
  /* the legends come out from behind W2's pill — but only where there is room for both them and
     the map; below 1025 px the pill stays and present mode leaves it alone */
  if (v && window.innerWidth > 1024)
    document.querySelectorAll(".mapwrap.mini").forEach(w => w.classList.add("legs-open"));
}

function set(v) {
  if (typeof UI === "undefined") return;
  v = !!v;
  if (UI.present === v) return;
  UI.present = v;
  if (typeof syncHash === "function") syncHash();
  apply();
  if (typeof renderTop === "function") renderTop();
  /* the column just changed width by the whole sidebar, and Leaflet only knows what it is told */
  setTimeout(() => {
    if (typeof mkFitHeight === "function") mkFitHeight();
    (window.__maps || []).forEach(m => { try { m.invalidateSize(); } catch (e) {} });
  }, 60);
}

const toggle = () => set(!on());

/* ---------- SVG → image ----------
   The panel charts are styled by src/style.css (`.grid`, `.ax`, `.dtick`…), and a stylesheet does
   not travel inside a data: URL — an SVG rasterised straight out of the page would come back as
   black shapes on nothing. So the clone carries every drawn property inline, copied from the
   *original's* computed style. The Charts view's own SVG is already built with inline styles for
   exactly this reason and goes through `png()` untouched. */
const SVG_PROPS = ["fill", "fill-opacity", "stroke", "stroke-width", "stroke-dasharray",
  "stroke-linejoin", "stroke-linecap", "opacity", "font-family", "font-size", "font-weight",
  "font-style", "text-anchor", "letter-spacing", "font-variant-numeric"];

function inlineSvg(src) {
  const clone = src.cloneNode(true);
  const from = src.querySelectorAll("*"), to = clone.querySelectorAll("*");
  for (let k = 0; k < from.length && k < to.length; k++) {
    const cs = window.getComputedStyle(from[k]);
    let css = "";
    SVG_PROPS.forEach(p => { const val = cs.getPropertyValue(p); if (val) css += p + ":" + val + ";"; });
    to[k].setAttribute("style", css);
    to[k].removeAttribute("class");
  }
  clone.removeAttribute("class");
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  const box = (src.getAttribute("viewBox") || "").split(/[ ,]+/).map(Number);
  const w = box.length === 4 ? box[2] : src.clientWidth || 1200;
  const h = box.length === 4 ? box[3] : src.clientHeight || 640;
  clone.setAttribute("width", w); clone.setAttribute("height", h);
  return { text: new XMLSerializer().serializeToString(clone), w, h };
}

function svgImage(text) {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = () => rej(new Error("this SVG could not be rasterised"));
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(text);
  });
}

/* ---------- the Leaflet map, onto a canvas ----------
   Not re-derived from the data: the map on the screen is already a stack of tiles, canvases and
   SVG overlays, each of which knows where it is. They are copied in painting order — by the
   z-index of the pane they belong to, not by their position in the DOM, because the custom panes
   (services 450, public 440, zones 455) are appended in creation order and would otherwise land
   under the markers. */

/* one tile, drawn into a 2 × 2 scratch canvas: if reading a pixel back throws, the tiles are
   cross-origin and every one of them would poison the export. Asked before anything is composed,
   so the answer can be written into the footer. */
function basemapUsable(mapEl) {
  const img = mapEl.querySelector("img.leaflet-tile");
  if (!img || !img.complete || !img.naturalWidth) return false;
  try {
    const c = document.createElement("canvas"); c.width = c.height = 2;
    const x = c.getContext("2d");
    x.drawImage(img, 0, 0);
    x.getImageData(0, 0, 1, 1);
    return true;
  } catch (e) { return false; }
}

const MAX_MARKS = 400;   /* a national view can carry thousands of labels; a 560-px panel cannot */

function mapPieces(mapEl, tiles) {
  const sel = (tiles ? "img.leaflet-tile," : "") + ".leaflet-pane canvas,.leaflet-pane svg,.leaflet-marker-icon";
  const list = [].slice.call(mapEl.querySelectorAll(sel));
  const zOf = el => {
    const p = el.closest ? el.closest(".leaflet-pane") : null;
    return p ? (parseInt(window.getComputedStyle(p).zIndex, 10) || 0) : 0;
  };
  return list.map((el, i) => ({ el, z: zOf(el), i }))
    .sort((a, b) => (a.z - b.z) || (a.i - b.i))
    .map(x => x.el);
}

function drawMarker(ctx, el, place) {
  const r = el.getBoundingClientRect();
  if (!r.width && !r.height) return;
  const p = place(r);
  const cx = p.x + p.w / 2, cy = p.y + p.h / 2;
  /* the test property's pin is a CSS shape with no text in it — redrawn rather than copied */
  if (el.classList.contains("tp-pin")) {
    const col = typeof cssVar === "function" ? cssVar("--pin", "#33372C") : "#33372C";
    ctx.beginPath(); ctx.arc(cx, cy, 8, 0, Math.PI * 2);
    ctx.fillStyle = "#FFFFFF"; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = col; ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy, 3.5, 0, Math.PI * 2); ctx.fillStyle = col; ctx.fill();
    return;
  }
  const txt = String(el.innerText || el.textContent || "").trim();
  if (!txt) return;
  const cs = window.getComputedStyle(el);
  const size = Math.max(10, parseFloat(cs.fontSize) || 11);
  const rows = txt.split("\n").filter(Boolean);
  ctx.font = "600 " + size + "px " + FONT;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.lineJoin = "round"; ctx.lineWidth = 3;
  ctx.strokeStyle = "rgba(255,255,255,.9)";
  ctx.fillStyle = cs.color || INK;
  rows.forEach((t, k) => {
    const y = cy + (k - (rows.length - 1) / 2) * (size + 2);
    ctx.strokeText(t, cx, y); ctx.fillText(t, cx, y);
  });
}

function drawMap(ctx, mapEl, box) {
  const m = mapEl.getBoundingClientRect();
  const tiles = basemapUsable(mapEl);
  ctx.save();
  ctx.beginPath(); ctx.rect(box.x, box.y, box.w, box.h); ctx.clip();
  /* no basemap: paper, so the polygons are read against the same background as the page */
  ctx.fillStyle = tiles ? "#FFFFFF" : PAPER;
  ctx.fillRect(box.x, box.y, box.w, box.h);
  if (!m.width || !m.height) { ctx.restore(); return Promise.resolve({ basemap: false }); }
  /* cover, centred: the panel is not the map's shape, and letterboxing a map looks like an error */
  const s = Math.max(box.w / m.width, box.h / m.height);
  const ox = box.x + (box.w - m.width * s) / 2, oy = box.y + (box.h - m.height * s) / 2;
  const place = r => ({ x: ox + (r.left - m.left) * s, y: oy + (r.top - m.top) * s,
                        w: r.width * s, h: r.height * s });
  let marks = 0;
  const pieces = mapPieces(mapEl, tiles);
  let chain = Promise.resolve();
  pieces.forEach(el => {
    chain = chain.then(() => {
      const tag = el.tagName;
      const r = el.getBoundingClientRect();
      if (tag === "IMG" || tag === "CANVAS") {
        if (!r.width || !r.height) return;
        if (tag === "IMG" && (!el.complete || !el.naturalWidth)) return;
        if (tag === "CANVAS" && (!el.width || !el.height)) return;
        const p = place(r);
        ctx.drawImage(el, p.x, p.y, p.w, p.h);
        return;
      }
      if (tag === "svg") {
        if (!r.width || !r.height) return;
        const s2 = inlineSvg(el);
        return svgImage(s2.text).then(img => { const p = place(r); ctx.drawImage(img, p.x, p.y, p.w, p.h); });
      }
      if (marks++ < MAX_MARKS) drawMarker(ctx, el, place);
    }).catch(() => {});    /* one unreadable layer must not lose the whole picture */
  });
  return chain.then(() => { ctx.restore(); return { basemap: tiles }; });
}

/* the map's own legend, redrawn as a card in the corner of the map panel: the swatch colours are
   read off the live elements, so the picture and the screen cannot key the same map differently */
/* the title carries the indicator, its unit in a <span>, and the fold control mmFoldable() puts
   there — the button is not part of the name, and the unit needs the space the markup gave it */
function legendTitle(el) {
  if (!el) return "";
  return [].slice.call(el.childNodes)
    .filter(n => !(n.nodeType === 1 && n.tagName === "BUTTON"))
    .map(n => String(n.textContent || "").trim()).filter(Boolean).join(" ");
}

function drawLegend(ctx, el, box) {
  if (!el) return;
  const title = el.querySelector(".lgtitle");
  const rows = [].slice.call(el.querySelectorAll(".lgrow")).slice(0, 9);
  if (!rows.length) return;
  const pad = 9, rowH = 15, titleH = title ? 16 : 0;
  const w = Math.min(box.w - 16, 220);
  const h = pad * 2 + titleH + rows.length * rowH;
  const x = box.x + 8, y = box.y + box.h - 8 - h;
  ctx.save();
  ctx.fillStyle = "rgba(251,252,250,.93)"; ctx.strokeStyle = LINE; ctx.lineWidth = 1;
  ctx.fillRect(x, y, w, h); ctx.strokeRect(x + .5, y + .5, w - 1, h - 1);
  ctx.textAlign = "left"; ctx.textBaseline = "middle";
  if (title) {
    ctx.font = "600 10px " + MONO; ctx.fillStyle = INK;
    ctx.fillText(clip(ctx, legendTitle(title), w - pad * 2), x + pad, y + pad + 7);
  }
  ctx.font = "10px " + MONO;
  rows.forEach((r, k) => {
    const cy = y + pad + titleH + k * rowH + rowH / 2;
    const sw = r.querySelector("i");
    if (sw) {
      ctx.fillStyle = window.getComputedStyle(sw).backgroundColor || MUTED;
      ctx.fillRect(x + pad, cy - 5, 10, 10);
    }
    ctx.fillStyle = INK;
    ctx.fillText(clip(ctx, String(r.textContent || "").trim(), w - pad * 2 - 16), x + pad + 16, cy);
  });
  ctx.restore();
}

/* The chart's own key is HTML beside the SVG, not part of it (`.bleg`), and so is the clipped-scale
   note W2 §3 writes under it — so both are redrawn here. A picture of a chart whose lines are not
   named is not a chart, and a scale that excludes years has to say so wherever it is shown. */
const LEG_ROW = 18;
function seriesLegend(panel) {
  if (!panel) return { items: [], note: "" };
  const items = [].slice.call(panel.querySelectorAll(".bleg>span")).map(s => {
    const sw = s.querySelector("i");
    return { color: (sw && window.getComputedStyle(sw).backgroundColor) || MUTED,
             text: String(s.textContent || "").replace(/\s+/g, " ").trim() };
  }).filter(it => it.text);
  const n = panel.querySelector("[data-testid=chart-scale-note]");
  return { items, note: n ? String(n.textContent || "").trim() : "" };
}
/* what `layout()` has to reserve for it, before there is a canvas to measure on */
const legHeight = leg => (leg.items.length ? LEG_ROW * Math.ceil(leg.items.length / 3) + 10 : 0)
  + (leg.note ? LEG_ROW : 0);

function drawSeriesLegend(ctx, box, leg) {
  if (!leg.items.length && !leg.note) return;
  ctx.save();
  ctx.textAlign = "left"; ctx.textBaseline = "middle";
  let x = box.x, y = box.y + 12;
  ctx.font = "12px " + FONT;
  leg.items.forEach(it => {
    const w = 24 + ctx.measureText(it.text).width + 20;
    if (x > box.x && x + w > box.x + box.w) { x = box.x; y += LEG_ROW; }
    ctx.strokeStyle = it.color; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 18, y); ctx.stroke();
    ctx.fillStyle = INK; ctx.fillText(clip(ctx, it.text, box.w - 24), x + 24, y);
    x += w;
  });
  if (leg.note) {
    y += leg.items.length ? LEG_ROW : 0;
    ctx.font = "italic 11px " + MONO; ctx.fillStyle = MUTED;
    ctx.fillText(clip(ctx, leg.note, box.w), box.x, y);
  }
  ctx.restore();
}

/* ---------- the composite ---------- */

function clip(ctx, s, max) {
  s = String(s == null ? "" : s);
  if (!s || ctx.measureText(s).width <= max) return s;
  let lo = 0, hi = s.length;
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (ctx.measureText(s.slice(0, mid) + "…").width <= max) lo = mid; else hi = mid - 1; }
  return s.slice(0, Math.max(1, lo)).replace(/[\s·,;:—–-]+$/, "") + "…";
}

function studyImage(o) {
  const leg = o.legend || { items: [], note: "" };
  const L = layout({ width: o.width, chartW: o.svgW, chartH: o.svgH, legH: legHeight(leg) });
  const scale = o.scale || 2;
  const c = document.createElement("canvas");
  c.width = Math.round(L.W * scale); c.height = Math.round(L.H * scale);
  const ctx = c.getContext("2d");
  ctx.scale(scale, scale);
  ctx.fillStyle = "#FFFFFF"; ctx.fillRect(0, 0, L.W, L.H);
  ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  ctx.font = "600 26px " + FONT; ctx.fillStyle = INK;
  ctx.fillText(clip(ctx, o.title, L.title.w), L.title.x, L.title.y + 24);
  ctx.font = "12px " + MONO; ctx.fillStyle = MUTED;
  ctx.fillText(clip(ctx, o.sub, L.title.w), L.title.x, L.title.y + 46);

  const drawChart = o.svg
    ? svgImage(o.svg).then(img => { ctx.drawImage(img, L.chart.x, L.chart.y, L.chart.w, L.chart.h); })
        .catch(() => {})
    : Promise.resolve().then(() => {
        ctx.fillStyle = CARD; ctx.fillRect(L.chart.x, L.chart.y, L.chart.w, L.chart.h);
        ctx.font = "14px " + MONO; ctx.fillStyle = MUTED; ctx.textAlign = "center";
        ctx.fillText("No chart is drawn for this indicator", L.chart.x + L.chart.w / 2, L.chart.y + L.chart.h / 2);
        ctx.textAlign = "left";
      });

  return drawChart
    .then(() => (o.mapEl ? drawMap(ctx, o.mapEl, L.map) : { basemap: true }))
    .then(res => {
      drawLegend(ctx, o.legendEl, L.map);
      drawSeriesLegend(ctx, L.legend, leg);
      ctx.strokeStyle = LINE; ctx.lineWidth = 1;
      ctx.strokeRect(L.map.x + .5, L.map.y + .5, L.map.w - 1, L.map.h - 1);
      ctx.strokeRect(L.chart.x + .5, L.chart.y + .5, L.chart.w - 1, L.chart.h - 1);
      ctx.font = "11px " + MONO; ctx.fillStyle = MUTED;
      const foot = o.foot + (o.mapEl && !res.basemap ? " · basemap omitted" : "");
      ctx.fillText(clip(ctx, foot, L.foot.w), L.foot.x, L.foot.y);
      return new Promise(done => c.toBlob(done, "image/png"));
    });
}

function download(blob, name) {
  if (!blob) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

/* the Charts view's own export: its SVG is already self-contained, so it only needs rasterising */
function png(svg, name, w, h) {
  return svgImage(svg).then(img => {
    const scale = 2;
    const c = document.createElement("canvas");
    c.width = (w || 1200) * scale; c.height = (h || 640) * scale;
    const ctx = c.getContext("2d");
    ctx.scale(scale, scale);
    ctx.fillStyle = "#FFFFFF"; ctx.fillRect(0, 0, w || 1200, h || 640);
    ctx.drawImage(img, 0, 0, w || 1200, h || 640);
    return new Promise(done => c.toBlob(done, "image/png"));
  }).then(b => download(b, name));
}

/* ⤓ PNG on the study row: whatever the panel is drawing, plus the mini map beside it */
function studyPng() {
  const panel = document.querySelector("[data-testid=chart-panel]");
  const card = document.querySelector("[data-testid=minimap]");
  const mapEl = card ? card.querySelector(".mapwrap>div[id]") : null;
  const legendEl = card ? card.querySelector("[data-testid=legend]") : null;
  const svgEl = panel ? panel.querySelector("svg.chart") : null;
  if (!panel && !mapEl) { toast("Nothing to export on this view."); return Promise.resolve(); }
  const ser = svgEl ? inlineSvg(svgEl) : null;
  let i = {}, area = "", per = "";
  try { i = curInd() || {}; area = presentArea(); per = period(i); } catch (e) {}
  const title = [area, i.short || i.label].filter(Boolean).join(" · ");
  const unit = typeof unitLabel === "function" ? unitLabel(i) : "";
  const sub = [per, unit, i.desc].filter(Boolean).join(" · ");
  return studyImage({
    svg: ser ? ser.text : "", svgW: ser ? ser.w : 1200, svgH: ser ? ser.h : 640,
    legend: seriesLegend(panel), mapEl, legendEl, title, sub, foot: footLine(),
  }).then(b => download(b, fileName(["study", i.key, area, per])))
    .catch(e => toast("The image could not be made: " + (e && e.message ? e.message : e)));
}

function toast(msg) {
  if (typeof exportToast === "function") { exportToast(msg); return; }
  if (typeof console !== "undefined") console.warn(msg);
}

/* ---------- wiring ----------
   Registered here rather than in app.js's own handlers so that this whole phase is one file, and
   first so that `P` and Esc reach it before the map's camera jumps and the area page's Esc-goes-
   back. A popover that is open owns Esc: leaving present mode with a menu still on screen would
   close the wrong thing. */
if (hasDom) {
  document.addEventListener("click", e => {
    const t = e.target;
    if (!t || !t.closest) return;
    if (t.closest("[data-present]")) { e.preventDefault(); toggle(); return; }
    if (t.closest("[data-studypng]")) { e.preventDefault(); studyPng(); }
  });
  document.addEventListener("keydown", e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const t = e.target;
    const typing = !!(t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || "") || t.isContentEditable));
    const popover = !!(typeof UI !== "undefined" && (UI.exOpen || UI.lyOpen || UI.navOpen || UI.mmFull))
      || !!(typeof IPK !== "undefined" && IPK.open);
    if (e.key === "Escape" && on() && !popover) { e.stopImmediatePropagation(); set(false); return; }
    if (!typing && (e.key === "p" || e.key === "P")) { e.stopImmediatePropagation(); e.preventDefault(); toggle(); }
  });
  /* the browser's own print dialog: Leaflet has to be told the page just changed shape, or the
     map prints as the grey tiles it had before the print stylesheet resized it */
  window.addEventListener("beforeprint", () => {
    (window.__maps || []).forEach(m => { try { m.invalidateSize(); } catch (err) {} });
  });
}

return { footerText, newestAsof, layout, legHeight, fileName, footLine, line, btn, pngBtn,
         apply, set, toggle, studyPng, studyImage, png, download, inlineSvg, SITE };
})();

if (typeof module !== "undefined" && module.exports) module.exports = PRESENT;
if (typeof window !== "undefined") window.PRESENT = PRESENT;
