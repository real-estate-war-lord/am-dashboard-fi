/* parseLocation / parseAddress / normAddr — the test-property input on the macro map
   (src/testprop.js). Run with `make test-js` or `node --test tests/`. */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const { parseLocation, parseAddress, normAddr, TP_BOUNDS } = require("../src/testprop.js");

const near = (a, b) => Math.abs(a - b) < 1e-6;
function ok(t, text, lat, lon, source) {
  const r = parseLocation(text);
  assert.strictEqual(r.error, undefined, `expected a hit, got ${r.error}: ${r.message}`);
  assert.ok(near(r.lat, lat) && near(r.lon, lon), `expected ${lat}, ${lon} — got ${r.lat}, ${r.lon}`);
  if (source) assert.strictEqual(r.source, source);
  return r;
}
function err(text, code) {
  const r = parseLocation(text);
  assert.strictEqual(r.error, code, `expected error "${code}", got ${r.error ? r.error : `${r.lat}, ${r.lon}`}`);
  assert.ok(r.message && r.message.length > 10, "an error carries a message the user can act on");
  return r;
}

/* ---------------------------------------------------------------- coordinates */

test("place URL: !3d/!4d wins over the @ viewport centre", () => {
  /* the @ pair is the map centre (24.9384), the !3d/!4d pair the pin itself (24.93825) */
  const url = "https://www.google.com/maps/place/Mannerheimintie+10,+00100+Helsinki/@60.1700,24.9384,17z/data=!3m1!4b1!4m6!3m5!1s0x468df7a0b3f0a0a1:0x1!8m2!3d60.16986!4d24.93825!16s%2Fg%2F11abc";
  ok(0, url, 60.16986, 24.93825, "place");
});

test("place URL without !3d falls back to @", () => {
  ok(0, "https://www.google.com/maps/place/Tampere/@61.49780,23.76090,15z/data=!3m1!4b1", 61.49780, 23.76090, "at");
});

test("bare @ view URL", () => {
  ok(0, "https://www.google.com/maps/@65.01210,25.46510,14z", 65.01210, 25.46510, "at");   // Oulu
});

test("q= parameter with a URL-encoded comma", () => {
  ok(0, "https://maps.google.com/?q=60.16986%2C24.93825", 60.16986, 24.93825, "param");
});

test("q= parameter with a + for the space", () => {
  ok(0, "https://www.google.com/maps?q=60.45180,+22.26660&z=16", 60.45180, 22.26660, "param");   // Turku
});

test("ll= parameter", () => {
  ok(0, "https://www.google.com/maps?ll=62.24150,25.72090&z=15", 62.24150, 25.72090, "param");   // Jyväskylä
});

test("query= parameter", () => {
  ok(0, "https://www.google.com/maps/search/?api=1&query=66.50390%2C25.72940", 66.50390, 25.72940, "param");   // Rovaniemi
});

test("/search/<lat>,<lon> path", () => {
  ok(0, "https://www.google.com/maps/search/60.98270,25.66150", 60.98270, 25.66150, "search");   // Lahti
});

test("plain coordinates — comma, space and semicolon", () => {
  ok(0, "60.16986, 24.93825", 60.16986, 24.93825, "plain");
  ok(0, "60.16986 24.93825", 60.16986, 24.93825, "plain");
  ok(0, "60.16986;24.93825", 60.16986, 24.93825, "plain");
  ok(0, "  61.49780,23.76090  ", 61.49780, 23.76090, "plain");
});

test("short share links cannot be read in the browser", () => {
  const r = err("https://maps.app.goo.gl/abc123XYZ", "short_link");
  assert.match(r.message, /address bar/);
  err("https://goo.gl/maps/abc123", "short_link");
});

test("the far north and Åland are inside the box", () => {
  ok(0, "69.90600, 27.02320", 69.90600, 27.02320, "plain");   // Utsjoki, the northernmost kunta
  ok(0, "60.09730, 19.93560", 60.09730, 19.93560, "plain");   // Mariehamn — locate() is what says Åland
});

test("swapped lon/lat is rejected by the Finland box", () => {
  /* Helsinki written lon-first: 24.9 is not a Finnish latitude */
  err("24.93825, 60.16986", "outside_fi");
});

test("clearly foreign coordinates are rejected", () => {
  err("https://www.google.com/maps/@48.85840,2.29450,17z", "outside_fi");   // Paris
  err("55.67610, 12.56830", "outside_fi");                                  // Copenhagen
  err("59.32930, 18.06860", "outside_fi");                                  // Stockholm — below 59.7 N
});

test("Tallinn is below the box; St Petersburg is inside it and locate() is what rejects it", () => {
  err("59.43700, 24.75360", "outside_fi");   // Tallinn — 59.44 N is below the 59.7 N floor
  /* St Petersburg is at 59.93 N, 30.34 E — inside a box drawn around Finland, because Finland
     reaches to 31.6 E. The coarse box cannot reject it; the point-in-polygon lookup does. */
  ok(0, "59.93430, 30.33510", 59.93430, 30.33510, "plain");
});

test("Haparanda passes the coarse box — locate() is what rejects it", () => {
  /* the box is deliberately generous; the Swedish side of the Tornio valley sits inside it,
     so the point-in-polygon lookup in app.js is what reports "outside Finland" */
  const r = ok(0, "65.83560, 24.13030", 65.83560, 24.13030, "plain");
  assert.strictEqual(r.source, "plain");
  assert.ok(TP_BOUNDS.lat[0] < 65.8356 && 24.1303 > TP_BOUNDS.lon[0]);
});

test("a negative or out-of-range number never becomes a silent hit", () => {
  err("-60.16986, 24.93825", "outside_fi");
  err("60.16986, -24.93825", "outside_fi");
});

test("empty input asks for something to work with", () => {
  err("", "empty");
  err("   ", "empty");
});

/* ---------------------------------------------------------------- addresses */

const addr = (text, street, house, place) => {
  const r = parseLocation(text);
  assert.strictEqual(r.source, "address", `expected an address, got ${r.error || r.source}`);
  assert.strictEqual(r.address.street, street);
  assert.strictEqual(r.address.house, house);
  if (place !== undefined) assert.strictEqual(r.address.place, place);
  return r.address;
};

test("street, number and kunta", () => {
  addr("Mannerheimintie 10, Helsinki", "Mannerheimintie", "10", "Helsinki");
  addr("Hämeenkatu 14, Tampere", "Hämeenkatu", "14", "Tampere");
});

test("a postal code counts as the place, with or without the comma", () => {
  addr("Mannerheimintie 10, 00100 Helsinki", "Mannerheimintie", "10", "00100 Helsinki");
  addr("Mannerheimintie 10 00100 Helsinki", "Mannerheimintie", "10", "00100 Helsinki");
  addr("Aleksanterinkatu 52, 00100", "Aleksanterinkatu", "52", "00100");
});

test("the entrance letter is kept and the flat number dropped", () => {
  const a = addr("Kalevankatu 12 A 3, Helsinki", "Kalevankatu", "12", "Helsinki");
  assert.strictEqual(a.letter, "A");
  assert.strictEqual(a.flat, "3");
  const b = addr("Kalevankatu 12a, Helsinki", "Kalevankatu", "12", "Helsinki");
  assert.strictEqual(b.letter, "A");
});

test("a street name that ends in a number keeps it", () => {
  /* the scan starts at the second token, so "Kehä III 5" is house 5 on Kehä III */
  addr("Kehä III 5, Vantaa", "Kehä III", "5", "Vantaa");
  addr("Vanha Hämeenkatu 3, Turku", "Vanha Hämeenkatu", "3", "Turku");
});

test("a street with no number is still an address", () => {
  const a = addr("Mannerheimintie, Helsinki", "Mannerheimintie", null, "Helsinki");
  assert.strictEqual(a.letter, "");
});

test("a Swedish street name survives unchanged", () => {
  addr("Ålandsvägen 24, Mariehamn", "Ålandsvägen", "24", "Mariehamn");
  addr("Skillnaden 3, Helsingfors", "Skillnaden", "3", "Helsingfors");
});

test("a link with no coordinates is reported as a link, not searched as an address", () => {
  const r = err("https://www.google.com/maps/place/Mannerheimintie+10", "no_match");
  assert.match(r.message, /no coordinates/i);
});

test("a bare word is not an address — a street needs a number or a place", () => {
  /* without a house number AND without a kunta or postal code there is nothing to look up,
     so the text is refused rather than guessed at */
  err("hello", "no_match");
  err("Mannerheimintie", "no_match");
  err("Kamppi", "no_match");
  err("?? !!", "no_match");
});

test("normAddr folds the Finnish way and collapses punctuation", () => {
  assert.strictEqual(normAddr("Mannerheimintie"), "mannerheimintie");
  assert.strictEqual(normAddr("Töölönkatu"), "toolonkatu");
  assert.strictEqual(normAddr("Ålandsvägen"), "alandsvagen");
  assert.strictEqual(normAddr("  Vanha   Hämeenkatu, "), "vanha hameenkatu");
  assert.strictEqual(normAddr("Kehä III"), "keha iii");
  /* the same street written either way must normalise to one key, or the lookup misses it */
  assert.strictEqual(normAddr("Itäväylä"), normAddr("ITÄVÄYLÄ"));
});

test("parseAddress on its own refuses a URL and empty text", () => {
  assert.strictEqual(parseAddress("https://example.com/a 12"), null);
  assert.strictEqual(parseAddress(""), null);
  assert.strictEqual(parseAddress(null), null);
});
