/* AM Dashboard — Finland Edition · ramp_core.js
   The colour model for **signed** indicators — the ones whose published values fall on both sides of
   zero (population growth, net migration, every y/y change, the Väestöennuste deltas, the crime
   trend). No DOM, no state, no fetch, so `node --test tests/ramp.test.js` can run all of it.

   Why it exists (owner request, 2026-09-25). Until v2.0 a signed indicator was drawn with the same
   quantile ramp as a level: five green classes over the quantiles of |v − centre|. Three things were
   wrong with that. The breaks moved every time the data was refetched, so the same municipality
   changed colour without changing. Zero — the one break a reader of a growth rate actually wants —
   was invisible, sitting somewhere inside a class. And a shrinking municipality was drawn in the
   same green as a growing one, only a shade lighter.

   The rule instead: **fixed breaks, centred on zero.** Two classes above zero and two below, at
   ±t and (when the data is that spread out) ±3t, where `t` is a per-indicator threshold chosen for
   readability and written down once, in SIGNED below. Green above zero, brick red below — and the
   other way round for an indicator where an increase is the bad news (`crime_trend`). Exactly 0 is
   a positive value here: it lands in the `0 … +t` class, so the reader never has to wonder which
   side of the line a flat year fell on.

   Inlined into dist/index.html by scripts/build_dashboard.py as {{RAMP_JS}}.
*/
"use strict";

var RAMP_CORE = (function () {

/* ---------- which indicators are signed, and at what threshold ----------

   One table, and the only place a threshold is written down. An indicator belongs here when its
   *published* values straddle zero — not when they could in principle. `fc_80p` (projected change
   in the 80+ population) is signed in arithmetic and +8.7 % … +108 % in fact: every kunta is
   growing old, so it keeps the sequential ramp and its darkest class still means "most".

   The thresholds come from the owner's rule (growth 0.5 %/yr; net migration 5 per 1 000; price and
   rent change 2 %; the 2026→2040 outlook 5 %; the crime trend 5 %) and are extended to the rest of
   the same families on the same logic — see docs/v2_1/DECISIONS.md V2. */
const SIGNED = {
  growth:          0.5,    /* % / yr            — population growth, kunta · postinumero · osa-alue */
  migration:       5,      /* per 1 000 inh.    — net migration */
  migration_dom:   5,      /* per 1 000 inh.    — intermunicipal net migration */
  rent_yoy:        2,      /* %                 — rent change, year on year */
  crime_trend:     5,      /* %                 — reported offences y/y; an increase is the bad news */
  fc_growth:       5,      /* %                 — projected population change 2026→2040 */
  fc_growth_5y:    2,      /* %                 — the same over 2026→2031, so a smaller window */
  fc_abs:          500,    /* residents         — projected change in residents 2026→2040 */
  fc_pop_rate_5y:  5,      /* per 1 000 / yr    — projected population change per year */
  fc_0_6:          5,      /* %                 — projected change, aged 0–6 */
  fc_7_15:         5,      /* %                 — projected change, aged 7–15 */
  fc_20_34:        5,      /* %                 — projected change, aged 20–34 */
  fc_20_34_rel:    2       /* pp                — projected 20–34 share against Finland's */
};
const isSigned = key => Object.prototype.hasOwnProperty.call(SIGNED, String(key == null ? "" : key));
const thresholdOf = key => isSigned(key) ? SIGNED[key] : null;

/* ---------- the classes ----------

   Four classes by default. A sixth pair is added when the middle four would hide most of the
   spread: if **more than 20 % of the areas being drawn** lie beyond ±3t, `> +3t` and `< −3t` get
   their own, darker class. That is the one thing the ramp reads off the data, and it reads it off
   the values actually on screen, so a national map and a single kunta's postal codes each get the
   classing their own spread deserves. The breaks themselves never move. */
const WIDE_SHARE = 0.20;
function beyond(vals, t) {
  const v = (vals || []).filter(x => x != null && !isNaN(x));
  if (!v.length || !(t > 0)) return 0;
  return v.filter(x => Math.abs(x) > 3 * t).length / v.length;
}
const needsWide = (vals, t) => beyond(vals, t) > WIDE_SHARE;
/* The sixth class is an **indicator-wide** decision, taken once over every level the build ships —
   never per map. If it were taken per map, the same +2 % would be one green on the national map
   and a different one in a kunta's mini map, and "the same ramp everywhere" would be a claim
   rather than a fact. A level with too few published values cannot swing the decision. */
const MIN_LEVEL_N = 30;
function wideFor(levels, t) {
  return (levels || []).some(v => {
    const clean = (v || []).filter(x => x != null && !isNaN(x));
    return clean.length >= MIN_LEVEL_N && needsWide(clean, t);
  });
}
/* ascending, so a class index is also a rank: 0 is the most negative class */
const breaksFor = (t, wide) => wide ? [-3 * t, -t, 0, t, 3 * t] : [-t, 0, t];
/* `>=`, not `>`: that is what puts an exact 0 in the `0 … +t` class rather than in `−t … 0`,
   and it also means the bottom class is `< −t` and the top one `> +t`, as the legend says. */
function classOf(v, breaks) {
  if (v == null || isNaN(v)) return null;
  let c = 0; while (c < breaks.length && v >= breaks[c]) c++;
  return c;
}

/* ---------- the colours ----------

   Greens are the observed ramp's own hue (#0A5846, `hue: [10, 88, 70]` in config/indicators.json)
   at two or three strengths; reds are the owner's brick red (#B5523B) family, dark enough at the
   extreme to clear 3:1 against its own light class on a paper background. Purple is the projection
   family (`--proj`): an Outlook indicator keeps purple on the positive side and takes the same red
   on the negative one, so a projection is never mistaken for an observation.

   Lightest first — the class nearest zero is the palest, the extreme class the darkest, on both
   sides. Magnitude is lightness, direction is hue. */
const SHADES = {
  green: { 2: ["#9FBEB2", "#0A5140"], 3: ["#B4D0C5", "#4F8B79", "#0A4B3B"] },
  red:   { 2: ["#DFA694", "#8A3A26"], 3: ["#EFC2B3", "#C0644A", "#7C3121"] },
  purple:{ 2: ["#B0A8CE", "#4A3B86"], 3: ["#C5BFE0", "#7568AC", "#42357A"] }
};
const NODATA = "#C4CBC4";
/* which hue carries the *favourable* side of zero; the other side is always the red */
const GOOD_HUE = { observed: "green", projection: "purple", climate: "green" };

function rgbOf(hex) {
  const h = String(hex).replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
/* WCAG relative luminance and contrast ratio — the ramp's own contrast claims are asserted in
   tests/ramp.test.js rather than asserted in prose. */
function lum(hex) {
  const c = rgbOf(hex).map(x => { const s = x / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contrast(a, b) {
  const la = lum(a), lb = lum(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}
/* a swatch is "warm" or "cool"; the no-data grey is neither, which is how a pale tint is told from
   "no figure published" without relying on lightness (grey sits mid-scale, so no colour on either
   ramp can reach 3:1 against it — see docs/v2_1/DECISIONS.md V2) */
const warmth = hex => { const c = rgbOf(hex); return c[0] - c[1]; };
/* how far a colour is from grey at all: the no-data grey has a chroma of 7, every ramp swatch ≥ 24 */
const chroma = hex => { const c = rgbOf(hex); return Math.max.apply(null, c) - Math.min.apply(null, c); };

/* ---------- the scale ----------

   `family` is PICKER_CORE.ramp(ind): "observed" | "projection" | "climate".
   `flip` is true for a lower-is-better indicator, where an increase is the red news. */
function signedScale(vals, t, opts) {
  const o = opts || {};
  const v = (vals || []).filter(x => x != null && !isNaN(x)).sort((a, b) => a - b);
  if (!(t > 0)) return null;
  const wide = o.wide != null ? !!o.wide : needsWide(v, t);
  const breaks = breaksFor(t, wide);
  const classes = breaks.length + 1;
  const zero = wide ? 3 : 2;                     /* the first class above zero */
  const per = zero;                              /* shades a side needs: 2 or 3 */
  const good = GOOD_HUE[o.family] || "green";
  const flip = !!o.flip;
  const hi = flip ? "red" : good, lo = flip ? good : "red";
  const shadeOf = c => {
    if (c == null) return NODATA;
    /* depth 0 = the class touching zero, depth per-1 = the open-ended extreme */
    return c >= zero ? SHADES[hi][per][c - zero] : SHADES[lo][per][zero - 1 - c];
  };
  const sc = {
    signed: true, wide, t0: t, breaks, classes, zero, flip, family: o.family || "observed",
    n: v.length, lo: v.length ? v[0] : null, hi: v.length ? v[v.length - 1] : null,
    beyond: beyond(v, t),
    cls: x => classOf(x, breaks),
    /* 0…1 with the class index spread over it, so every existing caller that asks a scale for a
       `t` and hands it to a shader keeps working */
    t: x => { const c = classOf(x, breaks); return c == null ? null : c / (classes - 1); },
    /* the inverse: a shade for a t the caller already has */
    shade: tt => tt == null ? NODATA : shadeOf(Math.round(Math.max(0, Math.min(1, tt)) * (classes - 1))),
    shadeOfClass: shadeOf,
    colorOf: x => shadeOf(classOf(x, breaks))
  };
  return sc;
}

/* ---------- the legend ----------

   One label per class, ascending, so `labels(sc, f, unit)[sc.classes - 1]` is the top bin. `f`
   formats a number the way the rest of the UI does (fi-FI, signed, no unit); `unit` is appended
   once per row, because "> +0,5 %" is what the reader is looking for and "> +0,5" is not. */
const DASH = "…";                                    /* … */
function labels(sc, f, unit) {
  const u = unit ? " " + unit : "";
  const b = sc.breaks, n = sc.classes;
  const out = [];
  for (let c = 0; c < n; c++) {
    if (c === 0) out.push("< " + f(b[0]) + u);
    else if (c === n - 1) out.push("> " + f(b[n - 2]) + u);
    else out.push(f(b[c - 1]) + " " + DASH + " " + f(b[c]) + u);
  }
  return out;
}
/* Which way round the colours read. Stated as fact, never as a verdict: the ramp says which side of
   zero a value is on and how far, and for an indicator where an increase is the bad news it says
   that an increase is the red one. */
function legendNote(sc) {
  if (sc.flip) return "an increase is red, a fall is green — lower is better";
  if (sc.family === "projection") return "projected change · purple above zero, red below";
  return "green above zero, red below";
}
/* the footer every signed legend carries, so a reader knows the bins will not have moved next year */
const LEGEND_FOOTER = "fixed breaks, centred on zero";

return { SIGNED, SHADES, NODATA, GOOD_HUE, WIDE_SHARE, MIN_LEVEL_N, DASH, LEGEND_FOOTER,
         isSigned, thresholdOf, beyond, needsWide, wideFor, breaksFor, classOf, signedScale,
         labels, legendNote, contrast, lum, warmth, chroma, rgbOf };
})();

if (typeof module !== "undefined" && module.exports) module.exports = RAMP_CORE;
if (typeof window !== "undefined") window.RAMP_CORE = RAMP_CORE;
