/* AM Dashboard — Finland Edition · w5_core.js   (v2.2 W5 — package E, the Danish SHOULD list)

   The arithmetic behind W5's seven items, with no DOM, no state and no fetch in it, so
   `node --test tests/w5_core.test.js` can run every rule directly:

     · PICK10  pinned indicator chips — the list arithmetic and its cap
     · DATA8   `Columns ▾` — which groups are shown, and the `cols=` spelling in the URL
     · AREA7   the sub-area sparkline — points, gaps and the last marker
     · A11Y7   the keyboard sequences (`/`, `g m`, `[`, `]`, `?`) and the help list
     · SHEET4  grouping rows that describe one thing on the ground
     · §6      the return-period pair on a bar chart, and the tint its second bar takes
     · A11Y8   the sentence a screen reader is handed when the map drills

   Inlined into dist/index.html by scripts/build_dashboard.py as {{W5_JS}}, before every other
   script that reads it (`chartsvg.js`, `app.js`).
*/
"use strict";

var W5_CORE = (function () {

/* ---------- PICK10: pinned indicator chips ---------- */

/* Twelve is the Danish cap and it is a layout number, not a taste one: thirteen chips wrap the
   toolbar onto a third row at 1366 px, which is the width the map card was tuned for in W2 §1.
   The list is oldest-first, so pinning a thirteenth drops the one pinned longest ago rather than
   refusing the click — a reader who pins is telling us what matters now. */
const PINS_MAX = 12;

function pinsAdd(list, key, max) {
  const cap = max || PINS_MAX;
  const out = (list || []).filter(k => k && k !== key);
  out.push(key);
  return out.slice(Math.max(0, out.length - cap));
}
function pinsRemove(list, key) { return (list || []).filter(k => k && k !== key); }
/* `[` / `]` walk the chips. Standing on an indicator that is not pinned, `]` goes to the first
   chip and `[` to the last — otherwise the keys would do nothing at all from the common case. */
function pinsStep(list, cur, d) {
  const l = (list || []).filter(Boolean);
  if (!l.length) return "";
  const i = l.indexOf(cur);
  if (i < 0) return d > 0 ? l[0] : l[l.length - 1];
  return l[((i + d) % l.length + l.length) % l.length];
}
/* localStorage is not a given: Safari in private mode throws on write, and a browser with storage
   off throws on read. Pins are a convenience, so every access is wrapped and a failure is silent. */
function pinsParse(raw) {
  try {
    const v = JSON.parse(raw);
    return Array.isArray(v) ? v.filter(k => typeof k === "string" && k).slice(0, PINS_MAX) : [];
  } catch (e) { return []; }
}

/* ---------- DATA8: `Columns ▾` on Data › Areas ---------- */

/* The chooser works in indicator *groups*, not in single columns: the Areas table is 40+ columns
   wide and a per-column list would be the same wall of names the table already is. A group is
   also what the URL can carry without becoming unreadable — `cols=Market,Taxes`. */
function colGroups(list, order) {
  const seen = [];
  (list || []).forEach(i => { const g = (i && i.group) || "Other"; if (seen.indexOf(g) < 0) seen.push(g); });
  const ord = order || [];
  return seen.slice().sort((a, b) => {
    const x = ord.indexOf(a), y = ord.indexOf(b);
    return (x < 0 ? 1e6 : x) - (y < 0 ? 1e6 : y) || (a < b ? -1 : a > b ? 1 : 0);
  });
}
/* An empty selection means "every group" — the default, and what a link written before W5 says.
   A reader who wants to see nothing has the columns hidden one group at a time, and the selected
   indicator's own column is never taken away: it is what the table is sorted by. */
function colsFilter(list, groups, keepKey) {
  const g = (groups || []).filter(Boolean);
  if (!g.length) return (list || []).slice();
  return (list || []).filter(i => g.indexOf((i && i.group) || "Other") >= 0 || (keepKey && i.key === keepKey));
}
function colsParse(raw) {
  return String(raw == null ? "" : raw).split(",").map(s => s.trim()).filter(Boolean);
}
function colsStr(groups) { return (groups || []).filter(Boolean).join(","); }
/* ticking and un-ticking one group; the result keeps `colGroups` order so the URL is stable */
function colsToggle(groups, g, all) {
  const cur = (groups || []).length ? groups.slice() : (all || []).slice();
  const i = cur.indexOf(g);
  if (i >= 0) cur.splice(i, 1); else cur.push(g);
  const ord = all || [];
  const out = cur.slice().sort((a, b) => ord.indexOf(a) - ord.indexOf(b));
  /* back to every group = back to the default spelling, so the URL loses `cols=` rather than
     carrying a list that says the same thing as no list at all */
  return out.length === (all || []).length ? [] : out;
}

/* ---------- AREA7: the sub-area sparkline ---------- */

/* Ten years of one indicator, drawn inline. A gap in the series breaks the line rather than
   bridging it: a postal code that published nothing in 2019 did not hold its 2018 value. The
   scale is the row's own — a sparkline is a shape, not a figure, and the figure is in the cell
   beside it. */
function sparkSegments(values, w, h, pad) {
  const p = pad == null ? 2 : pad;
  const vals = (values || []).map(v => (v == null || isNaN(v)) ? null : Number(v));
  const live = vals.filter(v => v != null);
  if (live.length < 2) return null;
  const lo = Math.min(...live), hi = Math.max(...live), sp = (hi - lo) || 1;
  const n = vals.length;
  const x = k => (n < 2 ? 0 : k / (n - 1) * w);
  const y = v => h - p - (v - lo) / sp * (h - 2 * p);
  const segs = [];
  let cur = [];
  vals.forEach((v, k) => {
    if (v == null) { if (cur.length > 1) segs.push(cur.join(" ")); cur = []; return; }
    cur.push(x(k).toFixed(1) + "," + y(v).toFixed(1));
  });
  if (cur.length > 1) segs.push(cur.join(" "));
  const li = vals.map((v, k) => v == null ? -1 : k).filter(k => k >= 0).pop();
  const last = li >= 0 ? { x: +x(li).toFixed(1), y: +y(vals[li]).toFixed(1), v: vals[li] } : null;
  /* a single point with no neighbour is a dot, not a line — still worth drawing */
  return { segs, last, lo, hi, n: live.length };
}
/* the last `n` entries of a period list, in order */
function lastPeriods(periods, n) {
  const p = (periods || []).slice();
  return n > 0 ? p.slice(Math.max(0, p.length - n)) : p;
}

/* ---------- SHEET4: rows that are one thing on the ground ---------- */

/* The register publishes one row per building part, so a daycare with two wings arrives as two
   rows with the same name, the same category and the same service class, eleven metres apart and
   with addresses that differ by a staircase letter. On the property sheet those already collapse
   into one row with a count (TP9, which groups on name + use code + distance ±20 m); the
   public-building *list* is the one place they never did.
   `canJoin` is why the address is not in the key: two schools of the same name at opposite ends
   of a municipality are two schools, and the caller answers that with a distance. When the key
   matches but `canJoin` says no, the row starts a group of its own. Order is preserved: the first
   row of a group keeps the group's position, and it is the row the sheet link opens. */
function groupSame(rows, keyOf, canJoin) {
  const out = [], at = {};
  (rows || []).forEach(r => {
    const k = String(keyOf(r));
    const idx = at[k];
    if (idx != null && (!canJoin || canJoin(out[idx].row, r))) { out[idx].n++; return; }
    at[k] = out.length;
    out.push({ row: r, n: 1 });
  });
  return out;
}

/* ---------- §6: the return-period pair ---------- */

/* A guarded read of picker_core's flood family, so a build without the pair (or without the
   picker) draws the single bar it always drew instead of throwing. */
function rpFamilyOf(pc, key) {
  try { return (pc && pc.rpFamily) ? pc.rpFamily(key) : []; } catch (e) { return []; }
}
/* `#1C6B5C` mixed `t` of the way to white. The rarer return period is the same measurement of the
   same area, so it keeps the area's hue and only loses saturation — two unrelated colours would
   read as two areas. */
function tint(hex, t) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || ""));
  if (!m || !(t > 0)) return hex;
  const n = parseInt(m[1], 16);
  const mix = c => Math.round(c + (255 - c) * Math.min(1, t));
  const r = mix(n >> 16 & 255), g = mix(n >> 8 & 255), b = mix(n & 255);
  return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
}

/* ---------- A11Y7: the keyboard ---------- */

/* `g` is a prefix, the way it is in every mail client and code host: `g` then `m` goes to the Map.
   A pending `g` is dropped by anything that is not one of its four letters, so `g` followed by a
   stray key never fires a navigation the reader did not ask for. */
const GO_KEYS = { m: "map", d: "data", c: "charts", p: "property" };
function keySeq(pending, key) {
  const k = String(key || "");
  if (pending === "g") {
    const g = GO_KEYS[k.toLowerCase()];
    return { pending: "", action: g ? "go:" + g : "" };
  }
  if (k === "g" || k === "G") return { pending: "g", action: "" };
  if (k === "/") return { pending: "", action: "search" };
  if (k === "?") return { pending: "", action: "help" };
  if (k === "[") return { pending: "", action: "pin:prev" };
  if (k === "]") return { pending: "", action: "pin:next" };
  return { pending: "", action: "" };
}
/* what the ? overlay lists, in the order it lists them */
const SHORTCUTS = [
  ["/", "Focus the search box — the indicator search when a picker is open"],
  ["g m", "Go to the Map"],
  ["g d", "Go to Data"],
  ["g c", "Go to Charts"],
  ["g p", "Go to the Test property"],
  ["[  ]", "Previous / next pinned indicator"],
  ["+", "Pin the indicator that is showing (up to " + PINS_MAX + ")"],
  ["H T U O F", "Jump the map camera to Helsinki · Tampere · Turku · Oulu · all of Finland"],
  ["P", "Present mode — Esc leaves it"],
  ["?", "This list"],
  ["Esc", "Close a menu, a popover or a full-screen map"],
];

/* ---------- A11Y8: the drill announcement ---------- */

/* "Showing Helsinki, 84 postal codes" — what a sighted reader gets from the map redrawing itself,
   said once, in an `aria-live="polite"` region. Nothing is announced for a zoom: zooming never
   changes the selection, so there is nothing new to say. */
const DRILL_LABEL = { kunta: ["municipality", "municipalities"], postinumero: ["postal code", "postal codes"],
                      osa_alue: ["osa-alue", "osa-alueet"], building: ["building", "buildings"] };
function drillLine(name, n, level) {
  const lab = DRILL_LABEL[level] || DRILL_LABEL.kunta;
  const count = (n == null || isNaN(n)) ? "" : ", " + n + " " + (Number(n) === 1 ? lab[0] : lab[1]);
  return "Showing " + (name || "Finland") + count;
}

return { PINS_MAX, pinsAdd, pinsRemove, pinsStep, pinsParse,
         colGroups, colsFilter, colsParse, colsStr, colsToggle,
         sparkSegments, lastPeriods, groupSame, rpFamilyOf, tint,
         GO_KEYS, keySeq, SHORTCUTS, DRILL_LABEL, drillLine };
})();

if (typeof module !== "undefined" && module.exports) module.exports = W5_CORE;
if (typeof window !== "undefined") window.W5_CORE = W5_CORE;
