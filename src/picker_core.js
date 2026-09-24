/* AM Dashboard — Finland Edition · picker_core.js
   The parts of the indicator picker and the period control that are a function of the indicator
   registry alone — no DOM, no state, no fetch — so `node --test tests/picker.test.js` can run them.

   The one rule they encode: **the period control is a function of the active indicator**, not a
   separate setting. An indicator with a year series gets a year select; an Outlook indicator gets a
   projection badge and no year (a year select next to a 2040 figure reads as an actual); a flood
   indicator gets the return-period switch; anything published once gets its as-of, and no control.

   Inlined into dist/index.html by scripts/build_dashboard.py as {{PICKER_JS}}.
*/
"use strict";

var PICKER_CORE = (function () {

/* the order groups are listed in, everywhere a list of indicators is shown */
const GROUP_ORDER = ["Demographics", "Income & jobs", "Housing stock", "Market", "Construction",
                     "Taxes", "Safety", "Climate", "Outlook", "Schools", "Growth signals"];
/* the pill on a group header that warns the period control is about to change shape */
const GROUP_PILL = { Outlook: "Projection", Climate: "Return period" };
/* the sub-heading inherited indicators are listed under on a postinumero or osa-alue page */
const GROUP_INHERITED = "From the municipality";

/* ---------- period modes ---------- */

/* A flood indicator carries its return period in its own key: the publisher draws two separate
   rasters, a 1-in-100 and a 1-in-1000 chance in any given year, and they are two measurements, not
   two views of one. So the control *swaps the indicator* rather than adding a URL key — and the
   pair below is the only place that relationship is written down. */
const RP_SUFFIX = { "100": "1/100a", "1000": "1/1000a" };
const RP_RE = /^(flood_(?:sea|river))_(100|1000)$/;

function rpParts(key) {
  const m = RP_RE.exec(String(key || ""));
  return m ? { base: m[1], rp: m[2] } : null;
}
/* every return period this family publishes, in order, as [{rp, key, label}] */
function rpFamily(key) {
  const p = rpParts(key);
  if (!p) return [];
  return Object.keys(RP_SUFFIX).map(rp => ({ rp, key: p.base + "_" + rp, label: RP_SUFFIX[rp] }));
}
const rpLabel = rp => RP_SUFFIX[String(rp)] || "";

/* `year` (a history to step through) · `returnperiod` (the flood pair) · `projection` (one vintage,
   no year) · `asof` (published once — the as-of is stated, there is nothing to choose) */
function periodMode(ind, years) {
  if (!ind) return "asof";
  if (ind.proj) return "projection";
  if (rpParts(ind.key)) return "returnperiod";
  return (years && years.length > 1) ? "year" : "asof";
}
/* which URL key that mode writes. A return period writes none: it is the indicator. */
const PERIOD_KEY = { year: "y", returnperiod: "", projection: "", asof: "" };

/* "Projection 2026→2040 · Tilastokeskus Väestöennuste 2024" */
function projBadge(ind) {
  const p = (ind && ind.proj) || null;
  if (!p) return "";
  return `Projection ${p.from}→${p.to} · ${p.publisher || ""} ${p.vintage || ""}`.replace(/\s+$/, "");
}

/* ---------- grouping and search ---------- */

/* [[groupName, [ind, …]], …] in GROUP_ORDER, with anything unlisted last under "Other", and the
   inherited ones pulled out into their own group at the end when `isInherited` says so. */
function grouped(list, isInherited) {
  const own = [], inh = [];
  (list || []).forEach(i => ((isInherited && isInherited(i)) ? inh : own).push(i));
  const by = {};
  own.forEach(i => { const g = GROUP_ORDER.indexOf(i.group) >= 0 ? i.group : (i.group || "Other"); (by[g] = by[g] || []).push(i); });
  const names = GROUP_ORDER.filter(g => by[g]).concat(Object.keys(by).filter(g => GROUP_ORDER.indexOf(g) < 0).sort());
  const out = names.map(g => [g, by[g]]);
  if (inh.length) out.push([GROUP_INHERITED, inh]);
  return out;
}

/* every word of the query has to hit somewhere in label · short · group · unit · key */
function matches(ind, q) {
  const words = String(q || "").toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return true;
  const hay = [ind.label, ind.short, ind.group, ind.unit, ind.key].filter(Boolean).join(" ").toLowerCase();
  return words.every(w => hay.indexOf(w) >= 0);
}
function filter(list, q) { return (list || []).filter(i => matches(i, q)); }

/* the right-aligned tag on a picker row: where the figure comes from, or what span it covers */
function availTag(ind, ctx) {
  ctx = ctx || {};
  if (ctx.inherited) return "muni";
  if (ind.proj) return `${ind.proj.from}→${ind.proj.to}`;
  if (rpParts(ind.key)) return rpLabel(rpParts(ind.key).rp);
  const ys = ctx.years || ind.years || [];
  if (ys.length > 1) return `${ys[0]}–`;
  if (ys.length === 1) return String(ys[0]);
  return "snapshot";
}

/* ↑ / ↓ over a list that wraps at both ends */
function step(i, len, d) { return len ? ((i + d) % len + len) % len : -1; }

/* which ramp a value of this indicator is drawn in — the three never share a legend */
function ramp(ind) {
  if (!ind) return "observed";
  if (ind.proj) return "projection";
  if ((ind.group || "") === "Climate") return "climate";
  return "observed";
}

return { GROUP_ORDER, GROUP_PILL, GROUP_INHERITED, RP_SUFFIX, rpParts, rpFamily, rpLabel,
         periodMode, PERIOD_KEY, projBadge, grouped, matches, filter, availTag, step, ramp };
})();

if (typeof module !== "undefined" && module.exports) module.exports = PICKER_CORE;
if (typeof window !== "undefined") window.PICKER_CORE = PICKER_CORE;
