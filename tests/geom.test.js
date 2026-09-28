/* node --test tests/geom.test.js — the point-in-polygon and distance arithmetic that places every
   pin, school and public building on the page (src/geom_core.js, moved out of app.js in v2.2 W3).

   Nothing here touches the DOM or the network: these are the answers the sheet is built on, and
   until W3 not one of them had a test. */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const G = require("../src/geom_core.js");

/* a 1° square with its south-west corner at [60, 24], in the [lat, lon] order the ring data uses */
const SQ = [[60, 24], [60, 25], [61, 25], [61, 24]];
/* the same square with a hole in the middle — a kunta with an enclave in it */
const HOLE = [[60.4, 24.4], [60.4, 24.6], [60.6, 24.6], [60.6, 24.4]];

test("a point inside a ring is inside, and one outside is not", () => {
  assert.equal(G.pip([60.5, 24.5], SQ), true);
  assert.equal(G.pip([59.9, 24.5], SQ), false);
  assert.equal(G.pip([60.5, 25.1], SQ), false);
});

test("a ring is closed implicitly — the last vertex joins the first", () => {
  const open = SQ, closed = SQ.concat([SQ[0]]);
  for (const p of [[60.5, 24.5], [60.01, 24.99], [61.5, 24.5]]) {
    assert.equal(G.pip(p, open), G.pip(p, closed), JSON.stringify(p));
  }
});

test("a polygon is its outer ring minus its holes", () => {
  const poly = [SQ, HOLE];
  assert.equal(G.inPoly([60.2, 24.2], poly), true, "in the ring, outside the hole");
  assert.equal(G.inPoly([60.5, 24.5], poly), false, "inside the hole is outside the polygon");
  assert.equal(G.inPoly([59.0, 24.5], poly), false, "outside the ring");
});

test("a concave ring does not swallow the notch cut out of it", () => {
  /* a C shape opening east: the middle of the opening is outside */
  const c = [[0, 0], [0, 3], [1, 3], [1, 1], [2, 1], [2, 3], [3, 3], [3, 0]];
  assert.equal(G.pip([0.5, 1.5], c), true);
  assert.equal(G.pip([1.5, 2.0], c), false, "the notch is outside");
  assert.equal(G.pip([2.5, 1.5], c), true);
});

test("the bbox is [south, west, north, east] and is cached on the area", () => {
  const a = { rings: [SQ] };
  assert.deepEqual(G.bboxOf(a), [60, 24, 61, 25]);
  assert.ok(a._bb, "a real box is remembered");
  assert.equal(G.bboxOf(a), a._bb, "and handed back, not recomputed");
});

test("an area whose rings have not landed yet answers, but never remembers", () => {
  /* dist/area/<kunta>.json is lazy. An inside-out box cached here rejects every point for the rest
     of the session — which is how a pin in the middle of Helsinki once reported no postal area. */
  const a = {};
  assert.deepEqual(G.bboxOf(a), [90, 180, -90, -180]);
  assert.equal(a._bb, undefined, "the empty box was cached");
  a.rings = [SQ];
  assert.deepEqual(G.bboxOf(a), [60, 24, 61, 25], "it answers properly once the rings arrive");
});

test("inBox is inclusive on every edge", () => {
  const b = [60, 24, 61, 25];
  assert.equal(G.inBox(60, 24, b), true);
  assert.equal(G.inBox(61, 25, b), true);
  assert.equal(G.inBox(60.5, 23.99, b), false);
  assert.equal(G.inBox(61.01, 24.5, b), false);
});

test("areaOf picks the area a point falls in, and null when none does", () => {
  const far = [[10, 10], [10, 11], [11, 11], [11, 10]];
  const list = [{ nr: "far", rings: [far] }, { nr: "here", rings: [SQ] }];
  assert.equal(G.areaOf(list, 60.5, 24.5).nr, "here");
  assert.equal(G.areaOf(list, 10.5, 10.5).nr, "far");
  assert.equal(G.areaOf(list, 0, 0), null);
  assert.equal(G.areaOf(null, 60.5, 24.5), null);
  assert.equal(G.areaOf([{ nr: "no rings yet" }], 60.5, 24.5), null);
});

test("the great-circle distance is metres, and symmetric", () => {
  assert.equal(G.havM(60.17, 24.94, 60.17, 24.94), 0);
  /* Helsinki → Tampere is about 161 km in a straight line */
  const d = G.havM(60.1699, 24.9384, 61.4978, 23.7610);
  assert.ok(d > 155000 && d < 165000, String(d));
  assert.ok(Math.abs(d - G.havM(61.4978, 23.7610, 60.1699, 24.9384)) < 1e-6);
  /* one degree of latitude is a touch over 111 km anywhere */
  const oneDeg = G.havM(60, 25, 61, 25);
  assert.ok(Math.abs(oneDeg - 111195) < 200, String(oneDeg));
});

test("a feature's distance: a point, a line, and 0 m inside a polygon", () => {
  const pt = { geometry: { type: "Point", coordinates: [24.9384, 60.1699] } };   /* GeoJSON is [lon, lat] */
  assert.equal(Math.round(G.featDistM(pt, 60.1699, 24.9384)), 0);
  assert.ok(Math.abs(G.featDistM(pt, 60.1699, 24.9384 + 0.01) - 554) < 30);

  const line = { geometry: { type: "LineString", coordinates: [[24.9, 60.0], [24.9, 61.0]] } };
  assert.equal(Math.round(G.featDistM(line, 60.5, 24.9)), 0, "on the line");
  const off = G.featDistM(line, 60.5, 24.95);
  assert.ok(off > 2500 && off < 3000, String(off));

  const poly = { geometry: { type: "Polygon", coordinates: [SQ.map(p => [p[1], p[0]])] } };
  assert.equal(G.featDistM(poly, 60.5, 24.5), 0, "inside a polygon is 0 m");
  assert.ok(G.featDistM(poly, 60.5, 25.1) > 0, "outside it is not");

  const donut = { geometry: { type: "Polygon", coordinates: [SQ, HOLE].map(r => r.map(p => [p[1], p[0]])) } };
  assert.ok(G.featDistM(donut, 60.5, 24.5) > 0, "the hole is not inside the polygon");
  assert.equal(G.featDistM(donut, 60.2, 24.2), 0);
});

test("a feature with no geometry, and a type nothing is drawn for, answer null", () => {
  assert.equal(G.featDistM(null, 60, 24), null);
  assert.equal(G.featDistM({}, 60, 24), null);
  assert.equal(G.featDistM({ geometry: { type: "Polygon" } }, 60, 24), null);
  assert.equal(G.featDistM({ geometry: { type: "GeometryCollection", coordinates: [] } }, 60, 24), null);
});
