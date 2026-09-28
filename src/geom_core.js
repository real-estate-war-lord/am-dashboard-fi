/* AM Dashboard — Finland Edition · geom_core.js
   The plane geometry that decides where a point is (v2.2 W3). No DOM, no state, no fetch, so
   `node --test tests/geom.test.js` can run it — which is the real reason it moved out of app.js:
   the ray casting below places every pin, every school and every public building on this page, and
   until now it was the one piece of arithmetic in the build with no test of its own.

   Coordinates are [lat, lon] everywhere in this file, because that is the order the ring data in
   `dist/area/<kunta>.json` and `dist/geo/kunnat_lookup.json` is written in. GeoJSON's own [lon, lat]
   is flipped by the caller at the one place it enters (`featDistM`), never here.
*/
"use strict";

const GEOM_CORE = (function () {

/* Ray casting: is [lat, lon] inside this ring? Crossings of the horizontal line through the point
   are counted; an odd number means inside. Rings need not be closed. */
function pip(pt, ring) {
  let ins = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const yi = ring[i][0], xi = ring[i][1], yj = ring[j][0], xj = ring[j][1];
    if ((yi > pt[0]) !== (yj > pt[0]) && pt[1] < (xj - xi) * (pt[0] - yi) / (yj - yi) + xi) ins = !ins;
  }
  return ins;
}

/* A polygon is its outer ring minus its holes: Kauniainen is a hole in Espoo, and without the holes
   every Kauniainen pin would land in Espoo. */
const inPoly = (pt, poly) => pip(pt, poly[0]) && !poly.slice(1).some(h => pip(pt, h));

/* a polygon's [south, west, north, east] box, cached on the area — the prefilter before the ray casting.
   **The empty box is never cached.** Rings arrive late (dist/area/<kunta>.json is lazy), and an
   area asked for its box before they land would otherwise keep the inside-out box [90,180,-90,-180]
   for the rest of the session — a prefilter that rejects every point, so a pin in the middle of
   Helsinki reported no postal area at all while the rings sat right there in memory. */
function bboxOf(a) {
  if (a._bb) return a._bb;
  let s = 90, w = 180, n = -90, e = -180;
  (a.rings || []).forEach(r => r.forEach(q => { if (q[0] < s) s = q[0]; if (q[0] > n) n = q[0]; if (q[1] < w) w = q[1]; if (q[1] > e) e = q[1]; }));
  if (s > n || w > e) return [s, w, n, e];      /* no rings yet — answer, but do not remember */
  return (a._bb = [s, w, n, e]);
}
const inBox = (lat, lon, b) => lat >= b[0] && lat <= b[2] && lon >= b[1] && lon <= b[3];
/* which area of a list a point falls in — bbox first, ray casting only on the handful that survive */
function areaOf(list, lat, lon) {
  return (list || []).find(a => inBox(lat, lon, bboxOf(a)) && (a.rings || []).some(r => pip([lat, lon], r))) || null;
}

const R_EARTH = 6371008.8;
/* great-circle distance in metres */
function havM(lat1, lon1, lat2, lon2) {
  const rad = Math.PI / 180, dLat = (lat2 - lat1) * rad, dLon = (lon2 - lon1) * rad;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R_EARTH * Math.asin(Math.min(1, Math.sqrt(a)));
}
/* distance from the pin to a GeoJSON feature: a Point is the great-circle distance, a line or a ring the
   nearest point on its segments, and a point inside a polygon is 0 m. Degrees are converted to metres at
   the pin's own latitude — exact enough over the few kilometres this sheet looks at. */
function featDistM(f, lat, lon) {
  const g = f && f.geometry; if (!g || !g.coordinates) return null;
  if (g.type === "Point") return havM(lat, lon, g.coordinates[1], g.coordinates[0]);
  const rad = Math.PI / 180, kx = 111320 * Math.cos(lat * rad), ky = 110540;
  /* nearest point on the segment a→b, both in metres relative to the pin */
  const segD = (a, b) => {
    const ax = (a[0] - lon) * kx, ay = (a[1] - lat) * ky, dx = (b[0] - a[0]) * kx, dy = (b[1] - a[1]) * ky;
    const l2 = dx * dx + dy * dy, t = l2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / l2)) : 0;
    return Math.hypot(ax + t * dx, ay + t * dy);
  };
  const ringD = r => { let m = Infinity; for (let i = 1; i < r.length; i++) { const d = segD(r[i - 1], r[i]); if (d < m) m = d; } return m; };
  const polys = g.type === "MultiPolygon" ? g.coordinates : g.type === "Polygon" ? [g.coordinates] : null;
  if (polys) {
    /* inside the outer ring and outside every hole → the pin is in the area */
    if (polys.some(poly => inPoly([lat, lon], poly.map(r => r.map(c => [c[1], c[0]]))))) return 0;
    return Math.min(...polys.map(poly => Math.min(...poly.map(ringD))));
  }
  const lines = g.type === "MultiLineString" ? g.coordinates : g.type === "LineString" ? [g.coordinates] : null;
  return lines ? Math.min(...lines.map(ringD)) : null;
}

return { pip, inPoly, bboxOf, inBox, areaOf, R_EARTH, havM, featDistM };
})();

if (typeof module !== "undefined" && module.exports) module.exports = GEOM_CORE;
if (typeof window !== "undefined") window.GEOM_CORE = GEOM_CORE;
