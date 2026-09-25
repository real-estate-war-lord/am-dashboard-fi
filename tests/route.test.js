/* node --test tests/route.test.js — the hash codec (src/route_core.js).

   Every v1.1 spelling in the table below is a link that exists in somebody's bookmarks. The rule
   these tests defend: a v1.1 link lands on the right v2.0 page, and feeding the codec its own
   output changes nothing (otherwise parseHash()'s canonical replaceState would rewrite the address
   bar on every frame). */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const RC = require("../src/route_core.js");

/* old spelling → canonical v2.0 spelling */
const TABLE = [
  ["#table", "data/areas/kunta"],
  ["#table/kunta", "data/areas/kunta"],
  ["#table/postinumero", "data/areas/postinumero"],
  ["#table/osa_alue", "data/areas/osa_alue"],
  ["#table/nonsense", "data/areas/kunta"],
  ["#table/postinumero?ind=growth&y=2024", "data/areas/postinumero?ind=growth&y=2024"],
  ["#pipeline", "data/projects"],
  ["#pipeline?ptype=rail&pstatus=decided", "data/projects?ptype=rail&pstatus=decided"],
  ["#sources", "data/sources"],
  ["#data", "data/areas/kunta"],
  ["#data/national", "data/areas/kunta"],          /* Finland ships no national-series dataset */
  ["#data/areas/osa_alue", "data/areas/osa_alue"],
  ["#data/projects", "data/projects"],
  ["#data/sources", "data/sources"],
  ["#analysis?a=60.24480,24.86650&la=Koti", "property?p=60.2448,24.8665:Koti"],
  ["#analysis?a=60.2448,24.8665", "property?p=60.2448,24.8665"],
  ["#analysis", "property"],
  ["#compare?a=kunta:091&b=kunta:837", "area/kunta/091"],
  ["#compare?a=postinumero:00100&b=postinumero:00200", "area/postinumero/00100"],
  ["#compare?a=osa_alue:091010", "area/osa_alue/091010"],
  ["#compare?a=kommune:091", "area/kunta/091"],     /* a link copied from the Danish edition */
  ["#compare", "map"],
  ["#compare?a=nonsense", "map"],
  ["#map", "map"],
  ["#map/091/postinumero?ind=growth", "map/091/postinumero?ind=growth"],
  ["#area/kunta/091?ind=rent", "area/kunta/091?ind=rent"],
  ["#charts?ind=growth&a=kunta:091", "charts?ind=growth&a=kunta:091"],
  ["#project/vt4-oulu", "project/vt4-oulu"],
  ["#school/280657", "school/280657"],
  ["", "map"],
];

test("every v1.1 hash lands on its v2.0 spelling", () => {
  for (const [from, to] of TABLE) assert.strictEqual(RC.toV2(from), to, from);
});

test("toV2 is idempotent — the address bar is rewritten once, not every frame", () => {
  for (const [from] of TABLE) {
    const once = RC.toV2(from);
    assert.strictEqual(RC.toV2(once), once, from);
    assert.strictEqual(RC.toV2("#" + once), once, from);
  }
});

test("the second Compare pin and the second analysis pin are dropped, not carried", () => {
  assert.strictEqual(RC.toV2("#analysis?a=60.2,24.9&b=61.5,23.8&lb=Toinen"), "property?p=60.2,24.9");
  assert.ok(!RC.toV2("#compare?a=kunta:091&b=kunta:837").includes("837"));
});

test("query keys that are not part of the route survive the rewrite", () => {
  assert.strictEqual(RC.toV2("#analysis?a=60.2,24.9&ind=unemp&lay=infra"),
                     "property?ind=unemp&lay=infra&p=60.2,24.9");
  assert.strictEqual(RC.toV2("#table/kunta?ind=unemp&y=2020"), "data/areas/kunta?ind=unemp&y=2020");
});

test("splitHash / buildHash round-trip", () => {
  const { path, query } = RC.splitHash("#area/kunta/091?ind=growth&y=2024");
  assert.strictEqual(path, "area/kunta/091");
  assert.deepStrictEqual(query, { ind: "growth", y: "2024" });
  assert.strictEqual(RC.buildHash(path, query), "area/kunta/091?ind=growth&y=2024");
});

test("buildHash drops null and undefined but keeps an empty string", () => {
  assert.strictEqual(RC.buildHash("map", { a: null, b: undefined, c: "", d: 0 }), "map?c=&d=0");
});

test("a hash is readable: comma, colon and slash stay unescaped", () => {
  assert.strictEqual(RC.buildHash("property", { p: "60.2448,24.8665:Koti" }),
                     "property?p=60.2448,24.8665:Koti");
  /* but the characters that would break the codec are still escaped */
  assert.strictEqual(RC.buildHash("property", { p: "a&b=c?d#e" }), "property?p=a%26b%3Dc%3Fd%23e");
});

test("parseLatLon takes the three separators and refuses everything else", () => {
  assert.deepStrictEqual(RC.parseLatLon("60.2448, 24.8665"), { lat: 60.2448, lon: 24.8665 });
  assert.deepStrictEqual(RC.parseLatLon("60.2448;24.8665"), { lat: 60.2448, lon: 24.8665 });
  assert.deepStrictEqual(RC.parseLatLon("60.2448 24.8665"), { lat: 60.2448, lon: 24.8665 });
  assert.deepStrictEqual(RC.parseLatLon("60.244801234,24.866501234"), { lat: 60.2448, lon: 24.8665 });
  assert.strictEqual(RC.parseLatLon("Mannerheimintie 10"), null);
  assert.strictEqual(RC.parseLatLon("99.5, 24.9"), null);       /* not a latitude */
  assert.strictEqual(RC.parseLatLon(""), null);
});

test("the property codec is a list, and the list has a ceiling", () => {
  assert.deepStrictEqual(RC.propParse("60.2448,24.8665:Koti;60.17,24.94"),
    [{ lat: 60.2448, lon: 24.8665, label: "Koti" }, { lat: 60.17, lon: 24.94, label: "" }]);
  assert.strictEqual(RC.propSerialise(RC.propParse("60.2448,24.8665:Koti;60.17,24.94")),
                     "60.2448,24.8665:Koti;60.17,24.94");
  const many = Array.from({ length: 40 }, (_, i) => `60.${i},24.9`).join(";");
  assert.strictEqual(RC.propParse(many).length, RC.PROP_MAX);
  /* an unparsable item is dropped, the rest of the list survives */
  assert.strictEqual(RC.propParse("nonsense;60.17,24.94").length, 1);
});

test("toInternal answers with the app's own view ids", () => {
  assert.strictEqual(RC.toInternal("#table/osa_alue").view, "table");
  assert.deepStrictEqual(RC.toInternal("#table/osa_alue").parts, ["osa_alue"]);
  assert.strictEqual(RC.toInternal("#pipeline").view, "pipeline");
  assert.strictEqual(RC.toInternal("#sources").view, "sources");
  assert.strictEqual(RC.toInternal("#map/091").view, "makro");
  assert.deepStrictEqual(RC.toInternal("#map/091").parts, ["091"]);
  assert.strictEqual(RC.toInternal("#analysis?a=60.2,24.9").view, "property");
  assert.strictEqual(RC.toInternal("#analysis?a=60.2,24.9").query.p, "60.2,24.9");
  assert.strictEqual(RC.toInternal("#compare?a=kunta:091").view, "area");
});

test("pathFor is the reverse of toInternal's path half", () => {
  assert.strictEqual(RC.pathFor("table", "postinumero"), "data/areas/postinumero");
  assert.strictEqual(RC.pathFor("pipeline"), "data/projects");
  assert.strictEqual(RC.pathFor("sources"), "data/sources");
  assert.strictEqual(RC.pathFor("makro"), "map");
  assert.strictEqual(RC.pathFor("charts"), "charts");
  for (const v of ["table", "pipeline", "sources", "makro", "charts", "property"])
    assert.strictEqual(RC.toInternal("#" + RC.pathFor(v, "kunta")).view, v, v);
});
