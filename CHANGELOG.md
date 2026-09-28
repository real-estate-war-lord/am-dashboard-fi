# Changelog

## v2.2 — readable at a glance, and presentable

Branch `v2.2-ui`, six phases (W1…W6). **No data source, figure or fetch changed**: as in v2.0 and
v2.1 this round is the interface. Where a number moved on screen it is because the page was reading
the wrong level for it (§ *Test property*) or printing it wrong (§ *Numbers and labels*).

Six new front-end files, each an IIFE exposing one global, inlined before `app.js`:
`src/scale_core.js` (one chart axis), `src/geom_core.js` (the point-in-polygon geometry),
`src/present.js` (present mode and the rasteriser), `src/w5_core.js` + `src/w5.js` (the Danish
SHOULD list) and `src/chartsvg.js` (the chart SVG builders, moved out of `app.js` to make room).

### Present mode

- **`present=1`, `▶ Present` in the top bar, or `P`** — on the Map, an area page, Test property and
  Charts. `Esc` leaves. The sidebar, the four toolbars and the chip rows go; the indicator, the
  period and the area path collapse into **one line in the top bar**; the headline figures grow a
  quarter; a mini map's legends come out from behind their pill and stay open; and a one-line
  **source footer** is pinned to the bottom of the window. Nothing that carries a figure is hidden —
  a check counts the tiles, the sections and the caveats with and without it and requires the three
  counts to match. Below 1025 px the pill stays and the footer is the last thing on the page.
- **A print sheet, A4 landscape** — `@page{size:A4 landscape}`, every control and popover gone, the
  legends unfolded, maps sized in millimetres, one view per page.
- **`⤓ PNG` on the study row** (area page and Test property): one 3 200 × 1 016 image with the
  chart, its key, its clipped-scale note, the mini map with its legend, a title, a sub-title and the
  source footer. Made out of the page, no library, nothing fetched; where the basemap tiles are
  cross-origin the polygons are drawn on the paper colour and the image says **· basemap omitted**.

### Maps and charts

- **The map card fills the window** — measured from the map's own top edge, floor 560 px,
  re-measured on resize, on every toolbar refresh and around full screen. The national view is
  fitted to the kunta polygons rather than to a hand-typed box.
- **A mini map's legends fold behind one `Legend ▾` pill at every width** (they were desktop-open,
  covering 40–60 % of a small map). The macro map keeps its legends open and its stack now fits
  60 % of the map instead of scrolling inside 72 %.
- **One chart axis for the whole build** (`src/scale_core.js`): ticks at 1 / 2 / 2,5 / 5 × 10ⁿ, zero
  always on a gridline where the range crosses it, the range read off the years every plotted series
  covers, a value outside it drawn on the edge with a ▲ / ▼ and named in a note under the chart, and
  the x axis starting at the first period anything is published for. The climate bars and the
  population outlook were folded into the same rule.
- **One title, not two** — the chart card's head is the area and the period (`Helsinki · 2011–2025`),
  not the indicator's name a second time under the picker that just said it.
- **The info strip names the layer that is drawn** — *municipalities drawn · zoom in for postal
  codes*, not the indicator's publication level.
- **A bar chart's canvas is as tall as its bars need** (W6) — a fixed 640 units left ~300 px of white
  under a two-area chart, on screen and in the PNG.
- **A chart's source line and its note stay on the canvas** (W6), each on a line of its own, clipped
  on a word with the full string in the element's `<title>`.

### Test property

- **The first screen** — the study row starts 265 px down at 1440 × 900, where it started at 496.
  The name, its area tags and the five actions share one line, the tiles sit directly under them,
  the explanatory sentence is an **ⓘ** beside the tags, and the toolbar card is the study row's own
  header. Every tablet and phone keeps the stacked header.
- **osa-alue → postal code → kunta, for every indicator.** A pin fell from its area straight to the
  kunta. On the reference pin (60,2448 / 24,8665) **Price** was Helsinki's 5 090 €/m² labelled
  "municipality figure" and is 00410 Malminkartano's own **2 280 €/m²** labelled "postal-code
  figure"; **Unemployment** was Helsinki's 12,1 % and is 00410's **15,2 %**. Rent and crime are
  still municipality figures, and `docs/v2_2/DECISIONS.md` says why that is the right answer.
- **Export ▾ in the property header opens on the screen** — it opened 340 px above the top of the
  page and 27 px past the right edge at 1536.

### The Danish SHOULD list

- **Pinned chips** — `+` pins the indicator that is showing, `×` unpins; the row is the reader's
  from the first pin, `localStorage` under `amfi.pins.v1`, max 12, never in the URL.
- **`Columns ▾` on Data › Areas** — indicator groups, not single columns, in the URL as
  `cols=Market,Taxes`. The sorted column is never hidden and **the CSV keeps every column**.
- **A sparkline column in the sub-areas table** — the last ten published years of the sorted
  indicator, each row on its own scale, a year the publisher did not publish breaking the line.
- **Keyboard shortcuts** — `/` focuses the search that is on screen, `g m` / `g d` / `g c` / `g p`
  go to Map, Data, Charts and Test property, `[` / `]` step the chip row, `?` lists them all and
  `Esc` closes the list. Every one is ignored while you are typing.
- **The public-building list groups building parts** of one thing into one row with the register's
  own `×n` count (name + category + type within 150 m; never on the address).
- **A Climate bar chart draws both return periods** per area, the rarer one in a lighter tint of the
  same colour, with no median tick — and the footer says why.
- **The drill is announced** — one `aria-live="polite"` region says *"Showing Helsinki, 84 postal
  codes"*, and says nothing on a zoom, because a zoom never changes the selection.

### Numbers, labels and the small fixes

- The build line reads one `APP_VERSION` — it had said `v2.0` a whole release after v2.1 shipped.
- A project sheet knows the areas it serves: 157 of the 169 projects now name at least one kunta,
  and the Municipalities column of Data › Projects is no longer empty on every row. A project with
  no published alignment says **"Not covered yet"** and frames **Finland**, not Jutland.
- A year never gets a thousands separator (`1 987 — 2 000` in the buildings legend).
- `Transport projects within 1.2 km` → `1,2 km`; registry text and colour are refreshed from
  `config/indicators.json` at page build time (nine presentation fields, never a value).
- `Oulun normaalikoulu` is in Oulu: `data/external/overrides/schools.csv`, applied before the
  point-in-polygon placement, with the replacement coordinate's own source printed on the sheet.
- The Housing-stock blue becomes a plum (it was within 6° of the Climate ramp).
- Data › Sources names its tables in the page's ink rather than the browser's blue (W6).
- A project label is drawn only where the map can show all of it, and the publisher's 28-character
  short label is marked as the cut it is (W6).

### Tests

- `tests/ui_v2.spec.py` **162 checks** (the 70 of v2.0, the v2.1 additions and 41 new in W1–W6),
  every route shot at 1440 and 390 into `docs/ui_v2/`, present mode among them.
- `node --test`: **132**, including `tests/scale.test.js`, `tests/geom.test.js`,
  `tests/present.test.js` and `tests/w5_core.test.js`.
- Budgets enforced by the gate: `src/app.js` ≤ 460 KB, `src/style.css` ≤ 165 KB,
  `dist/index.html` ≤ 3 300 000 B.

Phase-by-phase detail is in `docs/v2_2/PROGRESS.md`, every choice taken in the dark in
`docs/v2_2/DECISIONS.md`, the remaining issues in `docs/v2_2/QA.md`. v2.1's record is
`docs/v2_1/PROGRESS.md`.

## v2.0 — the UI overhaul (draft, not released)

Branch `v2.0-ui`, cut from `main` (= v1.1). Nothing merged, tagged or pushed. **No data source,
figure or build script changed**: this round is the interface. Where a number changed on screen it
is because v1.1 was printing it wrong (§ *Numbers and labels*).

### Navigation

- **Four destinations**: `Map · Data · Charts · Test property`. Table, Pipeline and Sources became
  the three tabs of **Data** (`#data/areas/<level>` · `#data/projects` · `#data/sources`), and
  **Compare is deleted** — a two-column sheet with no winner was a second way of reading what the
  area page already reads better.
- **Every v1.1 link still works.** `src/route_core.js` is the one place both spellings are known:
  `#table/*` → `#data/areas/*` · `#pipeline` → `#data/projects` · `#sources` → `#data/sources` ·
  `#analysis?a=…&la=…` → `#property?p=lat,lon:label` · `#compare?a=<type>:<code>&b=…` → the **a**
  side's area page. `toV2()` is idempotent and `parseHash()` rewrites the address bar once, so a
  link redirects exactly once and every route round-trips.
- **Export ▾** in the sidebar footer, in place of the single "Export data" button and its four
  lines of caption.

### The map

- **One toolbar row**: `[search ▾] [level switch] [Layers ▾] [Indicator ▾] [Period]`, with the
  indicator chips under it. At 1366×768 the map now starts **≤ 200 px** down the page (was 246) and
  is at least 480 px tall.
- **One search box** for four kinds of answer: a camera jump (Helsinki · Tampere · Turku · Oulu ·
  Finland, at the top of its dropdown — `H/T/U/O/F` unchanged), an area by name or code, a
  coordinate or a Google Maps link, and a street address through the DVV register. The last two open
  the Test property page. The privacy sentence left the map for the box's own tooltip.
- **Layers ▾** replaces the Infra projects / Public buildings / Services / Zoning / 1 km grid
  buttons and the Climate-risk segment with its four return-period pills, and it holds the
  sub-filters that used to live inside the floating legend cards. **A legend is a key now**: colour,
  label, source, a fold control, nothing to filter.
- **The area card is identity, five figures, two buttons and two toggles.** `Outlook 2040` and
  `Upcoming projects (n)` are `<details>` whose state is in the URL, and the whole card folds.

### One picker, one period control, one study row

- **`IndicatorPicker`** on the Map, the area page, Data › Areas, Charts and Test property: search,
  every group, the unit, `↓ lower is better`, an availability tag, and a **From the municipality**
  group on postal-code and osa-alue pages. Full keyboard model.
- **`PeriodControl`** is a function of the indicator, in four shapes: a year select, the
  **return-period switch `[1/100a | 1/1000a]`** for a flood indicator, the
  `Projection 2026→2040 · Tilastokeskus Väestöennuste 2024` badge for an Outlook one, or the as-of
  for something published once. A year select next to a 2040 figure read as an actual.
- **Choosing a Climate indicator draws SYKE's own flood zones** for that return period, and choosing
  anything else removes them; the zones and the figure are the same measurement seen two ways. The
  reader's hide toggle is `zones=0`.
- **Three families, three hues**: every projection purple, every climate figure blue, observed
  green, and the legend says which it is reading. They are never mixed in one legend.
- **The area page is one study row** — chart panel beside a draggable mini map with `⤢` full screen
  — with the toggles under it. The KEY FIGURES block (10 tabs over ~60 cards) is gone.
- **Test property** is the same study row anchored on the pin's finest published area, with the
  sections as `<details>` and the public-building rows grouped when the register publishes one line
  per building part.

### Export

One menu, five files, one schema. `level, code, name, parent_code, parent_name, maakunta,
population, indicator, label, unit, period, period_type, value, value_type, inherited_from,
direction, source, table_id, source_url, as_of, fetched, licence` — 168 k rows, **every one with a
source, a fetch date and a licence**, and an inherited figure carried as `value_type=inherited` with
`inherited_from` set. Projects and the Test property's surroundings have their own files. UTF-8 with
a BOM and `;` for Excel, `.` decimals and no grouping for a machine; the exporter refuses to let a
unit disagree with its magnitude.

### Numbers and labels (the Chrome review of v1.1)

- **Units on the number**: a price tile read `5 225 EUR` and a monthly rent `21,3 EUR` — a total
  price and a total rent. They read `5 225 EUR/m²` and `21,3 EUR/m²/month` everywhere.
- **"vs median" is a difference**, in percentage points for a share or a rate and in the indicator's
  own unit otherwise. v1.1 divided by the median, so net migration on `#area/kunta/091` read
  `+53 220,0 % VS MEDIAN` and intermunicipal net migration `-367,9 %`.
- **The outlook line** read `+104 297 residents (+12,1 %/yr)`. That bracket was `fc_pop_rate_5y` —
  residents per 1 000 per year over the **first five** years — beside a fourteen-year change. It now
  reads `+104 297 residents · +14,8 % over 14 years · ≈ +1,0 % / yr (compound)`, and the card says
  that both headline projections share the base year 2026.
- **One rank format**, `#n of N`, whose title says N counts the areas with a published figure for
  that indicator.
- **The lone `°` is gone.** An inherited figure is dimmed and tagged `muni` (`municipality figure`
  on a tile); a map popup says *From the kunta*; an exported chart says *(kunta)*.
- The period option names the active indicator's own latest period, never a global "latest (2025)".

### Bugs fixed on the way

- `Cannot read properties of undefined (reading '_leaflet_pos')` on the Test property sheet —
  Leaflet ends a zoom animation from a `setTimeout` that `map.remove()` cannot cancel. A teardown
  registry drops every map before `#body` is replaced, panes and canvas renderers are per map, and
  four guards on `L.Map.prototype` catch the rest.
- **`#area/postinumero/00100` took 18,3 s to render.** `V()` asks for a kunta's per-area file the
  moment it reads a postal code with no history, and a median over that page's peers reads all
  3 018 of them — so the page re-rendered once per file, 308 times. Coalesced: **0,77 s**.
- **`#property` on 00410 drew two tiles and an empty grey block.** An osa-alue carried the short
  indicator list although `eVal` already inherits, and the five-column grid's background showed
  through. Always five tiles, the inherited ones labelled.
- **Three legends drew on top of each other** on the Test property map, and the feature stack grew
  into the indicator legend on the big one. One scrollable column, folded to titles.
- The **Infra layer threw** on every project whose alignment the publisher has not drawn, and
  `geomStats()` threw on the same projects in the export. Both null-safe.
- Every map with a marker asked twice for Leaflet default-icon images the build does not ship.
- The sidebar's own Export menu was clipped by the scrolling sidebar and opened into nothing.
- "Upcoming projects" was empty on every map card unless the reader had switched the Infra layer on
  first — the per-area index rides in `infra.json`, not in the page.
- A headline figure on the map card could not be selected while the map was in osa-alue mode.

### Responsive

No horizontal overflow on any route at 1366×768, 1440×900, 1536×864 or 390×844. Below 1024 px the
sidebar is a 52 px top bar with a ☰ drawer that Esc closes; below 700 px the chips and the Data tabs
scroll sideways, the study row stacks, tables scroll inside their card and the map legends collapse
behind one `Legend ▾` pill.

### Tests

`tests/ui_v2.spec.py` (`make ui`) — 70 Playwright checks over ten phases, its own server on a free
ephemeral port. `tests/route.test.js` (11) and `tests/picker.test.js` (10) cover the two pure
modules. Screenshots of every route at 1440 px and 390 px in `docs/ui_v2/` (`make ui SHOTS=1`).


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
