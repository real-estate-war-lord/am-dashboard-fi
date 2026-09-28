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
- **W3** — **The resolution order is osa-alue → postal code → kunta, and the middle step is new.**
  Until tonight `eVal()` fell from an area straight to its kunta, because the only entity that ever
  inherited was an area *page*'s — and an osa-alue page has no single postal code to fall to. A
  **pin** does. So the middle step is carried on the entity (`pno`, filled by `tpEntity()` from the
  same `locate()` answer the header's tags are drawn from) rather than being guessed from geometry,
  and `fbChain()` is the one list every reader of a figure now walks: the tiles, the panel head, the
  Area profile table, the percentile bar's peer pool, the Verify link and the property CSV. The
  practical effect on the plan's own pin (60,2448 / 24,8665, 00410 Malminkartano): **Price** was
  Helsinki's 5 090 €/m² labelled "municipality figure" and is now 00410's own **2 280 €/m²**
  labelled "postal-code figure", and **Unemployment** was Helsinki's and is now 00410's **15,2 %**.
  An indicator the osa-alue layer publishes itself (`osaOwn`) is still never inherited at all.
- **W3** — **Rent and reported crime stay municipality figures on that pin, and that is the right
  answer, not a missed step.** 00410 *does* carry a `rent_pno` of 18,4 €/m²/month — but `rent_pno`
  is a **different indicator**, not a postal-code vintage of `rent`: Tilastokeskus discontinued the
  postal-code rent table (asvu 13eb) at 2025Q4, and the registry entry for it says in its own `warn`
  that it "is never extended and never blended with the live kunta-level rent". Blending them to
  make a tile look finer would be exactly the kind of quiet splice this dashboard exists not to do.
  `crime_1000` is published per kunta only, for the whole country, so there is nothing finer to
  reach for. Both keep saying "municipality figure", and the ⓘ in the header now names the chain so
  a reader can tell a missing level from a coarse one.
- **W3** — **The five-pin audit, as the page answers it tonight** (`own` = the pin's own area,
  `P` = taken from the postal code, `K` = from the kunta; the five tiles in their fixed order):

  | pin | resolves to | growth | price | rent | unemp | crime |
  | --- | --- | --- | --- | --- | --- | --- |
  | 60,2448 / 24,8665 | Helsinki · 00410 Malminkartano · osa-alue Malminkartano | own | **P** | K | **P** | K |
  | 60,1757 / 24,8050 | Espoo · 02100 Tapiola · osa-alue Tapiolan Keskus | own | **P** | K | **P** | K |
  | 61,4978 / 23,7610 | Tampere · 33200 Tampere Keskus Läntinen | own | own | K | own | K |
  | 65,0121 / 25,4651 | Oulu · 90100 Oulu Keskus | own | own | K | own | K |
  | 64,8680 / 27,6700 | Puolanka · 89200 Puolanka Keskus (rural) | own | — | K | own | K |

  Only the two Helsinki-region pins are read on an osa-alue, so only they can use the middle step;
  Tampere, Oulu and Puolanka resolve to a postal code, which is already the finest level there is.
  **Puolanka publishes no `price_m2` at any level** — 89200 has no figure and neither has the kunta —
  so the tile is not filled with something coarser: it drops out and `Renters` takes the fifth slot,
  which is what "always five tiles, never a filler slab" has meant since v2.0.
- **W3** — **The first screen is bought from the header, not from the content.** At 1440 × 900 the
  study row started 496 px down: a 30-px name on its own line, five action buttons on a second, the
  tiles on a third, a sentence under them, and then a whole card containing nothing but the picker,
  Layers ▾ and the period control. The name, its area tags and the actions now share one line (the
  tags wrap inside their own block rather than pushing the actions down — `flex:1 1 340px`, because
  at `auto` the block measures ~720 px against the 545 px left beside the buttons and wrapped
  whole), the sentence is an **ⓘ** next to the tags, and the toolbar card is gone: its row is the
  study row's own full-width header (`.strhead`, `#tpbar`). The row starts at **265 px** and the
  chart itself at 372. Nothing was removed — the sentence gained the fallback chain it never named,
  and Layers ▾ keeps its count badge. The one-line rule is scoped to **≥ 1280 px** rather than the
  usual 1025: the sidebar takes 250 px, so below that there is less than 340 px left beside the five
  actions and the identity block would collapse into a column instead of wrapping into two lines.
  Every tablet and every phone keeps the stacked header, and `W3-mobile-stays-stacked` asserts it.
- **W3** — **Export ▾ in the property header opened off the top of the page, and does not now.**
  `.exmenu`'s default is `bottom:100%; left:0` — written for the footer button, which has a whole
  screen below it and nothing above. Moving Export ▾ to the right-hand end of a one-line header put
  the menu 27 px past the window at 1536 *and* 340 px above the top of the page. It opens down and
  right-aligned inside `.anhead` now, in the same `min-width:1280px` block, so the stacked header
  below that keeps the default it was passing with. The upward open was already off-screen before
  W3 — the shorter header only made it further off — so `V4-property-export` gained two assertions
  that the menu is on the screen at all, which is what the check thought it was already saying.
- **W3** — **`V4-property-head-one-line` is adapted, not weakened.** It asserted the opposite of what
  §1 asks for — that the identity block claims a line of its own — so the same check now asserts the
  name, the tags and the actions share one line, that the actions do not overlap the identity block,
  and that the tiles still start at the title's left edge and below both. That last pair is what the
  original was really protecting (audit TP18); only the line count changed.
- **W3** — **The tile row is 84 px at 1440 and 112 at 1366, and the 1366 case is left alone.** At
  200 px of tile the Rent value "21,3 EUR/m²/month" takes two lines. That is true on the area page
  too and was true before W3; forcing the unit onto one line is precisely what used to paint it over
  the tile to its right (audit TILE5), and the denominator is one unbreakable token by NUM3. So the
  plan's ≤ 84 is asserted where the plan states it, at 1440, and 1366 is held at its own measured
  height so it cannot grow either.
- **W3** — **`src/geom_core.js`, with `node --test tests/geom.test.js` — the move W2 handed over.**
  `pip` / `inPoly` / `bboxOf` / `inBox` / `areaOf` and `R_EARTH` / `havM` / `featDistM` are pure, and
  they place every pin, school and public building on the page; they had no test of their own. They
  are now one IIFE exposing `window.GEOM_CORE`, aliased at the top of `app.js` so every call site
  reads exactly as it did, wired into `src/index.html` and `scripts/build_dashboard.py` (including
  its `check_js()` list) in this commit, and covered by eleven tests — among them the two bugs the
  comments in that code record: the inside-out bbox that must never be cached while rings are still
  loading, and a polygon being its outer ring *minus its holes*. `src/app.js` ends the phase at
  **459,2 KB of 460**.
- **W3** — **The page ceiling in `build_dashboard.py` goes 3,2 MB → 3,3 MB.** v2.1 shipped 2 KB under
  it and v2.2 is a release whose whole subject is the interface, so W2 and W3 together put the page
  6 KB over. No data changed: the payload is the same 3 018 areas and the same registry, still
  written with compact separators, and everything that can be lazy still is. The two ways out of a
  6 KB overrun were "delete the comments that explain this code" and "move the number" — and the
  comments in `src/*.js` are where every decision of the last three releases is written down, so
  they are worth more than the bytes. The reason is written at the constant, beside v1.1's own
  raise, and 3,3 MB still fails loudly if a *series* is ever inlined again (~94 KB for W4–W6).
- **W4** — **Present mode is a whole file, `src/present.js` (`window.PRESENT`), because app.js had
  787 bytes left.** W3 ended at 459,2 KB of the 460 KB budget, so the three W4 items could not be
  written where the code they touch lives. The file is *not* a `*_core.js`: it reads `S`, `UI`,
  `MK`, `D` and calls `renderTop()`, `syncHash()`, `esc()` by name, the way `src/testprop.js`
  already shares app.js's global lexical scope, and it is inlined **before** app.js so its own
  `click` and `keydown` listeners run first — that is what lets `P` and Esc be answered without
  reopening the key handling of three earlier phases. What is genuinely pure — the footer line, the
  composite PNG's geometry, the file name — takes arguments and is covered by 13 tests in
  `tests/present.test.js`. app.js keeps six hooks and `UI.present`, and ends the phase at
  **470 931 B of 471 040** — see the note at the end of PROGRESS W4: **W5 must move the chart-SVG
  builders out before it adds a line.**
- **W4** — **`present=1` is written last in `hashFor()`, after the two views that clear the query.**
  Charts and Test property both do `q.length = 0` and rebuild their own key list, so a push placed
  with the other map keys would have been dropped on exactly the two views the plan names. Present
  mode is a property of the *link*, not of the machine: a presented view can be mailed to someone,
  and every old link (which carries no `present=`) opens as it always did.
- **W4** — **Present mode hides controls and nothing else.** The plan's "nothing is removed from the
  data" is asserted rather than promised: `W4-present-numbers-bigger` counts the tiles, the
  `<details>` sections and the `.cap` caveats with and without `present=1` and requires the three
  counts to be equal. What goes is the sidebar, the four toolbars, the chips rows and the Data tab
  bar — every one of them an affordance for a reader with a mouse, and together the first ~300 px of
  each screen. The `Legend ▾` pill W2 §2 introduced goes too, with the legends left *open*: clicking
  a pill in front of an audience to find out what the colours mean is the thing the pill was
  supposed to save them from.
- **W4** — **The one thin line takes the breadcrumb's place rather than sitting under it.** The plan
  asks for "indicator name, period, area" and the top bar was already carrying the area as a crumb
  trail with a link on every step. Two rows saying overlapping things is what W2 §4 removed from the
  chart card, so in present mode `#hd` renders `PRESENT.line()` instead of `crumbs()`: the
  indicator in the display face, then the period and the area path in mono. The period is
  `panelPeriod()` on the area page and the property — the same function the chart card's own head
  uses — so the bar cannot claim a span the chart is not drawing.
- **W4** — **The source footer names the publishers, not the tables, and its as-of is the newest one
  in the build.** A screen that is being photographed in a meeting has to carry its own provenance,
  but a line that lists twenty table ids is not read by anyone. So: the distinct publishers behind
  the build's sources (the parenthetical in "Tilastokeskus (Paavo)" dropped first, so the same body
  is not named twice), at most four with the rest counted, then the newest `asof` any source
  carries, then the address of the live page. The full source list is one Esc and one *Data
  information* fold away, and Sources has never moved.
- **W4** — **The study-row PNG is made out of the page, not re-derived from the data.** The panel's
  chart is already an SVG and the mini map is already a stack of tiles, `<canvas>` renderers and
  overlay `<svg>`s that each know where they are; the export copies them onto one canvas in painting
  order — by the z-index of the pane, not by DOM order, because the custom panes (services 450,
  public 440, zones 455) are appended in creation order and would otherwise land under the markers.
  No library was added and nothing is fetched. Two things had to be handled by hand: the panel
  charts are styled by `src/style.css` and a stylesheet does not travel inside a `data:` URL, so the
  clone carries every drawn property inline, copied from the original's *computed* style; and the
  pin is a CSS-drawn `divIcon` with no text in it, so it is redrawn rather than copied.
- **W4** — **The chart in the PNG is never stretched, and the map has a floor.** The area page's
  panel chart is a 900 × 240 strip; drawn to fill a square it would be a chart whose slopes lie, and
  drawn at its own ratio with the map matched to it the map came out as a 100-px band of colour
  with nothing readable in it. So the chart keeps its aspect exactly, the body of the picture has a
  **360-px floor**, and the map takes the full body height beside it. The chart's own key is HTML
  next to the SVG rather than inside it (`.bleg`), and so is W2 §3's clipped-scale note — both are
  redrawn under the chart, because a picture of a chart whose lines are not named is not a chart,
  and a scale that excludes years has to say so wherever it is shown.
- **W4** — **On a phone, present mode keeps the `Legend ▾` pill and un-pins the source line.** Both
  rules that make present mode work on a projector are wrong below 1025 px: the map there is 55vh,
  so an open five-card stack would cover most of it (the pill is the only way both the map and its
  key fit), and the page scrolls as a document, so a bar bolted across the bottom of an 844-px
  screen costs a tenth of it for a line nobody is presenting from a phone. Both are scoped; the
  sidebar, the toolbars and the bigger numbers apply at every width.
- **W4** — **"basemap omitted" is measured, not assumed.** `tile.openstreetmap.org` sends no CORS
  header, so drawing one of its tiles taints the canvas and `toBlob` then throws — which would lose
  the whole picture rather than the basemap. So before anything is composed, one loaded tile is
  drawn into a 2 × 2 scratch canvas and a single pixel is read back: if that throws, the map panel
  is filled with the page's own paper colour, only the polygons and labels are drawn on it, and the
  footer of the image says **· basemap omitted**. When the tiles *are* readable — a same-origin or
  CORS-enabled basemap, which this build could switch to without touching this code — they are
  drawn and the footer says nothing. The test environment answers every off-machine image with a
  cross-origin pixel, so `W4-study-png` exercises the omitted path deliberately.
- **W4** — **The print sheet gives the maps a height in millimetres.** W2 §1 measures the map card
  against the window in JavaScript, and `100vh` means nothing on paper: printed, a Leaflet container
  with no height is a clipped grey strip. So `@page{size:A4 landscape}` plus a fixed 108 mm for the
  macro map and 88 mm for a mini map, the legends unfolded (on paper they can never be behind a
  pill), `break-inside:avoid` on every card and `break-after:page` on the study row, which is what
  "one view per page" means here. `beforeprint` tells every live map its container changed shape —
  without it Leaflet prints the tiles it had at the old size.
- **W4** — **The `P` and Esc keys are answered in `present.js`, before app.js sees them.** app.js's
  own `keydown` handler ends with the map's camera jumps (H/T/U/O/F) and, two lines above them,
  `Escape` on the area page means *go back*. Rather than thread present mode through that, the new
  listener is registered first and calls `stopImmediatePropagation()` on the two keys it takes.
  Neither is taken while the reader is typing, with a modifier held, or — for Esc — while a popover,
  the drawer or a full-screen mini map is open: those own Esc already, and leaving present mode with
  a menu still on the screen would close the wrong thing.
- **W5** — **The chart drawing left app.js, and W5's own code never entered it.** W4 ended 109 bytes
  under the 460 KB budget and scoped the move: `chartSvg` … `chartSvgLine` is now `src/chartsvg.js`
  (`window.CHARTSVG`), exporting exactly the four names the rest of app.js ever asked it for
  (`chartSvg`, `chTitleLive`, `DIST_DEFS`, `fmtP`). That freed 16,0 KB — and W5 then spent almost
  none of it on plumbing: the phase's arithmetic is `src/w5_core.js` (pure, node-tested) and its
  drawing is `src/w5.js` (`window.W5`), so app.js gained ~1,5 KB of aliases and hooks and ends the
  phase at 460,7 KB of 471,0. Both new files are inlined **before** app.js and read app.js's own
  `S` / `UI` / `MK` / `T` out of the shared script scope, the way `present.js` has since W4.
- **W5** — **Pinned chips are this browser's, never the link's.** PICK10 says localStorage and the
  plan says max 12; what it does not say is whether the pins ride in the URL. They do not. A link is
  a thing a reader sends to someone else, and a link that silently re-pinned a stranger's chip row
  would be a link that changes their tools rather than showing them a figure. So `amfi.pins.v1` is
  read and written inside try/catch (Safari in private mode throws on write) and nothing about it
  reaches `hashFor()`. The row is all-or-nothing rather than additive: six default quick chips until
  the reader pins one, then **their** list only. Twelve defaults plus twelve pins is eighteen chips
  and a third toolbar row at 1366 px, which is the width W2 §1 tuned the map card for. The cap drops
  the pin made longest ago rather than refusing the click — a reader who pins is saying what matters
  now.
- **W5** — **`Columns ▾` chooses indicator *groups*, not single columns, and the export ignores it.**
  Data › Areas is 40+ columns wide; a per-column chooser would be the same wall of names the table
  already is, and it could not go in a URL anyone would read. A group can: `cols=Market,Taxes`. No
  key at all means every group, so every link written before tonight still opens the table it always
  did. Two things are never taken away: the column the table is **sorted by** (it is what the order
  means) and every column in the CSV — what is hidden here is a reading aid, not a claim that the
  figure does not exist. Ticking the last missing group back on drops `cols=` rather than listing
  them all, so one state has one spelling.
- **W5** — **A sub-area sparkline is drawn on its own scale, and a gap is a gap.** AREA7 asks for the
  last ten years per row. A shared scale across forty postal codes would flatten every one of them
  against Helsinki's range; a row-local scale says *shape*, and the figure is in the cell to its
  left — which is why the column header reads "own scale" and the column is not sortable. A year the
  publisher did not publish **breaks the line** rather than being bridged: a postal code that
  published nothing in 2019 did not hold its 2018 value. Fewer than two published years draws a dash,
  because one point is not a trend.
- **W5** — **SHEET4 groups on name + category + type *and a distance*, not on the address.** The
  Danish item is "identical rows", but Finland's register is not Denmark's BBR: Palvelukartta and
  OpenStreetMap publish one row per building, and the duplicates that do exist — `Päiväkoti
  Kesäheinä` in Helsinki is the clean case — differ in exactly the field an address-based key would
  split on ("Isonniitynkatu 7" and "Isonniitynkatu 7 D", eleven metres apart). So the key drops the
  address and the caller adds `≤ 150 m`, which is the same shape as the property sheet's TP9 rule
  (name + use code + distance ±20 m) at list scale. Two `Kirkonkylän koulu` at opposite ends of a
  kunta stay two rows. Nothing is dropped: the badge is the register's own count, the head says how
  many rows the register has, and the sheet the row opens is the first part's.
- **W5** — **A Climate bar chart draws both return periods, with no median tick.** The audit logged
  "a Climate chart draws one return period" as a Charts change rather than a parity fix, because in
  this edition the return period *is* the indicator (D13). A reader looking at a 1/100a bar is
  asking "and how much worse in the rarer event?", so the bar chart now draws the whole family:
  one row per area × return period, the pairs kept together and ordered by the commoner period, the
  rarer one in the area's own colour mixed 45 % toward white so a pair reads as one area rather than
  two. The median tick is **off** in that mode and the footer says so — a single dashed line on an
  axis carrying two different measurements could only ever belong to one of them.
- **W5** — **`g p` belongs to the Test property, so present mode stops taking `p` mid-sequence.**
  W4 gave `P` to present mode in a listener registered before app.js's. W5's `g` prefix would have
  been eaten by it on the second keystroke, so `present.js` now skips `p` while `W5.KEYS.pending`
  is `"g"` — one condition, in the file that owns the key, rather than threading the sequence
  through two handlers. Everything else about `P` is unchanged.
- **W5** — **The `?` button is out of the tab sequence, and the `?` key is the keyboard's way in.**
  The sidebar comes before the map in the document, so *any* focusable control added to it pushes
  the indicator picker one Tab further from the top — and `V6-keyboard-popovers` guarantees the
  picker is reachable in twelve, which is the stronger promise. The first build of this failed that
  check at thirteen. So the button carries `tabindex="-1"` (it stays in the accessibility tree, and
  a screen reader still lists it), the build line next to it now *says* "press ? for shortcuts" so
  the feature is not folklore, and the keyboard route to the overlay is the key the overlay is
  about. The check was not relaxed.
- **W5** — **The drill is announced; the zoom is not.** A11Y8 asks for a live region on drill.
  `announce()` writes only when the sentence *changes*, which is what makes "zooming never changes
  the selection" (a v2.0 hard principle) true for a screen reader too: a zoom redraws the same
  layer of the same area and produces the same string, so nothing is said. Buildings mode is
  announced by name with no count — the building file is lazy, and a count read before it lands
  would be a wrong number rather than a missing one.
