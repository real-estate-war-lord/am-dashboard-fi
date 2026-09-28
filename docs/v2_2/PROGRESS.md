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
