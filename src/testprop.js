/* AM Dashboard — Finland Edition · testprop.js
   Reads a location out of a pasted Google Maps link, a plain "lat, lon" pair, or a Finnish
   street address. Browser only: nothing is fetched and no link is followed, so a short share
   link (maps.app.goo.gl) cannot be resolved here — the user is asked for the long URL.

   Coordinates are answered here and now. An **address** is only *parsed* here — into street,
   number and an optional place — because resolving it needs the DVV address file, which
   app.js loads per kunta. This file stays free of DOM, window and fetch so that
   tests/testprop.test.js (`make test-js`) can run it under plain node.

   Inlined into dist/index.html by scripts/build_dashboard.py.
*/
"use strict";

/* coarse Finland box — a first sanity check on the numbers (catches a swapped lon/lat pair).
   The real "is this in Finland" answer comes from locate() in app.js, on our own rings. */
const TP_BOUNDS = { lat: [59.7, 70.1], lon: [19.0, 31.6] };
const TP_SHORT_RE = /\b(?:maps\.app\.goo\.gl|goo\.gl|g\.co\/kgs)\b/i;
const TP_SHORT_MSG = "Short share links can't be read in the browser. Open the link and copy the full URL from the address bar, or right-click the spot in Google Maps and paste the coordinates.";
/* the formats the input accepts, in the order parseLocation tries them — also shown in the "?" tooltip */
const TP_FORMATS = [
  ["place", "…/place/Name/@60.17,24.94,17z/data=…!3d60.16986!4d24.93825", "a Google Maps place URL (the !3d/!4d pin wins over the @ viewport)"],
  ["at", "…/maps/@60.16986,24.93825,17z", "a Google Maps view URL"],
  ["param", "…/maps?q=60.16986,24.93825", "a q= / ll= / query= parameter"],
  ["search", "…/maps/search/60.16986,24.93825", "a Google Maps search URL"],
  ["plain", "60.16986, 24.93825", "plain coordinates — comma, semicolon or space"],
  ["address", "Mannerheimintie 10, Helsinki", "a street address — street, number, and the kunta or postal code"]];

const tpNum = s => { const v = parseFloat(s); return isNaN(v) ? null : v; };
const TP_D = "(-?\\d{1,3}(?:\\.\\d+)?)";                 /* a signed decimal degree */
const TP_SEP = "\\s*[,;]\\s*";                           /* the separator once "+" and %2C are decoded */

function tpPair(lat, lon, source) {
  if (lat == null || lon == null) return null;
  if (lat < TP_BOUNDS.lat[0] || lat > TP_BOUNDS.lat[1] || lon < TP_BOUNDS.lon[0] || lon > TP_BOUNDS.lon[1])
    return { error: "outside_fi", message: `${lat}, ${lon} is outside Finland (latitude ${TP_BOUNDS.lat[0]}–${TP_BOUNDS.lat[1]} N, longitude ${TP_BOUNDS.lon[0]}–${TP_BOUNDS.lon[1]} E). Latitude comes first — check the order.` };
  return { lat, lon, source };
}

/* ---------------------------------------------------------------- addresses

   Finnish addresses are written "Katu 12", "Katu 12 A 3", "Katu 12, 00100 Helsinki". The
   street name itself may end in a number (Vanha Hämeenkatu, but also Kehä III), and the
   Swedish name is often given beside the Finnish one with a slash — both are in DVV, so the
   whole string is kept and the lookup decides.

   normAddr() is the one normalisation both this file and the address file must agree on:
   lower case, accents folded the Finnish way (ä and ö are letters, not decorated a and o —
   so they are folded to "a"/"o" only for matching, never for display), punctuation dropped,
   whitespace collapsed. If this ever changes, the address files must be rebuilt. */
const TP_ADDR_FOLD = { "ä": "a", "å": "a", "ö": "o", "Ä": "a", "Å": "a", "Ö": "o", "é": "e", "ü": "u" };
function normAddr(s) {
  return String(s == null ? "" : s).toLowerCase()
    .replace(/[äåöéü]/g, c => TP_ADDR_FOLD[c] || c)
    .replace(/[.,:;'`´"()]/g, " ")
    .replace(/\s+/g, " ").trim();
}

/* "12 A 3" / "12-14" / "12a" -> the house number the register knows, as a string.
   DVV publishes the number as an integer plus a letter, so "12 A 3" is house 12, entrance A,
   flat 3 — the flat is dropped, because the register has no coordinate for it. */
const TP_HOUSE_RE = /^(\d{1,4})\s*([a-zäöå]?)\b/i;

/* text -> {street, house, letter, place} | null. `place` is a kunta name or a 5-digit postal
   code if the text carried one; it is what lets the lookup load one kunta instead of all. */
function parseAddress(text) {
  let s = String(text == null ? "" : text).trim();
  if (!s || /^https?:/i.test(s)) return null;
  let place = "";
  /* a trailing ", 00100 Helsinki" / ", Helsinki" / " 00100 Helsinki" — take the last comma group */
  const parts = s.split(",").map(x => x.trim()).filter(Boolean);
  if (parts.length > 1) { place = parts.pop(); s = parts.join(" ").trim(); }
  else {
    const m = s.match(/\s(\d{5})(?:\s+(.+))?$/);        /* "Katu 12 00100 Helsinki" with no comma */
    if (m) { place = (m[1] + " " + (m[2] || "")).trim(); s = s.slice(0, m.index).trim(); }
  }
  /* The house number is the FIRST standalone number after the street name, scanning from the
     left: "Kalevankatu 12 A 3" is house 12, entrance A, flat 3 — not house 3. A street name
     that itself ends in a numeral survives because the numeral is not a bare arabic number
     ("Kehä III 5" → house 5), and a two-word street survives because the scan starts at the
     second token ("Vanha Hämeenkatu 3" → house 3). */
  const toks = s.split(/\s+/).filter(Boolean);
  let hi = -1;
  for (let i = 1; i < toks.length; i++) { if (/^\d{1,4}[a-zäöå]?$/i.test(toks[i])) { hi = i; break; } }
  if (hi < 0) {
    /* No number at all. A bare word is not enough — "Kamppi" is a district, "hello" is not an
       address, and neither can be looked up. A street name is accepted only when the text also
       names a kunta or a postal code, which is what makes the lookup possible at all. */
    if (!place || !/[a-zäöåA-ZÄÖÅ]{3}/.test(s)) return null;
    return { street: s, house: null, letter: "", place, flat: "" };
  }
  const street = toks.slice(0, hi).join(" ");
  const rest = toks.slice(hi).join(" ");
  const m = rest.match(TP_HOUSE_RE);
  if (!m || !street) return null;
  return { street, house: m[1], letter: (m[2] || "").toUpperCase(),
           place, flat: rest.slice(m[0].length).trim() };
}

/* text → {lat, lon, source} | {address:{…}, source:"address"} | {error, message} */
function parseLocation(text) {
  const raw = String(text == null ? "" : text).trim();
  if (!raw) return { error: "empty", message: "Paste a Google Maps link, coordinates as \"60.16986, 24.93825\", or an address as \"Mannerheimintie 10, Helsinki\"." };
  /* "+" is a space in a query string and %2C a comma — decode once so every pattern below sees plain text */
  let s = raw;
  try { s = decodeURIComponent(raw.replace(/\+/g, " ")); } catch (e) { /* a stray % — read the text as it stands */ }

  if (TP_SHORT_RE.test(s)) return { error: "short_link", message: TP_SHORT_MSG };

  let m;
  /* 1. the place pin (!3d lat !4d lon) — the actual spot, so it wins over the @ viewport centre */
  if ((m = s.match(new RegExp("!3d" + TP_D + "!4d" + TP_D)))) return tpPair(tpNum(m[1]), tpNum(m[2]), "place");
  /* 2. the viewport centre: @lat,lon,17z */
  if ((m = s.match(new RegExp("@" + TP_D + TP_SEP + TP_D)))) return tpPair(tpNum(m[1]), tpNum(m[2]), "at");
  /* 3. a coordinate parameter: q= / ll= / query= / daddr= / center= */
  if ((m = s.match(new RegExp("(?:^|[?&#])(?:q|ll|query|daddr|center)=" + TP_D + TP_SEP + TP_D, "i")))) return tpPair(tpNum(m[1]), tpNum(m[2]), "param");
  /* 4. /search/<lat>,<lon> */
  if ((m = s.match(new RegExp("/search/" + TP_D + TP_SEP + TP_D)))) return tpPair(tpNum(m[1]), tpNum(m[2]), "search");
  /* 5. the coordinates on their own — comma, semicolon or whitespace */
  if ((m = s.match(new RegExp("^" + TP_D + "(?:" + TP_SEP + "|\\s+)" + TP_D + "$")))) return tpPair(tpNum(m[1]), tpNum(m[2]), "plain");

  /* 6. an address. A Google Maps *place* URL that carried no coordinates is not one — it is a
     link that lost its pin, and saying so is more useful than searching for its path segment. */
  if (/^https?:/i.test(s)) return { error: "no_match", message: "That Google Maps link carries no coordinates. Open it, then copy the full URL from the address bar, or right-click the spot and copy the \"60.16986, 24.93825\" pair it offers." };
  const a = parseAddress(s);
  if (a) return { address: a, source: "address" };

  return { error: "no_match", message: "No coordinates or address in that text. Paste the full Google Maps URL from the address bar, right-click the spot in Google Maps and copy the coordinate pair, or type an address as \"Mannerheimintie 10, Helsinki\"." };
}

if (typeof module !== "undefined" && module.exports) module.exports = { parseLocation, parseAddress, normAddr, TP_BOUNDS, TP_FORMATS, TP_SHORT_MSG };
