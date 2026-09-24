# Build plan — Finland edition (`am-dashboard-fi`)

**Written 2026-09-24.** Companion to `DATA_MAP_FI.md`. Reference implementation: the Danish repo `am-dashboard-dk` (v2.5.1, read-only). Pattern for the long unattended run: `BUILD_PLAN_SE_PARITY.md` §4.
**Operating model (unchanged):** pipeline runs on the Mac (Python 3.10+, stdlib-first), Claude Code builds in Terminal, this Cowork project plans and reviews. Everything automatable goes through Claude Code; the only manual steps are creating the repo and turning on Pages.

## 1. Architecture decisions

| Decision | Choice | Why |
|---|---|---|
| Repo | **new public repo `real-estate-war-lord/am-dashboard-fi`**, separate from DK/SE | Same decision as SE (18.9.2026): definitions differ across countries |
| Starting point | **copy of the DK repo (v2.5.1) without its git history and Danish data** | DK is the most complete UI (Analysis, overlays, outlook, safety, services) |
| Local folder | `~/Desktop/"Finland dashboard"/am-dashboard-fi` | Mirrors DK/SE |
| Levels | `kunta` → `postinumero` → `osa_alue` (Helsinki region, 3rd level like Copenhagen kvarterer) | Paavo + ashi + asvu all exist at postal-code level |
| Language | English UI, Finnish source terms verbatim | Same as DK/SE; i18n later if wanted |
| Private data | Never in this repo (no Portfolio Manager data, no scraped listings) | Public repo |
| Schema | `data/processed/makro.json` identical in shape to DK/SE | Keeps a later Nordic view possible |

## 2. Folder structure

One-way data flow, one producer per folder (same rule as `DATA_FOLDERS.md`):

```
am-dashboard-fi/
├── README.md                 live link, how to run, honest data limits
├── CHANGELOG.md
├── LICENSE                   code MIT; data per source (docs/SOURCES.md)
├── Makefile                  probe · geo · fetch · build · validate · test · verify · links · serve
├── .env.example              key names only (none needed for v1.0)
├── .gitignore                .env, data/raw/**/*.csv|json (except *.meta.json), data/geo/raw, dist/fixture.html, private/
├── .github/workflows/
│   ├── pages.yml             deploy dist/ to GitHub Pages
│   └── refresh.yml           monthly: fetch → build → commit data/processed
├── config/
│   ├── indicators.json       the registry (one indicator = one entry)
│   └── sources.json          pinned URLs for file-based sources (Kelasto, Verohallinto, YTL…)
├── scripts/
│   ├── statfin.py            PxWeb client (json-stat2, throttle, retries, meta)
│   ├── probe_fi.py           endpoint probe → docs/PROBE_FI.md
│   ├── fetch_statfin.py      all StatFin tables in indicators.json
│   ├── fetch_paavo.py        Paavo WFS per year (polygons + variables)
│   ├── fetch_geo_fi.py       kunta / maakunta / Helsinki-region osa-alue polygons
│   ├── fetch_aluesarjat.py   Helsinki-region sub-area tables
│   ├── fetch_macro.py        ECB / Suomen Pankki / khi
│   ├── import_*.py           file sources (kelasto, verohallinto, ytl, …)
│   ├── build_makro.py        calc engine ported from DK
│   ├── build_market.py
│   ├── build_dashboard.py    → dist/index.html
│   └── validate_config.py
├── data/
│   ├── raw/<source>/         untouched pulls, dated — not in git (only *.meta.json)
│   ├── geo/                  simplified GeoJSON/TopoJSON — in git; raw/ not
│   ├── external/             small hand/file-sourced CSVs — in git
│   └── processed/            JSON the page reads — in git
├── src/                      app.js, testprop.js, style.css, index.html, vendor/
├── dist/                     index.html (+ lazy per-kunta files) — in git
├── docs/
│   ├── PLAN.md               master checklist Claude Code ticks (survives context loss)
│   ├── BUILD_LOG.md          check table per phase
│   ├── PROBE_FI.md           live probe results
│   ├── DATA_MAP_FI.md        copy of the project doc, kept current
│   ├── DATA_FOLDERS.md       this structure + provenance chain
│   ├── SOURCES.md            every source, URL, licence, attribution, refresh
│   ├── GEO.md                vintages (kuntajako 2026, pno_tilasto_2026)
│   ├── VERIFICATION.md       spot-checks against the PxWeb UI
│   └── RUNBOOK.md            how to refresh, how to release
└── tests/
```

## 3. Release sequence

| Version | Content |
|---|---|
| **Phase 0** | Repo skeleton from DK, fixture renders, Pages workflow |
| **Phase 1 — Probe** | every 🔎 row in DATA_MAP_FI → `docs/PROBE_FI.md` |
| **v1.0** | Geo (kunta + postal) + core chip row 1–12 from StatFin + Paavo + **price €/m² and rent €/m² per postal code** + market panel (Euribor, mortgage rate, CPI, starts/completions) → live on Pages |
| **v1.1** | Time series + quarterly toggle for price/rent, outlook (Väestöennuste 2024), safety (rpk, kunta), property/municipal tax, Kela housing allowance |
| **v1.2** | Helsinki-region **osa-alue** 3rd level (Aluesarjat) + Helsinki city forecast by area |
| **v1.3** | Test property + Analysis + Compare (DVV address search) |
| **v1.4** | Climate (SYKE flood zones, sea level) + Services + Public buildings + Infra overlays |
| **v1.5** | Ryhti buildings micro layer + **zoning pipeline** (Ryhti kaavat) |
| later | Leasing monitor (Oikotie etc., private/local), DK overhaul round ported |

## 4. Step 1 — create the repo (the only manual step)

```bash
mkdir -p ~/Desktop/"Finland dashboard" && cd ~/Desktop/"Finland dashboard"
rsync -a --exclude .git --exclude 'data/raw' --exclude 'data/geo' --exclude 'data/processed' \
  --exclude 'dist' --exclude '.env' --exclude 'node_modules' \
  ~/Desktop/"Denmark dashboard, funny project"/am-dashboard-dk/ am-dashboard-fi/
cd am-dashboard-fi && mkdir -p docs && cp ~/Downloads/DATA_MAP_FI.md ~/Downloads/BUILD_PLAN_FI.md docs/
git init -b main && git add -A && git commit -m "chore: skeleton copied from am-dashboard-dk v2.5.1"
gh repo create real-estate-war-lord/am-dashboard-fi --public --source=. --push
```
(No `gh`? Create the empty public repo on github.com, then `git remote add origin https://github.com/real-estate-war-lord/am-dashboard-fi.git && git push -u origin main`.)
Then on GitHub: **Settings → Pages → Source: GitHub Actions**.

## 5. Step 2 — master prompt (SUPERSEDED by §7, kept for history)

```bash
cd ~/Desktop/"Finland dashboard"/am-dashboard-fi && git checkout -b v1.0-build && caffeinate -i claude
```

```
MASTER TASK — build the Finland edition of the Macro Dashboard to v1.0 in one unattended run. Branch v1.0-build (checked out). Do not push.

GROUND RULES
1. Data principle: official published figures or plain arithmetic on them only — no own models or imputations. Suppressed ≠ 0, not covered = "Not covered yet". Every figure carries source, period, fetch date and a verify-at-source link. Attribution "Lähde: Tilastokeskus" (CC BY 4.0) and per-source licences in docs/SOURCES.md.
2. This repo is a copy of the Danish edition. Reference repo ~/Desktop/"Denmark dashboard, funny project"/am-dashboard-dk is READ-ONLY. Reuse its UI, calc engine, config schema, naming and conventions; makro.json keeps the same shape. Levels here: kunta / postinumero / osa_alue.
3. English everywhere; Finnish source terms verbatim. Codes are strings with leading zeros (kunta "091", postal "00100"). Pin vintages (kuntajako 2026, pno_tilasto_<year>) and never join across vintages silently.
4. Stdlib-first scripts; raw pulls gitignored under data/raw/<source>/; no processed/dist file > 3 MB (lazy per kunta if needed). Keys only from .env, never printed.
5. Each phase ends with make validate && make test && make build clean, a check table in docs/BUILD_LOG.md, headless screenshots (temporary server on a random free port, stopped straight away), commits (feat:/data:/fix:/docs:), and the phase ticked in docs/PLAN.md with a 5-line status. Keep docs/PLAN.md current after every commit so a new session can "Continue from docs/PLAN.md".
6. Never stop to ask me: decide, log the decision, continue. If a route differs from docs/DATA_MAP_FI.md, find the working official route and log it. Never invent a figure, table ID or URL; if a feature has no workable open source, skip it and log why. Use subagents for research-heavy steps.

PHASE 0 — Clean skeleton
Copy this task verbatim into docs/PLAN.md with a checklist of phases 0–5; create docs/BUILD_LOG.md, docs/DATA_FOLDERS.md, docs/SOURCES.md, docs/GEO.md. Remove Danish-only code paths and data references (DST, DAWA/Datafordeler, BBR, boligstat, Copenhagen-specific scripts) — keep the generic UI, calc engine, overlays framework, testprop.js and Analysis code dormant but intact. Rename levels, title "Macro Dashboard — Finland", map box Finland 59.7–70.1 N / 19.0–31.6 E, quick jumps (camera only) Helsinki H, Tampere T, Turku U, Oulu O, Finland F. make fixture renders. Pages + monthly refresh workflows adapted. Commit.

PHASE 1 — Probe
scripts/probe_fi.py → docs/PROBE_FI.md (name | HTTP | s | bytes | result) for every source in docs/DATA_MAP_FI.md §1–§2: StatFin PxWeb v1 (and v2 if it exists) — metadata of asvu 13eb, ashi 13mt/13mu/13mx, vaerak, tjt, tyonv, ras, asas/rakke, muutl, khi, vaenn 14wy, rpk (find the kunta-level table), astuki; Paavo WFS layer list + latest year + variable names; Tilastokeskus tilastointialueet WFS (kunta 2026, maakunta); Aluesarjat PxWeb; HRI/kartta.hel.fi osa-alue WFS; ECB Data API EURIBOR3M/12M + MIR FI new mortgage rate; Suomen Pankki open data; Kelasto asumistuki export; Verohallinto property-tax and income-tax files; SYKE flood WFS; Ryhti buildings + kaavat; DVV building addresses; HSL GTFS; Palvelukartta API; YTL lukio results. Reference values: Helsinki 091 population latest, 00100 price €/m² latest quarter, 00100 rent €/m² latest quarter. Commit: chore: FI endpoint probe.

PHASE 2 — Geometry
scripts/fetch_geo_fi.py + fetch_paavo.py → data/geo/{maakunnat,kunnat,postinumerot}.geojson in EPSG:4326, simplified (mapshaper keep-shapes), raw kept out of git, ATTRIBUTION.txt. Sanity: kunta count = 2026 kuntajako, every postal area has a kunta code, no postal code lost its leading zero. Clip to land as in SE v1.0. Commit.

PHASE 3 — Core indicators
config/indicators.json with DATA_MAP_FI §1a rows 1–12 (postal level from Paavo, kunta from StatFin, ° for inherited values), plus §1b price_m2 (13mt/13mu, kerrostalo + rivitalo, sales count shown with the price) and rent (13eb, by room count, with observation counts if published), starts/completions/permits per 1 000 dwellings, net migration. scripts/statfin.py (json-stat2, throttle, retry, meta.json per table) + fetch_statfin.py. make fetch && make build; fix every ⚠. Commit.

PHASE 4 — Market panel
fetch_macro.py: Euribor 3/12 m, new mortgage rate FI, 10-yr govt bond, CPI + rent sub-index, price index y/y, starts/completions national — KPI tiles with 24-month sparklines and "as of" dates, as in the Danish market panel. Commit.

PHASE 5 — Verify, docs, release prep
docs/VERIFICATION.md: recompute 5 kunta × 3 indicators and 3 postal codes × (price, rent, income) straight from source. README (screenshot, live link placeholder, how to run, honest data limits from DATA_MAP_FI §1g). CHANGELOG v1.0 draft. Final validate/test/build/links clean. Print a ≤ 40-line summary: what shipped, what was skipped and why, every open ⚠, and a localhost review checklist. STOP — do not merge, tag or push.
```

## 6. Step 3 — release (after the localhost review)

```
Merge v1.0-build into main, tag v1.0, push main and tags, confirm the Pages deploy succeeded and print the live URL https://real-estate-war-lord.github.io/am-dashboard-fi/ with a 5-line check that it loads real data.
```

Then v1.1+ follows the same pattern: one branch, one master prompt, one localhost review, one push.

## 7. Master prompts — two unattended batches (decided 2026-09-24, supersedes §5)

**Scope decided 2026-09-24:** everything in the priority table except national macro (rows 24–28 and municipal finances in row 30 are dropped). Property-tax % and municipal income-tax % stay. Not built: rows 22, 23, 50 (no open data) and 48 (Hilma needs an API subscription). Row 49 (listings) is kept for a separate private build later.

- **Batch 1 (branch `v1.0-build`):** skeleton, probe, geometry at three levels, all area and market indicators, taxes, safety, outlook, and Helsinki-region osa-alue level. Rows 1–21, 29–34.
- **Batch 2 (branch `v1.1-layers`, from batch 1):** test property, climate, services, public buildings, infra, schools, buildings, energy certificates, zoning and the 1 km grid. Rows 35–47.

### Batch 1

```bash
cd ~/Desktop/"Finland dashboard"/am-dashboard-fi && git checkout main && git checkout -b v1.0-build && caffeinate -i claude
```

```
MASTER TASK — BATCH 1 of 2: build the Finland edition of the Macro Dashboard from the Danish skeleton to a complete v1.0 in one unattended run. Branch v1.0-build (checked out). Do not push.

GROUND RULES
1. Data principle: official published figures or plain arithmetic on them only — no own models, assumptions or imputations. Suppressed ≠ 0, not covered = "Not covered yet". Every figure carries source, period, fetch date and a verify-at-source link. "Lähde: Tilastokeskus" (CC BY 4.0) and every other source's licence in docs/SOURCES.md.
2. This repo is a copy of the Danish edition. The Danish repo ~/Desktop/"Denmark dashboard, funny project"/am-dashboard-dk (v2.5.1) is the READ-ONLY reference: never edit, build or run git commands there. Reuse its UI, calc engine, config schema, overlays framework, datasheets, Analysis sheet, testprop.js, verify-at-source links, make links and naming. makro.json keeps the Danish shape. Levels here: kunta / postinumero / osa_alue.
3. docs/DATA_MAP_FI.md and docs/BUILD_PLAN_FI.md are the spec. National macro is OUT of scope (no Euribor, mortgage rates, bond yields, CPI, GDP, municipal finances). If a route differs from the spec, find the working official route, log the difference and continue. Never invent a figure, table ID or URL. If a feature has no workable open source, skip it and log why.
4. English everywhere; Finnish source terms verbatim. Codes are strings with leading zeros (kunta "091", postal "00100"). Pin vintages (kuntajako 2026, pno_tilasto_<year>) and never join across vintages silently.
5. Stdlib-first Python like the Danish scripts (if geometry needs shapely/pyproj: requirements-geo.txt + .venv, documented, and make build still works without it for non-geo steps). Raw pulls gitignored under data/raw/<source>/. No processed/dist file > 3 MB; lazy-load per kunta where needed. Keys only from .env, never printed or committed. Throttle politely; resumable downloads.
6. Each phase ends with: make validate && make test && make build clean (log every ⚠ with a decision), a check table in docs/BUILD_LOG.md, headless screenshots (temporary server on a random free port, stopped straight away — never leave a server running), commits (feat:/data:/fix:/docs:), and the phase ticked in docs/PLAN.md with a 5-line status.
7. Run everything in one go: never stop between phases, never ask me to confirm or choose — decide, log it and continue. Use subagents for research-heavy or bulk steps. Keep docs/PLAN.md current after every commit so work survives context compaction; after a compaction re-read it and carry on. If the session is about to end for good, commit and write the exact resume point in docs/PLAN.md.

PHASE 0 — Plan + clean skeleton
Write docs/PLAN.md (this task verbatim + checklist of phases 0–8), docs/BUILD_LOG.md, docs/DATA_FOLDERS.md, docs/SOURCES.md, docs/GEO.md. Remove Danish-only code paths and data references (DST, DAWA/Datafordeler, BBR, boligstat, Copenhagen scripts, the Danish market panel); keep the generic UI, calc engine, overlay framework, testprop.js and Analysis code dormant but intact for batch 2. Title "Macro Dashboard — Finland", map box 59.7–70.1 N / 19.0–31.6 E, quick jumps (camera only, never selection, ignored while typing): Helsinki H, Tampere T, Turku U, Oulu O, Finland F. Zoom never changes the selection. make fixture renders. Pages + monthly refresh workflows adapted. Commit.

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

### Release v1.0 (after a quick localhost look)

```
Merge v1.0-build into main, tag v1.0, push main and tags, confirm the GitHub Pages deploy succeeded and print the live URL https://real-estate-war-lord.github.io/am-dashboard-fi/ with a 5-line check that it loads real data.
```

### Batch 2

```bash
cd ~/Desktop/"Finland dashboard"/am-dashboard-fi && git checkout main && git pull && git checkout -b v1.1-layers && caffeinate -i claude
```

```
MASTER TASK — BATCH 2 of 2: add every map layer and the Test property feature to the Finland edition in one unattended run. Branch v1.1-layers (checked out, based on v1.0). Do not push.

GROUND RULES: the same as batch 1. Read them in docs/PLAN.md and apply all of them unchanged: data principle, Danish repo read-only as reference, spec in docs/DATA_MAP_FI.md, English, string codes, stdlib-first, size limits, per-phase checks and commits, never stop or ask, subagents for bulk work, docs/PLAN.md kept current. First append this task and a checklist of phases 9–16 to docs/PLAN.md. Extra rules for layers: points and zones lazy-load per kunta; every point shows its source; overlays use the Danish overlay pills, stacked collapsible legends and canvas-renderer guard; disclaimers where the Danish edition has them.

PHASE 9 — Probe for layers
Extend scripts/probe_fi.py → docs/PROBE_FI.md: SYKE flood-hazard WFS/WMS (tulvavaaravyöhykkeet vesistö + meri, return periods, layer names, licence); sea-level scenarios (Ilmatieteen laitos / SYKE: years, scenarios, format); HSY/Helsinki stormwater (hulevesi) flood maps; STUK radon by area; Ryhti buildings + kaavat (OGC API/WFS, fields incl. use, year, floor area, storeys, dwellings; plan status and floor area); DVV building addresses (open file, size, fields); ARA energy certificates open data; HSL GTFS + Fintraffic national GTFS; Helsinki Palvelukartta API; Geofabrik finland-latest.osm.pbf; LIPAS; Väylävirasto open WFS project layers; YTL lukio results (open statistics route, latest year, fields); Opetushallitus / Palvelukartta school locations; Tilastokeskus 1 km grid. Commit.

PHASE 10 — Test property + Analysis + Compare (row 36)
Port DK v2.4 testprop.js: Google Maps link / coordinates parser (short links refused with a named error) PLUS address search from the DVV building-address file (built into a compact lazy lookup, no server). Finland box 59.7–70.1 N / 19.0–31.6 E. Exact kunta / postinumero / osa-alue by point-in-polygon on our own rings (holes kept). Pin in the URL hash, privacy line. Analysis sheet in the left nav reads everything the dashboard carries for the pin's areas (headline row, demographics, market price and rent, taxes, safety, outlook) and, as later phases land, climate, services, public buildings, infra, schools, buildings and zoning. Compare two pins with aligned rows, direction-aware, no overall winner. Tests with Finnish link and address cases. Commit.

PHASE 11 — Climate risk (rows 37–40)
Group "Climate" + "Climate risk" overlay; horizon or scenario always in the label. Area share of land per postinumero / osa-alue / kunta inside SYKE flood-hazard zones (sea and watercourse, 1/100 and 1/1000 at least; unmapped areas = "Not mapped"); sea-level scenario share where the data allows (label e.g. "Mean sea level 2100 (scenario, source)"); stormwater flood share where HSY/Helsinki publish it (others "Not mapped"); radon only if STUK publishes open area data, else log and skip. Disclaimer "Screening indicators for comparing areas, not a property-level risk assessment." Climate section in the Analysis sheet. Commit.

PHASE 12 — Services + Public buildings (rows 41–42)
Services overlay, points only, no area indicators: grocery (supermarket/convenience), restaurants/cafés from OSM; public-transport stops from HSL GTFS + Fintraffic GTFS (OSM stops as fallback, logged). Public buildings overlay with a category filter (education / daycare / health / culture): Ryhti buildings by use where fields allow, Palvelukartta for the Helsinki region, OSM elsewhere; source per point. Commit.

PHASE 13 — Infra projects (row 43)
Hand-curated data/external/infra_fi.geojson, 30–50 projects, each with a source URL: Väylävirasto projects and the national transport investment programme, Kruunusillat, Vantaan ratikka, Espoon kaupunkirata, Lentorata, Tunnin juna / Itärata / Turku rail, Tampere tram extensions, other major rail/metro/tram/road projects. Fields as in the Danish infra file (status, opening year or window, budget + price base, stations). Alignments only where officially published or OSM-tagged construction/proposed — else stations only, never drawn guesses. Overlay pill, datasheet, Pipeline view with CSV, growth-signal indicators projects_upcoming and stations_planned_1200m. Verify 5 projects against their sources. Commit.

PHASE 14 — Schools (row 35)
School points (comprehensive + upper secondary) from the official register / Palvelukartta / OSM. Lukio matriculation results from YTL where openly published (latest year + history, fields as published, suppressed ≠ 0), popup with value vs kunta vs Finland, school datasheet. State plainly that Finland publishes no comprehensive-school results. Commit.

PHASE 15 — Buildings, energy, zoning, grid (rows 44–47)
Buildings micro layer from Ryhti (as DK v1.5): building points with use, year, floor area, storeys, dwellings where published, lazy per kunta; area indicators only as plain counts/shares of published fields (e.g. share of dwellings built before 1980). ARA energy certificates joined by building ID where possible → energy-class share per area. Zoning overlay from Ryhti kaavat (+ Helsinki asemakaavat WFS if richer): plans in preparation / approved, residential floor area where published, datasheet, indicator planned_floor_area_1000 (per 1 000 residents) only if the floor area is published. 1 km grid population as an optional overlay. If a whole-country pull is too heavy, build the Helsinki region first, then whole country; log the coverage. Commit(s).

PHASE 16 — Verify, docs, wrap-up
Verification rows for every new layer in docs/VERIFICATION.md (5 samples each) and docs/verification/v1_1.csv; docs/SOURCES.md, DATA_MAP_FI.md, README updated; refresh workflow extended for the cheap sources; CHANGELOG v1.1 draft. Final validate / test / build / links clean. Print a ≤ 40-line summary: what shipped per phase, what was skipped and why, every open ⚠, and a localhost review checklist. STOP — do not merge, tag or push.
```
