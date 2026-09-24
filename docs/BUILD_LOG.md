# Build log — Finland edition, batch 1

One check table per phase: what was run, what it said, and what was decided about every ⚠.
Phases and their status live in `docs/PLAN.md`; this file is the evidence behind them.

---

## Phase 0 — Plan + clean skeleton

| Check | Result |
|---|---|
| `python3 scripts/validate_config.py` | ✓ "no indicators registered yet" — expected until phase 3 |
| `python3 scripts/check_source_links.py --quick` | ✓ "no verify-at-source links yet" — expected until phase 3 |
| `make test` (python + node) | ✓ see the table below |
| `make fixture` | ✓ `dist/fixture.html`, 0.8 MB, 8 synthetic kunnat · 40 postinumeroalueet · 24 osa-alueet |
| `make build` | ✓ `dist/index.html` assembles with no data (empty map, honest "no data" state) |
| headless screenshots | ✓ `docs/screenshots/fixture-1..3.png` — map, table, sources; server stopped |
| `node --check src/app.js` | ✓ parses after every transform pass |

### Decisions logged in phase 0

| ⚠ / question | Decision |
|---|---|
| The Danish app.js is 3 600 lines of `kommune` / `postnr` / `kvarter` / `bydel` | Renamed mechanically to `kunta` / `postinumero` / `osa_alue` / `peruspiiri` in six reviewed passes, each followed by `node --check`. The JSON container names (`municipalities`, `areas`) keep the Danish shape as the ground rules require; only the level identifiers changed. |
| The Copenhagen quarter layer is hard-coded to one municipality (`CPH_MUNI = "101"`) | Generalised: `OSA_MUNIS` is derived from the data (`[...new Set(OSA.areas.map(a => a.muni))]`) and `isOsaMuni()` / `osaParent()` replace every comparison against a single code. Finland needs four (Helsinki, Espoo, Vantaa, Kauniainen) and adding a fifth is now a data change. |
| National macro is out of scope, but the Danish **Market** view *was* the macro panel | `vMarket()` deleted. `vSources()` promoted from a fold inside Market to its own nav item under "Reference", so the source table, licences and indicator definitions stay reachable. |
| `testprop.js` still carries the Danish bounding box | Left as it is. It is dormant in batch 1, its unit tests are green, and batch 2 phase 10 rewrites it with the Finland box and DVV address search. Changing it now would only break `make test-js` for no gain. |
| The BBR / services / public-buildings / infra / schools code paths | Kept, dormant (each renders nothing while its data key is null), as the ground rules require for batch 2. Every Danish register *name* in their UI text was replaced with a neutral one, so no dormant string can claim a Danish source. |
| `config/indicators.json` starts empty | Deliberate: nothing is registered before it is probed. `validate_config.py` says so explicitly instead of failing. |
| `make build` has no `build_makro.py` yet | The target is `build_dashboard.py` alone in phase 0 and gains `build_makro.py` in phase 3, so `make build` is green in every phase rather than red until the data lands. |

---

## Phase 1 — Probe

| Check | Result |
|---|---|
| `make probe` (84 routes) | 74 answered, 10 ✗ — every ✗ is kept in `docs/PROBE_FI.md` with what replaced it |
| Reference values | 5 of 5 answer: Helsinki 694 392 · 00100 price 7 167 €/m² (35 sales) · 00100 rent 29,43 €/m² (746 obs) · Helsinki free rent 26,73 · Helsinki ARA rent 18,48 |
| `make validate` | ✓ (still no indicators registered — phase 3) |
| `make test` | ✓ 22 python + 15 node |
| `make build`, `make fixture` | ✓ |

### Decisions logged in phase 1

| ⚠ | Decision |
|---|---|
| No PxWebApi v2 exists (three candidate hosts, all 404) | `scripts/statfin.py` stays a v1 client and the docstring records the probe. |
| `ras`, `asas`, `rakke`, `astuki` all return HTTP 400 — the four database names in the spec are gone | Replaced by `raku` and `asku`; the frozen originals are reachable in `StatFin_Passiivi` and are used where the live table has no history. Every substitution is in `docs/PROBE_FI.md` §"What the probe changed about the plan". |
| `asvu/13eb` — postal-code rent, the indicator that made Finland's market layer unique — is **gone from live StatFin** and frozen at 2025Q4 | Both are carried: the frozen postal series (labelled with its own end date, 2025Q4, and never extended) and the live kunta-level `asvu/15fa`. Phase 4 decides which is the headline; neither is silently spliced into the other. |
| `asvu/15fa` publishes ARA rent as funding code `2`, the archive `11x4` as code `0` — the codes are **inverted** | Both recorded verbatim in the config. Never assume a funding code means the same thing in two tables. |
| `ashi/12dg` (new dwellings by sub-area) returns null for all 24 sub-areas | Not registered. A table of nulls is not a source. |
| `raku/156f` and `raku/15f7` are maakunta-level only — no kunta-level construction exists anywhere | Logged as gap 1. Phase 4 either publishes it at maakunta level with the level stated, or drops it. |
| `rpk/13ex` takes ~10 s per small request | Phase 6 chunks by year; the client already throttles. |
| Partial probe runs were overwriting the full table in the doc | `probe_fi.py --only …` now prints instead of writing unless `--force` is given, and the generated block is spliced between markers so the hand-written findings survive a re-run. |
| StatFin returned HTTP 429 mid-probe and the first run reported live tables as missing | `get()` now waits out a 429/503 and retries up to four times; a rate limit can no longer be reported as a dead route. |

---

## Phase 2 — Geometry

| Check | Result |
|---|---|
| `make geo` | ✓ 4 layers written, all under the 3 MB ceiling |
| kunta count = kuntajako 2026 | ✓ **308** |
| maakunta count | ✓ **19**, every kunta carries one |
| osa-alue coverage | ✓ **306** — Helsinki 148, Espoo 88, Vantaa 61, Kauniainen 9 |
| postal areas | ✓ **3 018** (`pno_tilasto_2026`), every one carries a kunta code that exists in the 2026 kuntajako |
| leading zeros | ✓ 36 kunta, 357 postal, 297 osa-alue, 8 maakunta codes start with a zero and keep it; every code is a string |
| land area sanity | ✓ 335 661 km² summed over the 308 simplified kunta polygons (Finland incl. inland waters ≈ 337 800 — the 0.6 % gap is the simplification) |
| point-in-polygon | ✓ 8 known places resolve correctly through all four layers, including Kauniainen, which stays a hole inside Espoo |
| `make test` | ✓ 24 python + 15 node |
| `make validate`, `make build`, `make fixture` | ✓ |

| File | Size | Simplification |
|---|---:|---|
| `kunnat.geojson` | 1 250 kB | 50 % mapshaper, keep-shapes |
| `maakunnat.geojson` | 600 kB | 30 % mapshaper, keep-shapes |
| `osa_alueet.geojson` | 766 kB | 50 % mapshaper, keep-shapes |
| `postinumerot.geojson` | 2 903 kB | 8 % mapshaper, keep-shapes |

### Decisions logged in phase 2

| ⚠ | Decision |
|---|---|
| No boundary layer carries a kunta → maakunta mapping | Taken from Tilastokeskus's own classification API (`kunta_1_20260101#maakunta_1_20260101`, 308 rows) and committed as `data/geo/kunta_maakunta.json`. A spatial guess was available and was **not** used: the official correspondence is the published fact. |
| HSY's Seutukartta is the only single layer covering all four Helsinki-region kunnat, but it is frozen at 2021 and 179 of its 824 features are unnamed | Helsinki is taken from its own fresher, fully named layer (`avoindata:Piirijako_osaalue`, updated 2026-09-23) and the other three from HSY. The two divisions were compared code by code for Helsinki — 148 codes, zero difference — so the mix cannot produce a mismatched division. Recorded in `docs/GEO.md` §3 and in each feature's `source` property. |
| Vantaa's rows in HSY's *pienalue* layer are really at *tila* level: all 61 have `pien = "000"` | The area number falls back to `tila` when `pien` is `000`, and the feature records which level it came from. Without this, all 61 Vantaa areas collapsed onto the single code `092000` — the sanity check caught it. |
| Kauniainen's 9 areas have no published name | Shown as "Kauniainen 002" etc. with `named: false`, so the UI can say the name is not published rather than inventing one. |
| `mapshaper` is not installed on this machine | Run through `npx --yes mapshaper@0.6.102`, with a Visvalingam pass written in `scripts/geo_common.py` as the fallback so `make geo` works without node. Whichever ran is recorded in each file's `meta.simplified` and in `ATTRIBUTION.txt`. |
| `postinumerot.geojson` at 2.9 MB is 97 % of the ceiling, and 3 018 rings cannot also fit inline in `dist/index.html` with their values and history | The committed file stays the detailed one. Phase 3 splits it into two levels of detail: a coarse set inlined for the national view, and per-kunta detail fetched when a kunta is drilled into. Logged here so phase 3 does not rediscover it. |
| Paavo's layer year is not its statistics year | `pno_tilasto_2026` carries statistics for **2024**, verified against PxWeb. Both years are written into the file's `meta` and the UI labels the statistics year. |
