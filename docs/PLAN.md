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
| 3 | Area indicators (rows 1–11) | ☐ | |
| 4 | Market indicators (rows 12–21) | ☐ | |
| 5 | Taxes (rows 29–30) | ☐ | |
| 6 | Safety + Outlook (rows 31–33) | ☐ | |
| 7 | Osa-alue level (row 34) | ☐ | |
| 8 | Verify, docs, wrap-up | ☐ | |

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

---

## 5. Resume point

**Next action:** Phase 3 — area indicators (rows 1–11): `config/indicators.json`, `scripts/fetch_statfin.py`, `scripts/build_makro.py` (with the level-of-detail split decided in phase 2).
