# AM Dashboard — Finland Edition: Open Data Map & Search Spec

**Status:** v0.1 · 2026-09-24 · desk research done, **nothing probed live yet** (the cloud sandbox cannot reach Finnish hosts — same as DK/SE; the live probe runs on the Mac in Phase 1 of `BUILD_PLAN_FI.md`)
**Scope:** everything the Danish edition has (v2.5.1 + climate branch) and the Swedish parity plan covers — macro/market map, safety, outlook, schools, test property + Analysis, climate, overlays — rebuilt on **Finnish public sources only**, plus the Finland-only extras.
**Principles carried over:** hard data only (official figures or plain arithmetic on them); English UI with Finnish source terms kept verbatim; every figure has source + period + fetch date + verify-at-source link; suppressed ≠ 0; not covered ≠ 0. **No data from the private Portfolio Manager** — the FI edition is public and built only from open sources.

Legend: ✅ confirmed to exist (table/page seen 2026-09-24) · 🔎 exists, exact ID/route to confirm in the probe · ⚠ gap / licence question

---

## 0. TL;DR — Finland is the richest of the three

| | Denmark | Sweden | **Finland** |
|---|---|---|---|
| Core API | DST StatBank | SCB PxWebApi v2 | **Tilastokeskus StatFin PxWeb API** (keyless, **CC BY 4.0** — attribution required) |
| Sub-municipal level | postnummer | RegSO/DeSO | **postinumeroalue (~3 000)** with a full socio-economic pack (**Paavo**) |
| Realised price €/m² below municipality | ✓ postal, quarterly | ✗ | ✅ **postal code, quarterly + annual** (`ashi 13mt / 13mu`) |
| Rent €/m² below municipality | kommune (scrape) | kommun (survey) | ✅ **postal code, quarterly** (`asvu 13eb`, free-market rents) |
| Building register | BBR (key) | none open | 🔎 **Ryhti rakennustiedot** (SYKE, open WFS/OGC) + DVV building addresses (open) |
| Zoning / land-use plans | Plandata | none national | 🔎 **Ryhti kaavat** — national plan data, open. Finland-only growth signal |
| City 3rd level | Copenhagen kvarterer | DeSO (national) | **Helsinki region osa-alueet** (Aluesarjat PxWeb, HRI geodata) |

**Verdict:** everything in the DK chip row is reproducible, and **price + rent at postal-code level make Finland the strongest market layer of the three**. Main weak spots: crime below municipality, school results (Finland does not publish comprehensive-school results), days-on-market / supply (only in private portals).

---

## 1. What to search — indicator by indicator

### 1a. Core chip row (DK `makro` → Finland)

| # | key | Indicator | Finnish source | Level | Cadence | Status |
|---|---|---|---|---|---|---|
| 1 | `growth` | Population growth %/yr | StatFin `vaerak` (population by area, annual) · Paavo `he_vakiy` | kunta, **postal** | annual | 🔎 |
| 2 | `income` | Median income of inhabitants / mean household income | Paavo `hr_mtu`, `tr_ktu` · StatFin `tjt` (kunta) | **postal**, kunta | annual (≈2-yr lag) | 🔎 |
| 3 | `young` | Share aged 20–34 | Paavo age bands `he_20_24`…`he_30_34` | **postal** | annual | 🔎 |
| 4 | `yks` | One-person households % | Paavo `te_yks` ÷ `te_taly` | **postal** | annual | 🔎 |
| 5 | `kela` | Housing-allowance households % | **Kelasto** yleinen asumistuki, saajaruokakunnat kunnittain; StatFin `astuki` | kunta | annual/monthly | 🔎 (Kelasto export route) |
| 6 | `rent` | Free-market rent €/m²/month | StatFin `asvu` **13eb** (vapaarahoitteiset, postinumeroalueittain, huoneluku) ✅; ARA rents in the same database | **postal** (larger cities), kunta | **quarterly** | ✅ table seen |
| 7 | `vuok` | Renter households % | Paavo `te_vuok_as` ÷ `te_taly` | **postal** | annual | 🔎 |
| 8 | `tyott` | Unemployment % | Paavo `pt_tyott` ÷ `pt_tyovy` (annual); StatFin `tyonv` TEM työnvälitystilasto (kunta, **monthly**) | postal / kunta | annual / monthly | 🔎 |
| 9 | `kork` | Tertiary education % | Paavo `ko_yl_kork` + `ko_al_kork` ÷ `ko_ika18y` | **postal** | annual | 🔎 |
| 10 | `kt` | Multi-dwelling (kerrostalo) share | Paavo `ra_kt_as` ÷ `ra_asunn` | **postal** | annual | 🔎 |
| 11 | `vk` | Foreign-language speakers % | StatFin `vaerak` by language | kunta (Helsinki region: osa-alue) | annual | 🔎 |
| 12 | `akoko` | Avg dwelling size m² / m² per person | Paavo `ra_as_kpa`, `te_as_valj` | **postal** | annual | 🔎 |

### 1b. Market & pipeline (Finland is strong here)

| key | Indicator | Source | Level | Cadence | Status |
|---|---|---|---|---|---|
| `price_m2` | Old flats €/m² (kerrostalo/rivitalo) + sales count | StatFin `ashi` **13mt** (quarterly), **13mu** (annual) ✅; kunta **13mx** ✅ | **postal**, kunta | quarterly | ✅ tables seen |
| `price_new` | New flats €/m² | StatFin `ashi` (osa-alueittain table, e.g. `12dg`) | big cities, sub-areas | annual | 🔎 |
| `price_idx` | Price index + y/y | StatFin `ashi` index tables | kunta/region | quarterly/monthly | 🔎 |
| `rent_chg` | Rent change y/y | StatFin `asvu` index tables | region, big cities | quarterly | 🔎 |
| `starts` / `completions` / `permits` | Dwellings started / completed / permitted per 1 000 dwellings | StatFin `ras` (rakennus- ja asuntotuotanto) | kunta | quarterly/monthly | 🔎 |
| `stock` | Dwelling stock by building type & tenure | StatFin `asas` / `rakke` | kunta | annual | 🔎 |
| `vacant` | Unoccupied dwellings % | StatFin asuntokanta "asunnot joissa ei vakituisia asukkaita" | kunta | annual | 🔎 |
| `migration` | Net migration (in-country + immigration) | StatFin `muutl` | kunta | annual/monthly | 🔎 |

### 1c. Macro panel

| Indicator | Source | Status |
|---|---|---|
| Euribor 3/12 m, daily | ECB Data Portal API (`FM` dataset) — keyless; Suomen Pankki tables as cross-check | 🔎 |
| New mortgage rate Finland, mortgage stock | ECB `MIR` (FI) · Suomen Pankki open data | 🔎 |
| 10-yr Finnish govt bond | ECB / Suomen Pankki | 🔎 |
| CPI + rent sub-index (khi, COICOP 04.1) | StatFin `khi` | 🔎 |
| GDP, construction volume | StatFin `ntp`, `rakvol` | 🔎 |
| Property tax rates per kunta (vakituinen asunto, yleinen) | Verohallinto annual open file | 🔎 |
| Municipal income tax %, municipal finances (vuosikate, lainakanta/as.) | Verohallinto · StatFin kuntatalous / Kuntaliitto | 🔎 |

### 1d. Parity layers (DK v2.0–v2.6 → Finland)

| DK feature | Finnish source | Level | Status / caveat |
|---|---|---|---|
| **Safety / crime** | StatFin **`rpk`** Rikos- ja pakkokeinotilasto (old `polrik` discontinued 2015 — do not use) — offences known to police by type | kunta, quarterly + annual | 🔎 kunta table ID to confirm. No open sub-kunta crime → Helsinki: check city safety survey (turvallisuustutkimus) per peruspiiri |
| **Population outlook** | StatFin `vaenn` **Väestöennuste 2024** (tables `14wy` ✅ etc.) | kunta | ✅; Helsinki: city forecast by osa-alue (HRI "Helsingin väestö- ja asuntotuotantoennuste alueittain") = the Finnish KK-equivalent; Espoo/Vantaa via Aluesarjat |
| **Schools** | ⚠ Finland publishes **no comprehensive-school results**. Available: **YTL** matriculation results per lukio (open statistics), school locations (Opetushallitus / Palvelukartta / OSM) | lukio points | Honest gap: show locations + lukio results only |
| **Test property + Analysis + Compare** | Port `testprop.js`; Finland box 59.7–70.1 N / 19.0–31.6 E. **Bonus:** DVV "Rakennusten osoitetiedot" (open, CC BY 4.0) enables *address search* offline, not only Google-Maps links | postal / osa-alue | 🔎 |
| **Climate risk** | SYKE **tulvavaaravyöhykkeet** (vesistö + meri, 1/20…1/1000) WMS/WFS · sea-level scenarios (Ilmatieteen laitos / SYKE) · HSY/Helsinki hulevesi maps where they exist · STUK radon (optional) | area share per postal / osa-alue | 🔎 layer names + licence |
| **Services** | OSM Geofabrik Finland (ODbL) · **HSL GTFS** (open) + Fintraffic national GTFS · Helsinki **Palvelukartta API** (official city services, HSY area) · LIPAS (sports) | points | 🔎 |
| **Public buildings** | **Ryhti** buildings by käyttötarkoitus (education, health, daycare, culture) · Palvelukartta for HSY | points | 🔎 |
| **Infra projects** | Hand-curated 30–50: Väylävirasto hankkeet (open WFS), Liikenne12 programme, Kruunusillat, Vantaan ratikka, Espoon kaupunkirata, Lentorata, Tunnin juna / Itärata, Tampere/Turku tram plans | points/lines | curation |
| **Buildings micro layer** (DK BBR v1.5) | **Ryhti rakennustiedot** (year, use, floor area, storeys — fields to confirm) + ARA energiatodistukset (open) | building | 🔎 |

### 1e. Finland-only extras

| Extra | Source | Why it matters |
|---|---|---|
| **Zoning pipeline** | Ryhti kaavat (asema-/yleiskaavat, national, open) · Helsinki asemakaavat WFS | Upcoming kerrosala per area = growth signal the DK/SE editions can't show |
| **1 km grid** | Tilastokeskus ruututietokanta 1 km (open) | Optional fine population layer |
| **Public construction tenders** | Hilma hankintailmoitukset (API) | Upcoming schools/hospitals signal (optional, v2) |

### 1f. Leasing / AM layer (later, private)

Same idea as SE HomeQ: **Oikotie** (existing `oikotie-rental-scraper` skill), Vuokraovi, landlords' own sites (SATO, Lumo, Avara, Retta, …). ⚠ ToS: scrape small, keep local/private, never republish in the public repo. Benchmark = `asvu 13eb` for the same postal code.

### 1g. Known gaps (say them in the README)

Days-on-market and supply (only Oikotie/Etuovi, KVKL hintaseuranta not open) · crime below kunta · comprehensive-school results · forced sales · MML kauppahintarekisteri is paid (only needed for property-level transactions — postal-level `ashi` covers the dashboard).

---

## 2. Geography model

| Level | Count | Polygon source | Licence |
|---|---|---|---|
| Maakunta | 19 | Tilastokeskus WFS `tilastointialueet` | CC BY 4.0 |
| **Kunta** | ≈308 (confirm 2026 kuntajako) | Tilastokeskus WFS `tilastointialueet:kunta1000k_2026` 🔎 | CC BY 4.0 |
| **Postinumeroalue** | ≈3 000 | Paavo WFS `postialue:pno_tilasto_2026` 🔎 (polygons + all Paavo variables in one layer) | CC BY 4.0 |
| **Helsinki region osa-alue** (3rd level) | Helsinki ≈148 osa-aluetta + Espoo/Vantaa/Kauniainen | HRI / kartta.hel.fi WFS; Aluesarjat PxWeb (`api.aluesarjat.fi`, `stat.hel.fi`) | CC BY 4.0 |
| 1 km grid (optional) | — | Tilastokeskus ruututietokanta | CC BY 4.0 |

**Traps:** (1) **Paavo vintage** — postal-code boundaries change yearly; pin `pno_tilasto_<year>` per table, never join across years silently. (2) Postal codes are 5-digit strings with leading zeros (`00100`) — never cast to int. (3) Kunta codes are 3-digit with leading zeros (`091` Helsinki). (4) Paavo suppresses small areas (<30 residents / <10 households) — suppressed ≠ 0. (5) `ashi` postal prices are suppressed when sales are few; show `–`. (6) Request `EPSG:4326` from the WFS (default is ETRS-TM35FIN, EPSG:3067).

---

## 3. How to search — method

1. **Probe first, on the Mac** (`scripts/probe_fi.py`, stdlib only): for every 🔎 row print `name | HTTP | seconds | bytes | result` into `docs/PROBE_FI.md`. The cloud sandbox is blocked from `pxdata.stat.fi`, `geo.stat.fi`, `api.aluesarjat.fi`, SYKE etc.
2. **StatFin:** list tables with `GET https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/<db>/`, read metadata with `GET …/<table>.px`, pull with `POST …/<table>.px` + JSON query, `"response":{"format":"json-stat2"}`. Check whether a PxWebApi v2 endpoint exists (Tilastokeskus is migrating) and prefer it if live. Respect the rate limit (≈10 calls/10 s, cell cap per call — read from `/config` or errors).
3. **Paavo:** one WFS call per year gives polygons *and* variables; archive raw, simplify with mapshaper.
4. **Browser-only routes** (Kelasto export, YTL statistics, Verohallinto tax files, Väylävirasto project list): Claude Code finds the file URL once, pins it in `config/sources.json`, logs it.
5. **Spot-check** 5 kunta × 3 indicators + 3 postal codes against the PxWeb UI; log in `docs/VERIFICATION.md`. Known references to capture in the probe: Helsinki (091) population, 00100 price €/m², 00100 rent €/m².
6. **Licence note per source** in `docs/SOURCES.md` (Tilastokeskus CC BY 4.0 requires the attribution "Lähde: Tilastokeskus").

Sources: [StatFin asvu 13eb](https://pxdata.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__asvu/statfin_asvu_pxt_13eb.px/) · [StatFin ashi 13mu](https://pxdata.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__ashi/statfin_ashi_pxt_13mu.px/) · [ashi 13mt](https://pxdata.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__ashi/statfin_ashi_pxt_13mt.px/) · [ashi 13mx](https://pxdata.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__ashi/statfin_ashi_pxt_13mx.px/) · [Väestöennuste 2024 14wy](https://pxdata.stat.fi/PxWeb/pxweb/fi/StatFin/StatFin__vaenn/statfin_vaenn_pxt_14wy.px/) · [Paavo](https://stat.fi/fi/palvelut/tilastodatapalvelut/paikkatietoaineistot/postinumeroalueittainen-paikkatieto-paavo) · [Paavo WFS](https://geo.stat.fi/geoserver/postialue/wfs?service=WFS&request=GetCapabilities&version=1.0.0) · [Rikos- ja pakkokeinotilasto](https://stat.fi/fi/tilasto/rpk) · [polrik discontinued](https://stat.fi/tilasto/polrik) · [Ryhti rakennustiedot](https://ckan.ymparisto.fi/dataset/rakennetun-ympariston-tietojarjestelman-rakennustiedot) · [Ryhti rajapinnat](https://github.com/sykefi/Ryhti-rajapintakuvaukset) · [SYKE open web services](https://www.syke.fi/en/environmental-data/open-web-services) · [Kelasto asumistuki](https://raportit.kela.fi/ibi_apps/WFServlet?IBIF_ex=NIT150AL) · [Aluesarjat](https://stat.hel.fi/pxweb/fi/Aluesarjat/) · [Helsinki forecast by area](https://avoindata.suomi.fi/data/fi/dataset/helsingin-vaesto-ja-asuntotuotantoennuste-alueittain) · [Suomen Pankki open data](https://www.suomenpankki.fi/en/statistics/open-data/)


---

# Batch 2 — what the layer phases actually found (v1.1)

`docs/PROBE_FI.md` §"Batch 2" carries the routes; this is the spec's own scorecard. Where the
spec and the live API disagreed, the API won and the difference is recorded here.

| Spec asked for | What exists | Built? |
|---|---|---|
| DVV building-address file | discontinued 14.3.2025; **Ryhti `open_address`** is the same register, live, keyless — 3 861 495 rows | ✅ as Ryhti |
| SYKE flood-hazard zones | 16 layers, return period in the **layer name**; 3.4 M + 4.0 M features, 5.6 GB bulk zips | ✅ measured from the publisher's WMS at 25 m |
| Sea-level scenarios | no machine-readable national dataset; 453 Helsinki-only points | ❌ not built, logged |
| Stormwater flood maps | HSY 397 layers, Helsinki 304 — neither publishes one | ❌ not built, logged |
| STUK radon by area | **two open spreadsheets**, by kunta *and* by postal area | ✅ better than the spec hoped |
| Ryhti buildings | 3 799 740, 7-code use classification, no tenure, no per-dwelling area | ✅ partially — only what it publishes |
| Ryhti kaavat | status yes, **floor area no**; in-preparation collections **empty nationally** | ⚠ overlay only, no indicator |
| ARA energy certificates | paid X-Road service, ARA *tietolupa* required | ❌ not built, logged |
| HSL GTFS | `dev.hsl.fi/gtfs/hsl.zip`, keyless, 80 MB | ✅ |
| Fintraffic national GTFS | Digitransit answers **401** without a registered key | ❌ OSM used instead, per point |
| Helsinki Palvelukartta | keyless, 21 506 units, 4 municipalities | ✅ |
| Geofabrik OSM extract | 767 MB, ODbL | ✅ 133 514 points extracted |
| LIPAS | keyless API confirmed | ⏸ probed, not built — sports facilities were not in any phase's scope |
| Väylävirasto project layers | `hanketiedot:tiehankkeet` (311) and `:ratahankkeet` (166), **with published alignments** | ✅ better than the spec hoped |
| YTL lukio results | **candidate-level** open CSV per session, 2022K–2026K | ✅ aggregated with a 10-candidate floor |
| School locations | Tilastokeskus `oppilaitokset`, 2 501, **with coordinates** | ✅ no geocoding needed |
| Tilastokeskus 1 km grid | `vaestoruutu:vaki2025_1km`, 96 904 cells | ✅ as an overlay |

**The one join with no key.** Tilastokeskus numbers a school `08888` and YTL numbers it `1488`;
padding one into the other matches **0 of 387**. The join is exact normalised-name equality and
nothing fuzzier — 338 of 380 lukios — because a near match would give one school another
school's results and nothing downstream would reveal it.
