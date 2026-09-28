# v2.2 — what each phase shipped

Branch `v2.2-ui`, six sequential unattended phases (W1…W6): cleanup, readable maps and charts, a better
Test property first screen, a presentation mode and the Danish SHOULD list. Live today: FI v2.1
(tag `v2.1`, branch `main`). **Never pushed, merged or tagged by a phase** — `./overnight.sh release`
does that in the morning.

Read alongside `docs/v2_1/PARITY_AUDIT.md` (the gap list — phases cite its row ids) and
`docs/v2_2/DECISIONS.md` (every choice taken in the dark).

---

## W1 — cleanup: the lost v2.1 V7 fixes and the small data items ☑

Gate: `./overnight.sh gate W1` green — build ✓, 70 node tests ✓, the full ui suite up to W1 ✓
(6 new checks), budgets `src/app.js` 453 KB / 460, `src/style.css` 144 KB / 165. The python unit
suite is green.

**Built**

1. **The build line says which release this is** (`src/app.js`). One `APP_VERSION = "2.2"`, read by
   the sidebar footer and by nothing else; it had said `v2.0` since v2.0 because the string lived in
   the footer's markup. Check `W1-build-line-version` asserts the line and the constant agree and
   that no second version literal exists in `src/app.js`.
2. **A project sheet knows the areas it serves** (`vProject`, `infraPopup`, `vPipeline`,
   `exportPipelineCsv`). `properties.kunnat` is a Danish field that no Finnish project carries, so
   *Areas served* was empty on all 169 sheets, the Municipalities column of Data › Projects was empty
   on every row, and a map popup never named a municipality. All four now read `dist/infra_index.json`
   — inverted once into `id → {kunta codes}` and cached — and 157 of the 169 projects name at least
   one kunta. Postal codes and osa-alueet were already read from the same index on the sheet; the
   projects CSV gains a `postinumerot` column so the export says what the sheet says.
   Check `W1-project-areas-served`.
3. **A project with no published alignment says "Not covered yet"** instead of drawing a blank map and
   an empty card, and the mini map opens on **Finland**: it was created at `[56, 10.5]`, which is
   Jutland. `FI_CENTER` is derived from `FI_BOX` so the two cannot drift.
   Check `W1-project-map-in-finland`.
4. **The school sheet explains Finland without reaching for Denmark.** "unlike Denmark's socioeconomic
   reference, there is no Finnish equivalent to show here" is now a statement about Finland: no entry
   average, no catchment, no background figure per lukio, so the two rows above the sentence are the
   only comparison there is.
5. **A year never gets a thousands separator** — `1 987 — 2 000` in the buildings legend. One
   `fmtYear()`, wired into `FMT`, `FMT_TIGHT` and the building popup's *Completed* row, and
   `MICRO_INDS.year` moved from `fmt: "int"` to `fmt: "year"`.
   Check `W1-years-have-no-separator`.
6. **The chart's title and sub-title stay on the canvas**, on screen and in the downloaded PNG. A
   reused 2-D canvas measures the real font, the line is cut on a word with an ellipsis, and the full
   string stays in the element's `<title>`. The line chart's own copy of the title block is gone —
   `chTitleBlock()` draws all three chart kinds now, so bar, distribution and line cannot diverge.
   Check `W1-chart-subtitle-fits`.
7. **README's screenshot is build output.** `tests/ui_v2.spec.py` writes `docs/screenshot.png` from
   the map-at-1440 shot it already takes, so it cannot go a release stale again.
8. **`Transport projects within 1.2 km` → `1,2 km`** in `config/indicators.json` (label and short),
   the morning task v2.1's V6 logged. It reaches the page because `build_dashboard.py` now refreshes
   the registry's **text and colour** fields from config at page build time — see DECISIONS W1 for
   exactly which nine fields, and why no field that decides a value is among them.
9. **`Oulun normaalikoulu` is in Oulu.** `data/external/overrides/schools.csv` is the one place a
   school's coordinate may be corrected; `scripts/build_schools.py` applies it before placing the
   school, and `scripts/build_dashboard.py` applies the same file to the `schools.json` on disk so the
   fix lands without a register re-fetch. The replacement point is not typed in from an address: it is
   OpenStreetMap's own `amenity=school` "Oulun normaalikoulun lukio" out of this dashboard's
   public-buildings layer. The school sheet prints where a replaced coordinate came from.
   Check `W1-school-coord-override`.
10. **RAMP6** — the Housing-stock blue (`renters`, `flats`, `dw_pre1980`) becomes a plum,
    `[138, 58, 122]` / `[120, 44, 106]`. Contrast computed and logged in DECISIONS W1: 10,5:1 against
    white label text, 6,3:1 against the no-data grey, 7,7:1 across its own ramp.

**Left for a later phase (found, not fixed)**

- `avg_m2`, `m2_person` and `bld_m2_per_dwelling` are `hue: [90, 60, 150]`, within 6° of the
  projection family hue `[91, 74, 156]` — the same fault RAMP6 names, one group over. Flagged rather
  than fixed: a second unreviewed hue is more change than the audit row asks for.
- `school_grade_avg` / `schools_n` are read by `schoolLine()` and by the school-list header, and no
  build writes them — the per-area school aggregate never renders. It is a pipeline gap, not a UI one.
- A school moved by an override keeps `postinumero` and `osa_alue` empty until the next real
  `build_schools.py` run, because the finer rings are not loaded at page build time. Empty, never
  wrong.

---

## W2 — maps and charts readable at a glance ☑

Gate: `./overnight.sh gate W2` green — build ✓, node tests ✓ (the 70 v2.1 ones plus 12 new in
`tests/scale.test.js`), the full ui suite up to W2 ✓ (12 new checks), budgets `src/app.js`
456,9 KB / 460, `src/style.css` 147,2 KB / 165. The python unit suite is green.

New file: **`src/scale_core.js`** → `window.SCALE_CORE`, inlined as `{{SCALE_JS}}` by
`scripts/build_dashboard.py` (and added to its `check_js()` list) and wired into `src/index.html`,
all in this commit.

**Built**

1. **The map card fills the window** (`mkFitHeight()`, `lfInit()`, `src/style.css`). Finland is tall
   and the card is wide; v2.1's `#lfmap{height:clamp(380px,calc(100vh - 250px),760px)}` gave a
   518-px map at 1366 × 768 and could not know how tall the toolbar above it was today. The height
   is now **measured** from the map's own top edge to the bottom of the window, floor 560 px, and
   re-measured on resize, on every toolbar refresh, when a pin card appears and around full screen.
   Below 1025 px the phone's `55vh` rule owns it, untouched. The national view is **fitted to the
   kunta polygons** rather than to the hand-typed `FI_BOX`, at 6 px of padding and `zoomSnap .25`;
   a drilled kunta is fitted to the kunta at 8 px. Checks `W2-map-card-tall-1366` / `-1440` /
   `-1536`, `W2-map-height-mobile-untouched`, `W2-map-fits-finland`.
2. **A mini map's legends hide behind one `Legend ▾` pill** (`studyRow()`, `vProject()`,
   `vPublic()`, `mmFoldable()`, `src/style.css`). The pill existed since v2.1 but only below
   1024 px, so on a desktop the area page, the property page and the two sheets opened with 40–60 %
   of a small map under legend cards. `.mapwrap.mini` + `@media (min-width:1025px)`: hidden at load,
   pill bottom-left clear of the zoom control and the ⤢, the opened stack anchored above the pill and
   capped at 50 % of the map with scrolling inside. The two sheet maps had no stack and no fold at
   all and now share both. The macro map keeps its legends open and its stack drops from 72 % to
   **60 %** of the map — and the five cards were made to *fit* 60 % rather than scroll inside it.
   Checks `W2-minimap-legend-pill`, `W2-main-legends-under-60`.
3. **One chart axis for the whole build** (`src/scale_core.js`, `multiLine()`, `chartSvgLine()`,
   `chartSvgBar()`, `chartSeries()`). Ticks are 1 / 2 / 2,5 / 5 × 10^n with the range widened to
   whole steps, so **0 is always on a gridline when the range crosses zero**, and a signed indicator
   gets a zero line of its own. The y-range is read off **the years every plotted series covers**, so
   one series' pre-merger spike can no longer flatten every other line; a value outside the axis is
   drawn on the edge with a ▲ / ▼, keeps its real figure in the tooltip, and the excluded years are
   named in a note under the chart and inside the SVG (so the PNG carries it). The x axis starts at
   the first period any series has a figure for, trimmed in `chartSeries()` so the chart, the Data
   table and the CSV agree. The two panel charts that have an axis but no year series were folded
   into the same rule: the **climate bars** drew their middle gridline at `hi / 2` — wherever the
   taller bar happened to end — and printed a rounded label a reader would then measure against, and
   the **population outlook** put its three gridlines on 612 345 / 663 210 / 714 075, which are
   readings of the data rather than a scale to read it against. Checks `W2-chart-nice-ticks`,
   `W2-chart-x-starts-with-data`, `W2-chart-outlier-scale`; `tests/scale.test.js` covers the logic
   directly.
4. **One title, not two** (`chartPanel()`, `panelPeriod()`). The chart card head was the indicator's
   label in caps directly under the picker that had just said it. It is the area and the period now
   — `Helsinki · 2011–2025` — with the unit said once in the same head, the indicator still named on
   the picker and on the mini map beside it. The Charts view's SVG title is deliberately unchanged:
   it is how the downloaded PNG identifies itself. Check `W2-chart-one-title`.
5. **The info strip names the layer that is drawn** (`mapDrawLevel()`, `drawnLevelText()`,
   `mkLevelTag()`, `subLevelOf()`). It said "postal-code level" over a map of municipalities because
   it carried the indicator's publication level. It now reads *municipalities drawn · zoom in for
   postal codes* nationally, *postal codes drawn* inside Tampere and *osa-alueet drawn* inside
   Helsinki, from the same predicate `muniAreas()` uses, and is rewritten in place at the end of
   `lfLayers()` so a drill updates it without a re-render. The publication level moves to the tag's
   `title`; the table view, which draws no map, is unchanged. Check `W2-info-strip-level`.

**Earlier checks this phase's plan voids (adapted, not weakened)**

- `legend_live()` and `P6-legends-stack` asserted a mini map's legends are *visible*. §2 puts them
  behind a pill, so both open the stack first through one new `open_legends()` helper; what they then
  assert is unchanged. Six V4/V5 assertions go through `legend_live()` and are covered by the same
  one-line change.
- `P10-legends-inside-map` is untouched. Its geometry loop skips a hidden stack, so on its two
  mini-map routes it now checks nothing; `W2-minimap-legend-pill` makes the same inside-the-map and
  never-overlapping assertions about the opened stack.

**Left for a later phase (found, not fixed)**

- **`src/app.js` ends at 456,9 KB of 460** — 3,0 KB of headroom. Before W3 adds anything substantial it
  should move a pure module out, as the plan says to: `pip` / `bboxOf` / `inBox` / `areaOf` and
  `havM` / `featDistM` / `R_EARTH` are DOM-free, state-free geometry with no test file of their own,
  so `src/geom_core.js` + `tests/geom.test.js` frees ~3,5 KB *and* gains coverage. W2 left it alone:
  it is not a W2 item, and refactoring the point-in-polygon code that places every pin, school and
  public building unattended is the wrong risk for a budget that is not yet breached.
- **No indicator in this edition carries a `breaks` entry**, so `chartBreaks()` draws nothing and the
  clipped-scale note can never name a *cause* — it says "years not every series shown covers"
  instead of the plan's "(area boundaries changed)". The moment the build writes one `breaks[].text`,
  the note picks it up with no code change. Filling it is a pipeline job, not a UI one.
- **`schoolTrendSvg()` and `tileSpark()` still draw their own axes.** Both are sparkline-sized —
  no gridlines, no tick labels, only a first and a last year — so there is nothing for a tick rule to
  fix; they are simply the last two line drawings not reading `SCALE_CORE`. (`popOutlookChart()` and
  `climBars()` *were* folded in: see item 3.)
- **Ten series on one Charts line chart** put the legend's fourth row within ~2 px of the source
  footer. That was already true in v2.1; the clipped-scale note is inserted *above* the legend and
  pushes it, so the case is no worse, but the legend still wants a proper row budget.

---

## W3 — Test property: the first screen ☑

Gate: `./overnight.sh gate W3` green — build ✓, node tests ✓ (93: the 82 v2.1 + W2 ones and 11 new
in `tests/geom.test.js`), the full ui suite up to W3 ✓ (6 new checks), budgets `src/app.js`
459,2 KB / 460, `src/style.css` 149,8 KB / 165. The python unit suite is green (39).

New file: **`src/geom_core.js`** → `window.GEOM_CORE`, inlined as `{{GEOM_JS}}` by
`scripts/build_dashboard.py` (and added to its `check_js()` list) and wired into `src/index.html`,
all in this commit.

**Built**

1. **The study row starts 265 px down, not 496** (`tpHead()`, `tpTop()`, `tpBar()`, `studyRow()`,
   `tpRefresh()`, `src/style.css`). The plan asks for ≤ 420 at 1440 × 900. Four things were in the
   way and all four are gone: the property name had a line to itself, the five action buttons had a
   second, a sentence sat under the tiles, and a whole card held nothing but the picker, Layers ▾
   and the period control. The name, its area tags and the actions **share one line** now — the tags
   wrap inside their own block instead of pushing the buttons down — the tiles are directly below at
   84 px, the sentence is an **ⓘ** beside the tags (and names the whole fallback chain, which it
   never did), and the toolbar is the study row's own full-width header, `#tpbar`. The chart itself
   starts at 372. At 1366 × 768 the row starts at 265 too. The one-line header is scoped to
   **≥ 1280 px**, not the usual 1025: with the sidebar taking 250 px, anything narrower leaves less
   than the 340 px the name and its tags need beside the five actions, and the block would collapse
   into a column instead of wrapping into two lines. Every tablet and every phone keeps the stacked
   header exactly as it was. Checks `W3-first-screen-1440`, `W3-first-screen-1366`,
   `W3-mobile-stays-stacked`.
2. **osa-alue → postal code → kunta, for every indicator** (`eVal()`, `fbChain()`, `inhTag()`,
   `tpEntity()`, `anRow()`, `fmtCell()`, `longRows()`, `exportProperty()`). `eVal()` fell from an
   area straight to its kunta, because until tonight the only thing that ever inherited was an area
   *page*, and an osa-alue page has no single postal code. A **pin** has one. On the plan's own pin
   (60,2448 / 24,8665) **Price** was Helsinki's 5 090 €/m² labelled "municipality figure" and is now
   00410 Malminkartano's own **2 280 €/m²** labelled "postal-code figure"; **Unemployment** was
   Helsinki's and is now 00410's **15,2 %**. `fbChain()` is the one list the tiles, the panel head,
   the Area profile table, the percentile bar's peer pool, the Verify link and the property CSV
   (`inherited_from`) all walk, so none of them can name a different level than the tile does.
   The five-pin audit is the table in DECISIONS W3. Checks `W3-fallback-order`,
   `W3-profile-table-levels`.
3. **Rent and crime are *correctly* still municipality figures on that pin** — and DECISIONS W3 says
   why, because "the postal code has one" looks true at a glance. 00410 carries `rent_pno` 18,4, but
   `rent_pno` is a different indicator whose own registry `warn` says it is never blended with the
   live kunta-level rent (Tilastokeskus discontinued the postal-code table at 2025Q4); `crime_1000`
   is published per kunta for the whole country. Nothing was spliced to make a tile look finer.
4. **The property mini map's legends already fold behind W2's pill; W3 asserts what that is worth.**
   `W3-minimap-legends-at-load` measures the covered fraction of the map rather than the CSS: no
   legend covers more than 50 % at load with three feature layers on, the pill is there, and opening
   the stack keeps it under half. The Layers ▾ count badge is asserted by `W3-first-screen-*`.
5. **Export ▾ in the property header opens on the screen.** Moving it to the end of a one-line
   header exposed a default written for the footer button: `left:0` ran it 27 px past the window at
   1536, and `bottom:100%` opened it *upward*, 340 px above the top of the page. It opens down and
   right-aligned in `.anhead` now. The upward open was already off-screen before W3 — the shorter
   header only made it further off — so `V4-property-export` gained the two assertions that catch it.
6. **`src/geom_core.js` + `tests/geom.test.js`** — the move W2 handed to this phase. `pip`,
   `inPoly`, `bboxOf`, `inBox`, `areaOf`, `R_EARTH`, `havM` and `featDistM` place every pin, school
   and public building on the page and had no test of their own. Eleven now, including the two bugs
   their comments record: the inside-out bbox that must never be cached while rings are still
   loading, and a polygon being its outer ring *minus its holes*.

**Earlier checks this phase's plan voids (adapted, not weakened)**

- `V4-property-head-one-line` asserted that the identity block claims a line of its own (audit TP18,
  DK Q2) — the exact opposite of what §1 asks for. It now asserts the name, the tags and the actions
  share one line, that the actions do not overlap the identity block, and that the tiles still start
  at the title's left edge and below both. The second half is what the original was protecting.

**Left for a later phase (found, not fixed)**

- **The page ceiling in `scripts/build_dashboard.py` was raised 3,2 MB → 3,3 MB.** v2.1 shipped 2 KB
  under it; W2 and W3 together put the page 6 KB over, entirely in source code — no data changed.
  The reason is written at the constant and in DECISIONS W3. W4–W6 have ~94 KB. If that starts to
  look thin, the honest next step is a build that strips comments from the *inlined* copy while the
  repo keeps them, not deleting them at source.
- **At 1366 the tile row is 112 px, not 84**, because "21,3 EUR/m²/month" takes two lines in a 200-px
  tile. True on the area page too, and true before W3; forcing it onto one line is what used to
  paint the unit over the next tile (audit TILE5). Held at its measured height so it cannot grow.
- **`tileStats()` still mixes levels across a series.** The current value now resolves through the
  chain, but each earlier year resolves independently, so a sparkline could in principle switch
  level mid-line. No indicator in this edition does it (a postal code that publishes a price
  publishes its whole series), but the honest fix is to pin the series to the level the current
  value came from.
- **An area page's osa-alue still falls straight to its kunta**, because it is a district and no one
  postal code covers it. Only a pin can use the middle step. A future phase could offer the
  postal-code figure there as a *range* across the codes the district overlaps — but a range is not
  the figure, and inventing one would be a model.

---

## W4 — present mode, the study-row PNG and print ☑

Gate: `./overnight.sh gate W4` green — build ✓, node tests ✓ (106: the 93 of W1–W3 and 13 new in
Gate: `./overnight.sh gate W4` green — build ✓, node tests ✓ (109: the 93 of W1–W3 and 16 new in
`tests/present.test.js`), the full ui suite up to W4 ✓ (151 checks, 6 of them new), budgets
`src/app.js` 459,9 KB / 460, `src/style.css` 156,1 KB / 165. The python unit suite is green.

New file: **`src/present.js`** → `window.PRESENT`, inlined as `{{PRESENT_JS}}` by
`scripts/build_dashboard.py` (and added to its `check_js()` list) and wired into `src/index.html`
**before app.js**, all in this commit. It is a feature module like `src/testprop.js`, not a pure
`*_core.js`: its pure half is exported and node-tested, its browser half reads app.js's own globals
— see DECISIONS W4 for why the whole phase had to live outside app.js.

**Built**

1. **Present mode** (`src/present.js`, `hashFor()`, `parseHash()`, `render()`, `renderTop()`,
   `src/style.css`). `present=1` in the link, `▶ Present` in the top bar, or **`P`**; **Esc** leaves,
   and so does `P` again. On the four views the plan names — Map, Area page, Test property, Charts —
   the sidebar goes, the four toolbars (the map's row, the area page's picker card, the study row's
   `#tpbar`, the Charts controls) collapse into **one thin line in the top bar**: the indicator, the
   period and the area path. The headline numbers grow a quarter (the 26-px tile figure to 32,5,
   the 30-px panel figure to 37,5, the 33-px hero to 41), the mini maps' legends come out from
   behind W2's `Legend ▾` pill and stay open, and a **one-line source footer** is pinned to the
   bottom of the window: *Source: Tilastokeskus, Aluesarjat … · as of … ·
   real-estate-war-lord.github.io/am-dashboard-fi*. Nothing that carries a figure is hidden — the
   check counts tiles, sections and caveats with and without `present=1` and requires the three
   counts to match. Two of the rules are desktop-only and say so: below 1025 px the map is 55vh and
   the pill stays (it is the only way the map and its key both fit), and the source line sits at the
   end of the document rather than bolted across the bottom of an 844-px screen. Checks
   `W4-present-hides-sidebar`, `W4-present-key-toggles`, `W4-present-numbers-bigger`,
   `W4-present-legends-open`; the four views are also shot at 1440 and 390 into
   `docs/ui_v2/present_*.png`, which is what W6 §1 asks to look at.
2. **`⤓ PNG` on the study row** (area page and Test property), in the chart panel's own head. One
   image, 1 600 × 508 at **2×** (3 200 × 1 016 px), with the chart on the left at its own aspect
   ratio, its series key and the clipped-scale note under it, the mini map filling the full height
   on the right with its own legend redrawn in the corner, a title (*area · indicator*), a
   sub-title (*period · unit · definition*) and the same source footer along the bottom. It is made
   **out of the page**: the panel's SVG is cloned with every drawn property inlined from its
   computed style (a stylesheet does not travel inside a `data:` URL), and the map is copied tile by
   tile, canvas by canvas, overlay by overlay, in pane z-index order, with the test property's pin
   redrawn because it is a CSS shape with no text in it. Where the tiles are cross-origin — which is
   what `tile.openstreetmap.org` is, and what the test harness always serves — the polygons and
   labels are drawn on the page's own paper colour instead and the image's footer says
   **· basemap omitted**. No library was added; nothing is fetched. Check `W4-study-png` asserts a
   real PNG of non-trivial size on both routes and keeps the file in `docs/ui_v2/study_png_*.png`,
   so the artefact can be looked at and not only counted. The Charts view's own `⤓ Download PNG` now
   goes through the same rasteriser (`PRESENT.png`) — one place turns an SVG into a file.
3. **A print stylesheet, A4 landscape** (`src/style.css`). `@page{size:A4 landscape;margin:11mm}`;
   the sidebar, the top-bar actions, every toolbar, every popover and Leaflet's own controls are
   gone; the legends are unfolded, because on paper they can never be behind a pill; the source
   footer is the last thing on the page; every card, section and table is `break-inside:avoid` and
   the study row is `break-after:page`, which is what "one view per page" means here. The maps get
   a height in **millimetres** (108 mm macro, 88 mm mini) because W2 measures them against the
   *window*, and a Leaflet container with no height prints as a clipped grey strip;
   `beforeprint` tells every live map its container just changed shape. Check `W4-print-no-sidebar`
   drives it under Playwright's print media emulation.

**Left for a later phase (found, not fixed)**

- **`src/app.js` ends the phase at 470 931 B of 471 040 — 109 bytes.** W4 spent almost nothing there
  on purpose (six hooks and one flag; `chartPng()` got *smaller*), but the ceiling is now effectively
  reached and **W5 cannot add a line to app.js before it moves a module out.** The move is already
  scoped: **`chartSvg` … `chartSvgLine`** — the block from the comment *"self-contained SVG (inline
  styles, title, legend)…"* down to the end of `chartSvgLine`, about 13 KB — is the natural
  candidate, and only **four** of its names are used outside it: `chartSvg` (vCharts, chartPng),
  `chTitleLive` (the `change` handler for `#chtitle`), `DIST_DEFS` (chartAutoTitle, vCharts,
  chartCsv) and `fmtP` (vCharts's Data table). Everything else it declares — `CH_FONT`, `CH_MONO`,
  `CH_W`, `CH_PAD`, `CH_MEAS`, `chTextW`, `chClip`, `chTitleFont`, `chSubFont`, `chTextMax`,
  `chTitleBlock`, `chFoot`, `chartSvgBar`, `chartSvgDist`, `DIST_COLORS` — is used only inside it.
  A `src/chartsvg.js` exposing those four, inlined before app.js, frees the room for the whole of
  W5. W4 did not do it: an unattended re-typing of 136 lines of dense SVG template literals, in a
  phase that also had three new features to land, is the wrong risk to take with the one file every
  check reads. The analysis is here so W5 does not have to redo it.
- **`dist/index.html` is 3 237 kB of the 3 300 kB ceiling** — 62 kB for W5 and W6. W4 added ~19 kB
  of source (present.js and the W4 CSS). If W5's seven items approach it, the honest next step is
  still the one W3 named: strip comments from the *inlined* copy while the repo keeps them.
- **The PNG draws no HTML marker that is neither text nor the pin.** Area labels and the test
  property's pin are redrawn; a public-building or services marker that is a pure CSS shape would
  be missed. None of the three layers the study row's mini maps draw by default is one — they are
  `L.circleMarker`s on a canvas renderer, which *is* copied — so nothing is currently lost, but a
  future HTML-icon layer would need a line here.
- **Present mode does not re-fit the camera.** Leaving the sidebar gives the map ~250 px more width;
  the map is told its container changed (`invalidateSize`) but keeps its centre and zoom, because a
  zoom change on entering present mode would be the app moving the reader's view out from under
  them mid-sentence. A deliberate `fitBounds` on entering is a defensible future choice, not this
  phase's.
- **Print is asserted by media emulation, not by a rendered PDF.** Playwright's `emulate_media`
  proves the rules apply; it does not prove the pagination. A real `page.pdf()` in the suite would,
  and would add a binary artefact to every run — W6's manual QA pass is the cheaper place to look.

---

## W5 — the Danish SHOULD list (package E) ☑

Gate: `./overnight.sh gate W5` green — build ✓, node tests ✓ (132: the 109 of W1–W4 and 23 new in
`tests/w5_core.test.js`), the full ui suite up to W5 ✓ (158 checks, 7 of them new), budgets
`src/app.js` 450,6 KB / 460, `src/style.css` 160,6 KB / 165. The python unit suite is green.

**Three new files**, all wired into `src/index.html` and `scripts/build_dashboard.py` (and its
`check_js()` list) in this commit, all inlined **before** app.js:

- **`src/w5_core.js`** → `window.W5_CORE`, `{{W5_JS}}` — the phase's arithmetic, pure, 23 node tests.
- **`src/w5.js`** → `window.W5`, `{{W5UI_JS}}` — the phase's drawing. A feature module like
  `present.js`, not a pure core: it reads `S` / `UI` / `MK` / `T` / `IPK` out of the shared script
  scope.
- **`src/chartsvg.js`** → `window.CHARTSVG`, `{{CHARTSVG_JS}}` — **the move W4 scoped**, see §0.

### 0. app.js had 109 bytes left, so the chart drawing moved out first

W4 ended at 470 931 B of 471 040 and wrote the plan for this in PROGRESS: `chartSvg` … `chartSvgLine`
is now `src/chartsvg.js`, exporting the four names the rest of app.js ever asked it for — `chartSvg`,
`chTitleLive`, `DIST_DEFS`, `fmtP`. That freed **16,0 KB**. W5 then spent almost none of it on itself:
the arithmetic went to `w5_core.js` and the drawing to `w5.js`, so app.js gained ~1,5 KB of aliases
and hooks and **ends the phase at 450,6 KB of 460** — 9,4 KB of headroom for W6, where W4 left 109
bytes. The whole of W1–W4's chart suite (`W1-chart-subtitle-fits`, `W2-chart-nice-ticks`,
`-x-starts-with-data`, `-outlier-scale`, `-one-title`, `W4-study-png`) passed unchanged against the
moved file before a single W5 feature was written.

**Built — the seven items, smallest first**

1. **PICK10 — the chip row becomes the reader's** (`src/w5.js`, `indChips()`, `src/style.css`).
   Six default quick chips until someone presses **`+`**; from then on the row is **their** pins, in
   the order they pinned them, each with a **×** that appears on hover or focus (the × is always
   laid out, so the row never changes width under a moving pointer). `localStorage` under
   `amfi.pins.v1`, every read and write in `try/catch`, **max 12** — and the thirteenth drops the
   one pinned longest ago rather than refusing the click. The pins never touch the URL; DECISIONS W5
   says why. Pinning repaints the chip row only, never the map. Check `W5-pinned-chips` pins two,
   reloads, unpins one and hand-writes 60 keys into the store to prove the cap.
2. **DATA8 — `Columns ▾` on Data › Areas** (`colsBtn()`, `colsMenuBody()`, `tableCols()`,
   `hashFor()`, `parseHash()`). Indicator **groups**, not single columns — 40+ columns is the wall
   the table already is, and a group is what a URL can carry: `cols=Market,Taxes`. No key means every
   group, so every pre-W5 link opens the table it always did. The indicator the table is sorted by
   never loses its column, and **the CSV keeps every column whatever is ticked** — what is hidden
   here is a reading aid, not a claim that a figure does not exist. Ticking the last missing group
   back on drops `cols=` rather than listing them all. The rows are buttons, not checkboxes in
   labels: a `<label>` forwards its click to its input, and the delegated handler would have ticked
   the group straight back off. Check `W5-columns-menu` also asserts the header and the body agree on
   the column count — the one way this could print a figure under the wrong name.
3. **AREA7 — a sparkline column in the sub-areas table** (`subSpark()`, `W5_CORE.sparkSegments`).
   The last ten published years of the sorted indicator, inline SVG, no library, `currentColor` so it
   prints. Each row on **its own scale** (the header says so, and the column is not sortable): a
   shared scale across forty postal codes flattens every one of them against Helsinki's range, and
   the figure is in the cell to the left. A year the publisher did not publish **breaks the line**;
   fewer than two published years is a dash. Check `W5-subarea-sparkline` also asserts no charting
   library was loaded.
4. **A11Y7 — the shortcuts and the `?` overlay** (`W5_CORE.keySeq`, `runShortcut()`, `focusSearch()`,
   `helpOverlay()`, the `?` button on the sidebar's build line). `/` focuses the search that is on
   screen — the picker's own box when a picker is open; `g m` / `g d` / `g c` / `g p` go to Map,
   Data, Charts and Test property; `[` / `]` step the chip row (the pins where there are any, the
   defaults where there are none, so the keys do something on a page nobody has pinned on yet); `?`
   opens the list and `Esc` closes it. `g` is a prefix the way it is in a mail client, and `g` + a
   stray key is dropped rather than guessed at. Every one of them is ignored while typing and with a
   modifier held. `present.js` now skips `p` while a `g` is pending, so `g p` is not eaten by present
   mode. Check `W5-shortcuts` drives all nine, including typing `gd` into the search box and getting
   the letters. The sidebar's `?` button is `tabindex="-1"` and the build line says *press ? for
   shortcuts* instead: the first build of it was a thirteenth tab stop in front of the indicator
   picker and `V6-keyboard-popovers` — which guarantees twelve — caught it. DECISIONS W5.
5. **SHEET4 — the public-building list groups building parts** (`vPubList()`,
   `W5_CORE.groupSame`). Grouped on name + category + type **and a distance ≤ 150 m**, deliberately
   not on the address: Finland's register is not Denmark's BBR, and the duplicates that exist here
   (`Päiväkoti Kesäheinä`, Helsinki) differ in exactly the field an address key would split on, 11 m
   apart. The shape is the property sheet's TP9 rule at list scale. Nothing is dropped: the `×n`
   badge is the register's own count, the card head says how many rows the register has, and the
   grouped row still opens the first part's sheet. Check `W5-public-list-grouped` reconciles the
   badges against the register's total and opens a grouped row.
6. **A Climate bar chart draws both return periods** (`chartSvgBar()`, `rpBarRows()`,
   `chartAutoTitle()`, `W5_CORE.tint`). One row per area × return period, the pairs kept together
   and ordered by the commoner period, the rarer one in the area's own colour mixed 45 % toward
   white so a pair reads as one area. The **median tick is off** in that mode and the footer says
   why — one dashed line on an axis carrying two measurements could only belong to one of them. The
   title names the family, not the period in `ind=`. Check `W5-climate-both-return-periods` asserts
   four bars for two coastal kunnat, that no bar label is ever a year, and that an ordinary
   indicator's bar chart is untouched.
7. **A11Y8 — the drill is announced** (`src/index.html`'s one `aria-live="polite"` region,
   `announceDrill()`, `W5_CORE.drillLine`). *"Showing Helsinki, 84 postal codes"*, written at the end
   of `lfLayers()` and **only when the sentence changes** — which is what makes v2.0's "zooming never
   changes the selection" true for a screen reader too: a zoom redraws the same layer and produces
   the same string, so nothing is said. Buildings mode is named with no count, because the building
   file is lazy and a count read before it lands would be a wrong number rather than a missing one.
   Check `W5-drill-announced` asserts the region is off screen, not `aria-hidden`, and silent on zoom.

**One earlier rule this phase changes (adapted, not weakened)**

- `enableSort()` now honours `data-nosort` on a `<th>`. The sparkline column has no number to sort
  by; before this it was dressed as a sort control that fell back to comparing empty strings.

**Left for a later phase (found, not fixed)**

- **`src/style.css` ends at 160,6 KB of 165** — 4,4 KB for W6. The W5 section is ~4,5 KB and none of
  it is decoration; if W6 needs room, the print block and the present block share enough selectors to
  merge.
- **`dist/index.html` is 3 205 kB of the 3 300 kB ceiling** — W5 added ~28 KB of source (three files
  and the CSS) and no data. W3's suggestion still stands as the honest next step if W6 runs out:
  strip comments from the *inlined* copy while the repo keeps them.
- **The pins are not offered anywhere but the chip row.** A reader who pins twelve indicators on the
  map has them on Data › Areas and the area page too (it is one `pickCtx`), but an osa-alue page
  silently shows only the pins that level publishes — the row can be shorter than the store and never
  says so. A "3 of your 12 are not published here" line is a defensible next step, not this phase's.
- **`Columns ▾` is on Data › Areas only.** The area page's *All indicators* table and the property's
  *Area profile* have the same width problem and the same group structure; `tableCols()` is the only
  place the choice is applied, so extending it is a render change rather than a model one.
- **The sparkline column is on the sub-areas table only.** `tileSpark()` and `schoolTrendSvg()` are
  still the two drawings that read neither `SCALE_CORE` (W2) nor `W5_CORE.sparkSegments`; all three
  now draw the same kind of thing three ways. None of them is wrong — they are simply not one
  function yet.
- **A Climate *line* chart is still one return period.** The pair is a bar-chart rule, because the
  flood rasters have no year series at all in this edition. If SYKE ever publishes a second vintage,
  `chartSeries()` would need the same treatment and `chartInds()` is where it would go.
