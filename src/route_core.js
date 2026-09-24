/* AM Dashboard — Finland Edition · route_core.js
   The hash codec, and nothing else. Two spellings exist: the **v1.1 hashes** that are already in
   people's bookmarks and in every screenshot ever taken of this dashboard, and the **v2.0 hashes**
   the app writes from now on. This file is the only place that knows both.

   `toV2()`  old spelling → canonical v2 spelling. Must be idempotent: feeding it its own output
             changes nothing (tests/route.test.js checks every row of the table twice).
   `toInternal()` either spelling → `{ view, parts, query }` using the app's own `S.view` ids, which
             did not change in v2.0 — only the spelling, the labels and the navigation did.

   No DOM, no window, no fetch, so `node --test tests/route.test.js` can run it directly. Inlined
   into dist/index.html by scripts/build_dashboard.py, the way testprop.js is.
*/
"use strict";

/* one IIFE: this file is inlined next to app.js, and nothing in it may reach the global scope
   except window.ROUTE_CORE. */
var ROUTE_CORE = (function () {

/* ---------- primitives ---------- */

/* "area/kunta/091?ind=growth&y=2024" → { path, parts, query } — the query keeps insertion order */
function splitHash(hash) {
  const h = String(hash == null ? "" : hash).replace(/^#/, "");
  const i = h.indexOf("?");
  const path = i < 0 ? h : h.slice(0, i);
  const qs = i < 0 ? "" : h.slice(i + 1);
  const query = {};
  qs.split("&").filter(Boolean).forEach(kv => {
    const j = kv.indexOf("=");
    const k = j < 0 ? kv : kv.slice(0, j);
    const v = j < 0 ? "" : kv.slice(j + 1);
    try { query[decodeURIComponent(k)] = decodeURIComponent(v); }
    catch (e) { query[k] = v; }                     /* a half-encoded link is still a link */
  });
  return { path, parts: path.split("/").filter(Boolean), query };
}

/* A fragment may legally carry "," ":" "/" and "@" unescaped, and a link is read by people here —
   `p=60.2448,24.8665:Koti` is a link someone can check at a glance, `p=60.2448%2C24.8665%3AKoti`
   is not. Everything that would break the codec (# ? & = %) is still escaped. */
function enc(s) {
  return encodeURIComponent(String(s)).replace(/%2C/g, ",").replace(/%3A/g, ":")
    .replace(/%2F/g, "/").replace(/%40/g, "@").replace(/%3B/g, ";");
}

/* the inverse of splitHash. Keys whose value is "" are still written (`y=` means "the empty year"),
   keys whose value is null or undefined are dropped — that is how a default stays out of the bar. */
function buildHash(path, query) {
  const q = [];
  Object.keys(query || {}).forEach(k => {
    const v = query[k];
    if (v === null || v === undefined) return;
    q.push(enc(k) + "=" + enc(v));
  });
  return String(path || "") + (q.length ? "?" + q.join("&") : "");
}

/* ---------- coordinates ---------- */

const RC_LATLON = /^\s*(-?\d{1,3}(?:[.,]\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:[.,]\d+)?)\s*$/;
/* five decimals is ~1 m — enough for a building, short enough for a shareable link */
const RC_DEC = 5;
const rcRound = n => Number(Number(n).toFixed(RC_DEC));

/* "60.24480, 24.86650" → {lat, lon}; anything else → null. Deliberately strict: an address is
   testprop.js's job, and a bare number pair that is not a coordinate must not become a pin. */
function parseLatLon(text) {
  const m = RC_LATLON.exec(String(text == null ? "" : text));
  if (!m) return null;
  const lat = Number(String(m[1]).replace(",", ".")), lon = Number(String(m[2]).replace(",", "."));
  if (isNaN(lat) || isNaN(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return { lat: rcRound(lat), lon: rcRound(lon) };
}

/* ---------- the property codec (list-capable) ----------
   v2.0 shows ONE property, but the owner's next idea is "paste several Google Maps links and they
   all appear on the map". The codec is a list from the start so that link format never has to
   change: `p=60.2448,24.8665:Kannelmäki;60.17,24.94`. The view takes the first item. */

const RC_PROP_MAX = 30;

function propParse(p) {
  return String(p == null ? "" : p).split(";").map(s => s.trim()).filter(Boolean).map(item => {
    const c = item.indexOf(":");
    const coords = c < 0 ? item : item.slice(0, c);
    const label = c < 0 ? "" : item.slice(c + 1);
    const ll = parseLatLon(coords);
    return ll ? { lat: ll.lat, lon: ll.lon, label } : null;
  }).filter(Boolean).slice(0, RC_PROP_MAX);
}

function propSerialise(list) {
  return (list || []).slice(0, RC_PROP_MAX).map(o => {
    if (o == null || o.lat == null || o.lon == null) return "";
    return rcRound(o.lat) + "," + rcRound(o.lon) + (o.label ? ":" + o.label : "");
  }).filter(Boolean).join(";");
}

/* ---------- the alias table ----------
   Every row here is a v1.1 link that must keep working for ever. Adding a spelling means adding it
   here, never in app.js. */

const RC_DATA_LEVELS = ["kunta", "postinumero", "osa_alue"];

function toV2(hash) {
  const { path, parts, query } = splitHash(hash);
  const v = parts[0] || "map";

  /* #table/<level> → #data/areas/<level> */
  if (v === "table") {
    const lvl = RC_DATA_LEVELS.indexOf(parts[1]) >= 0 ? parts[1] : "kunta";
    return buildHash("data/areas/" + lvl, query);
  }
  /* #pipeline → #data/projects (its ptype/pstatus filters ride along unchanged) */
  if (v === "pipeline") return buildHash("data/projects", query);
  /* #sources → #data/sources */
  if (v === "sources") return buildHash("data/sources", query);
  /* #data, and the Danish spec's fourth tab, which Finland has no dataset for */
  if (v === "data") {
    const tab = parts[1] || "";
    if (tab === "areas") return buildHash("data/areas/" + (RC_DATA_LEVELS.indexOf(parts[2]) >= 0 ? parts[2] : "kunta"), query);
    if (tab === "projects" || tab === "sources") return buildHash("data/" + tab, query);
    return buildHash("data/areas/kunta", query);
  }
  /* #analysis?a=lat,lon&la=label → #property?p=lat,lon:label — the second pin (`b`/`lb`) belonged
     to Compare, which v2.0 deletes, so it is dropped rather than carried into a one-pin view. */
  if (v === "analysis" || v === "property") {
    const q = {};
    Object.keys(query).forEach(k => { if (["a", "la", "b", "lb", "p"].indexOf(k) < 0) q[k] = query[k]; });
    let p = "";
    if (query.p) p = propSerialise(propParse(query.p));
    else {
      const ll = parseLatLon(query.a || "");
      if (ll) p = propSerialise([{ lat: ll.lat, lon: ll.lon, label: query.la || "" }]);
    }
    if (p) q.p = p;
    return buildHash("property", q);
  }
  /* #compare?a=<type>:<code>&b=… → the a side's area page; unparsable → the map (amendment A1) */
  if (v === "compare") {
    const a = String(query.a || "");
    const m = /^([a-z_]+):(.+)$/.exec(a);
    const q = {};
    Object.keys(query).forEach(k => { if (["a", "b", "c"].indexOf(k) < 0) q[k] = query[k]; });
    if (!m) return buildHash("map", q);
    const type = m[1] === "kommune" ? "kunta" : m[1] === "postnr" ? "postinumero" : m[1] === "kvarter" ? "osa_alue" : m[1];
    if (RC_DATA_LEVELS.indexOf(type) < 0) return buildHash("map", q);
    return buildHash("area/" + type + "/" + m[2], q);
  }
  /* everything else is already canonical; an empty hash is the map */
  return buildHash(path || "map", query);
}

/* the v2 path → the app's own view id. `S.view` did not change in v2.0 except for
   analysis → property, so this is mostly identity. */
const RC_VIEW = {
  map: "makro", area: "area", charts: "charts", property: "property",
  project: "project", public: "public", publist: "publist",
  school: "school", schoollist: "schoollist",
};

function toInternal(hash) {
  const canon = toV2(hash);
  const { parts, query } = splitHash(canon);
  const v = parts[0] || "map";
  if (v === "data") {
    const tab = parts[1] || "areas";
    return { view: tab === "projects" ? "pipeline" : tab === "sources" ? "sources" : "table",
             parts: parts.slice(2), query, tab };   /* parts[0] of an Areas tab is the level */
  }
  return { view: RC_VIEW[v] || "makro", parts: parts.slice(1), query, tab: "" };
}

/* the reverse of toInternal's path half: which v2 path a view id serialises to */
function pathFor(view, tab) {
  if (view === "table") return "data/areas/" + (tab || "kunta");
  if (view === "pipeline") return "data/projects";
  if (view === "sources") return "data/sources";
  if (view === "makro") return "map";
  return view;
}

return { splitHash, buildHash, parseLatLon, propParse, propSerialise, toV2, toInternal,
           pathFor, enc, DATA_LEVELS: RC_DATA_LEVELS, PROP_MAX: RC_PROP_MAX, round: rcRound };
})();

if (typeof module !== "undefined" && module.exports) module.exports = ROUTE_CORE;
if (typeof window !== "undefined") window.ROUTE_CORE = ROUTE_CORE;
