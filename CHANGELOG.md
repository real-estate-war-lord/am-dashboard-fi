# Changelog

## v1.1 — map layers and Test property (draft, not released)

Branch `v1.1-layers`. Nothing merged, tagged or pushed.

### Corrections to v1.0

- **Aluesarjat is not non-commercial-only.** Helsinki's own terms permit commercial use:
  *"Tietoaineistoa voi käyttää sekä ei-kaupallisiin että kaupallisiin tarkoituksiin"*. v1.0
  quoted half that sentence and read the missing half as a prohibition. **No source in this
  dashboard restricts commercial use.** What the terms require is a two-part attribution —
  *"Helsingin seudun aluesarjat -tilastokanta ja Tilastokeskus"* — worded so as not to imply
  endorsement, and that is now what the footer and Sources carry. Closes open ⚠1.
- **Verohallinto**: its CC BY 4.0 statement is scoped to the corporate-tax datasets on its
  open-data page and names neither tax-rate series, so they are labelled
  **"Licence not stated by publisher — public official figures"** rather than claimed as
  CC BY 4.0.
- **Frozen series** carry one standard sentence — *"Last published &lt;period&gt; — series
  discontinued by publisher"* — in the tooltip, on the summary line and in a new Status
  column in Sources.

### Three bugs inherited from the Danish skeleton

None of them raised an error; all three were found by driving the page in a browser.

- `String(Number("091"))` is `"91"`. Harmless in Denmark, where no kommune code starts with a
  zero; here it made **every 0xx kunta a lookup miss**, so a pin in the middle of Helsinki
  reported *"in water or outside Finland"* while Tampere worked perfectly. 27 call sites.
- `bboxOf()` **cached the empty bounding box** it computed before an area's lazy rings landed,
  so that area could never be found again for the rest of the session.
- Six `L.polygon(a.rings, …)` calls **threw** when the lazy rings had not arrived, taking the
  whole render down with them.

And two more found the same way: a filter on `f.geometry` would have **silently dropped the
five biggest infrastructure projects in the country**, and `loadMicro` rendered inside its own
promise chain, so a drawing exception was reported to the reader as a failed download.

### New

- **Test property, Analysis and Compare.** An address, a Google Maps link or a coordinate pair
  resolves to kunta → postinumero → osa-alue on our own rings. **3 719 340 addresses searchable
  with no server**, 33 MB across per-kunta files and 36 first-letter shards. Compare puts two
  properties on aligned rows, read in each indicator's own direction, with **no overall winner**.
- **Climate** — 8 indicators and a Climate risk overlay drawing SYKE's own WMS live.
- **Services and public buildings** — 113 372 points and 8 601 buildings, each naming its
  publisher.
- **Infrastructure** — 169 projects; where a publisher gives two or three cost estimates, all
  of them are carried.
- **Schools** — 2 501 points, matriculation results for 338 lukios.
- **Buildings, zoning and the 1 km grid** — 250 785 buildings drawn, plus two overlays.

### What Finland does not publish, asked and answered

Comprehensive-school results · energy certificates · planned floor area · sea-level scenarios ·
stormwater flood maps · a keyless national GTFS · tenure or per-dwelling area in the building
register. Each is documented beside the layer that wanted it.

### Verification

`scripts/verify.py` — **88 checks, 0 disagreements**, including a recount of the flood shares
from the publisher's own raster tiles and of the matriculation means from YTL's own candidate
rows. Full export `docs/verification/v1_1.csv`, 16 788 rows.

### Known ⚠

The page ceiling was raised from 3.0 MB to 3.2 MB deliberately; the page is 3 013 kB and
**732 kB gzipped**. See `scripts/build_dashboard.py` and `docs/BUILD_LOG.md`.

All notable changes to the Finland edition. Dates are the build date, not the data's.

## [v1.0] — 2026-09-24 (draft, unreleased)

The first complete edition: three map levels, 59 indicators, everything from open official
Finnish sources.

### Added

**Geography** — 308 kunnat (kuntajako 2026), 19 maakunnat, 3 018 postinumeroalueet (Paavo
`pno_tilasto_2026`) and 306 osa-alueet over Helsinki, Espoo, Vantaa and Kauniainen, all in
EPSG:4326, simplified with keep-shapes so no island and no hole is lost. The official
kunta → maakunta correspondence comes from Tilastokeskus's classification API, not from a
spatial guess.

**Demographics and income (Paavo, both levels, same definitions)** — population growth,
median income of inhabitants, mean household income, share aged 20–34, one-person
households, renter households, unemployment, tertiary education, dwellings in blocks of
flats, average dwelling size, floor area per person. Plus foreign-language speakers and the
monthly TEM unemployment rate per kunta, and housing-allowance households from Kela.

**Market** — old-flat price per m² and the sales count behind it (kerrostalo and rivitalo
separately, postal and kunta), free-market rent, ARA rent, rent change y/y and the
observation count, the discontinued postal-code rent series, unoccupied dwellings, total and
intermunicipal net migration, and dwellings completed / started / permitted per 1 000
dwellings. Yearly | Quarterly toggle on the publisher's own quarterly series.

**Taxes** — property tax on a permanent dwelling, on another dwelling, general (building),
general (land), an undeveloped building site, and the municipal income-tax rate.

**Safety** — reported penal-code offences, violence, property crime, criminal damage,
narcotics, dwelling burglary per 1 000 dwellings, and the y/y trend, with direction-aware
ranks and colours.

**Outlook** — Väestöennuste 2024: change 2026→2040 in per cent and in people, the five-year
change and rate, the 0–6, 7–15, 20–34 and 80+ bands, and the projected 20–34 share against
Finland's own. Observed solid, projected dashed, split at the last observed year. Helsingin
kaupunki's own projection by osa-alue is carried beside Tilastokeskus's for the city, with
the gap stated and never averaged.

**Osa-alue level** — nine indicators from Aluesarjat, area pages, and the breadcrumb
kunta → postinumero → osa-alue.

**Infrastructure** — a throttled, stamped StatFin PxWeb client; an Aluesarjat client; a
Verohallinto importer; a Kela importer; a calc engine that keeps suppression as null all the
way to the page; a live endpoint probe; and `scripts/verify.py`, which re-queries the
publishers and compares: **57 checks, 0 disagreements**.

### Notable decisions

- **Paavo is the backbone**, because it publishes the same definitions at kunta and postal
  level, so the two are directly comparable.
- **Lazy payloads.** The page carries the latest value of everything; history, detailed
  postal rings, monthly series and the osa-alue layer's geometry are fetched per kunta or on
  demand. `dist/index.html` is 2.4 MB with a hard 3 MB guard in the build.
- **° and ^** mark a value published for a coarser area than the row. A definition that
  differs between levels gets a different name, not the same name with a different meaning.

### Known gaps

No days-on-market or supply; no transaction-level prices; crime only at kunta level and
never quarterly; no comprehensive-school results; **no municipal construction data anywhere
in Finland** (maakunta only); postal-code rents frozen at 2025Q4; three incompatible
postal-code classification vintages; Paavo two years behind its release.

### Licence note

⚠ **Aluesarjat, the source of every osa-alue figure, allows non-commercial use only.** It is
not CC BY 4.0 like the rest of the dashboard. The restriction is labelled in the data, in
each osa-alue indicator's note and in the Sources view, and is an open item for the release
decision.

> **Corrected in v1.1 — this note was wrong.** Aluesarjat's own terms permit commercial use:
> "Tietoaineistoa voi käyttää sekä ei-kaupallisiin että kaupallisiin tarkoituksiin"
> (https://kaupunkitieto.hel.fi/fi/helsingin-tilastotietokannat/aluesarjat). The v1.0 text
> above is left standing because it is what v1.0 shipped; see the v1.1 entry.

### Not in this release

Test property, Analysis and Compare; climate risk; services; public buildings; infra
projects; schools; the buildings micro layer; energy certificates; zoning; the 1 km grid.
Their machinery is in `src/app.js`, dormant, for batch 2 (`docs/BUILD_PLAN_FI.md` §7).
National macro — Euribor, mortgage rates, bond yields, CPI, GDP, municipal finances — is out
of scope by decision, and the Danish market panel was removed rather than ported.
