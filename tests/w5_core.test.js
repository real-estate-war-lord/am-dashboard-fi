/* node --test tests/w5_core.test.js — the arithmetic behind v2.2 W5 (the Danish SHOULD list):
   the pinned-chip list and its cap, the column chooser's group set and its URL spelling, the
   sub-area sparkline's points and gaps, the key sequences, the row grouping, the return-period
   tint and the drill sentence (src/w5_core.js).

   Nothing here touches the DOM, localStorage or the network: what is tested is the rule, and the
   browser halves that read it are `src/w5.js` and `src/chartsvg.js`. */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const W = require("../src/w5_core.js");

/* ---------- PICK10 ---------- */

test("pinning appends, never duplicates, and re-pinning moves to the end", () => {
  assert.deepEqual(W.pinsAdd([], "growth"), ["growth"]);
  assert.deepEqual(W.pinsAdd(["growth"], "rent"), ["growth", "rent"]);
  assert.deepEqual(W.pinsAdd(["growth", "rent"], "growth"), ["rent", "growth"]);
});

test("the twelfth pin is the last one kept — the thirteenth drops the oldest, it never refuses", () => {
  let l = [];
  for (let i = 0; i < W.PINS_MAX; i++) l = W.pinsAdd(l, "k" + i);
  assert.equal(l.length, W.PINS_MAX);
  assert.equal(l[0], "k0");
  l = W.pinsAdd(l, "new");
  assert.equal(l.length, W.PINS_MAX, "the cap holds");
  assert.equal(l[0], "k1", "the one pinned longest ago is the one that goes");
  assert.equal(l[l.length - 1], "new");
});

test("unpinning removes exactly one key and leaves the order alone", () => {
  assert.deepEqual(W.pinsRemove(["a", "b", "c"], "b"), ["a", "c"]);
  assert.deepEqual(W.pinsRemove(["a", "b", "c"], "zz"), ["a", "b", "c"]);
  assert.deepEqual(W.pinsRemove(null, "a"), []);
});

test("[ and ] wrap, and start at an end when the current indicator is not on the row", () => {
  const l = ["a", "b", "c"];
  assert.equal(W.pinsStep(l, "a", 1), "b");
  assert.equal(W.pinsStep(l, "c", 1), "a", "] wraps to the first");
  assert.equal(W.pinsStep(l, "a", -1), "c", "[ wraps to the last");
  assert.equal(W.pinsStep(l, "zz", 1), "a", "standing outside the row, ] enters at the front");
  assert.equal(W.pinsStep(l, "zz", -1), "c", "and [ at the back");
  assert.equal(W.pinsStep([], "a", 1), "", "an empty row does nothing rather than throwing");
});

test("a corrupt or missing localStorage value reads as no pins, never as a crash", () => {
  assert.deepEqual(W.pinsParse(null), []);
  assert.deepEqual(W.pinsParse("not json"), []);
  assert.deepEqual(W.pinsParse('{"a":1}'), [], "an object is not a pin list");
  assert.deepEqual(W.pinsParse('["a",3,null,"b"]'), ["a", "b"], "non-strings are dropped");
  assert.equal(W.pinsParse(JSON.stringify(new Array(40).fill("x"))).length, W.PINS_MAX);
});

/* ---------- DATA8 ---------- */

const INDS = [{ key: "rent", group: "Market" }, { key: "price_m2", group: "Market" },
              { key: "growth", group: "Demographics" }, { key: "tax_home", group: "Taxes" },
              { key: "odd", group: "Not a group we know" }];

test("the chooser lists the groups that are actually there, in the picker's order", () => {
  const order = ["Demographics", "Market", "Taxes"];
  assert.deepEqual(W.colGroups(INDS, order), ["Demographics", "Market", "Taxes", "Not a group we know"]);
});

test("no selection means every column — which is what a link written before W5 says", () => {
  assert.equal(W.colsFilter(INDS, []).length, INDS.length);
  assert.equal(W.colsFilter(INDS, null).length, INDS.length);
});

test("a selection hides the rest, but never the column the table is sorted by", () => {
  const got = W.colsFilter(INDS, ["Taxes"], "growth").map(i => i.key);
  assert.deepEqual(got, ["growth", "tax_home"].sort(), got.sort());
  assert.deepEqual(W.colsFilter(INDS, ["Taxes"]).map(i => i.key), ["tax_home"]);
});

test("cols= round-trips, and ticking every group back on drops the key rather than listing them all", () => {
  const all = ["Demographics", "Market", "Taxes"];
  assert.deepEqual(W.colsParse("Market, Taxes"), ["Market", "Taxes"]);
  assert.deepEqual(W.colsParse(""), []);
  assert.equal(W.colsStr(["Market", "Taxes"]), "Market,Taxes");
  /* from "everything" (the default), un-ticking one group names the other two */
  const off = W.colsToggle([], "Market", all);
  assert.deepEqual(off, ["Demographics", "Taxes"]);
  /* ticking it back on is the default again, and the URL loses `cols=` */
  assert.deepEqual(W.colsToggle(off, "Market", all), []);
});

/* ---------- AREA7 ---------- */

test("a sparkline is one polyline over the years that have a figure", () => {
  const s = W.sparkSegments([1, 2, 3, 4], 60, 20, 2);
  assert.equal(s.segs.length, 1);
  assert.equal(s.segs[0].split(" ").length, 4);
  assert.equal(s.lo, 1); assert.equal(s.hi, 4);
  assert.equal(s.last.v, 4);
  assert.equal(s.last.x, 60, "the last point sits on the right edge");
});

test("a year the publisher did not publish breaks the line — it is never bridged", () => {
  const s = W.sparkSegments([1, 2, null, null, 5, 6], 50, 20, 2);
  assert.equal(s.segs.length, 2, "two runs, not one line across the gap");
  assert.equal(s.last.v, 6);
});

test("fewer than two published years draws nothing — one point is not a trend", () => {
  assert.equal(W.sparkSegments([null, 3, null], 50, 20, 2), null);
  assert.equal(W.sparkSegments([], 50, 20, 2), null);
});

test("a flat series still draws, on a line through the middle rather than dividing by zero", () => {
  const s = W.sparkSegments([7, 7, 7], 60, 20, 2);
  const ys = s.segs[0].split(" ").map(p => Number(p.split(",")[1]));
  assert.ok(ys.every(y => Number.isFinite(y)), s.segs[0]);
  assert.ok(ys.every(y => y === ys[0]), "a flat series is a flat line");
});

test("the sparkline shows the last ten periods, and everything it has when there are fewer", () => {
  const ys = ["2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022"];
  assert.deepEqual(W.lastPeriods(ys, 10), ys.slice(2));
  assert.deepEqual(W.lastPeriods(["2020", "2021"], 10), ["2020", "2021"]);
  assert.deepEqual(W.lastPeriods([], 10), []);
});

/* ---------- SHEET4 ---------- */

test("rows that describe one thing on the ground become one row with a count", () => {
  const rows = [{ n: "Hospital", a: "X 1" }, { n: "Hospital", a: "X 1" }, { n: "Hospital", a: "X 1" },
                { n: "School", a: "Y 2" }, { n: "Hospital", a: "Z 9" }];
  const g = W.groupSame(rows, r => r.n + "|" + r.a);
  assert.deepEqual(g.map(x => [x.row.n, x.row.a, x.n]),
                   [["Hospital", "X 1", 3], ["School", "Y 2", 1], ["Hospital", "Z 9", 1]]);
  assert.equal(g[0].row, rows[0], "the row kept is the first of its group, so the sheet it opens is real");
});

test("nothing is grouped when nothing agrees, and the order never moves", () => {
  const rows = [{ k: "a" }, { k: "b" }, { k: "c" }];
  assert.deepEqual(W.groupSame(rows, r => r.k).map(x => x.row.k), ["a", "b", "c"]);
  assert.deepEqual(W.groupSame([], r => r).length, 0);
});

test("two schools of the same name at opposite ends of a kunta stay two rows", () => {
  const rows = [{ n: "Kirkonkylän koulu", x: 0 }, { n: "Kirkonkylän koulu", x: 10 },
                { n: "Kirkonkylän koulu", x: 9000 }];
  const near = (a, b) => Math.abs(a.x - b.x) <= 150;
  const g = W.groupSame(rows, r => r.n, near);
  assert.deepEqual(g.map(x => x.n), [2, 1], "the near pair joins, the far one starts its own row");
  assert.equal(g[1].row.x, 9000);
});

/* ---------- §6: the return-period pair ---------- */

test("the flood family is read through picker_core, and a build without one draws its single bar", () => {
  const pc = { rpFamily: k => (k === "flood_sea_100" ? [{ rp: "100", key: "flood_sea_100", label: "1/100a" },
                                                        { rp: "1000", key: "flood_sea_1000", label: "1/1000a" }] : []) };
  assert.equal(W.rpFamilyOf(pc, "flood_sea_100").length, 2);
  assert.equal(W.rpFamilyOf(pc, "growth").length, 0);
  assert.deepEqual(W.rpFamilyOf(null, "flood_sea_100"), [], "no picker: no pair, and no throw");
  assert.deepEqual(W.rpFamilyOf({ rpFamily: () => { throw new Error("boom"); } }, "x"), []);
});

test("the second return period keeps the area's hue and only loses saturation", () => {
  assert.equal(W.tint("#1C6B5C", 0), "#1C6B5C", "the first bar is untouched");
  assert.equal(W.tint("#000000", 1), "#FFFFFF");
  assert.equal(W.tint("#1C6B5C", 0.45), "#82AEA5");   /* 28 + (255-28)·.45 = 130 = 0x82, and so on */
  assert.equal(W.tint("not a colour", 0.45), "not a colour", "anything unparseable passes through");
});

/* ---------- A11Y7 ---------- */

test("g is a prefix: g then m goes to the map, g then a stray key goes nowhere", () => {
  let s = W.keySeq("", "g");
  assert.deepEqual(s, { pending: "g", action: "" });
  assert.equal(W.keySeq(s.pending, "m").action, "go:map");
  assert.equal(W.keySeq("g", "d").action, "go:data");
  assert.equal(W.keySeq("g", "c").action, "go:charts");
  assert.equal(W.keySeq("g", "p").action, "go:property");
  const stray = W.keySeq("g", "q");
  assert.deepEqual(stray, { pending: "", action: "" }, "a half-typed g is dropped, never guessed at");
});

test("the single keys each do one thing, and anything else does nothing", () => {
  assert.equal(W.keySeq("", "/").action, "search");
  assert.equal(W.keySeq("", "?").action, "help");
  assert.equal(W.keySeq("", "[").action, "pin:prev");
  assert.equal(W.keySeq("", "]").action, "pin:next");
  assert.equal(W.keySeq("", "x").action, "");
  assert.equal(W.keySeq("", "Escape").action, "");
  assert.equal(W.keySeq("", "m").action, "", "m alone is not a navigation — only g m is");
});

test("every shortcut the overlay lists is one the key handler answers", () => {
  const listed = W.SHORTCUTS.map(s => s[0]);
  assert.ok(listed.includes("/") && listed.includes("?") && listed.includes("[  ]"));
  ["m", "d", "c", "p"].forEach(k => assert.ok(listed.includes("g " + k), "g " + k));
  W.SHORTCUTS.forEach(([k, d]) => { assert.ok(k && d, "every row has a key and a description: " + k); });
});

/* ---------- A11Y8 ---------- */

test("the drill sentence names the area and counts what was drawn", () => {
  assert.equal(W.drillLine("Helsinki", 84, "postinumero"), "Showing Helsinki, 84 postal codes");
  assert.equal(W.drillLine("Helsinki", 34, "osa_alue"), "Showing Helsinki, 34 osa-alueet");
  assert.equal(W.drillLine("Finland", 308, "kunta"), "Showing Finland, 308 municipalities");
  assert.equal(W.drillLine("Sottunga", 1, "postinumero"), "Showing Sottunga, 1 postal code", "singular");
  assert.equal(W.drillLine("Espoo", null, "building"), "Showing Espoo", "no count is said rather than a wrong one");
});
