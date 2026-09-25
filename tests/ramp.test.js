/* node --test tests/ramp.test.js — the signed colour ramp (src/ramp_core.js), v2.1 phase V2.

   What is worth testing here is not "does it return a colour" but the four promises the owner's rule
   makes: the breaks are fixed and centred on zero, an exact zero is a positive value, an indicator
   where an increase is the bad news has its colours the other way round, and a sixth class appears
   only when the data is spread out enough to need one. The last group runs against the real
   data/processed files, because a rule about "more than 20 % of areas" is only meaningful against
   the areas there actually are. */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");
const RC = require("../src/ramp_core.js");

const PROC = path.join(__dirname, "..", "data", "processed");
const readProc = f => JSON.parse(fs.readFileSync(path.join(PROC, f), "utf8"));

/* ---------- the registry ---------- */

test("only indicators whose published values straddle zero are signed", () => {
  for (const k of ["growth", "migration", "migration_dom", "rent_yoy", "crime_trend",
                   "fc_growth", "fc_growth_5y", "fc_abs", "fc_pop_rate_5y",
                   "fc_0_6", "fc_7_15", "fc_20_34", "fc_20_34_rel"])
    assert.ok(RC.isSigned(k), k + " should be signed");
  /* levels, shares and counts keep the sequential quantile ramp… */
  for (const k of ["unemp", "price_m2", "rent", "young", "flats", "crime_1000", "radon_mean",
                   "flood_sea_100", "tax_home", "completions_1000", "avg_m2", ""])
    assert.ok(!RC.isSigned(k), k + " must not be signed");
  /* …and so does the one Outlook indicator that is positive everywhere: every kunta's 80+
     population grows, so "darkest = most" is the honest reading and a red class would never fill */
  assert.ok(!RC.isSigned("fc_80p"));
  assert.strictEqual(RC.thresholdOf("growth"), 0.5);
  assert.strictEqual(RC.thresholdOf("migration"), 5);
  assert.strictEqual(RC.thresholdOf("rent_yoy"), 2);
  assert.strictEqual(RC.thresholdOf("unemp"), null);
});

/* ---------- breaks ---------- */

test("four classes by default, breaks at -t, 0, +t and nowhere else", () => {
  const sc = RC.signedScale([-1, -0.2, 0, 0.3, 1], 0.5, {});
  assert.strictEqual(sc.classes, 4);
  assert.deepStrictEqual(sc.breaks, [-0.5, 0, 0.5]);
  assert.strictEqual(sc.zero, 2);
  assert.strictEqual(sc.wide, false);
});

test("the breaks do not move when the data does — that is the whole point", () => {
  const a = RC.signedScale([-0.9, -0.1, 0.1, 0.9], 0.5, {});
  const b = RC.signedScale([-0.4, 0.05, 0.2, 0.44], 0.5, {});
  assert.deepStrictEqual(a.breaks, b.breaks);
  /* and the same value is the same colour in both */
  assert.strictEqual(a.colorOf(0.2), b.colorOf(0.2));
});

test("class edges: < -t, -t … 0, 0 … +t, > +t", () => {
  const sc = RC.signedScale([-2, 2], 0.5, { wide: false });
  assert.strictEqual(sc.classes, 4);
  assert.strictEqual(sc.cls(-0.51), 0);
  assert.strictEqual(sc.cls(-0.5), 1);       /* -t itself belongs to the -t … 0 class */
  assert.strictEqual(sc.cls(-0.01), 1);
  assert.strictEqual(sc.cls(0.49), 2);
  assert.strictEqual(sc.cls(0.5), 3);        /* +t itself belongs to the > +t class */
  assert.strictEqual(sc.cls(99), 3);
  assert.strictEqual(sc.cls(null), null);
  assert.strictEqual(sc.cls(NaN), null);
});

test("exactly 0 is a positive value: it lands in 0 … +t, never in -t … 0", () => {
  const sc = RC.signedScale([-1, 0, 1], 0.5, {});
  assert.strictEqual(sc.cls(0), sc.zero);
  assert.strictEqual(sc.colorOf(0), sc.colorOf(0.1));
  assert.notStrictEqual(sc.colorOf(0), sc.colorOf(-0.1));
  /* -0 is still 0 */
  assert.strictEqual(sc.cls(-0), sc.zero);
  const wide = RC.signedScale([-1, 0, 1], 0.5, { wide: true });
  assert.strictEqual(wide.cls(0), wide.zero);
});

/* ---------- the sixth class ---------- */

test("a sixth class appears only when more than 20 % of the areas lie beyond ±3t", () => {
  const tight = [];                                   /* 100 values, 10 of them beyond ±1.5 */
  for (let i = 0; i < 90; i++) tight.push(i % 2 ? 0.4 : -0.4);
  for (let i = 0; i < 10; i++) tight.push(9);
  assert.strictEqual(RC.needsWide(tight, 0.5), false);
  assert.strictEqual(RC.signedScale(tight, 0.5, {}).classes, 4);

  const spread = [];                                  /* 100 values, 25 beyond ±1.5 */
  for (let i = 0; i < 75; i++) spread.push(i % 2 ? 0.4 : -0.4);
  for (let i = 0; i < 25; i++) spread.push(i % 2 ? 9 : -9);
  assert.strictEqual(RC.needsWide(spread, 0.5), true);
  const sc = RC.signedScale(spread, 0.5, {});
  assert.strictEqual(sc.classes, 6);
  assert.deepStrictEqual(sc.breaks, [-1.5, -0.5, 0, 0.5, 1.5]);
  assert.strictEqual(sc.zero, 3);
  assert.strictEqual(sc.cls(-9), 0);
  assert.strictEqual(sc.cls(-1.5), 1);
  assert.strictEqual(sc.cls(0), 3);
  assert.strictEqual(sc.cls(1.5), 5);
  /* exactly 20 % is not "more than 20 %" */
  const edge = [];
  for (let i = 0; i < 80; i++) edge.push(0.1);
  for (let i = 0; i < 20; i++) edge.push(9);
  assert.strictEqual(RC.needsWide(edge, 0.5), false);
});

test("the sixth class is darker than the one inside it, on both sides", () => {
  const sc = RC.signedScale([], 0.5, { wide: true });
  const darker = (a, b) => RC.lum(a) < RC.lum(b);
  assert.ok(darker(sc.shadeOfClass(0), sc.shadeOfClass(1)), "< -3t must be darker than -3t … -t");
  assert.ok(darker(sc.shadeOfClass(1), sc.shadeOfClass(2)));
  assert.ok(darker(sc.shadeOfClass(5), sc.shadeOfClass(4)), "> +3t must be darker than +t … +3t");
  assert.ok(darker(sc.shadeOfClass(4), sc.shadeOfClass(3)));
});

/* ---------- direction ---------- */

test("green above zero, red below — and the other way round when lower is better", () => {
  const warm = v => RC.warmth(v) > 20, cool = v => RC.warmth(v) < -20;
  const up = RC.signedScale([-1, 1], 0.5, { family: "observed", flip: false });
  assert.ok(cool(up.colorOf(0.9)), "a growing area is green");
  assert.ok(cool(up.colorOf(0.1)));
  assert.ok(warm(up.colorOf(-0.1)), "a shrinking area is red");
  assert.ok(warm(up.colorOf(-0.9)));

  const down = RC.signedScale([-1, 1], 0.5, { family: "observed", flip: true });
  assert.ok(warm(down.colorOf(0.9)), "more crime is red");
  assert.ok(warm(down.colorOf(0.1)));
  assert.ok(cool(down.colorOf(-0.1)), "less crime is green");
  assert.ok(cool(down.colorOf(-0.9)));
  /* the flip swaps the sides and nothing else: the magnitudes still read outwards */
  assert.ok(RC.lum(down.colorOf(0.9)) < RC.lum(down.colorOf(0.1)));
  assert.strictEqual(down.cls(0), down.zero);
});

test("a projection is purple above zero and red below — never green", () => {
  const sc = RC.signedScale([-1, 1], 0.5, { family: "projection" });
  assert.ok(RC.SHADES.purple[2].includes(sc.colorOf(0.9)));
  assert.ok(RC.SHADES.purple[2].includes(sc.colorOf(0.1)));
  assert.ok(RC.SHADES.red[2].includes(sc.colorOf(-0.1)));
  assert.ok(!RC.SHADES.green[2].includes(sc.colorOf(0.9)));
  assert.match(RC.legendNote(sc), /purple above zero/);
});

test("no value and no scale ever produce a green or a red by accident", () => {
  const sc = RC.signedScale([-1, 1], 0.5, {});
  assert.strictEqual(sc.colorOf(null), RC.NODATA);
  assert.strictEqual(sc.colorOf(NaN), RC.NODATA);
  assert.strictEqual(sc.shade(null), RC.NODATA);
  assert.strictEqual(RC.signedScale([1, 2], 0, {}), null, "a threshold of 0 is not a scale");
  assert.strictEqual(RC.signedScale([1, 2], null, {}), null);
});

test("the 0…1 t() a caller hands to a shader round-trips to the same colour", () => {
  for (const wide of [false, true]) {
    const sc = RC.signedScale([-9, -0.1, 0.1, 9], 0.5, { wide });
    for (const v of [-99, -1.6, -0.6, -0.2, 0, 0.2, 0.6, 1.6, 99])
      assert.strictEqual(sc.shade(sc.t(v)), sc.colorOf(v), "t() lost the class for " + v + " (wide=" + wide + ")");
    assert.strictEqual(sc.t(-99), 0);
    assert.strictEqual(sc.t(99), 1);
  }
});

/* ---------- the legend ---------- */

test("legend labels are signed, in value order, with the unit on the number", () => {
  const f = v => v === 0 ? "0" : (v > 0 ? "+" : "−") + Math.abs(v).toFixed(1).replace(".", ",");
  const sc = RC.signedScale([-1, 1], 0.5, {});
  assert.deepStrictEqual(RC.labels(sc, f, "%"),
    ["< −0,5 %", "−0,5 … 0 %", "0 … +0,5 %", "> +0,5 %"]);
  /* the owner's example string, verbatim */
  assert.ok(RC.labels(sc, f, "%").includes("0 … +0,5 %"));
  const wide = RC.signedScale([-1, 1], 0.5, { wide: true });
  assert.deepStrictEqual(RC.labels(wide, f, "%"),
    ["< −1,5 %", "−1,5 … −0,5 %", "−0,5 … 0 %",
     "0 … +0,5 %", "+0,5 … +1,5 %", "> +1,5 %"]);
  /* no unit: the legend title carries it (per 1,000 inh., residents) */
  assert.deepStrictEqual(RC.labels(sc, f, ""), ["< −0,5", "−0,5 … 0", "0 … +0,5", "> +0,5"]);
  /* one label per class, and the top one is the highest */
  assert.strictEqual(RC.labels(sc, f, "%").length, sc.classes);
  assert.match(RC.labels(sc, f, "%")[sc.classes - 1], /^> \+/);
});

test("the legend says which way round the colours read", () => {
  assert.strictEqual(RC.LEGEND_FOOTER, "fixed breaks, centred on zero");
  assert.match(RC.legendNote(RC.signedScale([-1, 1], 5, { flip: true })), /increase is red/);
  assert.match(RC.legendNote(RC.signedScale([-1, 1], 5, { flip: true })), /lower is better/);
  assert.match(RC.legendNote(RC.signedScale([-1, 1], 5, {})), /green above zero/);
});

/* ---------- colour contrast ----------

   The owner asked for greens and reds that "pass 3:1 against each other and against `no data`
   grey". The first half holds and is asserted here. The second cannot: #C4CBC4 sits in the middle
   of the luminance scale (L = 0.58), so *no* colour of any hue reaches 3:1 against it on the light
   side — the darkest class of each side does, and a pale class is told from "no figure" by chroma
   instead, which the grey has almost none of. Recorded in docs/v2_1/DECISIONS.md V2. */

test("within a side, the light class and the dark class pass 3:1", () => {
  for (const hue of ["green", "red", "purple"]) {
    const s = RC.SHADES[hue][2];
    assert.ok(RC.contrast(s[0], s[1]) >= 3,
      hue + " 2-class pair is only " + RC.contrast(s[0], s[1]).toFixed(2) + ":1");
  }
});

test("with six classes the extremes still pass 3:1 and no two neighbours collapse", () => {
  for (const hue of ["green", "red", "purple"]) {
    const s = RC.SHADES[hue][3];
    assert.ok(RC.contrast(s[0], s[2]) >= 3, hue + " extremes " + RC.contrast(s[0], s[2]).toFixed(2));
    for (let i = 0; i < s.length - 1; i++)
      assert.ok(RC.contrast(s[i], s[i + 1]) >= 2, hue + " " + s[i] + "/" + s[i + 1] + " = " + RC.contrast(s[i], s[i + 1]).toFixed(2));
  }
});

test("no swatch can be mistaken for the no-data grey", () => {
  assert.ok(RC.chroma(RC.NODATA) <= 8, "the no-data grey must stay neutral");
  for (const hue of ["green", "red", "purple"]) {
    for (const n of [2, 3]) {
      const s = RC.SHADES[hue][n];
      s.forEach(c => assert.ok(RC.chroma(c) >= 24, hue + " " + c + " has a chroma of only " + RC.chroma(c)));
      /* the darkest class of every side also clears 3:1 against the grey outright */
      const d = s[s.length - 1];
      assert.ok(RC.contrast(d, RC.NODATA) >= 3, hue + " " + d + " vs no data = " + RC.contrast(d, RC.NODATA).toFixed(2));
    }
  }
});

test("red and the favourable hue are never the same warmth, at any depth", () => {
  for (const good of ["green", "purple"]) {
    for (const n of [2, 3]) {
      for (let i = 0; i < n; i++) {
        const gap = RC.warmth(RC.SHADES.red[n][i]) - RC.warmth(RC.SHADES[good][n][i]);
        assert.ok(gap >= 30, good + " " + n + "/" + i + " warmth gap is only " + gap);
      }
    }
  }
});

/* ---------- against the data that is actually shipped ---------- */

/* the three levels the build ships, exactly as src/app.js signedWide() reads them */
function shippedLevels(key) {
  const mk = readProc("makro.json"), osa = readProc("osa_alue.json");
  return [mk.municipalities || [], mk.areas || [], osa.areas || []]
    .map(list => list.map(o => o[key]).filter(v => typeof v === "number" && !isNaN(v)));
}

test("every signed indicator classes the real data into non-empty green and red bins", () => {
  let seen = 0;
  for (const key of Object.keys(RC.SIGNED)) {
    const t = RC.thresholdOf(key);
    const levels = shippedLevels(key);
    const wide = RC.wideFor(levels, t);
    for (const vals of levels) {
      if (vals.length < RC.MIN_LEVEL_N) continue;
      seen++;
      const sc = RC.signedScale(vals, t, { wide });
      const counts = new Array(sc.classes).fill(0);
      vals.forEach(v => counts[sc.cls(v)]++);
      const where = key + " (" + vals.length + " areas)";
      /* the classing is only worth drawing if both sides of zero are used */
      assert.ok(counts.slice(0, sc.zero).reduce((a, b) => a + b, 0) > 0, where + ": no area below zero");
      assert.ok(counts.slice(sc.zero).reduce((a, b) => a + b, 0) > 0, where + ": no area above zero");
      assert.strictEqual(sc.classes, wide ? 6 : 4, where + " class count");
    }
  }
  assert.ok(seen >= 13, "expected every signed indicator to be found in the data, saw " + seen);
});

test("the sixth class is decided per indicator, so every level draws the same ramp", () => {
  /* a level with a handful of published values cannot decide the classing for the whole country */
  assert.strictEqual(RC.wideFor([[9, -9, 9, -9]], 0.5), false, "4 values must not swing it");
  const many = []; for (let i = 0; i < 40; i++) many.push(i % 2 ? 9 : -9);
  assert.strictEqual(RC.wideFor([[0.1], many], 0.5), true);
  assert.strictEqual(RC.wideFor([], 0.5), false);
  /* and the decision, once taken, gives byte-identical colours at every level */
  for (const key of Object.keys(RC.SIGNED)) {
    const t = RC.thresholdOf(key);
    const levels = shippedLevels(key).filter(v => v.length >= RC.MIN_LEVEL_N);
    if (levels.length < 2) continue;
    const wide = RC.wideFor(shippedLevels(key), t);
    const scales = levels.map(v => RC.signedScale(v, t, { wide, family: "observed" }));
    for (const v of [-9, -1.6, -0.2, 0, 0.2, 1.6, 9])
      assert.strictEqual(new Set(scales.map(s => s.colorOf(v))).size, 1,
        key + ": level disagreement on " + v);
  }
});

test("the sequential ramp is left alone: a level indicator is never signed", () => {
  const mk = readProc("makro.json");
  /* every indicator in the shipped registry that is signed here must also *be* signed there —
     a key that disappears from the registry must not sit in SIGNED unnoticed */
  const keys = new Set((mk.indicators || []).map(i => i.key));
  const osaKeys = new Set(((readProc("osa_alue.json").indicators) || []).map(i => i.key));
  for (const k of Object.keys(RC.SIGNED))
    assert.ok(keys.has(k) || osaKeys.has(k), "SIGNED names " + k + ", which no registry publishes");
});
