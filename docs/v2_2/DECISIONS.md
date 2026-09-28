# v2.2 — decisions taken while building

Nobody is awake during this run. Every time the brief, the Danish spec and this repo disagree — or say
nothing — the phase picks the option that best fits the plan and writes one line here, prefixed with its
phase id. Newest at the bottom.

The decisions v2.0 took are in `docs/UI_PLAN.md` §2 (D1–D16) and v2.1's are in
`docs/v2_1/DECISIONS.md`; both still hold unless a line below replaces one.

---

- **W1** — **The kunnat a project serves are read off the spatial index, and the index is inverted
  once.** `properties.kunnat` is a Danish field; no Finnish project carries one, which is why *Areas
  served* was empty on all 169 project sheets and the Municipalities column of Data › Projects was
  empty on every row. `dist/infra_index.json` already answers the question the other way round
  (`kunta:091 → [project ids]`), so `infraKomIndex()` inverts it once into `id → {kunta codes}` and
  caches that — the Pipeline table asks for it 169 times per render, and a scan of the whole index per
  row is the kind of thing that only shows up on a slow machine. The cache is dropped when
  `dist/infra.json` lands with a fuller index. 157 of the 169 projects now name at least one kunta;
  the other twelve have no published alignment at all and say **"Not covered yet"** rather than
  drawing an empty list.
- **W1** — **A project with neither line, area nor point frames Finland and says why.** The mini map
  was created with Denmark's own centre (`[56, 10.5]` is Jutland) and only moved once `fitBounds`
  found something, so a project with no geometry opened on another country. Every map in this build
  now starts at `FI_CENTER`, the centre of `FI_BOX`, and the three states are said apart: still
  loading, "no alignment — the municipalities it serves are framed instead", and "Not covered yet".
- **W1** — **The projects CSV gains a `postinumerot` column, from the same index.** The sheet already
  listed the postal codes a project runs through; the export named only the kunnat. The column is
  added after `kunnat` rather than in place of it, so a file written before tonight still parses by
  name. No other export changed.
- **W1** — **A year is a label, not a quantity: one `fmtYear()`.** `Year built` was `fmt: "int"`, so
  fi-FI's thousands space made the buildings legend read `1 987 — 2 000`. The fix is a `year` entry in
  both `FMT` and `FMT_TIGHT` plus the building popup's Completed row — one function, and the map
  legend, the bins and the popup cannot disagree again. `nf(v, 0)` stays right for a count of
  dwellings, which *is* a quantity.
- **W1** — **The chart's title and sub-title are clipped by measurement, not by a character count.**
  The chart is a 1 200-unit SVG built as a string and rasterised straight to PNG, so the text cannot
  wrap by itself and cannot be measured in the document — an indicator description simply ran off the
  right edge and into the downloaded file. One reused 2-D canvas measures the same font, the line is
  cut on a word with an ellipsis, and the **full** string stays in the element's `<title>`: hover on
  screen, and nothing is lost from the export. Wrapping to a second line was the alternative and was
  rejected: the line chart's plot area starts at y = 84 and a second sub-title line would have had to
  push every chart's geometry down for the longest description in the registry.
- **W1** — **The build line reads one `APP_VERSION`.** It said `v2.0` a whole release after v2.1
  shipped because the string lived in the footer's markup. A check asserts the line and the constant
  agree, so the next release cannot ship the previous one's number.
- **W1** — **README's screenshot is build output now.** It was still the v2.0 look because it was made
  by hand. `tests/ui_v2.spec.py` writes `docs/screenshot.png` from the same map-at-1440 shot it already
  takes for `docs/ui_v2/`, so the two cannot drift. (`docs/ui_v2/*.png` stays uncommitted; this one
  file is committed because README embeds it.)
- **W1** — **`Oulun normaalikoulu` is moved by an override file, and the page says so.** The register's
  own coordinate for oppilaitosnumero 00599 is 60.158409, 24.958738 — central Helsinki, 540 km from
  the school it names — so the school sat on Helsinki's map and in Helsinki's benchmark. The
  replacement is 65.057742, 25.464132, which is not typed in from an address but taken from a dataset
  already on disk: OpenStreetMap's `amenity=school` "Oulun normaalikoulun lukio" in this dashboard's
  own public-buildings layer (`dist/public/564.json`). `data/external/overrides/schools.csv` is the
  one place a school coordinate may be corrected and it corrects nothing else — no name, no type, no
  figure — and the school sheet prints the source of a replaced coordinate under Sources.
- **W1** — **The override is applied twice, from one file, because `build_schools.py` cannot run
  tonight.** That script re-fetches the whole register over the network and writes `data/processed/`,
  which this run may not touch. So `build_schools.py` gained the permanent fix (the override is
  applied *before* the point-in-polygon placement, so kunta, postal code and osa-alue all follow from
  the corrected point), and `build_dashboard.py` applies the same CSV to the `schools.json` already on
  disk when it writes `dist/schools.json`. At page-build time only the kunta can be re-derived — the
  kunta rings are already loaded for `dist/geo/kunnat_lookup.json`, the finer rings are not — so the
  **postal code and osa-alue of a moved school are cleared rather than guessed**, and the kunta
  benchmark is recomputed through `build_schools.kunta_benchmarks()`, the one definition of that mean.
  Everything else about the school layer is exactly what the last real fetch produced.
- **W1** — **Registry text and colour are refreshed from `config/indicators.json` at page build
  time.** `data/processed/makro.json` embeds a copy of the registry taken when the figures were last
  fetched, so a one-character fix in config would otherwise have waited for the next national fetch to
  reach a reader — and tonight's two fixes (`Transport projects within 1,2 km`, and the Housing-stock
  hue) are both presentation. `build_dashboard.py` now refreshes **only** `label · short · unit ·
  desc · note · warn · hue · group · chip`, only for keys the built registry already has, and prints
  every field it touched. Nothing that decides a *value* — table ids, `vars`, `calc`, `select`,
  sources — is read from config here, so the figures on the page stay the ones the fetch produced.
  Tonight that is five fields, and the build says which five.
- **W1** — **RAMP6: the Housing-stock blue becomes a plum, `[138, 58, 122]`.** `renters` and `flats`
  were `[40, 84, 128]` and the Climate family ramp is `[47, 78, 140]` — the same hue to within 6°, on
  maps a reader switches between. Every neighbouring band of the wheel is already spoken for
  (observed green 160–170°, Climate blue 220°, projection purple 252°, Safety gold 30°, Construction
  brown 25°, Market brick 11°), and the one real gap is at ~310°. `dw_pre1980` was the darker of the
  two blues and keeps that relationship at `[120, 44, 106]`. Contrast, computed on the shipped ramp:
  darkest class `rgb(99,42,88)` is **10,5:1** against white label text, **6,3:1** against the no-data
  grey `#C4CBC4`, and **7,7:1** against its own lightest class — all above the 3:1 the v2.1 rule
  sets. The three Housing-stock indicators that are `[90, 60, 150]` (`avg_m2`, `m2_person`,
  `bld_m2_per_dwelling`) are **left alone and flagged instead**: that violet is within 6° of the
  projection family hue, which is the same fault one group over, and picking a second new hue
  unreviewed would have been a bigger change than the audit row asks for.
- **W2** — **The map card's height is measured in JavaScript, not written in CSS.** The plan asks for
  "fill the viewport below the toolbar, min 560 px at 1366 × 768", and no `calc(100vh - X)` can
  honour both halves of that: the chrome above the map is between ~230 px (national view, one
  toolbar row) and ~300 px (a drilled kunta, whose figure strip and pin card sit between the strip
  and the map), so v2.1's `100vh - 250px` gave 518 px at 768 and overshot the window at 900.
  `mkFitHeight()` reads the map's own top edge, subtracts 42 px for the collapsed *Data information*
  line under it, clamps to [560, 1040] and writes an inline height; it is re-run on resize, on every
  toolbar refresh, when a pin card appears and on entering or leaving full screen (where it clears
  the inline value so the `:fullscreen` rule can win). **Below 1025 px it clears the inline height
  and the phone's own `55vh` rule owns it** — a 560-px map under a phone's tall toolbar would push
  the source note two screens down, and `V6-legend-pill-clear-390` and `P9-*` describe that layout.
- **W2** — **Finland is framed by the polygons that are drawn, not by `FI_BOX`.** `FI_BOX` is a
  hand-typed rectangle that reaches past the last kunta on every side; fitting it added a band of
  empty sea to the empty flanks a tall country in a wide card already costs. `fiBounds()` is
  `boundsOf(MUNI)` (every kunta's own inline bbox, so no fetch is waited on) and falls back to
  `FI_BOX`. `zoomSnap` goes from 0.5 to **0.25**, which is what lets the fit land between whole
  zooms rather than rounding down and giving the space straight back. The camera is fitted when the
  national view is opened and again whenever the reader comes back up from a kunta — a pan on the
  national map is theirs to keep (`LF.fitted`) — and a drilled kunta is fitted by `applyPendingFit()`
  at 8 px rather than 12.
- **W2** — **A mini map's legends live behind one `Legend ▾` pill at every width; the macro map's
  stay open.** The pill and the collapse were built in v2.1 for ≤ 1024 px only (spec §6); on a
  desktop the area page, the property page and the two sheets still opened with 40–60 % of a 360–460
  px map under legend cards nobody had asked for. `.mapwrap` gains a `mini` class, the rules are
  scoped `@media (min-width:1025px)` so the phone's own geometry (pill top-right, clear of Leaflet's
  attribution — LEG5) is untouched, and the opened stack is anchored above the pill at bottom-left
  rather than jumping to the opposite corner. The two sheet maps (`#prmap` on the project and
  public-building sheets) had a bare `.maplegend` with no stack and no fold at all; they now use the
  same `.maplegs` and pill, and `prlegend` joins `mmFoldable()`'s "starts open" list because it is a
  choropleth legend like the other three, not a feature layer.
- **W2** — **The macro stack's cap goes 72 % → 60 %, and the legends are made to fit it rather than
  scroll.** 60 % of the 560-px floor is 336 px and five cards at v2.1's spacing measured 382, so
  `P10-legends-inside-map`'s "the stack never has to be scrolled" would have broken. The 46 px came
  out of slack: the gap between cards (8 → 6), each card's padding, the row leading, a 250-px note
  column instead of 190 — and the indicator legend no longer repeats **which level is drawn**, now
  that the info strip above the map says it. What is left of that note is the one thing the strip
  cannot say: *"postal codes take the kunta's value"*.
- **W2** — **One shared chart axis, in `src/scale_core.js` (`window.SCALE_CORE`), with
  `node --test tests/scale.test.js`.** Ticks are 1 / 2 / 2,5 / 5 × 10^n and the range is widened out
  to whole steps instead of padded by 8 %, which is what puts **0 on a gridline whenever the range
  crosses zero** — every tick is a multiple of the step, so it cannot be otherwise. An all-positive
  range is never widened below 0 (a count has no negative part), and the number of ticks is reduced
  until no two carry the same label under the indicator's own format. The area page, the property
  page, the Charts view and the downloaded PNG all read it, so they cannot disagree. The two panel
  charts with an axis but no year series — the climate bars and the population outlook — go through
  the same module by way of a two-point series (`chSpan()`), because the fault §3a describes was
  worst in them: the climate bars drew their middle gridline at `hi / 2`, wherever the taller bar
  happened to end, and labelled it with a rounded number a reader would then measure against.
- **W2** — **The y-range comes from the years every plotted series covers, and nothing is dropped.**
  The plan's case: an osa-alue published from 2014 against the median of all osa-alueet, whose
  2011–2012 jumps ±17 % where areas were redrawn — the area's own line rendered as a flat thread.
  The shared years are the ones a reader can actually compare, so they set the scale; a value the
  axis cannot reach is drawn **on the edge with a ▲ / ▼ in its series colour**, keeps the real figure
  in its tooltip, and the years the scale leaves out are named in a note under the chart (and inside
  the SVG, so the PNG carries it too). A single series excludes nothing — its own years *are* the
  shared ones.
- **W2** — **The note says "scale excludes 2011–2012 (years not every series shown covers)", not
  "(area boundaries changed)".** The plan's example wording names a *cause*. Nothing in this edition's
  data records one: `breaks` is read by `chartBreaks()` but no indicator in `config/indicators.json`,
  `makro.json` or `osa_alue.json` carries a single entry, and Aluesarjat's own metadata says nothing
  about 2011–2012 either. So the parenthesis is taken from `breaks[].text` when the registry has one
  for a clipped year, and is otherwise the fact the chart can prove. A boundary change is a claim
  about the publisher's geography, not something to infer from a jump — hard data only.
- **W2** — **The x axis is trimmed inside `chartSeries()`, not in the drawing code.** The Charts
  view's Data table and its CSV read the same function, so trimming the leading periods nothing is
  published for in one place keeps all three describing the same years; `vCharts()` now takes `ys`
  from `chartSeries()` rather than calling `chartYears()` a second time. The trim is skipped when it
  would leave fewer than two periods.
- **W2** — **The chart card's heading is the area and the period; the indicator keeps its two other
  names.** "POPULATION GROWTH" in caps sat directly under the picker button that said "Growth ▾", and
  told the reader nothing they had not just clicked. The head is `Helsinki · 2011–2025` (the years
  the *area's own* series covers, the projection window for an Outlook indicator, the as-of for
  anything published once), the unit stays in the head's hint exactly once, and the indicator is
  still named on the picker and on the mini map beside the chart. The Charts view's own SVG title is
  **left alone**: it is what the downloaded PNG is identified by, and a reader who opens that file
  weeks later has nothing else to tell them which indicator it is.
- **W2** — **The info strip names the level the map draws, and it is the only place that claim is
  made.** It carried `i.level`, the indicator's *publication* level, so the national map — one
  polygon per kunta — read "postal-code level" whenever a Paavo indicator was selected.
  `mapDrawLevel()` answers from the same predicate `muniAreas()` uses (`subLevelOf()`), so the tag
  and the polygons cannot drift: *municipalities drawn · zoom in for postal codes* nationally,
  *postal codes drawn* inside Tampere, *osa-alueet drawn* inside Helsinki (where the Helsinki-region
  drill really is by osa-alue), *buildings drawn* in Buildings mode. `mkLevelTag()` rewrites the tag
  in place at the end of `lfLayers()`, so a zoom or a drill updates it without a re-render, and the
  tag's `title` still gives the publication level. On the table view, which draws no map, the tag is
  unchanged.
- **W2** — **Two v2.1 checks are adapted rather than weakened, because §2 voids their premise.**
  `legend_live()` (used by six V4/V5 assertions) and `P6-legends-stack` asserted that a mini map's
  legends are *visible*; behind a pill they are not, so both now open the stack first through one new
  `open_legends()` helper — what each then asserts about the legend is unchanged.
  `P10-legends-inside-map` is left exactly as it was: its per-legend geometry loop skips a hidden
  stack, so on its two mini-map routes it now checks nothing, and `W2-minimap-legend-pill` makes the
  same inside-the-map and never-overlapping assertions about the *opened* stack instead.
- **W2** — **`src/app.js` ends the phase 3,0 KB under its 460 KB ceiling, and W3 should move a module
  out before adding to it.** The honest candidates are already pure: `pip` / `bboxOf` / `inBox` /
  `areaOf` and `havM` / `featDistM` / `R_EARTH` are DOM-free, state-free geometry with no test file of
  their own — a `src/geom_core.js` plus `tests/geom.test.js` would free ~3,5 KB and gain coverage.
  W2 did not do it because it is not a W2 item, and an unattended refactor of the point-in-polygon
  code that places every pin, school and public building is the wrong risk to take for a budget that
  is not yet breached.
