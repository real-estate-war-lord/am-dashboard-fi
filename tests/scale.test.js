/* node --test tests/scale.test.js — the shared chart axis (src/scale_core.js). */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const SC = require("../src/scale_core.js");

const ser = (name, pts) => ({ name, pts: pts.map(([y, v]) => ({ y: String(y), v })) });

test("a step is 1, 2, 2.5 or 5 times a power of ten — never anything else", () => {
  assert.equal(SC.niceStep(0.9), 1);
  assert.equal(SC.niceStep(1), 1);
  assert.equal(SC.niceStep(1.1), 2);
  assert.equal(SC.niceStep(2.1), 2.5);
  assert.equal(SC.niceStep(2.6), 5);
  assert.equal(SC.niceStep(5.1), 10);
  assert.equal(SC.niceStep(0.021), 0.025);
  assert.equal(SC.niceStep(230), 250);
  assert.equal(SC.niceStep(0), 1);
  assert.equal(SC.niceStep(-3), 1);
  /* every step in a wide sweep is a member of the family, and no rounding dust survives */
  for (let e = -4; e <= 6; e++) {
    for (let f = 1; f < 100; f++) {
      const s = SC.niceStep(f / 10 * Math.pow(10, e));
      const m = s / Math.pow(10, Math.floor(Math.log10(s) + 1e-9));
      assert.ok(SC.NICE.some(x => Math.abs(x - m * 10) < 1e-9 || Math.abs(x - m) < 1e-9),
                `step ${s} is not a nice one`);
    }
  }
});

test("every tick is a multiple of the step, and the range is widened out to whole steps", () => {
  const a = SC.niceTicks(3.2, 17.4, 5);
  assert.deepEqual(a.ticks, [0, 5, 10, 15, 20]);
  assert.equal(a.lo, 0);
  assert.equal(a.hi, 20);
  const b = SC.niceTicks(1001, 1099, 5);
  assert.ok(b.ticks.every(t => Math.abs(t / b.step - Math.round(t / b.step)) < 1e-9), b.ticks);
  assert.ok(b.lo <= 1001 && b.hi >= 1099, b);
});

test("0 is on the axis whenever the range crosses it", () => {
  const a = SC.niceTicks(-7.8, 17.6, 6);
  assert.ok(a.ticks.includes(0), a.ticks);
  assert.equal(a.zero, true);
  const b = SC.niceTicks(-0.004, 0.011, 5);
  assert.ok(b.ticks.includes(0), b.ticks);
  /* exactly zero, not -0 or 1e-18 — the zero line is drawn off this number */
  assert.ok(Object.is(b.ticks[b.ticks.indexOf(0)], 0));
});

test("an all-positive range is never widened below zero", () => {
  const a = SC.niceTicks(120, 480, 5);
  assert.ok(a.lo >= 0, a);
  const b = SC.niceTicks(0, 3.4, 5);
  assert.equal(b.lo, 0);
});

test("a flat series still gets an axis with two distinct ticks", () => {
  const a = SC.niceTicks(4.2, 4.2, 5);
  assert.ok(a.hi > a.lo, a);
  assert.ok(a.ticks.length >= 2, a);
  const z = SC.niceTicks(0, 0, 5);
  assert.ok(z.hi > z.lo, z);
});

test("the x axis starts at the first year any series has a value", () => {
  const years = ["2011", "2012", "2013", "2014", "2015"];
  const s = [ser("area", [[2011, null], [2012, null], [2013, null], [2014, 2], [2015, 3]])];
  assert.equal(SC.firstLive(s, years.length), 3);
  assert.equal(SC.firstLive([ser("none", [[2011, null]])], 1), -1);
});

test("the range comes from the years the series share, and the odd year is named not dropped", () => {
  /* the case in the brief: an osa-alue published from 2014, against a median whose 2011–2012
     jumps ±17 % where the areas were redrawn */
  const years = ["2011", "2012", "2013", "2014", "2015", "2016"];
  const area = ser("Kallio", [[2011, null], [2012, null], [2013, null], [2014, 1.2], [2015, 0.9], [2016, 1.5]]);
  const med = ser("median", [[2011, 17.6], [2012, -7.8], [2013, 0.4], [2014, 0.5], [2015, 0.6], [2016, 0.7]]);
  const ax = SC.axis([area, med], years, { fmt: v => String(v) });
  assert.equal(ax.shared, true);
  assert.equal(ax.from, 0, "the median starts in 2011, so the axis does too");
  assert.ok(ax.hi < 17.6, `the spike must not set the top of the scale (${ax.hi})`);
  assert.ok(ax.lo > -7.8, `nor the dip the bottom (${ax.lo})`);
  assert.deepEqual(ax.clipped, ["2011", "2012"]);
  assert.equal(ax.note, "scale excludes 2011–2012");
});

test("one series alone excludes nothing — its own years are the shared ones", () => {
  const years = ["2011", "2012", "2013"];
  const ax = SC.axis([ser("a", [[2011, 17.6], [2012, -7.8], [2013, 0.4]])], years, {});
  assert.equal(ax.shared, false);
  assert.deepEqual(ax.clipped, []);
  assert.equal(ax.note, "");
  assert.ok(ax.hi >= 17.6 && ax.lo <= -7.8, ax);
});

test("series that share every year exclude nothing", () => {
  const years = ["2020", "2021", "2022"];
  const ax = SC.axis([ser("a", [[2020, 1], [2021, 2], [2022, 3]]),
                      ser("b", [[2020, 2], [2021, 3], [2022, 4]])], years, {});
  assert.equal(ax.shared, true);
  assert.deepEqual(ax.clipped, []);
  assert.ok(ax.lo <= 1 && ax.hi >= 4, ax);
});

test("two gridlines never carry the same label", () => {
  /* a 0,25 step printed with no decimals would read "0 0 1 1 1" */
  const years = ["2020", "2021"];
  const s = [ser("a", [[2020, 0], [2021, 1]])];
  const ax = SC.axis(s, years, { fmt: v => String(Math.round(v)) });
  const labs = ax.ticks.map(v => String(Math.round(v)));
  assert.equal(new Set(labs).size, labs.length, labs);
});

test("a run of years is written as a span, separate years as a list", () => {
  assert.equal(SC.spanText(["2011", "2012"]), "2011–2012");
  assert.equal(SC.spanText(["2012", "2011", "2013"]), "2011–2013");
  assert.equal(SC.spanText(["2011", "2019"]), "2011, 2019");
  assert.equal(SC.spanText(["2011", "2012", "2019"]), "2011–2012, 2019");
  assert.equal(SC.spanText(["2011"]), "2011");
  assert.equal(SC.spanText([]), "");
  assert.equal(SC.spanText(["2011K3", "2012K1"]), "2011K3, 2012K1");
});

test("no series, no axis — the caller draws its own empty state", () => {
  assert.equal(SC.axis([], ["2020"], {}), null);
  assert.equal(SC.axis([ser("a", [[2020, null]])], ["2020"], {}), null);
  assert.equal(SC.range([], []), null);
});
