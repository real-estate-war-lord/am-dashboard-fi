/* AM Dashboard — Finland Edition · scale_core.js
   The y axis every chart in this build shares (v2.2 W2 §3) — no DOM, no state, no fetch, so
   `node --test tests/scale.test.js` can run it.

   Three rules, written down once so the area page, the property page, the Charts view and the
   downloaded PNG cannot disagree about them:

   1. **Nice ticks.** A gridline lands on 1, 2, 2.5 or 5 × 10^n and nothing else, and the range is
      widened out to the nearest one rather than padded by a percentage. Every tick is therefore a
      multiple of the step, which is what makes `0` land on a gridline whenever the range crosses
      it — a reader of a signed indicator has to be able to see which side of zero a point is on.
      An all-positive range is never widened below 0: a count has no negative part.
   2. **The range comes from the years every drawn series covers.** An osa-alue that starts in 2014
      plotted against the median of all osa-alueet, whose own 2011–2012 jumps ±17 % where areas were
      redrawn, otherwise renders the area's own line as a flat thread at the bottom of the card. The
      years the series share are the ones a reader can actually compare, so they set the scale.
   3. **Nothing is dropped.** A value the axis cannot show is reported in `clipped` (by its label,
      not its index) so the caller can draw it at the edge with a ▲ / ▼ marker, keep the real figure
      in its tooltip, and print a note naming the years the scale leaves out.

   Inlined into dist/index.html by scripts/build_dashboard.py as {{SCALE_JS}}.
*/
"use strict";

var SCALE_CORE = (function () {

/* 0.1 + 0.2 must not become a tick label: every number this module hands back is snapped to
   twelve significant digits, and anything within a rounding error of zero *is* zero — the zero
   line and the "does this range cross zero" test both depend on that being exact. */
const q = v => { if (v == null || !isFinite(v)) return v; const r = +Number(v).toPrecision(12); return Math.abs(r) < 1e-12 ? 0 : r; };

/* the only step sizes a gridline may use */
const NICE = [1, 2, 2.5, 5, 10];

/* the smallest nice step that is at least `raw` */
function niceStep(raw) {
  if (!(raw > 0) || !isFinite(raw)) return 1;
  const e = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / e;
  for (let k = 0; k < NICE.length; k++) if (f <= NICE[k] + 1e-9) return q(NICE[k] * e);
  return q(10 * e);
}

/* [lo, hi] widened to whole steps, with the ticks between them. `want` is a wish, not a promise:
   widening to the nearest step can add one tick at either end. */
function niceTicks(lo, hi, want) {
  const n = Math.max(2, want || 5);
  if (!isFinite(lo) || !isFinite(hi)) return { lo: 0, hi: 1, step: 1, ticks: [0, 1], zero: true };
  if (hi < lo) { const t = lo; lo = hi; hi = t; }
  if (hi === lo) { const d = Math.abs(hi) * .05 || 1; lo -= d; hi += d; }
  const step = niceStep((hi - lo) / (n - 1));
  /* an all-positive series keeps 0 as its floor: padding a count or a rate below zero invents a
     part of the axis the data cannot reach */
  let t0 = q(Math.floor(lo / step + 1e-9) * step);
  if (lo >= 0 && t0 < 0) t0 = 0;
  const t1 = q(Math.ceil(hi / step - 1e-9) * step);
  const ticks = []; const steps = Math.max(1, Math.round((t1 - t0) / step));
  for (let k = 0; k <= steps; k++) ticks.push(q(t0 + k * step));
  return { lo: t0, hi: ticks[ticks.length - 1], step, ticks, zero: ticks.some(t => t === 0) };
}

/* does a series have a value at all? */
const live = s => !!(s && s.pts && s.pts.some(p => p && p.v != null));
const at = (s, i) => { const p = s && s.pts && s.pts[i]; return p && p.v != null ? p.v : null; };

/* the first index any drawn series has a value at — where the x axis starts (§3c). -1 when none. */
function firstLive(series, n) {
  for (let i = 0; i < n; i++) if ((series || []).some(s => at(s, i) != null)) return i;
  return -1;
}

/* the indices every drawn series covers; [] when they share fewer than two, or when there is only
   one series (then its own years *are* the shared ones and nothing has to be excluded) */
function sharedIdx(series, n) {
  const ls = (series || []).filter(live);
  if (ls.length < 2) return [];
  const out = [];
  for (let i = 0; i < n; i++) if (ls.every(s => at(s, i) != null)) out.push(i);
  return out.length >= 2 ? out : [];
}

/* the raw range: read off the shared years where there are some, off everything otherwise */
function range(series, labels) {
  const n = (labels || []).length, ls = (series || []).filter(live);
  if (!ls.length || !n) return null;
  const idx = sharedIdx(ls, n), vals = [];
  const use = idx.length ? idx : labels.map((_, i) => i);
  ls.forEach(s => use.forEach(i => { const v = at(s, i); if (v != null) vals.push(v); }));
  if (!vals.length) return null;
  return { lo: Math.min.apply(null, vals), hi: Math.max.apply(null, vals), shared: !!idx.length };
}

/* "2011–2012" for a run of years, "2011–2012, 2019" for two runs; anything that is not a plain
   year (a quarter label) is listed as it came in */
function spanText(list) {
  const l = [];
  (list || []).forEach(x => { const s = String(x); if (l.indexOf(s) < 0) l.push(s); });
  if (!l.length) return "";
  if (!l.every(s => /^\d{4}$/.test(s))) return l.join(", ");
  const n = l.map(Number).sort((a, b) => a - b), out = [];
  let a = n[0], b = n[0];
  for (let i = 1; i <= n.length; i++) {
    if (i < n.length && n[i] === b + 1) { b = n[i]; continue; }
    out.push(a === b ? String(a) : a + "–" + b);
    if (i < n.length) { a = n[i]; b = n[i]; }
  }
  return out.join(", ");
}

/* Everything a chart needs from its data: where the x axis starts, the y range and its ticks, and
   which labels hold a value the axis cannot show.

   `opts.fmt` is the caller's own number formatter; it is used to make sure two gridlines never
   carry the same label (a 0,25 step under a 0-decimal format would print "0 0 1 1"), by asking for
   fewer ticks until they are all distinct — down to the two endpoints, which is the floor. */
function axis(series, labels, opts) {
  const o = opts || {}, n = (labels || []).length;
  const r = range(series, labels);
  if (!r) return null;
  const fmt = o.fmt || String;
  let ax = niceTicks(r.lo, r.hi, o.want || 6);
  for (let k = (o.want || 6); k >= 2; k--) {
    ax = niceTicks(r.lo, r.hi, k);
    const l = ax.ticks.map(fmt);
    if (new Set(l).size === l.length) break;
  }
  const clipped = [];
  for (let i = 0; i < n; i++)
    if ((series || []).some(s => { const v = at(s, i); return v != null && (v < ax.lo - 1e-9 || v > ax.hi + 1e-9); }))
      clipped.push(String(labels[i]));
  return { lo: ax.lo, hi: ax.hi, step: ax.step, ticks: ax.ticks, zero: ax.zero,
           from: firstLive(series, n), shared: r.shared, clipped,
           note: clipped.length ? "scale excludes " + spanText(clipped) : "" };
}

return { q, NICE, niceStep, niceTicks, firstLive, sharedIdx, range, spanText, axis };
})();

if (typeof module !== "undefined" && module.exports) module.exports = SCALE_CORE;
if (typeof window !== "undefined") window.SCALE_CORE = SCALE_CORE;
