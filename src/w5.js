/* AM Dashboard — Finland Edition · w5.js   (v2.2 W5 — package E, the browser half)

   The five W5 items that draw something, in one place:

     1. PICK10 — the pinned chip row (`+` pins what is showing, `×` unpins, localStorage, max 12)
     2. DATA8  — `Columns ▾` on Data › Areas, and its popover
     3. AREA7  — one sub-area's sparkline cell
     4. A11Y7  — what each key sequence does, the `/` target, and the `?` overlay
     5. A11Y8  — the `aria-live` region the map drill writes into

   Like `src/present.js` this is a feature module, not a pure `*_core.js`: it reads `S`, `UI`,
   `MK`, `T`, `IPK` and calls `pickCtx()`, `indSet()`, `go()`, `esc()` and friends by name out of
   the one global lexical scope the build inlines every script into. The arithmetic behind all of
   it — the cap, the group filter, the sparkline points, the key sequences, the row grouping and
   the drill sentence — is `src/w5_core.js` and is node-tested there.

   Why a file and not app.js: app.js is 460 KB of a 460 KB budget. W5 moved the chart drawing out
   (`src/chartsvg.js`) and spends what that freed on the features, not on their plumbing.

   Inlined into dist/index.html by scripts/build_dashboard.py as {{W5UI_JS}}, before app.js.
*/
"use strict";

var W5 = (function () {

const WC = (typeof window !== "undefined" && window.W5_CORE) || {};

/* ---------- PICK10: the chip row is the reader's, once they pin anything ----------
   Until a reader pins something the row is the six quick chips v2.0 chose for them. `+` pins the
   indicator that is showing; from then on the row is **their** twelve, in the order they pinned
   them, each with a × that takes it off again. Nothing else changes: a chip is still a click that
   writes `ind=`, so a pinned row shares as the same links it always did.
   The pins live in localStorage and nowhere else — they are a convenience of this browser, not
   state a link carries, and a link that quietly re-pinned a stranger's chips would be worse than
   no pins at all. Every read and every write is wrapped: Safari in private mode throws on write. */
const PINS_LS = "amfi.pins.v1";
const PINS = { list: [], loaded: false };
function pinsLoad() {
  if (PINS.loaded) return PINS.list;
  PINS.loaded = true;
  try { PINS.list = WC.pinsParse(localStorage.getItem(PINS_LS)); } catch (e) { PINS.list = []; }
  return PINS.list;
}
function pinsSave() { try { localStorage.setItem(PINS_LS, JSON.stringify(PINS.list)); } catch (e) { /* storage off or full — the pins are this session's then */ } }
/* the indicators the chip row is actually showing, pinned or default, in the picker's own list */
function chipInds(target) {
  const c = pickCtx(target || "ind");
  const pinned = pinsLoad().map(k => c.list.find(x => x.key === k)).filter(Boolean);
  if (pinned.length) return { c, list: pinned, pinned: true };
  /* QUICK_KEYS is written for the kunta level; an osa-alue page has one of them (`growth`), and a
     one-chip row that is always filled tells nobody anything. Pad from the level's own list, in
     GROUP_ORDER, so the row is the same shape everywhere. */
  const seen = new Set(), ks = [];
  const take = key => { const i = c.list.find(x => x.key === key); if (i && !seen.has(key)) { seen.add(key); ks.push(i); } };
  QUICK_KEYS.forEach(take); CARD_KEYS.forEach(take);
  if (ks.length < 6) PC.grouped(c.list).forEach(([, l]) => l.forEach(i => { if (ks.length < 6) take(i.key); }));
  return { c, list: ks, pinned: false };
}
function indChips(target) {
  target = target || "ind";
  const r = chipInds(target), c = r.c, ks = r.list;
  const cur = c.list.find(i => i.key === c.key);
  const isPinned = pinsLoad().indexOf(c.key) >= 0;
  const add = cur ? `<button class="iqb iqadd ${isPinned ? "on" : ""}" data-pinadd="${esc(target)}" data-testid="pin-add"
      aria-pressed="${isPinned}" title="${isPinned ? "Unpin " + esc(cur.label) : "Pin " + esc(cur.label) + " to this row (up to " + WC.PINS_MAX + ")"}">${isPinned ? "−" : "+"}</button>` : "";
  if (!ks.length && !add) return "";
  return `<div class="iq ${r.pinned ? "iqpin" : ""}" data-testid="ind-chips" data-row="2" data-cpt="${esc(target)}">${ks.map(i =>
    `<button class="iqb ${c.key === i.key ? "on" : ""}" data-ind="${esc(i.key)}" data-pt="${esc(target)}" title="${esc(i.label)}">${esc(i.short || i.label)}${r.pinned ? `<i class="iqx" data-unpin="${esc(i.key)}" data-pt="${esc(target)}" role="button" aria-label="Unpin ${esc(i.label)}" title="Unpin">×</i>` : ""}</button>`).join("")}${add}</div>`;
}
/* pinning repaints the chip row and nothing else: a full render would drop and rebuild the map
   under a reader who only said "keep this one handy" (the same rule V5 wrote for the area page) */
function chipsRefresh() {
  document.querySelectorAll("[data-cpt]").forEach(el => { el.outerHTML = indChips(el.dataset.cpt); });
}
function pinAdd(target) {
  const c = pickCtx(target || "ind"); if (!c.key) return;
  pinsLoad();
  PINS.list = PINS.list.indexOf(c.key) >= 0 ? WC.pinsRemove(PINS.list, c.key) : WC.pinsAdd(PINS.list, c.key);
  pinsSave(); chipsRefresh();
}
function pinDrop(key) { PINS.list = WC.pinsRemove(pinsLoad(), key); pinsSave(); chipsRefresh(); }
/* `[` / `]` step the row that is on screen — the reader's pins where there are any, the six
   defaults where there are none, so the keys do something on a page nobody has pinned on yet */
function pinStep(d) {
  const el = document.querySelector("[data-cpt]");
  const target = el ? el.dataset.cpt : "ind";
  const r = chipInds(target);
  const key = WC.pinsStep(r.list.map(i => i.key), r.c.key, d);
  if (key && key !== r.c.key) indSet(target, key);
}

/* ---------- DATA8: `Columns ▾` on Data › Areas ---------- */

/* every group the level's own list has, in the picker's order — the chooser's rows */
function colGroupsFor() { return WC.colGroups(tableCols(true), PC.GROUP_ORDER); }
let COLS_OPEN = false;
function colsClose() {
  if (!COLS_OPEN) return;
  COLS_OPEN = false;
  document.querySelectorAll(".colspop").forEach(p => { p.hidden = true; });
  document.querySelectorAll("[data-colsopen]").forEach(b => b.setAttribute("aria-expanded", "false"));
}
function colsToggleMenu(btn) {
  const pop = btn.parentElement.querySelector(".colspop"); if (!pop) return;
  COLS_OPEN = pop.hidden;
  pop.hidden = !COLS_OPEN; btn.setAttribute("aria-expanded", COLS_OPEN ? "true" : "false");
  if (COLS_OPEN) pop.innerHTML = colsMenuBody();
}
function colsPick(g) {
  T.cols = WC.colsToggle(T.cols, g, colGroupsFor());
  syncHash();
  /* the head and the body are rewritten together — a header row and a body row that disagree on
     the column count is the one way this could ever print a figure under the wrong name */
  renderKeep();
}
function colsMenuBody() {
  const all = colGroupsFor(), on = T.cols.length ? T.cols : all, every = tableCols(true);
  /* buttons, not checkboxes in labels: a <label> forwards its click to its input, so the same
     click would arrive twice at the delegated handler and tick the group straight back off */
  return `<div class="colsh"><b>Columns</b><button class="lk mini" data-colsall ${T.cols.length ? "" : "disabled"}>show all</button></div>`
    + all.map(g => { const isOn = on.indexOf(g) >= 0;
      return `<button class="colsr ${isOn ? "on" : ""}" data-cols="${esc(g)}" role="menuitemcheckbox" aria-checked="${isOn}"><i>${isOn ? "✓" : ""}</i>${esc(g)}
        <span class="dim">${every.filter(i => (i.group || "Other") === g).length}</span></button>`; }).join("")
    + `<p class="cap">The indicator the table is sorted by always keeps its column. Every export carries every column whatever is ticked here.</p>`;
}
function colsBtn() {
  const all = colGroupsFor(), n = T.cols.length;
  return `<div class="colswrap"><button class="tbtn" data-colsopen data-testid="cols-btn" aria-haspopup="true" aria-expanded="false"
      title="Choose which indicator groups the table lists">Columns ▾${n ? `<span class="dtn">${n}/${all.length}</span>` : ""}</button>
    <div class="colspop" data-testid="cols-pop" hidden></div></div>`;
}

/* ---------- AREA7: one row's sparkline ----------
   Inline SVG, no library, `currentColor` so it inherits the table's ink (and prints). Fewer than
   two published years is a dash: two points make a line, one makes a claim about a trend that is
   not there. */
function subSpark(o, ind, ys) {
  const vals = ys.map(y => V(o, ind.key, y));
  const s = WC.sparkSegments(vals, 58, 18, 2);
  const live = vals.filter(v => v != null);
  if (!s || !s.segs.length) return `<td class="spk dim">–</td>`;
  const tip = `${ind.label} ${ys[0]}–${ys[ys.length - 1]}: ${fmtOf(ind)(s.lo)} – ${fmtOf(ind)(s.hi)}, ${live.length} of ${ys.length} years published`;
  return `<td class="spk"><svg class="minispk" data-testid="sub-spark" viewBox="0 0 58 18" width="58" height="18" preserveAspectRatio="none" role="img" aria-label="${esc(tip)}">
    ${s.segs.map(p => `<polyline points="${p}" fill="none" stroke="currentColor" stroke-width="1.4" vector-effect="non-scaling-stroke"/>`).join("")}
    ${s.last ? `<circle cx="${s.last.x}" cy="${s.last.y}" r="1.7" fill="currentColor"/>` : ""}<title>${esc(tip)}</title></svg></td>`;
}

/* ---------- A11Y7: what each sequence does ---------- */

/* the half-typed `g` */
const KEYS = { pending: "" };
const NAV_HREF = id => id === "property" ? anNavLink() : id === "table" ? dataTabHash(dataTab()) : viewOf(id)[3];
const GO_VIEW = { map: "makro", data: "table", charts: "charts", property: "property" };
function runShortcut(a) {
  if (a === "help") { helpOverlay(!UI.helpOpen); return; }
  if (a === "search") { focusSearch(); return; }
  if (a === "pin:prev") { pinStep(-1); return; }
  if (a === "pin:next") { pinStep(1); return; }
  if (a.indexOf("go:") === 0) { const id = GO_VIEW[a.slice(3)]; if (id) { navToggle(false); go(NAV_HREF(id)); } }
}
/* `/` goes to the search that is actually on the screen: the indicator picker's own box when a
   picker is open, otherwise the view's search field, in the order a reader would look for one. */
function focusSearch() {
  const sels = IPK.open ? [".ipkpop:not([hidden]) .ipks"] : [];
  const el = sels.concat(["#tq", "#mq", "#chq", "#tpq", "#mf-addr", "input[type=search]"])
    .map(s => document.querySelector(s)).find(x => x && x.getClientRects().length);
  if (el) { el.focus(); if (el.select) el.select(); return; }
  /* nothing to type into on this view — open the picker, which always has one */
  const b = document.querySelector("[data-ipkopen]"); if (b) ipkOpen(b.dataset.ipkopen);
}
/* the ? overlay: the list, and nothing the page has to carry when it is closed */
function helpOverlay(open) {
  UI.helpOpen = !!open;
  const old = document.getElementById("kbhelp");
  if (!UI.helpOpen) { if (old) old.remove(); return; }
  const el = old || document.createElement("div");
  el.id = "kbhelp"; el.className = "kbhelp"; el.setAttribute("role", "dialog");
  el.setAttribute("aria-modal", "true"); el.setAttribute("aria-label", "Keyboard shortcuts");
  el.dataset.testid = "kb-help";
  el.innerHTML = `<div class="kbcard"><div class="kbhead"><b>Keyboard shortcuts</b><button class="lk mini" data-helpclose aria-label="Close">×</button></div>
    <dl class="kblist">${(WC.SHORTCUTS || []).map(p => `<div><dt>${p[0].split(/\s+/).map(x => `<kbd>${esc(x)}</kbd>`).join(" ")}</dt><dd>${esc(p[1])}</dd></div>`).join("")}</dl>
    <p class="cap">Ignored while you are typing. <kbd>?</kbd> again or <kbd>Esc</kbd> closes this.</p></div>`;
  if (!old) document.body.appendChild(el);
  const b = el.querySelector("[data-helpclose]"); if (b) b.focus();
}

/* ---------- A11Y8: what the map just did, for a reader who cannot see it ----------
   One `aria-live="polite"` region in the document, written only when the sentence changes — so a
   zoom, which never changes the selection, never announces anything. */
let LIVE_SAID = "";
function announce(msg) {
  const el = document.getElementById("srlive");
  if (!el || !msg || msg === LIVE_SAID) return;
  LIVE_SAID = msg; el.textContent = msg;
}
function announceDrill() {
  if (S.view !== "makro") return;
  const m = MK.muni ? byCode[MK.muni] : null;
  const lv = mapDrawLevel();
  const n = !m ? MUNI.length : lv === "building" ? null : muniAreas(MK.muni).length;
  announce(WC.drillLine(m ? m.name : "Finland", n, lv));
}

return { PINS, pinsLoad, indChips, chipInds, chipsRefresh, pinAdd, pinDrop, pinStep,
         colGroupsFor, colsClose, colsToggleMenu, colsPick, colsBtn, subSpark,
         KEYS, runShortcut, focusSearch, helpOverlay, announce, announceDrill };
})();

if (typeof window !== "undefined") window.W5 = W5;
