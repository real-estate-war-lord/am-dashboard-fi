/* The pure half of src/present.js — the source footer line, the composite PNG's geometry and the
   file name it is saved under. Run with `make test-js` or `node --test tests/`.

   The rest of that file needs a document (it copies the live map and the live chart onto a canvas)
   and is covered by the W4 checks in tests/ui_v2.spec.py instead. */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const P = require("../src/present.js");

/* ---------------------------------------------------------------- footerText */

test("the footer names the publishers, the as-of and where the live page is", () => {
  const s = P.footerText({ publishers: ["Tilastokeskus", "Aluesarjat"], asof: "2025Q4" });
  assert.ok(s.startsWith("Source: Tilastokeskus, Aluesarjat"), s);
  assert.ok(s.includes(" · as of 2025Q4 · "), s);
  assert.ok(s.endsWith(P.SITE), s);
});

test("a publisher's parenthetical is dropped, so the same body is not named twice", () => {
  const s = P.footerText({ publishers: ["Tilastokeskus", "Tilastokeskus (Paavo)", "Tilastokeskus"] });
  assert.strictEqual(s.indexOf("Tilastokeskus"), s.lastIndexOf("Tilastokeskus"), s);
  assert.ok(!s.includes("(Paavo)"), s);
});

test("more publishers than the line can carry are counted, not listed", () => {
  const s = P.footerText({ publishers: ["A", "B", "C", "D", "E", "F"], max: 4 });
  assert.ok(s.startsWith("Source: A, B, C, D and 2 more ·"), s);
});

test("blank and missing publishers never produce an empty 'Source:'", () => {
  assert.ok(P.footerText({ publishers: ["", null, "  "] }).startsWith("Source: open data"));
  assert.ok(P.footerText({}).startsWith("Source: open data"));
  assert.ok(P.footerText().includes(P.SITE));
});

test("no as-of means no empty 'as of' segment", () => {
  const s = P.footerText({ publishers: ["Tilastokeskus"] });
  assert.ok(!s.includes("as of"), s);
});

test("newestAsof takes the newest string and ignores the blanks", () => {
  assert.strictEqual(P.newestAsof([{ asof: "2024" }, { asof: "2025Q4" }, { asof: "" }, {}]), "2025Q4");
  assert.strictEqual(P.newestAsof([]), "");
  assert.strictEqual(P.newestAsof(), "");
});

/* -------------------------------------------------------------------- layout */

test("the chart and the map fill the width between the margins, and never overlap", () => {
  const L = P.layout({});
  assert.strictEqual(L.chart.x, L.pad);
  assert.strictEqual(L.map.x, L.chart.x + L.chart.w + L.gap);
  assert.strictEqual(L.map.x + L.map.w, L.W - L.pad);
  assert.ok(L.map.x >= L.chart.x + L.chart.w, L);
});

test("the two panels start together and the map fills the body beside the chart", () => {
  const L = P.layout({});
  assert.strictEqual(L.chart.y, L.map.y);
  assert.strictEqual(L.map.h, L.bodyH);
  assert.ok(L.chart.h <= L.map.h, L);
});

test("the chart keeps the aspect ratio of the SVG it is given — never stretched", () => {
  for (const [w, h] of [[880, 190], [900, 240], [1200, 640]]) {
    const L = P.layout({ chartW: w, chartH: h });
    assert.ok(Math.abs(L.chart.w / L.chart.h - w / h) < 0.02, [w, h, L.chart]);
  }
});

test("a flat panel chart still gets a map tall enough to read", () => {
  const L = P.layout({ chartW: 900, chartH: 240 });   /* the area page's own strip */
  assert.ok(L.chart.h < 300, L.chart);                /* it really is that flat */
  assert.ok(L.map.h >= 360, ("the map came out as a band", L.map));
});

test("the series legend is reserved under the chart, inside its column", () => {
  const L = P.layout({ chartW: 900, chartH: 240, legH: 46 });
  assert.strictEqual(L.legend.x, L.chart.x);
  assert.strictEqual(L.legend.w, L.chart.w);
  assert.strictEqual(L.legend.y, L.chart.y + L.chart.h);
  assert.ok(L.legend.y + L.legend.h <= L.map.y + L.map.h, L);
  /* and a legend taller than the floor pushes the whole body, rather than being cut off */
  const tall = P.layout({ chartW: 1200, chartH: 640, legH: 80 });
  assert.strictEqual(tall.bodyH, tall.chart.h + 80);
});

test("legHeight counts the rows the legend will need, and nothing when there is none", () => {
  assert.strictEqual(P.legHeight({ items: [], note: "" }), 0);
  const one = P.legHeight({ items: [1, 2, 3], note: "" });
  const two = P.legHeight({ items: [1, 2, 3, 4], note: "" });
  assert.ok(two > one, [one, two]);
  assert.ok(P.legHeight({ items: [1], note: "scale excludes 2011" }) > P.legHeight({ items: [1], note: "" }));
});

test("the picture is tall enough for the title, the panels and the footer", () => {
  const L = P.layout({});
  assert.ok(L.H > L.map.y + L.map.h, L);
  assert.ok(L.foot.y <= L.H - 1 && L.foot.y > L.map.y + L.map.h, L);
  assert.ok(L.W > 0 && L.H > 0);
});

test("a wider picture gives both panels more room, not just the chart", () => {
  const a = P.layout({}), b = P.layout({ width: 2000 });
  assert.ok(b.chart.w > a.chart.w && b.map.w > a.map.w, [a, b]);
});

/* ------------------------------------------------------------------ fileName */

test("the file name survives Finnish letters, spaces and the crumb arrow", () => {
  assert.strictEqual(P.fileName(["study", "price_m2", "Helsinki › Malminkartano", "2011–2025"]),
                     "study_price_m2_Helsinki_Malminkartano_2011_2025.png");
  assert.strictEqual(P.fileName(["Jyväskylä"]), "Jyvaskyla.png");
});

test("an empty name is still a file", () => {
  assert.strictEqual(P.fileName([]), "export.png");
  assert.strictEqual(P.fileName(["", null, "  "]), "export.png");
  assert.strictEqual(P.fileName(["a"], ".csv"), "a.csv");
});
