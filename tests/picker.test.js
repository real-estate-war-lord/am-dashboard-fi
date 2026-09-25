/* node --test tests/picker.test.js — the indicator picker and period control (src/picker_core.js). */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const PC = require("../src/picker_core.js");

const growth = { key: "growth", short: "Growth", label: "Population growth", unit: "% / yr",
                 group: "Demographics", years: ["2016", "2017", "2024"] };
const rent = { key: "rent", short: "Rent", label: "Rent, private tenancies", unit: "EUR/m²/month",
               group: "Market", years: ["2020", "2024"] };
const unemp = { key: "unemp", short: "Unemp.", label: "Unemployment rate", unit: "%",
                group: "Income & jobs", years: ["2019", "2024"] };
const fc = { key: "fc_growth", short: "Outlook 2040", label: "Projected population change",
             unit: "%", group: "Outlook",
             proj: { from: "2026", to: "2040", publisher: "Tilastokeskus", vintage: "Väestöennuste 2024" } };
const sea100 = { key: "flood_sea_100", short: "Sea flood 1/100a", label: "Sea flood zone, 1/100a",
                 unit: "% of land", group: "Climate" };
const sea1000 = { key: "flood_sea_1000", short: "Sea flood 1/1000a", label: "Sea flood zone, 1/1000a",
                  unit: "% of land", group: "Climate" };
const radon = { key: "radon_mean", short: "Radon mean", label: "Radon, mean", unit: "Bq/m³",
                group: "Climate", years: ["2024"] };
const bbr = { key: "avg_m2", short: "Avg m²", label: "Average dwelling size", unit: "m²",
              group: "Housing stock" };

test("the period mode is a function of the indicator, not a separate setting", () => {
  assert.strictEqual(PC.periodMode(growth, growth.years), "year");
  assert.strictEqual(PC.periodMode(fc, []), "projection");
  assert.strictEqual(PC.periodMode(sea100, []), "returnperiod");
  assert.strictEqual(PC.periodMode(sea1000, []), "returnperiod");
  assert.strictEqual(PC.periodMode(radon, radon.years), "asof");   // one year is not a series
  assert.strictEqual(PC.periodMode(bbr, []), "asof");
  assert.strictEqual(PC.periodMode(null, []), "asof");
});

test("only a year mode writes a URL key", () => {
  assert.strictEqual(PC.PERIOD_KEY.year, "y");
  assert.strictEqual(PC.PERIOD_KEY.returnperiod, "");
  assert.strictEqual(PC.PERIOD_KEY.projection, "");
});

test("the return period is carried by the indicator key, and sea and river stay separate", () => {
  assert.deepStrictEqual(PC.rpParts("flood_sea_100"), { base: "flood_sea", rp: "100" });
  assert.deepStrictEqual(PC.rpParts("flood_river_1000"), { base: "flood_river", rp: "1000" });
  assert.strictEqual(PC.rpParts("flood_mapped"), null);
  assert.strictEqual(PC.rpParts("growth"), null);
  assert.deepStrictEqual(PC.rpFamily("flood_sea_100"), [
    { rp: "100", key: "flood_sea_100", label: "1/100a" },
    { rp: "1000", key: "flood_sea_1000", label: "1/1000a" }]);
  // switching the return period never crosses from sea to river
  assert.ok(PC.rpFamily("flood_river_100").every(x => x.key.startsWith("flood_river")));
  assert.deepStrictEqual(PC.rpFamily("growth"), []);
});

test("the projection badge names the window, the publisher and the vintage", () => {
  assert.strictEqual(PC.projBadge(fc), "Projection 2026→2040 · Tilastokeskus Väestöennuste 2024");
  assert.strictEqual(PC.projBadge(growth), "");
});

test("groups come out in GROUP_ORDER, with anything unlisted last", () => {
  const odd = { key: "x", label: "X", group: "Zebra" };
  const gs = PC.grouped([rent, growth, odd, unemp]).map(g => g[0]);
  assert.deepStrictEqual(gs, ["Demographics", "Income & jobs", "Market", "Zebra"]);
});

test("inherited indicators are pulled into their own group at the end", () => {
  const gs = PC.grouped([growth, unemp, rent], i => i.key !== "growth");
  assert.deepStrictEqual(gs.map(g => g[0]), ["Demographics", PC.GROUP_INHERITED]);
  assert.deepStrictEqual(gs[1][1].map(i => i.key), ["unemp", "rent"]);
});

test("search matches label, short, group, unit and key — every word has to hit", () => {
  assert.ok(PC.matches(growth, "population"));
  assert.ok(PC.matches(growth, "GROWTH"));
  assert.ok(PC.matches(growth, "demographics"));
  assert.ok(PC.matches(rent, "eur"));
  assert.ok(PC.matches(growth, "population growth"));
  assert.ok(!PC.matches(growth, "population rent"));
  assert.ok(PC.matches(growth, ""));
  assert.deepStrictEqual(PC.filter([growth, rent, unemp, sea100], "flood").map(i => i.key),
                         ["flood_sea_100"]);
});

test("the availability tag says where the figure comes from", () => {
  assert.strictEqual(PC.availTag(growth, {}), "2016–");
  assert.strictEqual(PC.availTag(growth, { inherited: true }), "muni");
  assert.strictEqual(PC.availTag(fc, {}), "2026→2040");
  assert.strictEqual(PC.availTag(sea1000, {}), "1/1000a");
  assert.strictEqual(PC.availTag(bbr, {}), "snapshot");
  assert.strictEqual(PC.availTag(radon, {}), "2024");
  assert.strictEqual(PC.availTag(growth, { years: ["2009", "2024"] }), "2009–");
});

test("a projection, a climate figure and an observed one are never the same ramp", () => {
  assert.strictEqual(PC.ramp(fc), "projection");
  assert.strictEqual(PC.ramp(sea100), "climate");
  assert.strictEqual(PC.ramp(radon), "climate");
  assert.strictEqual(PC.ramp(growth), "observed");
  assert.strictEqual(PC.ramp(null), "observed");
});

test("step wraps at both ends", () => {
  assert.strictEqual(PC.step(0, 3, 1), 1);
  assert.strictEqual(PC.step(2, 3, 1), 0);
  assert.strictEqual(PC.step(0, 3, -1), 2);
  assert.strictEqual(PC.step(0, 0, 1), -1);
});
