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

---

## Phase 3 — Area indicators (rows 1–11)

| Check | Result |
|---|---|
| `make validate` | ✓ 14 indicators, 5 StatFin tables, every code checks out; 6 verify-at-source links reachable |
| `make links` (full sweep) | ✓ 6 of 6 |
| `make fetch` | ✓ 24 StatFin pulls (9.5 MB raw, stamped) + Kela 2 764 rows |
| `make build` | ✓ `makro.json` 2 212 kB · `monthly.json` 531 kB · 308 per-kunta files (largest 200 kB) · `index.html` 2 810 kB — all under the 3 MB ceiling |
| `make test` | ✓ 24 python + 15 node |
| Spot-check against source | ✓ 8 of 8 reconcile exactly (below) |
| Screenshots | ✓ `docs/screenshots/v10-1..4.png` — national map, Helsinki drilled in, table, 00100 area page |

### Spot-check, phase 3 (recomputed straight from the PxWeb cells)

| Area | Indicator | Published cells | Recomputed | On the page |
|---|---|---|---|---|
| 00100 | population | he_vakiy | 18 492 | 18 492 |
| 00100 | renters | 5 352 ÷ 10 544 | 50,759 % | 50,8 % |
| 00100 | median income | hr_mtu | 34 408 € | 34 408 € |
| 00100 | unemployment | 834 ÷ (10 107 + 834) | 7,623 % | 7,6 % |
| 00100 | aged 20–34 | (1 683+2 402+1 771) ÷ 18 492 | 31,668 % | 31,7 % |
| 091 | renters | 194 095 ÷ 359 689 | 53,962 % | 54,0 % |
| 091 | median income | hr_mtu | 29 159 € | 29 159 € |
| 091 | population growth | 694 392 ÷ 684 018 − 1 | +1,517 % | +1,5 % |

### Decisions logged in phase 3

| ⚠ | Decision |
|---|---|
| Two candidate backbones: StatFin's thematic databases, or Paavo | **Paavo** (`12f7` postal, `12f8` kunta/maakunta, 2010–2024), because it publishes the *same definitions at both levels*. A kunta figure and a postal figure are therefore directly comparable, which is not true of the Danish edition. Only where Paavo has nothing — foreign-language speakers, monthly unemployment, housing allowance — does another source appear. |
| Population growth: Paavo ends at 2024, `vaerak` reaches 2025 | Kunta growth comes from `vaerak/11re` (to 2025), postal growth from Paavo (to 2024). The two levels' periods are recorded separately in `asof` and shown in the ⓘ line; they are never averaged. This is the Danish edition's own pattern. |
| Paavo publishes unemployment as two counts, not a rate | `pt_tyott ÷ (pt_tyoll + pt_tyott)` — the labour force is the employed plus the unemployed. The division is ours and is stated in the indicator's definition. It is plain arithmetic on two published cells, which the hard-data rule allows; an assumed participation rate would not be. |
| Kela's newest month is 2026-08 but Paavo's household count ends 2024 | The share is computed only where both exist, so it ends at **2024**. Extending it with a carried-forward household count would be an assumption. The raw Kela series is kept in `data/external/kela_asumistuki.csv` to 2026-08 for the verification export. |
| Kela's annual rows are a flow, not a stock | `aikatyyppi='Vuosi'` counts *distinct households during the year* and is several times the month-end figure. Only `Kuukausi` rows are read, and a year is its **December** value — a stock, like the household count it is divided by. Written into `import_kela.py` and its stamp. |
| Kelasto has no API | Kela's WebFOCUS reports need a browser session. The same figures are on avoindata.suomi.fi's CKAN datastore under **CC BY 4.0**, and that is the route used. Helsinki 2026-08 = 44 228 households, which matches the Kelasto page. |
| 3 018 postal polygons plus their values and history do not fit in one HTML file (3.3 MB on the first build) | **Two levels of detail and two lazy payloads.** The page inlines coarse kunta rings, every kunta's annual history, and every postal area's latest values and bounding box. `dist/area/<kunta>.json` carries the detailed postal rings and their history, fetched when a kunta is opened; `dist/monthly.json` carries every monthly series, fetched when a monthly indicator is selected. Result: 2 810 kB inline. Both files come from the same build, so they cannot disagree about which areas exist. |
| The national map used to draw all 3 018 postal polygons | It now draws the 308 kunta polygons. Nothing is lost: the Danish edition coloured those postal outlines by their municipality's value anyway, so they carried no information of their own at that zoom. |
| Monthly unemployment and annual Paavo unemployment are different definitions | Registered as two indicators, each with its own caveat saying so, rather than one series spliced from two sources. |
| Verify-at-source URLs returned HTTP 500 | The `statfin_<db>_pxt_<id>.px` spelling that appears in older links is dead; the PxWeb UI wants the same id the API uses (`.../StatFin__vaerak/11re.px/`). Fixed in `statfin.ui_url`, in `srcUrl()` in the page, and in the 24 stamps already written. `make links` now sweeps all six clean. |
| `validate_config.py` did not know the `num`/`den` → contentscode convention the fetcher uses | Taught it the same rule, and it now also fails when a code in `num`/`den` matches no value of any variable and no other source provides it. |

---

## Phase 4 — Market indicators (rows 12–21)

| Check | Result |
|---|---|
| `make validate` | ✓ 28 indicators, 11 StatFin tables |
| `make links` | ✓ 14 of 14 |
| `make fetch` | ✓ 48 pulls in `data/raw/statfin` |
| `make build` | ✓ `makro.json` 1 537 kB · `hist.json` 849 kB · `monthly.json` 1 123 kB · 308 area files · `index.html` **2 137 kB** |
| `make test` | ✓ 24 python + 15 node |
| Spot-check | ✓ every market figure reconciles (below) |
| Screenshots | ✓ `docs/screenshots/v10m-*.png`, `v10q-*.png` |

### Spot-check, phase 4

| Area | Indicator | Published cells | Recomputed | On the page |
|---|---|---|---|---|
| 00100 | price, kerrostalo 2025 | (7 371×136 + 7 254×152 + 7 353×132) ÷ 420 | 7 323 €/m² | 7 323 €/m² |
| 00100 | sales 2025 | 136 + 152 + 132 | 420 | 420 |
| 00100 | price, quarterly 2026Q1 | 13mt | 7 165 €/m² | 7 165 €/m² (chart) |
| 091 | free-market rent 2026Q2 | 15fa, funding 1 | 21,34 €/m² | 21,3 €/m² |
| 091 | ARA rent 2026Q2 | 15fa, funding 2 | 15,30 €/m² | 15,3 €/m² |
| 091 | rent y/y 2026Q2 | 15fa, published | −0,2 % | −0,2 % |
| 091 | unoccupied dwellings 2025 | 46 457 ÷ 410 ### | 11,33 % | 11,3 % |
| 091 | completions per 1 000 dw. | 9 226 ÷ 973 670 × 1000 (Uusimaa) | 9,48 | 9,5 ^ |
| 261 Kittilä | completions per 1 000 dw. | 570 ÷ 108 694 × 1000 (Lappi) | 5,24 | 5,2 ^ |

### Decisions logged in phase 4

| ⚠ | Decision |
|---|---|
| `ashi/13mt` and `13mu` publish **no building-type total** — only three room-count classes of blocks of flats and one terraced total | The kerrostalo figure is the **sales-weighted mean** of the three room-count classes, using each class's own published transaction count. That is exactly the arithmetic mean over the underlying transactions, not an approximation, because the published figure is itself an arithmetic mean per transaction. Written into the indicator's definition so no reader mistakes it for a plain average. |
| `ashi/13mx` spells building types differently from `13mt` (0 total / 1 terraced / 3 blocks of flats, versus room-count classes) | A source entry may carry `cells`, a per-table rename onto the indicator's own code names. Without it, the kunta price was silently a mix of terraced houses and flats — caught by a spot-check, not by a test. |
| Headline price: the published annual figure, or a rolling four-quarter mean? | **The published annual figure.** It exists at both levels, needs no arithmetic at all, and is far less suppressed than a single quarter. The publisher's own quarterly series rides along behind the Yearly \| Quarterly toggle, so nothing is lost — 00100 reads 7 323 €/m² for 2025 and its chart ends at 7 165 €/m² for 2026Q1. |
| Postal-code prices are on the **2022** postal classification (1 724 areas), the map on the **2026** one (3 018) | Only areas whose code exists in both carry a price; 701 of 3 018 have one for 2025. The rest read `–`. No figure is ever borrowed from a neighbouring or a predecessor area. Stated in the indicator's caveat and in `docs/GEO.md`. |
| `asvu/13eb` — the postal-code rent table — is discontinued, frozen at 2025Q4 | Registered as its own indicator, `rent_pno`, labelled "discontinued" in its own label, with its end date in its caveat. It is never extended and never blended with the live kunta series. 580 postal areas. |
| Rents and construction are published for 27 kunnat / 19 maakunnat, not 308 | Where a kunta has no figure of its own it shows its **maakunta's**, marked **^**, and the indicator records how many areas inherited. A rate inherited this way is computed on the maakunta's own denominator — an early version divided the maakunta's completions by the kunta's dwelling stock and made Kittilä look like it was building 157 dwellings per 1 000. Caught by a sanity read, fixed, and now spot-checked. |
| **Statistics Finland publishes no municipal building and dwelling production at all** | Not a gap we can close: `raku/156f` and `15f7` are by maakunta, and the discontinued `ras` tables were too. The three construction indicators are maakunta figures shown on kunnat with ^, and their caveat says "two municipalities in the same maakunta always show the same number". |
| `ashi/12dg` (new dwellings by sub-area) | **Not registered.** Every one of its 24 sub-area codes returns null for every year and building type. A table of nulls is not a source. |
| `raku/15f6` publishes one year | Unoccupied dwellings has no history. Said so in the caveat rather than reaching into the frozen `asas` archive, which is on a different classification. |
| The page passed 3 MB again as market rows landed | **Kunta history moved to `dist/hist.json`**, fetched when a chart, an area page or any period other than the latest asks for a series. The build now records each indicator's own period list, so the year selector and the chart axis are right before any history is fetched. The page is 2 137 kB, with room for phases 5–8. `build_dashboard.py` now fails the build if any dist file passes 3 MB, rather than warning. |
| The observed-population series was inline for every kunta but read by one area page at a time | Moved into that kunta's own lazy file. |

---

## Phase 5 — Taxes (rows 29–30)

| Check | Result |
|---|---|
| `make validate` | ✓ 34 indicators |
| `make links` | ✓ including the two Verohallinto pages |
| `python3 scripts/import_verohallinto.py` | ✓ 20 020 property-tax rows (308 kunnat, 2014–2026) · 308 income-tax rows (2026) |
| `make build` | ✓ `index.html` 2 224 kB |
| `make test` | ✓ 24 + 15 |
| Spot-check | ✓ Helsinki 2026: permanent dwelling **0,41 %** · other dwelling **0,93 %** · general building **0,93 %** · general land **1,30 %** · undeveloped site **4,30 %** · municipal income tax **5,30 %** — every one matches the published decision |

### Decisions logged in phase 5

| ⚠ | Decision |
|---|---|
| The spec expected an annual XLSX from vero.fi | Better route found and used: **Verohallinto runs its own keyless PxWeb** at `vero2.stat.fi`, table `kive_202`, with the applied percentage per kunta per category for **2014–2026**. That is thirteen years of history instead of one file, and it needs no spreadsheet parsing. |
| **The municipal income-tax rate is not a statistic anywhere.** Not in StatFin, not in `Kuntien_avainluvut`, not in Verohallinto's own PxWeb, not on avoindata.fi | Verohallinto publishes it as an annual *decision*. Its page renders the table from JSON in a `:rows=` attribute, and that JSON is read, with the URL pinned in the new `config/sources.json`. The rows carry names, not codes, so they are matched against kuntajako 2026 and **every unmatched name fails the import**. That caught Maarianhamina, whose boundary name is "Maarianhamina - Mariehamn"; bilingual names are now registered as aliases and all 308 match. |
| Only one year of income-tax history | Said so in the caveat. The 2023 hyvinvointialue reform cut every municipal rate by about 12 pp when health and social care moved to the wellbeing services counties, so an older rate is not comparable with a current one anyway — also said, rather than quietly splicing a series across the break. |
| `direction` for a tax rate | `lower_better`, read explicitly from an owner's side, with the note saying it is not a judgement about the municipality: the same rate funds its services. |
| 199 of 308 kunnat have an undeveloped-site rate | Not every municipality sets one. A missing rate is shown as `–` with a caveat saying it is not a rate of zero. |
| Verohallinto states no open licence on the tax-rate pages | Recorded honestly in `docs/SOURCES.md` and in `config/sources.json`: the figures are used with the attribution "Lähde: Verohallinto" and are not republished as an open-licensed dataset. |
| A third file-based source after Kela | Generalised into a `csv` source type in `build_makro.py` that names its own columns, so the next file source needs no new engine code. |

---

## Phase 6 — Safety + Outlook (rows 31–33)

| Check | Result |
|---|---|
| `make validate` | ✓ 50 indicators |
| `make fetch` | ✓ `rpk/13h4` 6 pulls · `rpk/13ex` 1 · `vaenn/14wx` 53 |
| `make build` | ✓ `index.html` 2 310 kB |
| `make test`, `make fixture` | ✓ |
| Spot-check, Safety | ✓ Helsinki 2025: crime **133,26**, violence **11,38**, property **77,38** per 1 000 — the publisher's own rates, unchanged; y/y 133,26 ÷ 118,47 − 1 = **+12,48 %**; burglary 424 ÷ 398 541 × 1000 = **1,06** per 1 000 dwellings |
| Spot-check, Outlook | ✓ Helsinki 706 283 → 810 580 = **+14,77 %**, **+104 297** residents; five-year 749 128 ÷ 706 283 − 1 = **+6,07 %**; 20–34 share 23,26 % vs Finland 18,15 % = **+5,12 pp** |
| Screenshots | ✓ `v10safe-*.png`, `v10out-*.png` |

### Decisions logged in phase 6

| ⚠ | Decision |
|---|---|
| Should the per-1 000 crime rate be computed here? | **No.** `rpk/13h4` publishes offences per 1 000 population in the area, so the published rate is used unchanged. A published figure always beats our own arithmetic on it. |
| Which "all offences" total? | `101T504X406` "1 Offences against penal code", not the broader `101T603`, which also counts traffic infractions and minor public-order matters. About a quarter of even the penal-code total is traffic offences, which the indicator's own note says out loud, pointing readers at the thematic rates instead. |
| Burglary per 1 000 **dwellings**, as the spec asks | The count comes from `rpk/13ex` (`101T103a0101`, "Thefts, through unlawful breaking into other residence" — a permanent dwelling, excluding the summer houses the publisher counts separately) and the denominator is Paavo's dwelling stock. The division is ours and says so. |
| "Quarterly series if published" | **There is none.** The only quarterly table in `rpk` is `13iv`, which has no area variable at all; sub-annual municipal data exists only monthly (`13it`) and is marked preliminary from 2026M01. The annual series (final through 2025) is what is shown, and `docs/SOURCES.md` says plainly that Finland publishes no open crime data below kunta level. |
| The crime rate counts offences where they happened, against the population registered there | Said in every Safety indicator's note, in the publisher's own words. A city centre carries offences against people who do not live there, and the note tells the reader to read it as where crime is recorded, not as how dangerous residents' lives are. |
| Which age bands for the Outlook? | The Finnish school ages: **0–6** (before school, the daycare cohort) and **7–15** (comprehensive school), not the Danish 0–5 / 6–16. Plus 20–34 and 80+. Each band is a sum of the projection's own single-year cells. |
| Väestöennuste 2024 is one vintage, not a series | The Outlook indicators return one number and no history, the year selector is replaced by the projection window, and the projected part of every chart is dashed with a "2025 · today" marker between observed and projected. The publication date (2024-10-24) is read from the table's own `updated` field, not from the table listing, which carries a later bulk re-stamp. |
| `fc_20_34_rel` needs Finland's own projected share | The whole-country row is kept for the projection only — the comparison comes from the same projection as the area's own figure, never from a different source. |
| Indicators now end in different years (Paavo 2024, taxes 2026) | "Latest" became a sentinel meaning *this indicator's newest period*, and the year selector says which year that is — "latest (2025 data)". Picking it can never mix two indicators' years. |

---

## Phase 7 — Osa-alue level (row 34)

| Check | Result |
|---|---|
| `make validate` | ✓ |
| `make links` (full sweep) | ✓ **25 of 25**, including the six Aluesarjat tables |
| `python3 scripts/build_osa.py` | ✓ 306 areas · 9 indicators · 4 per-kunta files amended |
| `make build` | ✓ `index.html` 2 429 kB (osa_alue.json 123 kB inline; rings and history in the per-kunta files) |
| `make test`, `make fixture` | ✓ |
| Spot-check | ✓ Kruununhaka 7 465 inhabitants (2025), growth +1,3 %, 19–34 27,8 %, foreign-language 8,5 %, one-person households 48,3 % · Helsinki city projection PER26 702 767 → 821 774 = **+16,93 %** against Tilastokeskus's +14,77 %, shown side by side, **2,16 pp apart** |
| Screenshots | ✓ `v10osa-*.png` |

### Decisions logged in phase 7

| ⚠ | Decision |
|---|---|
| **Aluesarjat is not CC BY 4.0** — its terms allow **non-commercial use only** | This is the one licence restriction in the whole dashboard, and it is confined to one layer. It is written into the layer's own `meta.licence`, into every osa-alue indicator's note, into the Sources view and into `docs/SOURCES.md`, so nobody can lift a figure out of it without seeing the terms. Logged as an **open ⚠** for the release decision. |
| Joining Aluesarjat to our geometry | No crosswalk needed: Aluesarjat's ten-digit area code *is* Helsingin kaupunki's `kokotunnus`, which the boundary file stores verbatim. **296 of 306** match. The ten that do not are Kauniainen's nine sub-areas, which Aluesarjat publishes as one municipality, and Helsinki's territorial-sea polygon, which has no residents; they keep their geometry and show the kunta value, marked °, exactly as a postal area does. |
| Three Aluesarjat definitions differ from the kunta level | They get **their own keys**, never the kunta key with a different meaning behind it: `young_19_34` (the published band is 19–34, not 20–34), `rented_dw` (rented *dwellings*, where the kunta figure is *households* in rented dwellings) and `higher_ed_15` (of everyone 15+, where the kunta figure is 18+). Keys that do mean the same thing — growth, foreign, single, flats, vacant — are shared, so an osa-alue can sit beside its kunta honestly. |
| Espoo and Vantaa publish their own area projections | **Not shown.** `alu_vaenn_010e` runs to 2033 and `alu_vaenn_040o` to 2035, on different vintages. Stretching them to a common 2026→2040 window would mean inventing the years between. Only Helsinki's `alu_vaenn_006c` (PER26) is carried, labelled as the city's own forecast. |
| Helsinki now has two projections | Shown **side by side with the gap stated** — Tilastokeskus +14,8 %, Helsingin kaupunki +16,9 %, 2,16 pp apart — never averaged. The rule and its arithmetic are written down in the new `docs/OUTLOOK_FI.md`, which the UI links to. |
| A variable left out of an Aluesarjat query is silently eliminated to its total | Every dimension is named explicitly in every pull. Also: the area variable is `Alue` in some tables and `Osa-alue` in others, and the wrong one is an HTTP 400 — `scripts/aluesarjat.py` reads which it is rather than assuming. |
| `api.aluesarjat.fi` does not answer, and the English tree exposes two of seven folders | The **Finnish** tree at `stat.hel.fi/api/v1/fi/Aluesarjat/` is the route. Recorded in `docs/SOURCES.md`. |
| The Aluesarjat verify-at-source links 404'd | PxWeb's UI folder is the API path joined with double underscores and prefixed by the database name. Fixed, and `make links` now sweeps all 25 clean. |
| The area page's mini-map opened on Denmark | The Danish default centre had survived in `arMapInit`. It now starts from the current view and always fits the area, whose bounding box is inline even before its rings are fetched. |
