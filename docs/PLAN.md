# PLAN — Finland edition, batch 1 (branch `v1.0-build`)

**This file is the memory of the unattended run.** It carries the master task verbatim, the
phase checklist, and a short status per phase. After a context compaction: re-read this file,
find the first unticked phase, and carry on from the resume point at the bottom.

Spec: `docs/DATA_MAP_FI.md` (what exists) · `docs/BUILD_PLAN_FI.md` §7 (the plan).
Reference implementation: `~/Desktop/"Denmark dashboard, funny project"/am-dashboard-dk` (v2.5.1) — **read-only**.

---

## 1. Master task (verbatim)

```
MASTER TASK — BATCH 1 of 2: build the Finland edition of the Macro Dashboard from the Danish skeleton to a complete v1.0 in one unattended run. Branch v1.0-build (checked out). Do not push.

GROUND RULES
1. Data principle: official published figures or plain arithmetic on them only — no own models, assumptions or imputations. Suppressed ≠ 0, not covered = "Not covered yet". Every figure carries source, period, fetch date and a verify-at-source link. "Lähde: Tilastokeskus" (CC BY 4.0) and every other source's licence in docs/SOURCES.md.
2. This repo is a copy of the Danish edition. The Danish repo ~/Desktop/"Denmark dashboard, funny project"/am-dashboard-dk (v2.5.1) is the READ-ONLY reference: never edit, build or run git commands there. Reuse its UI, calc engine, config schema, overlays framework, datasheets, Analysis sheet, testprop.js, verify-at-source links, make links and naming. makro.json keeps the Danish shape. Levels here: kunta / postinumero / osa_alue.
3. docs/DATA_MAP_FI.md and docs/BUILD_PLAN_FI.md (§7 is the current plan) are the spec. National macro is OUT of scope (no Euribor, mortgage rates, bond yields, CPI, GDP, municipal finances). If a route differs from the spec, find the working official route, log the difference and continue. Never invent a figure, table ID or URL. If a feature has no workable open source, skip it and log why.
4. English everywhere; Finnish source terms verbatim. Codes are strings with leading zeros (kunta "091", postal "00100"). Pin vintages (kuntajako 2026, pno_tilasto_<year>) and never join across vintages silently.
5. Stdlib-first Python like the Danish scripts (if geometry needs shapely/pyproj: requirements-geo.txt + .venv, documented, and make build still works without it for non-geo steps). Raw pulls gitignored under data/raw/<source>/. No processed/dist file > 3 MB; lazy-load per kunta where needed. Keys only from .env, never printed or committed. Throttle politely; resumable downloads.
6. Each phase ends with: make validate && make test && make build clean (log every ⚠ with a decision), a check table in docs/BUILD_LOG.md, headless screenshots (temporary server on a random free port, stopped straight away — never leave a server running), commits (feat:/data:/fix:/docs:), and the phase ticked in docs/PLAN.md with a 5-line status.
7. Run everything in one go: never stop between phases, never ask me to confirm or choose — decide, log it and continue. Use subagents for research-heavy or bulk steps. Keep docs/PLAN.md current after every commit so work survives context compaction; after a compaction re-read it and carry on. If the session is about to end for good, commit and write the exact resume point in docs/PLAN.md.

PHASE 0 — Plan + clean skeleton
Write docs/PLAN.md (this task verbatim + checklist of phases 0–8), docs/BUILD_LOG.md, docs/DATA_FOLDERS.md, docs/SOURCES.md, docs/GEO.md. Remove Danish-only code paths, data and docs (DST, DAWA/Datafordeler, BBR, boligstat, LBF, Copenhagen scripts, Danish data/external files, Danish docs and screenshots, the Danish market panel); keep the generic UI, calc engine, overlay framework, testprop.js and Analysis code dormant but intact for batch 2. Title "Macro Dashboard — Finland", map box 59.7–70.1 N / 19.0–31.6 E, quick jumps (camera only, never selection, ignored while typing): Helsinki H, Tampere T, Turku U, Oulu O, Finland F. Zoom never changes the selection. make fixture renders. Pages + monthly refresh workflows adapted. Commit.

PHASE 1 — Probe
scripts/probe_fi.py → docs/PROBE_FI.md (name | HTTP | s | bytes | result) for every batch-1 source: StatFin PxWeb (v1, and v2 if live) metadata for vaerak, tjt, tyonv, asvu 13eb + ARA-rent and rent-index tables, ashi 13mt/13mu/13mx + new-flat and index tables, ras, asas/rakke (stock by tenure/type, unoccupied dwellings), muutl, vaenn (Väestöennuste 2024), rpk (find the kunta-level table: offence types, quarters, years); Paavo WFS (layer list, latest year, variable names); Tilastokeskus tilastointialueet WFS (kunta 2026, maakunta); Aluesarjat PxWeb (api.aluesarjat.fi / stat.hel.fi) sub-area tables; HRI / kartta.hel.fi / Seutukartta osa-alue boundaries for Helsinki, Espoo, Vantaa, Kauniainen; Helsinki population forecast by area (HRI); Kelasto housing-allowance by kunta (export route); Verohallinto property-tax % and municipal income-tax % files by kunta. Reference values: 091 population latest, 00100 price €/m² latest quarter, 00100 rent €/m² latest quarter. Commit: chore: FI endpoint probe.

PHASE 2 — Geometry
fetch_geo_fi.py + fetch_paavo.py → data/geo/{maakunnat,kunnat,postinumerot,osa_alueet}.geojson in EPSG:4326, clipped to land (as SE v1.0), simplified with mapshaper keep-shapes, raw out of git, ATTRIBUTION.txt. Sanity: kunta count = 2026 kuntajako; every postal area and osa-alue carries its kunta code; no code lost a leading zero. Commit.

PHASE 3 — Area indicators (rows 1–11)
config/indicators.json + scripts/statfin.py (json-stat2, throttle, retry, meta.json per table) + fetch_statfin.py: population growth, median income + mean household income, share 20–34, one-person households, housing-allowance households (kunta, Kelasto), renter households, unemployment (Paavo annual at postal level; TEM monthly at kunta level with a Yearly | Monthly toggle), tertiary education, multi-dwelling share, foreign-language speakers (kunta; osa-alue where Aluesarjat has it), avg dwelling size + m² per person. Postal level from Paavo, kunta from StatFin, ° for inherited values. Full time series where published. Commit.

PHASE 4 — Market indicators (rows 12–21)
Old flats €/m² + sales count (13mt quarterly, 13mu annual, 13mx kunta; kerrostalo and rivitalo separately; sales count always shown with the price; suppressed = –), new flats €/m² (where published), price index + y/y, free-market rent €/m² (13eb by room count, with observation counts if published), ARA rent (kunta), rent change y/y, dwellings started / completed / permitted per 1 000 dwellings (quarterly), stock by tenure and building type, unoccupied-dwelling share, net migration. Yearly | Quarterly toggle and trend charts as in DK. Group "Market". Commit.

PHASE 5 — Taxes (rows 29–30)
import_verohallinto.py → property-tax % (vakituinen asuinrakennus, muu asuinrakennus, yleinen, maa) and municipal income-tax % per kunta, current year + history the files give. Group "Taxes", kunta level. Commit.

PHASE 6 — Safety + Outlook (rows 31–33)
Safety from rpk at kunta level, group "Safety", lower_better with direction-aware ranks and colours as in DK v2.0: crime_1000, violence_1000, property_1000, burglary_1000dw (per 1 000 dwellings), vandalism_1000, drugs_1000, crime_trend; quarterly series if published. Say plainly in docs that Finland publishes no open crime data below kunta. Outlook from Väestöennuste 2024, group "Outlook", kunta: fc_growth (2026→2040 %), fc_growth_5y, fc_abs, fc_0_6, fc_7_15, fc_20_34, fc_80p; label with the edition and publication date; projected segment dashed in charts (as DK v2.5). Helsinki city forecast by osa-alue as its own series, labelled as the city's forecast. Commit.

PHASE 7 — Osa-alue level (row 34)
Third map level for Helsinki, Espoo, Vantaa and Kauniainen, reusing the Danish Copenhagen-quarter machinery: indicators from Aluesarjat where published, else ° inherited from the postal area or kunta (state which). Area pages, breadcrumb kunta → postinumero → osa-alue. Commit.

PHASE 8 — Verify, docs, wrap-up
docs/VERIFICATION.md: recompute 5 kunta × 4 indicators, 5 postal codes × (price, rent, income, unemployment) and 3 osa-alueet straight from source. Verification export docs/verification/v1_0.csv (all kunta × all indicators). README (screenshot, live-link placeholder, how to run, honest data limits: no days-on-market or supply, no transaction-level prices, crime only at kunta, no comprehensive-school results). CHANGELOG v1.0 draft. Final validate / test / build / links clean. Print a ≤ 40-line summary: what shipped per phase, what was skipped and why, every open ⚠, and a localhost review checklist. STOP — do not merge, tag or push.
```

---

## 2. Phase checklist

| # | Phase | State | Commit |
|---|---|---|---|
| 0 | Plan + clean skeleton | ✅ | `feat: Finland skeleton` |
| 1 | Probe | ✅ | `chore: FI endpoint probe` |
| 2 | Geometry | ✅ | `data: Finnish boundary layers` |
| 3 | Area indicators (rows 1–11) | ✅ | `feat: area indicators` |
| 4 | Market indicators (rows 12–21) | ✅ | `feat: market indicators` |
| 5 | Taxes (rows 29–30) | ✅ | `feat: municipal tax rates` |
| 6 | Safety + Outlook (rows 31–33) | ✅ | `feat: safety and outlook` |
| 7 | Osa-alue level (row 34) | ✅ | `feat: osa-alue level` |
| 8 | Verify, docs, wrap-up | ✅ | `docs: v1.0 verification, README and changelog` |

---

## 3. Standing decisions (do not re-litigate)

| Decision | Choice | Taken |
|---|---|---|
| Level names | `kunta` / `postinumero` / `osa_alue` replace `kommune` / `postnr` / `kvarter` everywhere (config, JSON, URLs, UI) | Phase 0 |
| Coarse sub-city level | Helsinki `peruspiiri` replaces the Danish `bydel` in the third-level machinery | Phase 0 |
| Third-level data file | `data/processed/osa_alue.json`, same shape as the Danish `cph.json`; payload key `osa` | Phase 0 |
| makro.json shape | unchanged from Denmark: `meta` / `indicators` / `municipalities` / `areas` (`municipalities` = kunnat, `areas` = postinumeroalueet) | Phase 0 |
| National macro | out of scope for batch 1 — the Danish **Market** nav item is removed and `vSources()` promoted to its own **Sources** view | Phase 0 |
| Batch-2 machinery | overlay framework, micro/buildings layer, services, public buildings, infra, schools, `testprop.js` and the Analysis sheet stay in `src/app.js` but are dormant (they render nothing while their data key is null) | Phase 0 |
| `testprop.js` bounds | left on the Danish box until batch 2 phase 10, so `make test-js` stays green; Finland's box is already used by the map | Phase 0 |
| Locale | `fi-FI` number formatting, English UI text, Finnish source terms verbatim | Phase 0 |

---

## 4. Status log

### Phase 0 — Plan + clean skeleton ✅
- Danish-only code, data and docs removed: 32 scripts, 13 docs, 8 screenshots, `data/external`, the Danish tests and the two local run logs.
- `src/app.js` transformed in six reviewed passes (`node --check` after each): levels renamed to kunta / postinumero / osa_alue / peruspiiri, locale `fi-FI`, Finland map box + camera-only quick jumps H/T/U/O/F, StatFin verify-at-source links, the Danish national-macro **Market** view deleted and **Sources** promoted to its own view.
- The osa-alue layer is no longer tied to one municipality: `OSA_MUNIS` is derived from the data and `isOsaMuni()` / `osaParent()` replace every single-code comparison, so Helsinki, Espoo, Vantaa and Kauniainen all work.
- New: `scripts/statfin.py` (throttled, retrying, stamped PxWeb client), Finnish `validate_config.py` and `check_source_links.py`, a Finland fixture generator, `scripts/shot.sh`, Pages + monthly refresh workflows, `docs/{BUILD_LOG,DATA_FOLDERS,SOURCES,GEO,RUNBOOK}.md`.
- Checks: `make validate` ✓ · `make test` ✓ (21 tests) · `make build` ✓ · `make fixture` ✓ 0.8 MB, renders; screenshots in `docs/screenshots/`.

### Phase 1 — Probe ✅
- `scripts/probe_fi.py` probes 84 routes across StatFin, StatFin_Passiivi, the three WFS services, Aluesarjat, Kelasto, Verohallinto and avoindata.fi, and writes `docs/PROBE_FI.md` (name | HTTP | s | bytes | result) between markers so the hand-written findings survive a re-run.
- Seven of `docs/DATA_MAP_FI.md`'s assumptions did not survive the live API; each is recorded with the route that replaced it. Biggest: **no PxWebApi v2**, **`ras`/`asas`/`rakke`/`astuki` are gone**, and **postal-code rent (`asvu/13eb`) is frozen at 2025Q4**.
- Ten gaps written down plainly, including: no kunta-level construction data exists anywhere in StatFin, `ashi/12dg` is entirely null, and there are three incompatible postal-code universes (1 724 / 580 / 3 018).
- All five reference values answer and match by hand: Helsinki 694 392; 00100 price 7 167 €/m² on 35 sales; 00100 rent 29,43 €/m² on 746 observations.
- Checks: `make probe` ✓ · `make validate` ✓ · `make test` ✓ · `make build` ✓ · `make fixture` ✓.

### Phase 2 — Geometry ✅
- `scripts/geo_common.py` (WFS download with paging and caching, mapshaper-or-Visvalingam simplification with a searched percentage, ring/bbox/centroid/area helpers), `fetch_geo_fi.py` and `fetch_paavo.py`.
- Written: `kunnat` 308 · `maakunnat` 19 · `osa_alueet` 306 (Helsinki 148, Espoo 88, Vantaa 61, Kauniainen 9) · `postinumerot` 3 018, all EPSG:4326, all under the 3 MB ceiling, plus `kunta_maakunta.json` from Tilastokeskus's classification API and `ATTRIBUTION.txt`.
- Sanity: every code a string with its leading zero, every postal area and osa-alue carrying a kunta that exists, 335 661 km² of land, and 8 known points resolving correctly through all four layers — Kauniainen still a hole inside Espoo.
- Two bugs the checks caught: all 61 Vantaa osa-alueet collapsing onto one code (HSY publishes Vantaa at *tila* level), and kunnat with no maakunta (no boundary layer carries the mapping).
- Checks: `make geo` ✓ · `make validate` ✓ · `make test` ✓ 24+15 · `make build` ✓ · `make fixture` ✓.

### Phase 3 — Area indicators ✅
- 14 indicators live: growth, median income, household income, 20–34, one-person households, renters, unemployment (annual Paavo, both levels) and monthly (TEM, kunta), tertiary education, kerrostalo share, average dwelling size, m² per person, foreign-language speakers, housing-allowance households.
- **Paavo is the backbone** (`12f7` postal / `12f8` kunta, 2010–2024): the same definitions at both levels, so a kunta and a postal figure are directly comparable. Other sources appear only where Paavo has nothing.
- New: `scripts/fetch_statfin.py` (one selection per table, chunked under the cell cap, stamped), `scripts/import_kela.py` (CKAN datastore, CC BY 4.0), `scripts/build_makro.py` (the calc engine: passthrough / share_pct / ratio_pct / yoy_pct, suppression preserved as null).
- **Size:** the first build was 3.3 MB. Split into two lazy payloads — `dist/area/<kunta>.json` (detailed postal rings + history) and `dist/monthly.json` — bringing the page to 2 810 kB with makro.json at 2 212 kB.
- Checks: validate ✓ · links ✓ 6/6 · test ✓ 24+15 · build ✓ · fixture ✓ · 8 of 8 spot-checks reconcile exactly against the published cells.

### Phase 4 — Market indicators ✅
- 14 more indicators: old-flat price €/m² and sales (kerrostalo and rivitalo separately, postal and kunta), free-market rent, ARA rent, rent y/y and rent observations, the discontinued postal-code rent series, unoccupied dwellings, total and intermunicipal net migration, and dwellings completed / started / permitted per 1 000 dwellings. **28 indicators live.**
- Yearly | Quarterly toggle wired to the publisher's own quarterly series (`histq`), and a new **^** marker for a figure published for a coarser area than the row — rents and construction exist per maakunta for most of the country.
- Three things the spec assumed and the data refused: no building-type total in the price tables (solved by a sales-weighted mean of published classes), no municipal construction data anywhere in StatFin (maakunta figures, marked ^), and `ashi/12dg` entirely null (not registered).
- **Size:** kunta history moved to `dist/hist.json`; the page is 2 137 kB with a hard 3 MB guard in the build.
- Checks: validate ✓ · links ✓ 14/14 · test ✓ 24+15 · build ✓ · fixture ✓ · 9 spot-checks reconcile exactly.

### Phase 5 — Taxes ✅
- 6 indicators in a new **Taxes** group, kunta level: property tax on a permanent dwelling, on another dwelling, general (building), general (land), undeveloped building site, and the municipal income-tax rate. **34 indicators live.**
- Property tax comes from **Verohallinto's own keyless PxWeb** (`vero2.stat.fi`, `kive_202`), 2014–2026 — a far better route than the annual spreadsheet the spec expected.
- The municipal income-tax rate is published as a *decision*, not a statistic, anywhere; it is read from the JSON its own page renders, with the URL pinned in the new `config/sources.json` and every unmatched municipality name failing the import.
- New: `scripts/import_verohallinto.py`, `config/sources.json`, and a generic `csv` source type in the engine.
- Checks: validate ✓ · links ✓ · test ✓ · build ✓ 2 224 kB · all six Helsinki rates match the published decision.

### Phase 6 — Safety + Outlook ✅
- **Safety** (7 indicators, kunta, lower_better with direction-aware ranks and colours): reported offences, violence, property crime, vandalism, narcotics, dwelling burglary per 1 000 dwellings, and the y/y trend. The per-1 000 rates are the publisher's own (`rpk/13h4`), not ours.
- **Outlook** (9 indicators from Väestöennuste 2024, `vaenn/14wx`, published 2024-10-24): change 2026→2040 in per cent and in people, the five-year change and rate, the 0–6, 7–15, 20–34 and 80+ bands, and the 20–34 share against Finland's own projected share. Observed solid, projected dashed, split at "2025 · today".
- **50 indicators live.** Finland publishes no open crime data below kunta and no quarterly municipal crime data at all — both said plainly rather than worked around.
- Checks: validate ✓ · test ✓ · build ✓ 2 310 kB · fixture ✓ · 11 spot-checks reconcile exactly.

### Phase 7 — Osa-alue level ✅
- The third map level is live for **Helsinki (148), Espoo (88), Vantaa (61) and Kauniainen (9)** — 306 osa-alueet with their own 9 indicators from Aluesarjat, their own area pages, and the breadcrumb kunta → postinumero → osa-alue.
- New: `scripts/aluesarjat.py` (PxWeb client for stat.hel.fi) and `scripts/build_osa.py`. Rings and history ride in the same per-kunta lazy file as the postal areas, so the page grew by only 123 kB.
- **Helsingin kaupunki's own projection (PER26) by osa-alue** is carried as its own series and shown beside Tilastokeskus's for the city, with the gap stated and never averaged — the rule is written down in the new `docs/OUTLOOK_FI.md`.
- ⚠ **Aluesarjat is non-commercial-use-only, not CC BY 4.0.** The one licence restriction in the dashboard, confined to this layer and labelled everywhere it appears. Open item for the release decision.
- Checks: validate ✓ · links ✓ **25/25** · test ✓ · build ✓ 2 429 kB · fixture ✓.

### Phase 8 — Verify, docs, wrap-up ✅
- `scripts/verify.py` re-queries the publishers, redoes the arithmetic and compares with the page: **57 checks, 0 disagreements** across 5 kunnat × 4 indicators, 5 postal codes × 5 and 3 osa-alueet × 4. `docs/VERIFICATION.md` records every one with the cells it used.
- `docs/verification/v1_0.csv`: 14 341 rows, 308 kunnat × 50 indicators, long format with the source table and period beside every figure.
- README rewritten with the screenshot, how to run, the licence position and the honest limits; CHANGELOG v1.0 drafted; `make verify` added.
- Eight open ⚠ written down in `docs/BUILD_LOG.md`, headed by the Aluesarjat non-commercial licence.
- Final: validate ✓ · links ✓ 25/25 · test ✓ 24+15 · build ✓ 2 414 kB · fixture ✓ · verify ✓.

**Batch 1 is complete.** Nothing merged, tagged or pushed.

---

## 5. Resume point

**Batch 1 finished on branch `v1.0-build`.** Nothing is merged, tagged or pushed.

**Next action (a human's):** review `dist/index.html` on localhost (`make build && make serve`), then decide the two licence questions in `docs/BUILD_LOG.md` → "Open ⚠" before releasing. Batch 2 starts from `docs/BUILD_PLAN_FI.md` §7 on a new branch `v1.1-layers`.

---
---

# PLAN — Finland edition, batch 2 (branch `v1.1-layers`)

Batch 2 adds every map layer and the Test-property feature on top of the live v1.0.
**Ground rules are batch 1's, unchanged** (§1 above) plus the layer rules in §7 below.
After a context compaction: re-read this file, find the first unticked phase in §8, and
carry on from the resume point at the bottom.

## 6. Master task, batch 2 (verbatim)

```
MASTER TASK — BATCH 2 of 2: add every map layer and the Test property feature to the Finland edition in one unattended run. Branch v1.1-layers (checked out, based on v1.0 which is live). Do not push.

GROUND RULES: the same as batch 1. Read them in docs/PLAN.md and apply all of them unchanged: data principle, Danish repo read-only as reference, spec in docs/DATA_MAP_FI.md (probe results in docs/PROBE_FI.md override it), English, string codes, stdlib-first, size limits, per-phase checks and commits, never stop or ask, subagents for bulk work, docs/PLAN.md kept current. First append this task and a checklist of phases 8b–16 to docs/PLAN.md. Extra rules for layers: points and zones lazy-load per kunta; every point shows its source; overlays use the Danish overlay pills, stacked collapsible legends and canvas-renderer guard; disclaimers where the Danish edition has them.

PHASE 8b — Licence corrections from the v1.0 review
(a) Aluesarjat is NOT non-commercial: Helsinki's terms page https://kaupunkitieto.hel.fi/fi/helsingin-tilastotietokannat/aluesarjat states "Tietoaineistoa voi käyttää sekä ei-kaupallisiin että kaupallisiin tarkoituksiin" (attribution required: "Helsingin seudun aluesarjat -tilastokanta" + underlying source; no implied endorsement). Re-check the page yourself, then fix the licence on every osa-alue indicator, docs/SOURCES.md, the Sources view, README and BUILD_LOG (close ⚠1 with quote + URL). (b) Verohallinto: find its open-data licence statement; record it with URL, else label "Licence not stated by publisher — public official figures". (c) Frozen series (postal rents 2025Q4, HSY 2021) show "Last published <period> — series discontinued by publisher" in tooltips and Sources. Commit.

PHASE 9 — Probe for layers
Extend scripts/probe_fi.py → docs/PROBE_FI.md: SYKE flood-hazard WFS/WMS (tulvavaaravyöhykkeet vesistö + meri, return periods, layer names, licence); sea-level scenarios (Ilmatieteen laitos / SYKE: years, scenarios, format); HSY/Helsinki stormwater (hulevesi) flood maps; STUK radon by area; Ryhti buildings + kaavat (OGC API/WFS, fields incl. use, year, floor area, storeys, dwellings; plan status and floor area); DVV building addresses (open file, size, fields); ARA energy certificates open data; HSL GTFS + Fintraffic national GTFS; Helsinki Palvelukartta API; Geofabrik finland-latest.osm.pbf; LIPAS; Väylävirasto open WFS project layers; YTL lukio results (open statistics route, latest year, fields); Opetushallitus / Palvelukartta school locations; Tilastokeskus 1 km grid. Commit.

PHASE 10 — Test property + Analysis + Compare
Port DK v2.4 testprop.js: Google Maps link / coordinates parser (short links refused with a named error) PLUS address search from the DVV building-address file (built into a compact lazy lookup, no server). Finland box 59.7–70.1 N / 19.0–31.6 E. Exact kunta / postinumero / osa-alue by point-in-polygon on our own rings (holes kept — Kauniainen inside Espoo must resolve to Kauniainen). Pin in the URL hash, privacy line. Analysis sheet in the left nav reads everything the dashboard carries for the pin's areas (headline row, demographics, market price and rent, taxes, safety, outlook) and, as later phases land, climate, services, public buildings, infra, schools, buildings and zoning. Compare two pins with aligned rows, direction-aware, no overall winner. Tests with Finnish link and address cases. Commit.

PHASE 11 — Climate risk
Group "Climate" + "Climate risk" overlay; horizon or scenario always in the label. Area share of land per postinumero / osa-alue / kunta inside SYKE flood-hazard zones (sea and watercourse, 1/100 and 1/1000 at least; unmapped areas = "Not mapped"); sea-level scenario share where the data allows (label e.g. "Mean sea level 2100 (scenario, source)"); stormwater flood share where HSY/Helsinki publish it (others "Not mapped"); radon only if STUK publishes open area data, else log and skip. Disclaimer "Screening indicators for comparing areas, not a property-level risk assessment." Climate section in the Analysis sheet. Commit.

PHASE 12 — Services + Public buildings
Services overlay, points only, no area indicators: grocery (supermarket/convenience), restaurants/cafés from OSM; public-transport stops from HSL GTFS + Fintraffic GTFS (OSM stops as fallback, logged). Public buildings overlay with a category filter (education / daycare / health / culture): Ryhti buildings by use where fields allow, Palvelukartta for the Helsinki region, OSM elsewhere; source per point. Commit.

PHASE 13 — Infra projects
Hand-curated data/external/infra_fi.geojson, 30–50 projects, each with a source URL: Väylävirasto projects and the national transport investment programme, Kruunusillat, Vantaan ratikka, Espoon kaupunkirata, Lentorata, Tunnin juna / Itärata / Turku rail, Tampere tram extensions, other major rail/metro/tram/road projects. Fields as in the Danish infra file (status, opening year or window, budget + price base, stations). Alignments only where officially published or OSM-tagged construction/proposed — else stations only, never drawn guesses. Overlay pill, datasheet, Pipeline view with CSV, growth-signal indicators projects_upcoming and stations_planned_1200m. Verify 5 projects against their sources. Commit.

PHASE 14 — Schools
School points (comprehensive + upper secondary) from the official register / Palvelukartta / OSM. Lukio matriculation results from YTL where openly published (latest year + history, fields as published, suppressed ≠ 0), popup with value vs kunta vs Finland, school datasheet. State plainly that Finland publishes no comprehensive-school results. Commit.

PHASE 15 — Buildings, energy, zoning, grid
Buildings micro layer from Ryhti (as DK v1.5): building points with use, year, floor area, storeys, dwellings where published, lazy per kunta; area indicators only as plain counts/shares of published fields (e.g. share of dwellings built before 1980). ARA energy certificates joined by building ID where possible → energy-class share per area. Zoning overlay from Ryhti kaavat (+ Helsinki asemakaavat WFS if richer): plans in preparation / approved, residential floor area where published, datasheet, indicator planned_floor_area_1000 (per 1 000 residents) only if the floor area is published. 1 km grid population as an optional overlay. If a whole-country pull is too heavy, build the Helsinki region first, then whole country; log the coverage. Commit(s).

PHASE 16 — Verify, docs, wrap-up
Verification rows for every new layer in docs/VERIFICATION.md (5 samples each) and docs/verification/v1_1.csv; docs/SOURCES.md, DATA_MAP_FI.md, README updated; refresh workflow extended for the cheap sources; CHANGELOG v1.1 draft. Final validate / test / build / links clean. Print a ≤ 40-line summary: what shipped per phase, what was skipped and why, every open ⚠, and a localhost review checklist. STOP — do not merge, tag or push.
```

## 7. Extra ground rules for layers (batch 2)

| Rule | Meaning |
|---|---|
| Lazy per kunta | Points and zones never ship in `makro.json`; they live in `dist/<layer>/<kunta>.json` and load when the map needs them, like `dist/area/<kunta>.json`. |
| Source per point | Every point popup names the publisher it came from, because one layer mixes sources (Palvelukartta in the Helsinki region, OSM elsewhere). |
| Danish overlay chrome | The overlay pills, stacked collapsible legends and the canvas-renderer guard come from the Danish `src/app.js` unchanged. |
| Disclaimers | Wherever the Danish edition shows one (climate screening, schools, infra pipeline), Finland shows the same, reworded for the Finnish source. |

## 8. Phase checklist, batch 2

| # | Phase | State | Commit |
|---|---|---|---|
| 8b | Licence corrections | ✅ | `fix: licence corrections from the v1.0 review` |
| 9 | Probe for layers | ☐ | |
| 10 | Test property + Analysis + Compare | ☐ | |
| 11 | Climate risk | ☐ | |
| 12 | Services + Public buildings | ☐ | |
| 13 | Infra projects | ☐ | |
| 14 | Schools | ☐ | |
| 15 | Buildings, energy, zoning, grid | ☐ | |
| 16 | Verify, docs, wrap-up | ☐ | |

## 9. Status log, batch 2

### Phase 8b — Licence corrections ✅
- **⚠1 closed, and it was our error.** Helsinki's terms page, re-read 2026-09-24, permits
  commercial use in so many words. v1.0 quoted half the sentence and read the missing half as
  a prohibition. **No source in this dashboard restricts commercial use.** The correction runs
  through `aluesarjat.py`, `build_osa.py`, the six cached stamps, `indicators.json`,
  `SOURCES.md` §3 (with the verbatim quote and URL), README and CHANGELOG.
- The terms' real condition — a **two-part attribution**, database *and* underlying source —
  is now what the footer and the Sources view carry: "Lähde: Helsingin seudun aluesarjat
  -tilastokanta ja Tilastokeskus".
- **⚠2 answered, not closed:** Verohallinto's CC BY 4.0 statement exists but is scoped to the
  corporate-tax datasets on its open-data page and names neither tax-rate series. Both are now
  labelled "Licence not stated by publisher — public official figures", with the CC BY 4.0 page
  recorded beside them.
- **Frozen series** get one standard sentence in three places (ⓘ tooltip, summary line, a new
  Status column in Sources), driven by a machine-readable `frozen` field so it cannot drift:
  `rent_pno` 2025Q4, HSY boundaries 2021. `SOURCES.md` §6b lists them together.
- Checks: validate ✓ 50 indicators · links ✓ 4/4 · test ✓ 24+15 · build ✓ 2.4 MB · screenshot
  `docs/screenshots/v1_1_p8b-1.png`; `grep` confirms 0 occurrences of the old claim in `dist/`.

## 10. Resume point, batch 2

Phase 8b committed. Phase 9 (probe for layers) in progress — four research subagents out.
