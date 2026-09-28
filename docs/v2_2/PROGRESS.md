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
