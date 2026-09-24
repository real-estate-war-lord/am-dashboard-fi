# Macro Dashboard — Finland

A single-page map of Finland's housing market and demographics, built only from open
official data. Three levels — **kunta → postinumeroalue → osa-alue** — with prices, rents,
income, demographics, construction, taxes, safety, climate risk and the population outlook
side by side, plus map layers for services, public buildings, infrastructure projects,
schools, buildings and zoning, and a **Test property** sheet that reads all of it for one
address.

![The macro map, old-flat prices per m²](docs/screenshot.png)

**Live:** _(GitHub Pages link goes here once `main` is published)_

## What is in it

| | Count |
|---|---|
| Kunnat | **308** (kuntajako 2026) |
| Postinumeroalueet | **3 018** (Paavo `pno_tilasto_2026`) |
| Osa-alueet | **306** — Helsinki 148, Espoo 88, Vantaa 61, Kauniainen 9 |
| Indicators | **62** at kunta and postal level, **14** more at osa-alue level |
| Groups | Demographics · Income & jobs · Housing stock · Market · Construction · Taxes · Safety · **Climate** · Outlook · **Growth signals** |
| Addresses | **3 719 340** searchable, with no server |
| Service points | **113 372** · **8 601** public buildings |
| Buildings | **250 785** drawn, of 3 799 740 in the register |
| Schools | **2 501**, with matriculation results for **338** lukios |
| Infrastructure projects | **169** |
| Map overlays | Climate risk · Infra projects · Public buildings · Services · Zoning · 1 km population grid |

Every area has its own page, every indicator its own definition, source, period and a link
to the publisher's own table. The Table view puts every area side by side and exports CSV;
the Charts view plots any indicator for up to eight areas, yearly or quarterly, and exports
PNG or CSV.

**Test property** takes an address, a Google Maps link or a coordinate pair, resolves it to
its kunta, postal area and osa-alue on our own boundaries, and reads everything the dashboard
carries for those areas on one sheet — and **Compare** puts two of them side by side on
aligned rows, read in each indicator's own direction, with no overall winner.

## The rule this project runs on

**Every figure is an official published number, or plain arithmetic on official numbers** —
a difference, a share, a sum, a ratio, a per-1 000. Nothing here is modelled, fitted,
assumed or imputed.

- A **suppressed** cell is shown as `–` and is never read as zero.
- An area we do not cover reads **"Not covered yet"**, which is also not a zero.
- Where a figure is published for a **coarser area** than the one you are looking at, it is
  marked **°** (a kunta figure on a postal area) or **^** (a maakunta figure on a kunta) —
  never silently passed off as that area's own measurement.
- Where two publishers measure the same thing differently, both are shown with the gap
  stated, never averaged. See `docs/OUTLOOK_FI.md` §4.
- Where a definition differs between levels, it gets a **different name**, not the same name
  with a different meaning behind it.

`scripts/verify.py` re-queries the publishers, redoes the arithmetic from the returned
cells, and compares the result with what the page carries: **57 checks, 0 disagreements**
(`docs/VERIFICATION.md`). The full export is `docs/verification/v1_0.csv` — 14 341 rows,
every kunta × every indicator, long format.

## Run it

```bash
make probe      # live endpoint probe of every source  → docs/PROBE_FI.md
make validate   # every table/variable/value code checked against live metadata
make geo        # vendor the boundary layers (a pinned vintage; not part of the refresh)
make fetch      # pull every registered table, throttled, stamped
make build      # raw + geo + external → data/processed → dist/index.html
make verify     # recompute figures straight from the publisher and compare
make test       # unit tests (python + node)
make serve      # http://localhost:8080
make fixture    # synthetic render check — never publish a build made from this
```

Python 3.10+, **standard library only**. Node is optional: it runs the JavaScript syntax
check, the parser unit tests, and `mapshaper` for boundary simplification (there is a pure
Python fallback). No API keys are needed for anything in this repository.

## Sources and licences

Full detail in `docs/SOURCES.md`. The short version:

- **Tilastokeskus** — StatFin, Paavo and the boundary WFS: **CC BY 4.0**, attribution
  **"Lähde: Tilastokeskus"**.
- **Kela** — housing allowance, via avoindata.suomi.fi: **CC BY 4.0**.
- **Verohallinto** — property tax and the municipal income-tax rate: **licence not stated by
  publisher — public official figures.** Verohallinto's CC BY 4.0 statement covers only the
  corporate-tax datasets on its open-data page, not these two; used with the attribution
  "Lähde: Verohallinto" and not republished as an open-licensed dataset.
- **Helsingin kaupunki / HSY** — osa-alue boundaries: **CC BY 4.0**.
- **Aluesarjat** — every osa-alue figure: open for **both non-commercial and commercial
  use** ("Tietoaineistoa voi käyttää sekä ei-kaupallisiin että kaupallisiin tarkoituksiin",
  [terms](https://kaupunkitieto.hel.fi/fi/helsingin-tilastotietokannat/aluesarjat)). The
  condition is a two-part attribution — **"Helsingin seudun aluesarjat -tilastokanta ja
  Tilastokeskus"** — worded so as not to imply endorsement.
- **OpenStreetMap** — basemap tiles: ODbL 1.0.

**No source in this dashboard restricts commercial use.** v1.0 said Aluesarjat did; that was
a misreading of its terms and is corrected in v1.1.

The code in this repository is MIT (`LICENSE`). The data is not ours to license.

## What Finland does not publish

Each of these was asked of the publisher, and the answer is in the docs beside the layer:

| | |
|---|---|
| **Comprehensive-school results** | There is no national peruskoulu exam published per school. Not suppressed — it does not exist. `docs/SCHOOLS_FI.md` |
| **Energy certificates** | ARA's register is a paid X-Road service needing a *tietolupa*; `avoindata.fi` has 0 open datasets. `docs/BUILDINGS_FI.md` |
| **Planned floor area** | Ryhti's plans-in-preparation collections return **0 features nationally**, and Helsinki's 78 plans in preparation carry no floor-area field. `docs/BUILDINGS_FI.md` |
| **Sea-level scenarios** | No machine-readable national dataset; the only quantified figures are prose per sea basin. `docs/CLIMATE_FI.md` |
| **Stormwater flood maps** | Asked of HSY's 397 layers and Helsinki's 304 — neither publishes one. `docs/CLIMATE_FI.md` |
| **A keyless national GTFS** | Digitransit's national feed answers 401 without a registered key. `docs/SERVICES_FI.md` |
| **Tenure or per-dwelling area in the building register** | Ryhti publishes neither, so neither is shown. `docs/BUILDINGS_FI.md` |

## Honest limits

- **No days-on-market and no supply.** Only the commercial portals have them.
- **No transaction-level prices.** MML's kauppahintarekisteri is paid; `ashi`'s postal-code
  averages are what the dashboard shows.
- **Crime only at kunta level.** Finland publishes no open crime data below municipality,
  and no quarterly municipal crime data at all.
- **No comprehensive-school results.** Finland does not publish them. Upper-secondary
  matriculation results do exist and are in the dashboard, for the **338 of 380** lukios whose
  name matches the school register exactly — the two publishers share no key.
- **Flood hazard is mapped for designated areas only.** An area with no flood figure has
  **not been assessed**, which is not the same as no flood hazard, and the Flood-mapped row
  says how much of an area has been. The shares are screening indicators measured at 25 m
  from the publisher's own zone polygons, not a property-level risk assessment.
- **OpenStreetMap coverage is not uniform.** A rural area with no shop mapped is not the same
  as an area with no shop, and every point says which publisher it came from.
- **No municipal construction data anywhere.** Statistics Finland publishes dwellings
  started, completed and permitted by **maakunta** only, so every kunta shows its region's
  rate, marked ^.
- **Postal-code rents stop at 2025Q4.** `asvu/13eb` was discontinued; the series is frozen,
  labelled with its end date, and never extended. The live replacement is kunta level.
- **Three postal-code universes.** Prices are on the 2022 classification (1 724 areas),
  rents on a third (580), Paavo on 2026 (3 018). They are never reconciled: an area shows a
  price only if its own code exists in the price universe. See `docs/GEO.md` §2.
- **Paavo runs two years behind.** The 2026 release carries 2024 figures, and the UI labels
  the statistics year, never the release year.
- **Espoo's and Vantaa's own area projections are not shown** — different vintages, different
  end years.

## Documentation

| File | What it is |
|---|---|
| `docs/PLAN.md` | the build plan and its status, phase by phase |
| `docs/BUILD_LOG.md` | every check and every decision, with the reasoning |
| `docs/PROBE_FI.md` | the live endpoint probe, and what it changed about the plan |
| `docs/SOURCES.md` | every source, route, licence and attribution |
| `docs/GEO.md` | levels, classification vintages, and the traps |
| `docs/DATA_FOLDERS.md` | the one-way data flow and who writes what |
| `docs/OUTLOOK_FI.md` | how projections are handled |
| `docs/VERIFICATION.md` | figures recomputed from source and compared |
| `docs/RUNBOOK.md` | how to refresh, and what to do when a source breaks |
