# v2.1 — Parity audit: Danish v3.0 → Finland v2.0

**Written by phase V1 (2026-09-25).** This is the gap list every later phase works from. One row per
Danish behaviour, component or acceptance criterion, read against what this repo does **today on
`v2.1-ui` (= v2.0, tag `v2.0`)**.

## Method

- Danish side: `docs/v2_1/ref/UI_SPEC_v3.md` (**owner amendments A1–A4 at the top override the rest**),
  `ref/UI_V3.md` (routes, keys, components as built), `ref/QA.md` (the P9 fresh-eyes pass, Q1–Q14 + O1–O10),
  `ref/DK_P10.md` (the owner's four review fixes — they apply here too), and the code in `ref/dk_src/`.
- Finnish side: `docs/UI_PLAN.md` (how v2.0 was built, P1–P10 + decisions D1–D16), `src/app.js`,
  `src/route_core.js`, `src/picker_core.js`, `src/style.css`, the 70 checks in `tests/ui_v2.spec.py`,
  and the screenshots in `docs/ui_v2/` (`./overnight.sh gate V1`, run at the top of this phase).

### Finland adaptations applied throughout

| Denmark | Finland |
|---|---|
| kommune · postnr · kvarter | kunta · postinumero · osa_alue |
| DKK, `kDKK`, `da-DK` | EUR, `EUR/m²`, `EUR/m²/month`, `fi-FI` |
| Copenhagen region (quarters) | Helsinki region (osa-alueet) |
| Climate horizons Today · 2070 · 2120 | **SYKE return periods 1/100a · 1/1000a**, sea and river separate indicators |
| storm-surge zones (Kystdirektoratet) | SYKE flood-hazard WMS, zoom-gated |
| Data tabs: Areas · Projects · **National series** · Sources | **3 tabs**: Areas · Projects · Sources |
| 5 nav items (amended to 4) | 4: Map · Data · Charts · Test property |

### How to read a row

`FI status`: **done** (parity, with evidence) · **partial** (present but short of the DK behaviour) ·
**missing** · **n/a** (cannot or must not exist in Finland).
`Pri`: **MUST** = must be true at v2.1 release · **SHOULD** = do it if the phase has room ·
**LATER** = listed at the bottom, not built this round.
`Phase`: where the gap is fixed. V2 is fixed (colour ramps); V3 map; V4 test property; V5 area page,
sheets, Data, Export; V6 responsive, numbers, accessibility, states; V7 QA and docs. A done row carries
`—` and its existing check id as evidence; later phases must not weaken it.

---

## 1. Navigation, routes and redirects (spec §3.1, UI_V3 §2, AC-D1/D2/U1)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| NAV1 | Sidebar = 4 items `Map · Data · Charts · Test property` (amendments A1, A3) | done | `src/app.js:601` `VIEWS`, `:606` `NAV_GROUPS`; check `P1-nav-4` | — | MUST |
| NAV2 | Two nav groups (Market intelligence / Analysis), footer `Export ▾` + build line | done | `renderNav()` `src/app.js:624`; screenshot `docs/ui_v2/map_1440.png` | — | MUST |
| NAV3 | Compare deleted everywhere; `#compare?a=…&b=…` → area page of `a` (`#map` if unparsable) | done | `route_core.js` `toV2`; checks `P1-no-compare`, `P1-redirects` | — | MUST |
| NAV4 | Redirects `#table/*`, `#pipeline`, `#sources`, `#data`, `#analysis?a=&la=` | done | `route_core.js` alias table; check `P1-redirects` | — | MUST |
| NAV5 | `#market` → Data › National series | n/a | Finland has no national-series tab (UI_PLAN D5); `#data/national` → `#data/areas/kunta` | — | n/a |
| NAV6 | `#map?…&infra=1&public=1&services=1` → canonical `lay=infra,public,services` | **done (V3)** | `mapLayerList()` `src/app.js:344`; `hashFor()` writes one `lay=` key, `parseHash()` reads one; `ROUTE_CORE.layerFlags()` converts the four old flags (incl. `micro=1` → `buildings`); `wms=`/`zones=0` stay value keys — see DECISIONS V3; checks `V3-map-lay-key`, `route.test.js` | — | MUST |
| NAV7 | `#area/…?t=bbr\|ind\|sub` (+ `g=`) → `show=figures\|sub` so v1.1 links still open the right section | **done (V3)** | `ROUTE_CORE.areaTabs()` in the alias table; check `V3-area-tab-alias` | — | SHOULD |
| NAV8 | `hashFor()` the only serialiser, `parseHash()` the only parser, one canonical `replaceState`, idempotent (AC-U1) | done | `src/app.js:498`, `:537`; checks `P1-hash-roundtrip`, `P10-hash-stable-everywhere` | — | MUST |
| NAV9 | Internal view ids unchanged; nav highlight for non-destination views (`NAV_OF`) | done | `src/app.js:609` | — | MUST |

## 2. IndicatorPicker (spec §4.2, AC-I1–I6)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| PICK1 | One component on Map, Area, Data › Areas, Charts, Test property (AC-I1) | done | `indPicker(target)` `src/app.js:1049`; checks `P3-picker-everywhere`, `P10-picker-once` | — | MUST |
| PICK2 | Popover: search box focused, ≥ 12 `[data-group]` headers, one row per indicator (AC-I2) | done | `indPickerBody()` `:1059`; `PICKER_CORE.GROUP_ORDER`; check `P3-picker-popover` | — | MUST |
| PICK3 | Search filters label/short/group/unit; ↑/↓ moves, Enter selects, Esc closes and returns focus (AC-I3, I6) | done | `src/app.js:835-845` keydown, `PC.step`; check `P3-picker-popover` | — | MUST |
| PICK4 | Row shows label, unit, `↓ lower is better`, availability tag (`2011–` · `muni` · `snapshot`) | done | `indPickerBody()`; `PICKER_CORE.availTag` | — | MUST |
| PICK5 | Group headers for Outlook / Climate carry a `Projection` / return-period pill | done | `PICKER_CORE.GROUP_PILL`; check `P3-period-modes` | — | MUST |
| PICK6 | `From the municipality` group with `muni` tag on postinumero / osa-alue pages (AC-I5) | done | `picker_core.js:22` `GROUP_INHERITED`; check `P3-inherited-group` | — | MUST |
| PICK7 | Button shows a level tag when the value is not native to the page level | done | `indPicker()` `:1055` `tag-muni municipality` | — | MUST |
| PICK8 | Selecting re-renders only the dependent parts — **no full page rebuild** (AC-P4) | **done (V5)** | `indSet()` ends in `syncHash()` + `areaRefresh()` / `tpRefresh()` on the area page and the property, and in `go(hashFor())` everywhere else (DECISIONS V5); `arMapInit()` split into init + `arMapPaint()`, `anMapPaint()` extracted likewise, so the Leaflet map is re-painted, never rebuilt; checks `V5-area-refresh-in-place`, `V5-property-refresh-in-place`, `V5-area-fullscreen-survives` | — | MUST |
| PICK9 | Chips row = picker short form, active one filled, never empty (AC-I4) | done | `indChips()` `:1118`; check `P3-chips` | — | MUST |
| PICK10 | Pinned chips (`+`, localStorage, max 12) | missing | SHOULD in DK §9, deferred there too (`ref/QA.md` "Deferred") | — | LATER |
| PICK11 | Picker on the Test property offers the pin's finest level first, then inherited groups (DK P10 §4) | **done (V4)** | `pickCtx()` takes `anEntity()` — `tpEntity()` dressed as an area-page entity — so the property gets `e.inds` and the area page's own `inherits()`; `curInds()` got the same branch so the hash guard cannot reset what the picker just offered (DECISIONS V4); check `V4-property-picker-groups` | — | MUST |

## 3. PeriodControl (spec §4.3, AC-T1/T2)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| PER1 | One control, mode chosen by the indicator; never two at once (AC-T1) | done | `periodControl()` `src/app.js:1135`; check `P3-period-modes` | — | MUST |
| PER2 | `mode=year`: select labelled with the **active indicator's own** latest period | done | `:1135`, `asofShortOf()` `:1163`; check `P8-period-label` | — | MUST |
| PER3 | `mode=horizon` Today/2070/2120 → **Finland: return period `[1/100a \| 1/1000a]`** (AC-T2) | done (adapted) | `period-rp`; UI_PLAN D13 — the return period swaps `ind=`, there is no `rp=` key; check `P3-period-modes` | — | MUST |
| PER4 | `mode=projection`: static badge `Projection 2026→2040 · Tilastokeskus Väestöennuste 2024` | done | `PICKER_CORE.projBadge`; check `P3-period-modes` | — | MUST |
| PER5 | Leaving a family drops its URL key (`y` / `hz`) | done (adapted) | `indSet()` resets `MK.year` to latest; `clim=` derived, never written (D14) | — | MUST |
| PER6 | The climate **sheet** header uses the shared control (`periodHz(where)`, AC-SH2) | n/a | Finland has no `#climate/<kunta>` sheet — see SHEET5 | — | n/a |

## 4. Layers ▾ (spec §4.4, DK P10 §3, AC-L1–L3)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| LAY1 | One `Layers ▾` button with a count badge replaces the per-layer toolbar buttons (AC-L1) | done | `layersBtn()` `src/app.js:1475`; check `P2-layers-menu`, `P2-one-row` | — | MUST |
| LAY2 | Every feature layer has exactly one switch, with its sub-filters inside the menu | done (map) | `layersMenu()` `:1486`; check `P2-layers-menu`, `P2-legends-are-keys` | — | MUST |
| LAY3 | Context section: flood zones row present only while a Climate indicator is active; hiding writes `zones=0` (AC-L3) | done | `layersMenu()`, `hashFor()` `:505`; check `P3-climate-zones` | — | MUST |
| LAY4 | Menu state in `lay=` (AC-L2) | **done (V3)** | one key on both routes; the map's names are the menu's own `data-layer` values. See NAV6; check `V3-map-lay-key` | — | MUST |
| LAY5 | Menu closes on Esc / outside click, `role=dialog`, `aria-expanded` | done | `layersClose()` `:1529`, keydown `:838`, `:1480` | — | MUST |
| LAY6 | **Test property has the same menu** (`TP_LAYERS`, DK P10 §2/§3) | **done (V4)** | `tpMapTools()` is **deleted**; `layersBtn()` is on the property toolbar and `layersMenu()` branches to `anLayersMenu()` (`src/app.js`), with the radius chips and the zones row in it; check `V4-property-layers-menu` | — | MUST |
| LAY7 | Every drawn layer is switchable and the async loader never re-adds a layer that is off (DK P10 §3) | **done (V4)** | every overlay — infra, public, services, zones, buildings, rings — is drawn in `anMapOverlays()` from `ANL`/`MK.clim` alone, and `pubLoad`/`srvLoad`/`loadMicro`/`infraLoad` all land back in that one function; checks `V4-property-layer-off-sticks`, `V4-property-services` | — | MUST |
| LAY8 | State survives a re-render and a reload | **done (V4)** | `anParseLayers()` reads five names now (`rings` joined them — see DECISIONS V4), `hashFor()` writes the same five plus `srv=` and `zones=0`; check `V4-property-layer-off-sticks` reloads the hash it produced | — | MUST |

## 5. Unified search and the map pin (spec §5.1, **DK P10 §1**, AC-M1–M3)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| SRCH1 | One combobox: area names and codes, addresses, Google Maps links, `lat, lon`; quick jumps at the top of the dropdown | done | `mapSearch()` `src/app.js:1221`, `msRows()` `:1193`; checks `P2-search-jumps`, `P2-search-area` | — | MUST |
| SRCH2 | Privacy sentence off the map, on the search tooltip and the Test property page | done | check `P2-privacy-off-map` | — | MUST |
| SRCH3 | **A pasted link / coordinate drops a pin and stays on `#map`** (pan, zoom ≈ 13, radius rings) | **done (V3)** | `msPick()` no longer sets `TP.toProp` (the flag is deleted); a coordinate, a Google Maps link and an address all reach `tpDrop()`'s macro branch, which drills to the pin's kunta with `pin=`/`pl=`/`rad=1000` and `tpLayers()` does `setView(pin, 13)`; check `V3-pin-stays-on-map` | — | MUST |
| SRCH4 | Pin card near the toolbar (`pin-card`): label, coordinates, osa-alue › postinumero › kunta, `View test property ›` (`pin-open`) and `×` | **done (V3)** | `pinCard()` `src/app.js`, rendered into `#mkpin` between the info strip and the map; checks `V3-pin-stays-on-map`, `V3-pin-removable` | — | MUST |
| SRCH5 | The coord row reads "Drop a pin here"; `data-testid=search-coord` kept | **done (V3)** | `msRows()` / `msHtml()`; check `V3-pin-stays-on-map` | — | MUST |
| SRCH6 | The Test property's own paste box keeps replacing the pin in place | done | check `P6-paste-google-link` | — | MUST |
| SRCH7 | The pin card never overlaps the toolbar or the legend stack at 1440 / 1366 / 390 | **done (V3)** | the card is a block in the flow, not a float (DECISIONS V3); checks `V3-pin-card-clear-1440` / `-1366` / `-390` | — | MUST |
| SRCH8 | The search input is wide enough for its placeholder | **done (V3)** | the cause was specificity: `#mapcard .tools>*{flex:0 0 auto}` outranked `.msearch`'s own `flex`, so the box never grew past an input's intrinsic ~200 px. One rule, `#mapcard .tools>.msearch{flex:1 1 200px}` with a 470 px cap (the basis stays 200 px so the 1366 toolbar does not wrap and break `P2-map-top-1366`), plus a shorter placeholder; check `V3-search-fits` measures the placeholder in the input's own font | — | SHOULD |

## 6. Legends (spec §4.5, AC-LG1, DK Q1/Q10)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| LEG1 | Legends are keys only — every filter button moved into Layers ▾ | done | check `P2-legends-are-keys` | — | MUST |
| LEG2 | Legends stack in one column, never overlap, never leave the map (AC-LG1) | done | `.maplegs` `src/style.css:1461`; checks `P10-legends-inside-map`, `P6-legends-stack` | — | MUST |
| LEG3 | The stack never exceeds the map; the oldest layer legend folds to its title | done | `LEG_FOLD` / `mmFoldable()` `src/app.js:991-1004`; check `P10-legends-inside-map` | — | MUST |
| LEG4 | The stack must not cover Leaflet's attribution (licence condition — DK Q1) | done / n/a | FI's stack is anchored top-right (`src/style.css:1461`), DK's was bottom-right; `docs/ui_v2/map_1440.png` shows the credit clear | — | MUST |
| LEG5 | On a phone the legends fold behind one `Legend ▾` pill | **done (V6 for the last width)** | `legendPill()`, `src/style.css`; the pill sat **on top of Leaflet's attribution** at 390 (`docs/ui_v2/map_390.png`, flagged since V2) because the credit wraps to two full-width lines there. Pill and open stack moved to the map's top-right corner at ≤ 1024, where nothing else lives; check `V6-legend-pill-clear-390` asserts it on the macro map and both mini maps, opened and closed (DK Q1) | — | MUST |
| LEG6 | Indicator legend carries title, unit, 5 bins with values, `no data`, level footer, and the lower-is-better note | done | `legendHtml()` `src/app.js:962`; `docs/ui_v2/map_1440.png` | — | MUST |
| LEG7 | Legend for a **signed** indicator shows fixed breaks centred on zero, red below / green above | **done (V2)** | was five greens (`> +0,3 %` … `≤ −1,6 %`, zero invisible); now `legendHtml()` `src/app.js:975` renders `RAMP_CORE.labels()` with a `.lgzero` rule on the zero line and the footer "fixed breaks, centred on zero"; checks `V2-signed-legend`, `V2-signed-lower-better` | — | MUST |

## 7. Map view and the map area card (spec §5.1, AC-M1/M4/M9, task P4)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| MAP1 | Toolbar row 1 = `search · Layers ▾ · Indicator ▾ · Period` and nothing else (AC-M1) | done | `mkTools()` `src/app.js:1569`; check `P2-one-row` | — | MUST |
| MAP2 | Level segment on row 1 when drilled (postal codes / osa-alueet / buildings) | done | `levelSeg()` `:1553`; check `P2-one-row` | — | MUST |
| MAP3 | Row 2 = chips; info strip with label, level tag, unit, as-of, `ⓘ details` | done | `mkRefreshStrip()` `:1573`, `indExplain()` `:1257`; `docs/ui_v2/map_1440.png` | — | MUST |
| MAP4 | Full screen is a top-bar action, not a toolbar button | done | `renderTop()` `:668`; check `P2-fullscreen-topbar` | — | MUST |
| MAP5 | At 1366×768 the map starts ≤ 200 px down and is ≥ 480 px tall (AC-S3) | done | check `P2-map-top-1366` | — | MUST |
| MAP6 | Projection indicator: purple legend + "Projection" in the info strip (AC-M4) | done | `FAMILY_HUE` `:909`; check `P3-family-ramps` | — | MUST |
| MAP7 | **Zooming never changes the selection** (AC-M9) | **done (V3)** | the macro map's `zoomend` rebuilds polygons only when the display level changes and never touches `MK.muni` or the hash path; check `V3-zoom-keeps-selection` drives `setZoom(12/9/11)` on `window.__maps[0]` | — | MUST |
| MAP8 | Area card: identity, 5 clickable headline figures, two actions, two toggles, whole card folds | done | `vMakro()`/card code; checks `P4-card-contents`, `P4-card-toggles`, `P4-card-fold`, `P4-card-tiles-select` | — | MUST |
| MAP9 | Clicking an area opens a popup with headline figures and "Open page ›" | done | `lfPopup()` `:2718` | — | MUST |

## 8. Area page and the study row (spec §5.2, AC-P1–P6, H1/H2, E2)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| AREA1 | No KEY FIGURES block, no separate Trend / Neighbours cards (AC-P1) | done | check `P5-no-key-figures` | — | MUST |
| AREA2 | `study-row` = `chart-panel` + `minimap`, siblings, ~60/40, equal height, panel left (AC-P1) | done | `studyRow()` `src/app.js:2278`; check `P5-study-row` | — | MUST |
| AREA3 | Toggles are `<details>` with state in `show=`; Population outlook open on kunta pages only (AC-P2) | done | `showSec()` `:1351`, `AR.showSet`; check `P5-toggles` | — | MUST |
| AREA4 | **Chip / tile change updates the study row in place** — scroll, mini-map zoom and full screen survive (AC-P4) | **done (V5)** | see PICK8. `vArea()` renders `#artop` · study row · `#arsecs`; `areaRefresh()` repaints the first and the third and re-paints the map. Full screen survives **and is usable**: the `⤢` overlay got DK's own `.mm-chips` row, or the only indicator control would sit underneath it; checks `V5-area-refresh-in-place`, `V5-area-fullscreen-survives` | — | MUST |
| AREA5 | All figures table: active row highlighted and scrolled into view; row click selects the indicator (AC-P6) | **done (V5)** | the `toggle` handler scrolls `tr.hi` into view with `block: nearest` when `figures` opens — DK's own rule (`ref/dk_src/app.js:680`); check `V5-area-active-row` | — | SHOULD |
| AREA6 | Sub-areas table (postal codes / osa-alueet) | done | `areaSubTable()` `:2157`; check `P5-toggles` | — | MUST |
| AREA7 | Sub-areas sparkline column | missing | SHOULD in DK §9, deferred there too | — | LATER |
| AREA8 | At 390 the panel stacks above the mini map, each ≥ 300 px, no overflow (AC-P5) | done | check `P9-stacks`, `P9-no-overflow-390`; `docs/ui_v2/area_kunta_390.png` | — | MUST |
| AREA9 | At 1366×768 the study row starts inside the first screen (AC-R2) | **done (V6)** | was inferred from two other checks' shell metrics; check `V6-study-row-first-screen` now measures the row's own top at 1366×768 on the kunta page, the postinumero page and the property | — | SHOULD |
| AREA10 | Osa-alue pages keep the safety-survey block and the two-forecast note | done (FI-specific) | `kkCard()` `:2336`, `osaFcCaveat()` `:1427` | — | MUST |

## 9. Chart panel modes (spec §5.2, AC-P3, E2)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| PANEL1 | **History**: headline row + line chart (area, parent, peer median, national) with sources in the footer | done | `chartPanel()` `src/app.js:2257`, `multiLine()` `:2029`; check `P5-panel-modes` | — | MUST |
| PANEL2 | **Snapshot**: `state-nohistory` + distribution strip with peers as ticks (AC-E2) | done | `distStrip()` `:2207`; check `P5-panel-modes` | — | MUST |
| PANEL3 | **Outlook**: observed solid → projected dashed purple | done | `popOutlookChart()` `:2054`, `PROJ_COLOR` `:2052`; check `P5-panel-modes` | — | MUST |
| PANEL4 | **Climate**: bars per horizon → **Finland: per return period**, peers' median as a tick (AC-P3) | done (adapted) | `climBars()` `:2228`; check `P5-panel-modes` | — | MUST |
| PANEL5 | Every mode carries the same head: value, Δ y/y, `#n of N`, vs median, inherited / projection tags | done | `panelHead()` `:2193`; checks `P5-vs-median`, `P8-one-rank-format` | — | MUST |
| PANEL6 | `Climate sheet ›` button from a Climate indicator | n/a | no climate sheet in FI — see SHEET5 | — | n/a |

## 10. Headline tiles (spec §4.7, AC-H1/H2)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| TILE1 | Five tiles, clickable, `.on` for the active indicator (AC-H2) | done | `headlineHtml()` `src/app.js:2019`; checks `P4-card-tiles-select`, `P6-five-tiles` | — | MUST |
| TILE2 | Inherited tiles dimmed with "municipality figure", never a lone `°` (AC-H1) | done | `tileStats()` `:2000`; checks `P5-inherited-labelled`, `P8-no-lone-degree` | — | MUST |
| TILE3 | Projection tiles carry a `Projection` pill | done | `projValueHtml` path, `docs/ui_v2/area_kunta_390.png` (outlook card) | — | MUST |
| TILE4 | No grey filler cell when a row is short (DK Q4 / AC-SH1) | **done (V6)** | check `V6-tiles-not-clipped` re-reads every `[data-testid=tiles]` row at 1536 · 1440 · 1366 · **1180** · 820 · 390: no row carries a background of its own (which is what used to show through as a slab) and no cell is empty | — | MUST |
| TILE5 | A tile's figure and unit sit on one baseline and are not clipped | **done (V6)** | the cause was one unbreakable 12-character token: `EUR/m²/month` at 26 px is wider than a two-column tile, so it ran under the next tile and was painted over. Three parts to the fix: `tileValueHtml()` sets the **money denominator** at `.64em` on the figure's own baseline (which is how a unit is normally set, and is what actually makes it fit), the figure type is fluid below the tile grid's own breakpoints (23 px ≤ 1180, 20 px ≤ 820), and `overflow-wrap:anywhere` is the floor for whatever unit a later build adds. Check `V6-tiles-not-clipped` measures the **text** with a `Range`, not the `<b>`'s border box, which is what let the clipping pass unnoticed for two phases | — | MUST |

## 11. MiniMap (spec §4.6, AC-MM1–MM3)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| MM1 | `dragging:true`, scroll zoom, `+ −`, legend inside (AC-MM1) | done | `arMapInit()` `src/app.js:2359`; check `P5-minimap-drag` | — | MUST |
| MM2 | `⤢` full screen as a fixed overlay, Esc closes, `invalidateSize()` after each transition (AC-MM2) | done | `miniFull()` / `miniFullClose()` `:3907`; check `P5-minimap-drag` | — | MUST |
| MM3 | Teardown registry: every Leaflet map registered and removed before `#main` is replaced; `window.__maps` (AC-MM3) | done | `LF_MAPS` `:381`, `dropMaps()` `:400`; checks `P1-maps-registry`, `P1-maps-no-errors` | — | MUST |
| MM4 | Clicking a neighbour opens its page; the selected area is outlined | done | `arMapInit()`; `docs/ui_v2/area_kunta_390.png` | — | MUST |
| MM5 | The mini map keeps its zoom when the indicator changes | **done (V5)** | `arMapPaint(fit)` — `fit` is only true when the map is first built or the sub-level changes, so a chip click repaints the polygons and leaves the camera alone; checks `V5-area-refresh-in-place`, `V5-property-refresh-in-place` read the centre and zoom off the live Leaflet instance before and after | — | MUST |
| MM6 | Flood zones drawn in the mini map when a Climate indicator is active | **done (V4 property, V5 area)** | the property map draws its own SYKE tile layer in its own `climPane` inside `anMapOverlays()` (`LF.anClimL`); the area map has `arMapZones()` / `LF.amClimL`, same shape, with a folded `legend-zones` card in `AR_LEGENDS`. `climLayers()` is untouched and stays the macro map's. On the area route the zones follow `ind=` and have no switch — the toolbar is `Indicator ▾ · Period` (DECISIONS V5); checks `V4-property-climate`, `V5-area-minimap-zones` | — | MUST |

## 12. Test property (spec §5.5′, AC-TP1–TP9, DK P10 §1–§4)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| TP1 | `#property?p=lat,lon[:label]`, one pin; `#analysis?a=&la=` redirects (AC-TP1) | done | `route_core.js` codec (list-capable, D6); check `P1-redirects` | — | MUST |
| TP2 | Header: kunta · postinumero · osa-alue · coordinates + `Open on map`, area chips, `OpenStreetMap ↗`, `Copy link` | done | `tpHead()`; check `P6-header`; `docs/ui_v2/property_1440.png` | — | MUST |
| TP3 | Header also carries **`Export ▾`** (UI_V3 §4: sidebar footer, Data header **and** the property header) | **done (V4)** | `exportBtn("prop")` is the last action in `tpHead()`'s `.tools`; the menu opens in place and its `Test property` item downloads the pin's two files; check `V4-property-export` | — | MUST |
| TP4 | Always five tiles, no grey filler slab | done | check `P6-five-tiles`; `docs/ui_v2/property_1440.png` | — | MUST |
| TP5 | The shared study row anchored on the pin's finest area, with the level named (AC-TP2) | done | `studyRow()` reused; check `P6-study-row` | — | MUST |
| TP6 | Tiles clickable → select the indicator and recolour the mini map (AC-TP3) | **done (V5)** | `indSet` on `[data-ind]` tiles, and since V5 it repaints rather than re-renders: `tpRefresh()` rebuilds `#tptop` / `#tpsecs` and the panel and calls `anMapPaint()` + `anMapOverlays()`; checks `P6-study-row`, `V5-property-refresh-in-place` | — | MUST |
| TP7 | Sections as `<details>` with state in `show=`; Infrastructure nearby open by default | done | `tpSec()` / `showSec()`; check `P6-sections` | — | MUST |
| TP8 | Eight sections (outlook, profile, safety, infra, public, schools, climate, sources) | done | `vAnalysis()` `:3510+`; check `P6-sections` | — | MUST |
| TP9 | Duplicate public-building rows grouped by (name, use code, distance ±20 m) with a count | done | check `P6-sections` (P6 build note 5) | — | MUST |
| TP10 | Radius rings and a radius select (500 / 1 000 / 2 000 / 5 000 m) | **done (V4)** | one `tpRadChips()` row, in `Layers ▾` on both routes; and the control now *works* here — `parseHash()` fills `TP.lat/lon` from `p=`, so `tpWithin()` is armed and the overlays really shrink (DECISIONS V4); check `V4-property-radius` counts the markers before and after | — | MUST |
| TP11 | **Services layer** on the property map with the macro map's category filters, own legend, per-map panes (DK P10 §2, AC-TP7) | **done (V4)** | `ANL.srv`, `anSrvKoms()` / `anSrvRows()` (bounded by `AN_SRV_M` = 2 000 m, not by the zoom floors — DECISIONS V4), `srvMarkers(rows, map)` extracted so both maps build markers through `amOf(map)`, `legend-services` in `TP_LEGENDS`, `srv=` in the property hash; check `V4-property-services` | — | MUST |
| TP12 | Every drawn layer has one switch in Layers ▾; off removes markers **and** legend at once; survives reload (DK P10 §3, AC-TP8) | **done (V4)** | see LAY6/LAY7; checks `V4-property-layers-menu`, `V4-property-layer-off-sticks` | — | MUST |
| TP13 | Full indicator list incl. Climate, with the inheritance groups (DK P10 §4, AC-TP9) | **done (V4)** | see PICK11; check `V4-property-picker-groups` asserts a `Climate` header, a `From the municipality` header, ≥ 45 rows and the `muni` tags | — | MUST |
| TP14 | A Climate indicator on the property shows the return-period control, climate bars and the zones in the mini map (AC-TP9) | **done (V4)** | all three asserted together in `V4-property-climate`, plus the `zones=0` hide toggle and that anything else takes the row away again | — | MUST |
| TP15 | Empty state: input focused, one example (AC-E1) | done | `anEmpty()` `:3467`; check `P6-empty-state` | — | MUST |
| TP16 | Per-map panes and renderers — never the macro map's layers | done | `mapPanes()` `:403`, `amOf()`; check `P6-per-map-renderers` | — | MUST |
| TP17 | Mini-map note names the fill, the radius and the place (DK Q8: not all three rings spelled out) | **done (V4)** | the note reads `<level> <name> · rings out to 1,2 km` — one line at 1440, two at 390; the three radii are spelled out once, in the `Radius rings` row of `Layers ▾`, where the switch for them is | — | SHOULD |
| TP18 | The identity block always claims its own line in the header (DK Q2 — the 1536 px two-column break) | **done (V4)** | `.anhead .arid{flex:1 1 100%}` (`src/style.css`); check `V4-property-head-one-line` runs at 1536×864 and asserts the actions sit below the identity block and the tiles share its left edge | — | MUST |
| TP19 | Portfolio / multi-pin | n/a | amendment A2 moved it to LATER in Denmark; the FI codec is already list-capable | — | LATER |

## 13. Export ▾ (spec §4.9, AC-X1–X4, TP4)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| EXP1 | One menu, two places (sidebar footer + Data header) with ≥ 5 items (AC-X1) | done | `EXPORT_ITEMS` `src/app.js:1681`, `exportBtn()` `:1690`; check `P7-menu` | — | MUST |
| EXP2 | Long schema with all 22 columns (AC-X1) | done | `LONG_COLS` `:1719`; check `P7-long-schema` | — | MUST |
| EXP3 | Every row has a non-empty `source`, `as_of`, `fetched`, `licence` (AC-X4) | done | `indStamp()` `:1745`; check `P7-long-schema` | — | MUST |
| EXP4 | Inherited rows carry `value_type=inherited` + `inherited_from` (AC-X4) | done | `longRows()` `:1792`; check `P7-long-schema` | — | MUST |
| EXP5 | Projects in their own file, never mixed into indicator columns (AC-X3) | done | `PROJECT_COLS` `:1723`; check `P7-projects-own-file` | — | MUST |
| EXP6 | Unit / magnitude assertion at the export boundary (AC-X2) | done (adapted) | `assertUnit()` `:1774` — `k€` / `mio €` instead of `kDKK`; check `P7-unit-agreement` | — | MUST |
| EXP7 | Test property: long schema behind `property_label, lat, lon` + a `_nearby_` file (AC-TP4) | done | `exportProperty()` `:1884`; check `P7-property-export` | — | MUST |
| EXP8 | Sources catalogue = the rows the Sources table renders | **done (V5)** | `sourceRecords()` is the one set; `vSources()` renders it (with a new Publisher column and `–` where a publisher gave no date) and `exportSourcesCsv()` writes it. Both now include the osa-alue catalogue, which only the table had; check `V5-sources-table-is-the-export` compares the table's `data-src` keys against the file's `key` column row for row | — | SHOULD |
| EXP9 | National series file | n/a | no national-series dataset surfaced in FI (D5) | — | n/a |
| EXP10 | Climate exposure file (`climate_exposure_<date>.csv`, level × horizon) | **done (V5, adapted)** | `exportClimateCsv()` / `CLIMATE_COLS` — every area × every Climate indicator, with `hazard` (`sea flood` · `river flood` · `radon`) and `return_period` (`1/100a` · `1/1000a`) in columns of their own. A return period is a probability, not a date (D13), so no value in that column is ever a year; check `V5-climate-export` asserts exactly that | — | SHOULD |
| EXP11 | CSV rules: UTF-8 BOM, `;`, `.` decimal, no grouping, one header row | done | `downloadCsv()` `:1946`; check `P7-long-schema` | — | MUST |
| EXP12 | One-line status toast naming the file | done | `exportToast()` `:1938` | — | MUST |
| EXP13 | `Everything (.zip)` | missing | LATER in DK §9 | — | LATER |

## 14. Data tabs (spec §5.3, AC-D1/D3/D4/D5)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| DATA1 | `#data` → `#data/areas/kunta`; tab state in the path (AC-D1) | done | `dataTabHash()` `src/app.js:634`; check `P1-data-tabs` | — | MUST |
| DATA2 | Four tabs → **three in Finland** (Areas · Projects · Sources) | done (adapted) | `DATA_TABS` `:495`; D5; check `P1-data-tabs` | — | n/a (4th) |
| DATA3 | Areas: the active indicator's column is highlighted and the table sorted by it (AC-D5) | done | `vTable()` `:1654` (`th.num.hi`), `tableBodyHtml()` sorts by `curInd()` | — | MUST |
| DATA4 | `th[data-col=<key>]` test ids on the Areas table (spec §10) | **done (V5)** | every `th` in `vTable()` carries one — `name` · `code` · `parent` · `population` · the indicator keys · `<key>_delta`; check `V5-areas-table-col-ids` also asserts they are unique and that `th.hi` is the active indicator's | — | SHOULD |
| DATA5 | Sources as a proper table, no empty `Fetched` cell (AC-D4) | done | `vSources()` `:5186`; check `P1-sources-fetched` | — | MUST |
| DATA6 | Projects: unchanged table + filters, header names the count and the publishers | done | `vPipeline()` `:5039` | — | MUST |
| DATA7 | Row click opens the area page; `↗` opens Charts | done | `tableBodyHtml()` `clickrow` / `tch` | — | MUST |
| DATA8 | `Columns ▾` on Data › Areas | missing | SHOULD in DK §9, deferred there too | — | LATER |
| DATA9 | National series tab and its table | n/a | see NAV5 / DATA2 | — | n/a |

## 15. Detail sheets (spec §5.7, AC-SH1–SH3)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| SHEET1 | No grey filler tile on any sheet (AC-SH1) | **done (V5)** | the CSS override at `src/style.css` (`.arhead .hl{background:none;border:0;gap:var(--s2)}`, v2.0 P6) already ended the grey slab; what was missing was anything asserting it off the area page. `V5-sheets-no-filler` now reads the computed background, border and gap of every `[data-testid=tiles]` row on the project, school and public sheets and fails on an empty cell. Two real faults fell out of writing it: the **public sheet was unreachable** (no `id` in the FI register — `pubStamp()` derives one) and its tiles and table were the Danish BBR's, drawn as `–`; and `prMapInit()` **threw on every project sheet** before the lazy alignments landed. Both fixed — see PROGRESS V5 | — | MUST |
| SHEET2 | Breadcrumb names the municipality, not the app (AC-SH3) | **done (V5)** | `crumbs()` `src/app.js` pushes the kunta for `public`, `publist`, `school`; a project is not in one kunta, so its crumb is `Finland › Data › Projects`; check `V5-sheet-breadcrumbs` asserts all four | — | MUST |
| SHEET3 | `data-testid=tiles` on sheet tile rows (spec §10) | **done (V5)** | the project, school and public sheets carry it; the outlook card deliberately does **not**, so `[data-testid=tiles]` still means "the headline row" on the area page and the property (`P6-five-tiles` counts it); check `V5-sheets-no-filler` | — | SHOULD |
| SHEET4 | Public-building list groups identical rows with a count | missing | DK's own O2 — SHOULD, and the grouping *is* implemented on the property (TP9) | — | LATER |
| SHEET5 | Climate deep-dive sheet `#climate/<kommune>` (AC-SH2) | **missing** | FI has no such route; climate content lives on the area page (`climBars()`) and in the property's Climate section (`anClimateCard()` `:3565`) | — | LATER |
| SHEET6 | Project sheet: `Source ↗`, `updated`, "Where it runs" map over the active indicator | done | `vProject()` `:4978-4980` | — | MUST |
| SHEET7 | School sheet: verify link on the tiles, suppression explained, no fake zeroes | done | `vSchool()` `:4817`, `SUPPRESSED` `:4767` | — | MUST |

## 16. Number and label rules (spec §2.4, AC-G1, DK Q13)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| NUM1 | One `fmt()` path, fi-FI on screen, `.` decimals and no grouping in CSV | done | `FMT` `src/app.js:41`, `nf()`; checks `P8-fi-numbers`, `P7-long-schema` | — | MUST |
| NUM2 | Signed changes always signed; `pp` for a change of a share, `%` for a level | done | check `P8-fi-numbers` | — | MUST |
| NUM3 | Money units on the number (`5 225 EUR/m²`, `21,3 EUR/m²/month`) | done | `unitLabel()` `:40`, `fmtOf()` `:55`; check `P8-units` | — | MUST |
| NUM4 | One rank format `#n of N`, `title` explains N | done | `rankText()` `:1327`; check `P8-one-rank-format` | — | MUST |
| NUM5 | "vs median" is a difference (pp or the unit), never a percent of a median | done | `vsMedianText()` `:1995`; checks `P5-vs-median`, `P8-vs-median-text` | — | MUST |
| NUM6 | `–` for "the publisher has no figure", `n/c` for "not computed at this level", never `0` | done | `fmtCell()` `:1607`, `MUNI_TAG` `:1606` | — | MUST |
| NUM7 | Projection: total change over the window **and** a compound annual rate | done | check `P8-outlook-rate` | — | MUST |
| NUM8 | Every decimal on screen is fi-FI (DK Q13: `1.2 km` → `1,2 km`) | **done (V6)** | `tpRadLabel` goes through `nf()` now (whole kilometres keep no decimal); the SYKE depth legend said `under 0.5 m` / `0.5–1 m` and the building-register note `3.8 million` — both fi-FI now. Check `V6-fi-decimals` walks every visible text node on all 26 routes, with `Layers ▾` open, and allows only a coordinate, a licence name, a date, a version, a URL and a file name. One hit is left and is **registry text, not app text** — `Transport projects within 1.2 km` in `config/indicators.json`, out of this run's reach (DECISIONS V6); the check asserts exactly that, so a new app-written `1.2` fails | — | MUST |
| NUM9 | No visible text matches `/\b(score\|weighted\|index of)\b/i` (AC-G1) | **done (V6)** | check `V6-no-scores`, DK's own two halves: the app's chrome may not say the words at all, and any other occurrence must be verbatim out of the built registry. Two sentences the app wrote were rewritten rather than exempted — "…ends up with more points for that reason alone" for the school warning, and "the municipality figure is per candidate, not per school" for the aggregation, which says the same thing and says it better | — | MUST |
| NUM10 | The `^` "coarser area" marker explains itself (DK Q12: `<abbr title=…>`) | **done (V6)** | `caretMark(why)` `src/app.js:105` — one `<abbr class="cmark" title>` with the right sentence for each of the two meanings (a peruspiiri figure, a coarser-area figure), used by `peruspiiriMark()`, `inhMark()` and the KK-survey popup heading, which was still a bare glyph; check `V6-caret-explains-itself` | — | SHOULD |
| NUM11 | No double-escaped entity on any route (DK Q3 / AC-Q5) | done | `&amp;` appears only as a literal in HTML templates, never through `esc()` twice; check `V6-no-double-escape` sweeps all 26 routes for `&amp;` · `&lt;` · `&gt;` · `&quot;` · `&#nn;` in `innerText` | — | SHOULD |

## 17. Responsive (spec §6, AC-S1–S3, R1/R2, DK Q7/Q11)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| RESP1 | No horizontal overflow at 1366×768, 1440×900, 1536×864, 390×844 on every route (AC-R1) | done (**widened V6**) | `P9-no-overflow-*` swept the ten main routes; `V6-sweep-sheets-*` adds the other sixteen — the three detail sheets, the two list panels, a pinned map, a property with every layer — at the same four widths | — | MUST |
| RESP2 | ≤ 1024: 52 px top bar + `☰` drawer, Esc closes, focus returns (AC-S1, S2) | done | `navToggle()` `src/app.js:613`; check `P9-drawer` | — | MUST |
| RESP3 | ≤ 1024: study row, map card and toolbars stack; tables scroll inside their card | done | check `P9-stacks`; `.scrollx` on every table | — | MUST |
| RESP4 | Chips never wrap — the row scrolls sideways (DK Q7) | done | `docs/ui_v2/area_kunta_390.png` — the chips row scrolls, "Med…" clipped at the edge | — | MUST |
| RESP5 | Tiles 5 → 3 + 2 → 2 columns | done | `src/style.css:1378-1389` | — | MUST |
| RESP6 | Zero `pageerror` at every route × width (AC-R1) | done (**widened V6**) | `P1-zero-js-errors`, `P10-every-route-clean` walk every route at 1440; `V6-sweep-sheets-*` asserts `ERRORS` empty on the sheet routes at all four widths as well | — | MUST |
| RESP7 | The screenshot set covers 1440 and 390 for the morning review | done | `docs/ui_v2/*_1440.png`, `*_390.png` (38 files) | V7 (refresh) | MUST |

## 18. Keyboard and accessibility (spec §7, AC-A1/A2)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| A11Y1 | Zero serious/critical accessibility violations on the main routes (AC-A1 — DK ran a DOM sweep, not axe) | **done (V6)** | check `V6-a11y-sweep` on all 26 routes: every visible `button`/`input`/`select`/`a[href]`/`[role=button]` outside Leaflet's own controls has an accessible name (`aria-label` → `aria-labelledby` → `title` → `<label>` → placeholder → text), every `[aria-haspopup]`/`[aria-controls]` carries `aria-expanded`, every `img` an `alt`. Same offline stand-in DK used — the run installs nothing and `src/vendor/axe.min.js` is not vendored (audit "Later") | — | MUST |
| A11Y2 | Tab from the page start reaches `ind-picker-btn` within 12 tabs; Enter opens, Esc closes (AC-A2) | **done (V6)** | check `V6-keyboard-popovers`: Tab from a blurred `#map` reaches the picker inside the twelve, Enter opens it, Esc closes it and hands focus back — and the same three assertions run on `Layers ▾` and on `Export ▾` | — | MUST |
| A11Y3 | `aria-expanded` on every trigger | **done (V6)** | swept on all 26 routes for all six triggers — picker, `Layers ▾`, `Export ▾`, `☰`, the `Legend ▾` pill and the map card's fold — each must read `"true"` or `"false"`, never absent (`V6-a11y-sweep`) | — | MUST |
| A11Y4 | Popovers use `role=dialog` (Layers, Export) or `role=listbox` (picker) | **done (V6)** | roles were already right (Layers `role=dialog`, picker `role=listbox`, export `role=menu`). What was missing: **the drawer did not trap Tab**, and `Layers ▾` / `Export ▾` did not return focus on Esc — and `exportClose()` would have focused the *first* `[data-exopen]` in the document, which is the sidebar's, not the one the reader opened. `UI.exBtn` / `UI.lyBtn` remember the trigger; checks `V6-drawer-traps-focus`, `V6-keyboard-popovers` | — | SHOULD |
| A11Y5 | Focus visible everywhere (`:focus-visible` ring) | done | `src/style.css:1721` | — | MUST |
| A11Y6 | Colour is never the only carrier (values in legend bins, labels on inherited, pill on projections) | done | LEG6, TILE2, TILE3 | — | MUST |
| A11Y7 | Shortcuts `/`, `g m / g d / g c / g p` | **missing** | the global keydown (`src/app.js:835`) has Esc, arrows, Enter and the H/T/U/O/F camera jumps only | — | LATER |
| A11Y8 | `aria-live` announcement when the map drills into a municipality | missing | — | — | LATER |

## 19. Empty, loading and error states (spec §4.10, AC-E1/E2)

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| STATE1 | `state-empty` with a focused input on `#property` with no pin (AC-E1) | done | `src/app.js:3467`; check `P6-empty-state` | — | MUST |
| STATE2 | `state-nohistory` + distribution strip when an indicator has no series (AC-E2) | done | `:2265`; check `P5-panel-modes` | — | MUST |
| STATE3 | `state-loading` — a noun, never a bare spinner; skeleton, not a blocked page | **done (V6)** | `stateCard(kind, title, note, action)` ported from `ref/dk_src/app.js:1960` — one shape for all three states, `role="status" aria-live="polite"` while loading, three skeleton bars instead of a spinner. Now on the school sheet and school list, the public-building sheet, the map's postal-boundary wait, Charts' history wait and the property's own wait (which had the only one before tonight); check `V6-states` | — | SHOULD |
| STATE4 | `state-error` names the file that failed and offers the source | **done (V6)** | the same card with `data-kind=error`: `schools.json`, `public/<kunta>.json`, `area/<kunta>.json`, `history.json` are each named, with the publisher and a link or a way back. `schoolsLoad()` used to swallow its failure into an empty school list (`SCHOOLS = {schools: []}`), so "could not load" and "no schools here" read identically — there is a `SCH_ERR` flag now; check `V6-states` drives both branches | — | SHOULD |
| STATE5 | "Not covered yet" for a layer with no data in this kunta (hard-data principle) | done | `tpMapTools()` `:3512-3514` tooltips | — | MUST |

## 20. Colour, ramps and families (spec §2.1 + the owner's new rule)

| # | DK item / owner rule | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| RAMP1 | Observed = green, Outlook = purple, Climate = blue; never mixed in one legend | done | `FAMILY_HUE` `src/app.js:909`; check `P3-family-ramps` | — | MUST |
| RAMP2 | Projections dashed and pilled, never bold green/red | done | `PROJ_COLOR` `:2052`; check `P5-panel-modes` | — | MUST |
| RAMP3 | Lower-is-better keeps "darkest = highest" and says so in the legend footer | done | `legendHtml()` `:962` | — | MUST |
| RAMP4 | **Signed indicators get a diverging ramp with fixed breaks centred on 0** (owner, 2026-09-25) | **done (V2)** | `src/ramp_core.js` — 13 signed keys with a threshold each, breaks at ±t (±3t where > 20 % of areas lie beyond), 0 in the positive-low class, `crime_trend` flipped; `scaleOf()` `src/app.js:952`; `tests/ramp.test.js` (20 tests), check `V2-signed-not-quantiles` | — | MUST |
| RAMP5 | The same ramp on map, area mini map, property mini map and the distribution strip | **done (V2)** | one shader, `shadeOf(sc, t, key)` `src/app.js:927`, on every fill; the sixth-class decision is per indicator (`signedWide()` `:938`), not per map, so the four surfaces cannot disagree; check `V2-same-ramp-everywhere`, `V2-dist-strip-dot` | — | MUST |
| RAMP6 | Housing-stock group's blue is close to the Climate blue | open (data) | DK's own O1: the hue is per-indicator in `config/indicators.json`, which this run may not touch | — | LATER |

## 21. Global acceptance and housekeeping

| # | DK item | FI status | Evidence | Phase | Pri |
|---|---|---|---|---|---|
| GLOB1 | Hash round-trips on every route, after an interaction and after `history.back()` (AC-U1) | done | checks `P1-hash-roundtrip`, `P10-hash-stable-everywhere` | — | MUST |
| GLOB2 | One picker, one period control, one tab bar per view | done | check `P10-picker-once` | — | MUST |
| GLOB3 | The retired v1.1 controls are named nowhere | done | check `P10-retired-words`, plus `V6-no-scores` for AC-G1's own vocabulary (see NUM9) | — | MUST |
| GLOB4 | Budgets: `src/app.js` ≤ 460 KB, `src/style.css` ≤ 165 KB | done | 400 KB / 137 KB today — ~60 KB of headroom for V2–V6 | — | MUST |
| GLOB5 | `tests/test_codes.py` is red: it flags `String(Number(v))` in `src/app.js` | **done (V6)** | the lint now flags the idiom only on a **code-named** argument (`code`, `kom`, `muni`, `nr`, …), which is the bug it exists for, and a second test pins the one remaining use by name: exactly one `String(Number(…))` may be in the file and it must be `csvNum`. Strictly stronger than the old grep, and green — `src/app.js` was not changed for it | — | SHOULD |
| GLOB6 | `docs/UI_PLAN.md`, `CHANGELOG.md`, README screenshots kept current | partial | v2.0 state; V7 updates them for v2.1 | V7 | MUST |

---

## MUST gaps, distributed

**V2 — colour rule (fixed scope)** ☑ shipped
RAMP4, RAMP5, LEG7 — all three `done (V2)` above, six checks registered under phase V2.

**V3 — map** ☑ shipped
SRCH3, SRCH4, SRCH5, SRCH7, NAV6 + LAY4, MAP7 — and both of the "if there is room" rows, NAV7 and
SRCH8. All eight are `done (V3)` above, nine checks registered under phase V3. TP10's map half moved
with them: the test-property radius is now a row in `Layers ▾` instead of a sixth toolbar control
(the property page's own copy is still V4's).

**V4 — test property** ☑ shipped
LAY6 + LAY7 + LAY8 + TP12 (one `Layers ▾` with one switch per drawn layer, off means gone, state
sticks), TP11 (Services), TP13 + PICK11 (inherited groups in the property picker), TP14 + MM6's
property half (zones in the mini map), TP3 (`Export ▾` in the property header), TP18 (`.anhead .arid`
at 1536), TP10 (radius into the menu — and made to filter). All `done (V4)` above, eight checks
registered under phase V4. TP17 came with them. **MM6's area-page half shipped in V5.**

**V5 — area page, sheets, Data, Export** ☑ shipped
PICK8 + AREA4 + MM5 + TP6 (the in-place refresh: `areaRefresh()` / `tpRefresh()`, `arMapPaint()` /
`anMapPaint()`, and DK's chips row inside the `⤢` overlay), SHEET1, SHEET2, MM6's area half — and
every one of its "if there is room" rows: AREA5, DATA4, EXP8, EXP10, SHEET3. All `done (V5)` above,
eleven checks registered under phase V5, plus four new sweep routes (`area_climate`, `project`,
`school`, `public`). Writing SHEET1's check found two faults nothing had covered: the public-building
sheet was **unreachable** (the FI register publishes no id) and `prMapInit()` **threw** on every
project sheet before the lazy alignments landed. Both fixed.

**V6 — responsive, numbers, accessibility, states** ☑ shipped
A11Y1, A11Y2, A11Y3, NUM8, NUM9, TILE5, TILE4 — and **every one** of its "if there is room"
rows: NUM10, NUM11, STATE3, STATE4, A11Y4, AREA9, GLOB5. LEG5 came with them (the `Legend ▾`
pill had sat on Leaflet's attribution at 390 since v2.0, flagged in every phase since V2), and
RESP1/RESP6 were widened from the ten main routes to all 26. All `done (V6)` above, fifteen
checks registered under phase V6. One NUM8 hit is left on purpose and is logged, not hidden:
`Transport projects within 1.2 km` is an indicator description in `config/indicators.json`,
which no night phase may touch — a morning one-word fix (DECISIONS V6).

**V7 — QA and docs**
GLOB6, RESP7, and a re-read of every MUST row above.

## Later (not v2.1)

| # | Item | Why not now |
|---|---|---|
| PICK10 | Pinned chips (`+`, localStorage) | SHOULD in DK §9; deferred in Denmark too |
| AREA7 | Sub-areas sparkline column | same |
| DATA8 | `Columns ▾` on Data › Areas | same |
| SHEET4 | Grouping identical rows in the public-building **list** | DK's own open O2; the property list already groups |
| SHEET5 | A climate deep-dive sheet `#climate/<kunta>` | new surface, not a parity gap a reader can see: the FI climate content already has a home on the area page and the property |
| EXP13 | `Everything (.zip)` | LATER in DK §9 |
| A11Y7 | `/` and `g m / g d / g c / g p` shortcuts | SHOULD in DK §7, never built there either |
| A11Y8 | `aria-live` drill announcement | same |
| RAMP6 | The Housing-stock blue vs the Climate blue | lives in `config/indicators.json`, out of this run's reach |
| TP19 | Multi-pin / portfolio | amendment A2 |
| — | Charts: a Climate chart draws one return period, not both (DK AC-C2 draws three horizons) | logged as not-a-MUST when v2.0 shipped P3; the return period is the indicator here (D13), so "both" means two entities, a Charts change rather than a parity fix |
| — | Real axe-core in the accessibility check | the run installs nothing and `src/vendor/axe.min.js` is not vendored — same deviation DK documented (O9) |

---

*Row count: 176 audit rows over 21 sections. Every MUST row is either `done` with a check id, or
assigned to V2–V6 above. `tests/ui_v2.spec.py::v21_audit_exists` (phase V1) asserts this file exists and
still has ≥ 40 rows, so a later phase cannot quietly empty it.*
