# UI overhaul v2.0 — plan, decisions and progress

Branch `v2.0-ui`, cut from `main` (= live v1.1). **Do not push, merge or tag.**
A new session continues from here: read §Progress, then §Next, then the phase checklist.

---

## 0. The task, verbatim

> MASTER TASK — UI overhaul v2.0 of the Finland Macro Dashboard, one unattended overnight run. Branch v2.0-ui (checked out from main = live v1.1). Do not push, merge or tag.
>
> GROUND RULES
> 1. Data principle unchanged: official figures or plain arithmetic only; suppressed ≠ 0; not covered = "Not covered yet"; every figure keeps source, period, fetch date, verify link. This is a UI round: do not change data build scripts except where a bug below says so.
> 2. Reference: the Danish repo ~/Desktop/"Denmark dashboard, funny project"/am-dashboard-dk is READ-ONLY. If docs/UI_SPEC_v3.md (or ENG_BRIEF_v3.md) exists there or on any of its branches, read it: it is the detailed spec for the same UI overhaul — follow it wherever this prompt is silent, adapted to Finland (kunta / postinumero / osa-alue, EUR, fi-FI number format). If the Danish v3.0 code already exists on a branch, port its components rather than re-inventing them. This prompt wins where the two conflict.
> 3. Quality bar: consistency and zero glitches beat extra features — one picker, one period control, one study row, one export schema, one number format, no overlapping legends, no horizontal overflow, zero JS errors.
> 4. Never stop or ask; decide, log in docs/UI_PLAN.md, continue. Write docs/UI_PLAN.md first (this task verbatim + phase checklist) and keep it current after every commit so a new session can "Continue from docs/UI_PLAN.md". Use subagents for bulk work. Commit per phase (feat:/fix:/docs:). Before each commit: make validate && make test && make build clean + the Playwright spec below green for the phases done so far. Temporary servers on a random free port, always stopped.
>
> PHASE 1 — Navigation and routes
> Sidebar: exactly 4 items Map · Data · Charts · Test property, plus Export ▾ in the footer (replaces the single "Export data" button and its 4-line text). Data has 3 tabs: Areas (old Table) · Projects (old Pipeline) · Sources. Compare is removed entirely (no button "Compare with…" anywhere; #compare… redirects to the area page of a). Redirects so old links never break: #table/* → #data/areas/*, #pipeline → #data/projects, #sources → #data/sources, #analysis?a=… → #property?p=lat,lon[:label] (URL codec list-capable for later multi-pin, but v2.0 shows ONE property). Leaflet teardown registry: every map registered and removed before a view is replaced (fixes the live errors "Cannot read properties of undefined (reading 'lat')" in _animateZoom and "reading 'intersects'" in _updateCircle on #analysis).
>
> PHASE 2 — One toolbar on the Map
> Row 1 only: [unified search ▾] [Layers ▾] [Indicator ▾] [Period] — plus, when drilled into a kunta, one segmented level switch [Postal codes | Osa-alueet (148) | Buildings (23 935)] on the same row. Unified search accepts kunta / postinumero / osa-alue names and codes, addresses (existing DVV lookup), Google Maps links and "lat, lon"; a coordinate/address result opens #property?p=…; quick jumps Helsinki / Tampere / Turku / Oulu / Finland live at the top of the search dropdown (keyboard shortcuts H/T/U/O/F kept, camera only). The privacy sentence leaves the map (tooltip on search + on the Test property page). Row 2: indicator chips. REMOVE: the Climate risk button and the 1/100a sea · 1/1000a sea · 1/100a river · 1/1000a river pills; separate Infra / Public buildings / Services / Zoning / 1 km grid buttons (→ Layers ▾ with their sub-filters; floating legends become keys only, no ONLY/filter buttons). Full screen → top bar right. At 1366×768 the map top ≤ 200 px.
>
> PHASE 3 — Indicator picker + period control (shared everywhere)
> One IndicatorPicker component (button + popover: search, all groups, unit, ↓ lower-is-better, availability tag, "From the municipality" group on postal/osa-alue pages) used on Map, Area page, Data › Areas, Charts, Test property. Period control, one component, three modes by indicator: Year ▾ (history); Return period [1/100a | 1/1000a] for Climate indicators (sea and river stay separate indicators); static badge "Projection 2026→2040 · Tilastokeskus Väestöennuste 2024" for Outlook. Choosing a Climate indicator draws the SYKE flood zones for that return period automatically (zoom-gated, shown in the legend with its own hide toggle); choosing any other indicator removes them. Projections purple + dashed, climate blue, observed green; never mixed in one legend.
>
> PHASE 4 — Map area card (owner's request: less, and toggles)
> When a kunta is selected on the map the card shows only: name · maakunta · inhabitants · level count, the 5 headline figures in one row (Growth, Price, Rent, Unemp., Crime — clickable = select indicator), and actions [Open <kunta> page ›] [↗ Chart]. Everything else folds into toggles, closed by default, state in the URL: "Outlook 2040 ▸" (inside: Tilastokeskus and Helsingin kaupunki side by side, the "+104 297 residents" line and the two-projections note) and "Upcoming projects (n) ▸" (replaces the UPCOMING chip row). The whole card is collapsible (–) and remembers its state. Nothing else on the card.
>
> PHASE 5 — Area page (kunta / postinumero / osa-alue)
> Header → 5 clickable headline tiles → picker + period + chips → study row: chart panel left (~60 %) | draggable mini-map right (~40 %, scroll zoom, ⤢ full screen, Esc closes, legend inside), equal height → toggles (<details>, state in show=): Population outlook (open by default on kunta pages), All figures, Sub-areas (postal codes / osa-alueet). Remove the KEY FIGURES block with its 10 tabs and card grid. Postal-code and osa-alue pages: kunta-level values dimmed with the text "municipality figure" (tiles) / "muni" tag (tables), never a lone °. Chart panel modes: history line (area, parent, peer median, Finland), snapshot → distribution strip, outlook → observed solid + projected dashed purple, climate → bars per return period.
>
> PHASE 6 — Test property (#property?p=lat,lon[:label], one pin)
> Same study-row component as the area page anchored on the pin's finest area (osa-alue > postinumero > kunta, level tag shown). Header: kunta · postinumero · osa-alue · coordinates + [Open on map] [area ›] [OpenStreetMap ↗] [Copy link]. Always 5 headline tiles (Growth, Price, Rent, Unemp., Crime): use the pin's own level where published, otherwise the kunta value labelled "municipality figure" — never a grey filler slab (live bug: 00410 shows 2 tiles + an empty grey block). Mini-map draggable, ⤢ full screen, radius rings, Layers ▾ for infra / public buildings / services; public-building and infra legends stacked, never overlapping (live bug). Sections as <details>: Infrastructure nearby (open), Public buildings within ring (group identical name+use+distance ±20 m with a count), Schools, Climate, Area profile (all figures), Sources & as-of. Empty state (no p=): input focused + one example. Public-building markers use per-map panes/renderers (never the Macro map's layer).
>
> PHASE 7 — Export ▾ (one menu, sidebar footer + Data header)
> Items: This view (CSV) · All area data (long) · Projects · Test property · Sources catalogue. Long schema: level, code, name, parent_code, parent_name, maakunta, population, indicator, label, unit, period, period_type, value, value_type (actual|projection|inherited|derived), inherited_from, direction, source, table_id, source_url, as_of, fetched, licence. Projects in their own file, never mixed into indicator columns. Test property: property_label, lat, lon + long schema, plus nearby file (kind, name, type, status, distance_m, source, source_url). CSV UTF-8 BOM, ";" separator, "." decimal, no grouping. Assert unit/magnitude agreement at export (the Danish edition exported kDKK labels on raw values — check the EUR income fields here the same way).
>
> PHASE 8 — Number and label fixes found in the Chrome review of v1.1
> a) Units: price tiles read "5 225 EUR" → "5 225 EUR/m²"; rent "21,3 EUR" → "21,3 EUR/m²/month" everywhere (tiles, tables, legends, charts, export unit).
> b) "vs median" on rates and per-1 000 indicators is shown as a percent of the median, giving nonsense such as "+53 220,0 % VS MEDIAN" and "-367,9 % VS MEDIAN" (net migration on #area/kunta/091). Rule: for shares and rates show the difference in pp; for per-1 000 and levels show the absolute difference in the indicator's unit; never a percent of a median that can be near zero or negative.
> c) Outlook line "+104 297 residents (+12,1 %/yr)" on Helsinki: the /yr label is wrong for a 2026→2040 change. Show the total change % for the period, and if an annual rate is shown compute it as a compound annual rate and label it "≈ x % / yr (compound)". Also check the two headline outlook figures (+14,8 % and +16,9 %) use the same base year and say which.
> d) The period select reads "latest (2025 data)" even when indicators have different latest periods — show the active indicator's own latest period.
> e) One rank format everywhere: "#n of N" with N = areas that have a value (title attribute explains).
> f) Numbers fi-FI on screen (space thousands, comma decimal), signed changes always signed, pp for share changes.
>
> PHASE 9 — Responsive
> ≤ 1024 px: sidebar becomes a 52 px top bar with a ☰ drawer (Esc closes, focus returns); controls stack; chart and mini-map stack; tables scroll inside their card; legends collapse to a "Legend ▾" pill on mobile. No horizontal overflow at 1366×768, 1440×900, 1536×864 and 390×844 on #map, #map/091, #area/kunta/091, #area/postinumero/00100, #area/osa_alue/091010, #data/areas/kunta, #data/projects, #charts, #property?p=60.2448,24.8665.
>
> PHASE 10 — Tests, screenshots, wrap-up
> tests/ui_v2.spec (Playwright, headless Chromium): the 4-item sidebar; redirects (#table, #pipeline, #sources, #analysis, #compare); no text "Climate risk", "1/100a sea", "Compare", "KEY FIGURES" outside the right places; picker exists exactly once per view; climate indicator → return-period control + zones legend, non-climate → neither; map card has no UPCOMING chip row and its toggles work; property page has 5 tiles and no empty filler, mini-map drags (window.__maps), full screen works; legends pairwise non-overlapping inside the map; export headers match the schema; the unit and vs-median fixes (no "% VS MEDIAN" text on per-1 000 indicators); zero pageerror on every route above at every width; scrollWidth ≤ innerWidth. Capture docs/ui_v2/*.png of every route at 1440 and 390 for the morning review. Update README screenshots, CHANGELOG v2.0 draft, docs/UI_PLAN.md final. Print ≤ 40 lines: what shipped per phase, what was skipped and why, open ⚠, and a 10-point localhost review checklist. STOP — do not merge, tag or push.

---

## 1. Reference material read

- `~/Desktop/Denmark dashboard, funny project/am-dashboard-dk/docs/v3/UI_SPEC_v3.md` (69 KB) — the detailed
  spec for the same overhaul, incl. the owner amendments A1–A4, the `data-testid` contract (§10) and the
  acceptance criteria. Followed wherever this task is silent; **this task wins on conflict.**
- `docs/v3/PROGRESS.md` on branch `v3.0-ui` — the Danish P1–P3 build log. P1 map lifecycle, P2 nav/Data
  section/redirects, P3 picker/period. Its `src/route_core.js` and `src/picker_core.js` are **ported**
  (adapted to kunta / postinumero / osa_alue and to this repo's `S.view` ids), not re-invented.
- Danish P4–P10 do not exist yet, so phases 2 and 4–10 here are original work against the spec.

### Finland adaptations of the Danish spec
| Denmark | Finland |
|---|---|
| kommune / postnr / kvarter | kunta / postinumero / osa_alue |
| `#properties` (portfolio) | `#property?p=…`, **one** pin (amendment A2 + this task) |
| Data tabs: Areas·Projects·National·Sources | **3 tabs**: Areas · Projects · Sources (no national tab in FI) |
| Climate horizon Today/2070/2120 | **Return period** `1/100a | 1/1000a`, sea and river separate indicators |
| storm-surge zones (Kystdirektoratet) | SYKE flood-hazard WMS, zoom-gated |
| `da-DK`, DKK, kDKK bug | `fi-FI`, EUR, `EUR/m²` and `EUR/m²/month` unit bug |
| 5 nav items | **4**: Map · Data · Charts · Test property |

---

## 2. Decisions taken along the way

(Appended as they are made; the ones taken before coding started are D1–D8.)

- **D1 — Port, don't re-invent.** `src/route_core.js` and `src/picker_core.js` are new pure modules in
  this repo, node-tested, inlined by `scripts/build_dashboard.py` the way `testprop.js` already is.
  Everything else is written against this repo's own structures — the Danish `app.js` is a different
  file with different data shapes, so a textual port would be worse than a rewrite of the same idea.
- **D2 — Internal `S.view` ids are unchanged** (`makro`, `table`, `pipeline`, `sources`, `analysis`).
  Only the hash spelling, the labels and the navigation move. `route_core.js` is the only place that
  knows both spellings; `hashFor()` serialises canonical v2 hashes, `parseHash()` accepts either.
- **D3 — `hashFor()` is the one serialiser, `parseHash()` the one parser.** `parseHash()` ends with a
  canonical `replaceState`, so an old link redirects exactly once and every route round-trips.
- **D4 — Climate period is a *return period*, not a horizon.** Finland's climate indicators are SYKE
  flood-hazard shares at 1/100a and 1/1000a, and sea and river are separate indicators (different
  publishers' rasters). The period control therefore renders `[1/100a | 1/1000a]` and the URL key is
  `rp=`. Choosing a climate indicator turns the matching SYKE WMS layer on; leaving the family turns
  it off. The old `clim=` / `wms=` keys keep working as aliases.
- **D5 — Data has three tabs.** Finland has no "national series" dataset in the page payload, so the
  spec's fourth tab does not exist here. `#data/national` redirects to `#data/areas/kunta`.
- **D6 — The old `#analysis` view is rebuilt in place** as `#property`, rather than kept beside it:
  the task's Phase 6 replaces its content entirely, and keeping two would break "one study row".
  `#analysis?a=…&la=…` redirects; `AN.b` (the second pin / Compare) is deleted with Compare.
- **D7 — `window.__maps`** is the test hook for every map AC, kept in sync by the teardown registry.
- **D8 — Test runner.** `tests/ui_v2.spec.py` is a plain Playwright-python script (`make ui`), not
  pytest: the repo's other tests are `unittest` + `node --test`, and a third runner would need a new
  dependency. It starts its own server on a free ephemeral port and always stops it.

---

## 3. Phase checklist

Legend: ☐ not started · ◐ in progress · ☑ done and committed.

- ☑ **P1 Navigation and routes** — 4 nav items, Export ▾ footer, Data 3 tabs, Compare deleted,
  redirects (`#table/*`, `#pipeline`, `#sources`, `#analysis`, `#compare`), Leaflet teardown registry,
  `window.__maps`.
- ☐ **P2 One toolbar on the Map** — row 1 `[search ▾][Layers ▾][Indicator ▾][Period]` + level segment;
  unified search (names, codes, addresses, Google Maps links, `lat, lon`, quick jumps); row 2 chips;
  Climate button and return-period pills removed; Infra/Public/Services/Zoning/grid → Layers ▾;
  legends become keys only; Full screen → top bar; map top ≤ 200 px at 1366×768.
- ☐ **P3 IndicatorPicker + PeriodControl** — one component each, on Map / Area / Data › Areas /
  Charts / Test property; year · return period · projection badge; climate indicator ⇄ SYKE zones;
  projection purple dashed, climate blue, observed green.
- ☐ **P4 Map area card** — identity + 5 headline figures + two actions; `Outlook 2040 ▸` and
  `Upcoming projects (n) ▸` as toggles with URL state; whole card collapsible.
- ☐ **P5 Area page** — header → tiles → picker/period/chips → study row (chart | draggable mini-map,
  equal height) → `<details>` toggles in `show=`; KEY FIGURES block removed; inherited values labelled.
- ☐ **P6 Test property** — `#property?p=lat,lon[:label]`, the shared study row on the pin's finest
  area, always 5 tiles, no filler; draggable mini-map with ⤢; `<details>` sections; per-map panes.
- ☐ **P7 Export ▾** — one menu in the sidebar footer and the Data header; long schema; projects and
  nearby in their own files; UTF-8 BOM `;` CSV; unit/magnitude assertion.
- ☐ **P8 Number and label fixes** — EUR/m² and EUR/m²/month units; vs-median in pp or absolute, never
  % of a median; compound annual outlook rate; period label per indicator; `#n of N` everywhere; fi-FI.
- ☐ **P9 Responsive** — ≤ 1024 px top bar + drawer; stacking; table scroll; legend pill; no overflow
  at 1366×768, 1440×900, 1536×864, 390×844.
- ☐ **P10 Tests, screenshots, wrap-up** — `tests/ui_v2.spec.py` green, `docs/ui_v2/*.png` at 1440 and
  390, README screenshots, CHANGELOG v2.0 draft, this file final.

---

## 4. Gate before every commit

```
make validate          # StatFin metadata + a sampled link sweep   (network)
make test              # python unittest + node --test
make build             # raw -> processed -> dist/index.html, JS syntax-checked
make ui                # tests/ui_v2.spec.py, phases done so far   (own server, free port)
```
`make ui` starts `python3 -m http.server 0` on an ephemeral port in `dist/`, and stops it in a
`finally:` — never port 8080, which a sibling dashboard on this machine sometimes holds.

---

## 5. Progress

### P1 — navigation, routes, the Leaflet teardown registry ☑
Commit: `feat: v2.0 P1 — four destinations, the Data section, the v1.1 redirects and the map registry`
Gate: green — `make validate` ✓, `make test` 38 python + 38 node ✓, `make build` clean, `make ui` 10/10.

**Built**
1. **`src/route_core.js`** (IIFE → `window.ROUTE_CORE`, inlined as `{{ROUTE_JS}}`, 11 node tests in
   `tests/route.test.js`). `splitHash` / `buildHash` / `parseLatLon` / `propParse` / `propSerialise`
   (list-capable) / `toV2` (old → canonical, **idempotent**) / `toInternal` / `pathFor`. The table:
   `table/<lvl>`→`data/areas/<lvl>` · `pipeline`→`data/projects` · `sources`→`data/sources` ·
   `data`/`data/national`→`data/areas/kunta` · `analysis?a=&la=`→`property?p=lat,lon:label` ·
   `compare?a=<type>:<code>`→that area's page (→`map` if unparsable). `buildHash` leaves `, : / @ ;`
   unescaped so a link stays readable.
2. **Four nav items** — Map · Data · Charts · Test property, each `data-testid=nav-item`; the sidebar
   footer is **Export ▾** (This view · All area data · Projects · Sources catalogue) plus a build line,
   replacing the single button and its four lines of caption. Menu closes on Esc and on an outside click.
3. **Data = three tabs** (`dataTabs()`, `data-testid=data-tab`): Areas (old Table), Projects (old
   Pipeline), Sources. The internal view ids (`table`, `pipeline`, `sources`) are unchanged — only the
   hash, the labels and the breadcrumb moved. An empty **Fetched** cell now falls back to the build date
   with a `build` tag.
4. **Compare deleted** — `cmpGo`, `anCompare`, `anCmpCells/Table/Sources`, `anLocB`, `anCmpLink`,
   `UI.cmpOpen`, `AN.b`/`AN.labelB`, the three `data-cmp*` handlers and the "⇄ Compare with…" button.
5. **`hashFor()` / `parseHash()` rewritten** on top of `route_core`; `parseHash()` ends with a canonical
   `replaceState`, so a v1.1 link redirects exactly once and every route round-trips. New URL keys:
   `show=` (open `<details>`, all three views) and `card=0` (the map area card collapsed).
6. **Leaflet teardown registry** — `LF_MAPS` names the four map keys (`map`, `amap`, `anmap`, `pmap`)
   and their layer groups; `dropMap()` does `off(); stop(); remove()` and nulls the groups and draw
   caches; `dropMaps()` runs at the top of `render()`, before `#body` is replaced. `mapPanes(map)`
   creates the `srvpane`/`pubpane`/`climPane` panes and the three canvas renderers **per map**
   (`amOf(map)`); the app-wide `LF.canvas / srvCanvas / pubCanvas / anCanvas` are gone.
   `window.__maps` is the live list and the test hook.
7. **Two live bugs fixed on the way.**
   - `Cannot read properties of undefined (reading '_leaflet_pos')` on the Test property sheet: Leaflet
     ends a zoom animation from a `setTimeout` that `map.remove()` cannot cancel. Four one-line guards
     on `L.Map.prototype` (`_onZoomTransitionEnd`, `_move`, `_getMapPanePos`, `_getNewPixelOrigin`).
   - **`#area/postinumero/00100` took 18.3 s to render.** `V()` asks for a kunta's per-area file the
     moment it reads a postal code with no history, and a median over a postal-code page's peers reads
     all 3018 of them — so v1.1 re-rendered the page once per file that landed, 308 times. `pnoWant`
     now coalesces the re-render into one 220 ms tick: **0.77 s**.
8. **`tests/ui_v2.spec.py` + `make ui`** — the acceptance runner (own server on a free ephemeral port,
   stopped in a `finally:`). Ten P1 checks.

**Decisions added**
- **D9 — the Export menu ships four items in P1, five in P7.** *Test property (CSV)* needs the rebuilt
  property view (P6) and the long schema (P7); shipping a menu item that downloads nothing would be
  exactly the kind of glitch this round is meant to remove. P7 adds it and rewrites the four others'
  schema.
- **D10 — `AR.group` and `AR.tab` keep their `g=` / `t=` URL keys until P5** rebuilds the area page,
  so the interim commits do not regress the key-figures tabs.
- **D11 — the test harness answers off-machine requests with a 200, it does not abort them.** Aborting
  makes Leaflet re-request a tile for ever (44 retries of one tile in four seconds starved Playwright's
  own selector polling), and every abort raises a `console.error` that would count as a page error.
- **D12 — `goto()` in the spec adds a cache-busting `?n=`**: a `page.goto` that differs only in its
  fragment is a same-document navigation, and Chromium then never fires a load.

**Known issues / open**
- The map toolbar is still v1.1's: both search boxes, the Climate risk button, the four return-period
  pills and the separate Infra / Public buildings / Services / Zoning / grid buttons. **P2.**
- The area page still has the KEY FIGURES block and its group tabs. **P5.**
- The Test property sheet is still the v1.1 analysis sheet under a new route. **P6.**
- `exportCsv` / `exportAll` still carry v1.1 (and, in `exportAll`, some leftover Danish) column names
  and the file is named `macro-dashboard-dk_all_…`. **P7 rewrites both.**
- Horizontal overflow at 390 px is not yet asserted. **P9.**

## 6. Next

Start P2 — one toolbar on the Map.
