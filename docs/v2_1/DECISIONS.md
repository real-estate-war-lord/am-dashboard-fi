# v2.1 — decisions taken while building

Nobody is awake during this run. Every time the brief, the Danish spec and this repo disagree — or say
nothing — the phase picks the option that best fits the Danish spec adapted to Finland and writes one
line here, prefixed with its phase id. Newest at the bottom.

The decisions v2.0 took are in `docs/UI_PLAN.md` §2 (D1–D16) and still hold unless a line below
replaces one.

---

- **V1** — The audit is a table of 176 numbered rows in 21 sections rather than a prose comparison: V3–V7
  cite a row id (`TP11`, `NUM8`) in their commit and in `PROGRESS.md`, so "what shipped" and "what the
  audit asked for" can be diffed without re-reading the Danish spec.
- **V1** — Rows are marked `n/a` only where Finland *cannot* have the behaviour (the National series tab
  and its export, the 2070/2120 horizons, the climate-sheet period control), not where Finland merely
  does it differently. The return period `1/100a · 1/1000a` is recorded as `done (adapted)` against the
  horizon rows, because it is the same control.
- **V1** — The map's layer keys (`infra=1&public=1&services=1&micro=1`) are treated as a **MUST** gap
  (NAV6/LAY4), not cosmetics: the property route already writes `lay=`, and two spellings of one idea in
  one serialiser is exactly what the Danish spec's "one serialiser, one parser" rule exists to prevent.
  V3 must keep the old keys working as aliases — old links never break.
- **V1** — A climate deep-dive sheet (`#climate/<kunta>`, DK AC-SH2) goes to **Later**, not to a phase.
  It is new surface rather than a gap a reader can see: Finland's climate figures already have a home in
  the area page's `clim-bars` and the property's Climate section, and building a sheet unreviewed would
  be the one thing amendment A4 warns against (features over consistency).
- **V1** — `tests/test_codes.py` is red on `csvNum` (`String(Number(v))` at `src/app.js:1731`). That
  function formats **values** for CSV, not area codes, so the lint is a false positive and the code is
  correct. The gate treats the python suite as informational; the row is logged as GLOB5 (SHOULD, V6 —
  narrow the lint, do not change `csvNum`). No data or config file was touched to find this.
- **V2** — **Which indicators are signed.** The rule is "the published values straddle zero", read off
  `data/processed/*.json` rather than off the arithmetic: 13 keys qualify — `growth`, `migration`,
  `migration_dom`, `rent_yoy`, `crime_trend`, `fc_growth`, `fc_growth_5y`, `fc_abs`, `fc_pop_rate_5y`,
  `fc_0_6`, `fc_7_15`, `fc_20_34`, `fc_20_34_rel`. **`fc_80p` does not**: the projected change in the
  80+ population runs from +8,7 % to +108,2 % and no kunta is below zero, so a red class would never
  fill and "darkest = most" stays the honest reading. The list lives in `SIGNED` in `src/ramp_core.js`.
- **V2** — **Thresholds the owner did not name.** Given: growth 0,5 %/yr · net migration and
  intermunicipal net migration 5 per 1 000 · price and rent change 2 % · outlook change 2026→2040 5 % ·
  crime trend 5 %. Extended on the same logic: `fc_0_6` / `fc_7_15` / `fc_20_34` are the same
  2026→2040 window as `fc_growth`, so 5 %; `fc_growth_5y` is the same measure over 2026→2031, a window
  a third as long, so 2 %; `fc_pop_rate_5y` is a rate per 1 000, so 5 like the migration rates;
  `fc_20_34_rel` is a share difference in pp, so 2 like the other two-point thresholds; `fc_abs` is a
  headcount with no family to borrow from — **500 residents**, which is the order of magnitude that
  separates the quartiles of the published values (p25 −634, p75 −7).
- **V2** — **`rent_yoy` at t = 2 % draws a nearly two-class map** — Finnish rents moved less than 2 %
  in 290 of 292 kunnat between the last two vintages, so `< −2 %` is empty and `> +2 %` holds one
  kunta. The owner named 2 % explicitly, so 2 % is what shipped; the flatness is a true statement about
  the data rather than a fault in the ramp. **Worth a morning look**: 0,5 % would give this indicator
  four populated classes without changing the rule.
- **V2** — **The sixth class is decided per indicator, not per map.** The rule is "> 20 % of areas
  beyond ±3t", and it is evaluated once over every level the build ships (kunta, postinumero,
  osa-alue; a level with fewer than 30 published values cannot swing it), then reused by every surface.
  Deciding it per map would have made the same +2 % one green on the national map and a different one
  in a kunta's mini map, which is precisely what RAMP5 forbids. Today's answer, from the shipped data:
  **six classes** for `growth` (25 % · 52 % · 38 % by level), `crime_trend` (37 %), `fc_growth`
  (16 % · 35 %), `fc_growth_5y` (26 %), `fc_7_15` (84 %) and `fc_20_34_rel` (59 %); **four** for
  `migration` (8 %), `migration_dom` (10 %), `rent_yoy` (0 %), `fc_abs` (18 %), `fc_pop_rate_5y` (11 %),
  `fc_0_6` (16 %) and `fc_20_34` (3 %).
- **V2** — **The 3:1 contrast rule cannot hold against the no-data grey, and does hold everywhere else.**
  `#C4CBC4` sits in the middle of the luminance scale (L = 0,58); 3:1 against it would need a swatch at
  L ≤ 0,16 or L ≥ 1,85, so *no* colour of any hue clears it on the light side — the owner's own example
  pair fails it too (`#B5523B` reaches 2,99:1). What shipped instead, and is asserted in
  `tests/ramp.test.js`: every light↔dark pair passes 3:1 within its side; the darkest class of every
  side passes 3:1 against the grey outright; and a pale class is told apart from "no figure" by chroma
  — the grey has 7, every ramp swatch ≥ 24. The reds are the owner's brick-red family, the dark class
  taken deeper (`#8A3A26`, `#7C3121`) than his `#B5523B` so the pair clears 3:1 at all.
- **V2** — **Red/green overrides `direction: neutral` on the choropleth.** `migration`, `fc_growth` and
  the rest of the Outlook family are `neutral` in the registry, and v2.0 therefore never coloured them
  good-to-bad. The owner's rule names them anyway, so the ramp now puts green above zero and red below.
  The wording stays factual — the legend says "green above zero, red below", never "better" — and the
  ⓘ details keep the "neither end is better: a shrinking area is not failing" sentence unchanged.
- **V2** — **Charts' Distribution mode is not the shared path.** Phase item 7 asks for the rule there
  "if the code path is shared". It is not: `chartSvgDist()` draws donuts of a building stock's size
  distribution from `bbr.dist`, which has no signed values, no `scaleOf()` and — in this build —
  `distAvail()` is false, so the mode is not even offered. Nothing to apply the rule to.
- **V2** — The dead Danish `scale: "diverging"` path (`divergingScale()`, `mkShade`'s `hue_neg` branch,
  the `.lgmid` / `.lgctr` legend markers) is **deleted**, not left beside the new one: no indicator in
  `config/indicators.json` carries `scale`, so it never ran here, and two diverging ramps in one file
  is how the next phase picks the wrong one.
- **V3** — **What goes into the map's `lay=` key, and what does not.** Denmark puts three names there
  (`infra`, `public`, `services`) and keeps `micro=1` as a flag of its own. Finland puts **four**: the
  property route has written `lay=infra,public,buildings` since v2.0, so a map that spelled the same
  layer `micro=1` would be exactly the two-spellings-of-one-idea NAV6/LAY4 exist to end. `mind=` stays
  a key of its own — it names *which* building figure is drawn, the way `ind=` does, and is not a
  switch. `wms=` stays too: it is a single-choice value ("which context map"), not an on/off flag, so
  folding it into a comma list would make one key answer two questions. `zones=0` is unchanged (LAY3).
  Every old flag keeps working through `ROUTE_CORE.layerFlags()`, which is idempotent and tested.
- **V3** — **The pin card is a block in the page flow, not a card floating over the map.** DK P10 §1
  says "a small pin card near the toolbar/info strip". Floating it would put a third element into the
  space the toolbar and the legend stack already compete for at 1366 and 390 (SRCH7 asks for exactly
  that not to happen). It therefore sits **between the map area card and the map**, full width, and
  the no-overlap checks at all three widths are true by construction rather than by tuning. Directly
  above the map rather than directly under the toolbar because that is where the thing it describes
  is, and it keeps the kunta's identity card and the pin's identity card next to each other.
- **V3** — **SRCH8 was a specificity bug, not a width choice.** `#mapcard .tools>*{flex:0 0 auto}`
  outranks `.msearch{flex:1 1 330px}`, so the search never grew and collapsed to an input's intrinsic
  ~200 px — the clipped "Search kunta, postinum" in every v2.0 screenshot. The fix is one rule,
  `#mapcard .tools>.msearch{flex:1 1 200px}` with a 470 px cap. The **basis is deliberately the old
  200 px**: a 330 px basis counts towards the flex line, wrapped the 1366 toolbar onto two rows and
  pushed the map to 237 px, breaking AC-S3's 200 px (`P2-map-top-1366`). Growing only spends free
  space, so the row count cannot change at any width. The check measures the placeholder in the
  input's own font rather than asserting a pixel width, so it stays true if either one changes.
- **V3** — **A pin dropped from the search takes the map to zoom 13, and opens no popup.** The old
  code fitted the map to the outermost ring, which made the camera a function of the radius — change
  the radius and the map jumps. `setView(pin, 13)` is the owner's own "sensible zoom, e.g. 13" and
  does not move when the radius does. The marker popup is no longer auto-opened either: it says what
  the pin card now says, and two copies of one answer is one too many.
- **V3** — **The test-property radius moved from row 1 into `Layers ▾`.** With SRCH3 a pin can now be
  dropped from the map itself, so the `Within 500 m · 1 km …` segment would have appeared on the
  toolbar for the first time — a sixth control on a row the spec fixes at four (AC-M1). DK P10 §1 puts
  it in `Layers ▾` ("keep the existing Test-property radius row"), which is also where it belongs: it
  filters the layers that menu switches. It counts towards the `Layers ▾` badge when it is not "Any".
- **V3** — **Two earlier checks were rewritten, not weakened, because the spec voids them.**
  `P2-search-area` asserted that Enter on a coordinate lands on `#property` — DK P10 §1 replaces that
  behaviour outright, so the check now asserts the pin and the map. `P2-layers-menu` asserted
  `infra=1` in the hash — NAV6 replaces that spelling, so it asserts `lay=infra`. Both old spellings
  are still *readable* (the alias table), and `V3-map-lay-key` asserts that they are.
- **V4** — **The radius rings are a member of `lay=`, so an old property link opens without them.**
  DK P10 §3 lists "radius rings" among the layers that must each have exactly one switch, and the
  property's `lay=` key is the only place a layer switch is written. `rings` therefore joins
  `infra · public · services · buildings` there and is **on by default** — but a link written before
  tonight (`…&lay=infra,public`) names the layers it wants, and `rings` is not among them, so it
  opens with the rings off. Nothing is lost and no link breaks: the pin, the fill, the tiles and
  every section are what they were, and one click in `Layers ▾` puts the rings back. The
  alternative — a second opt-out key of the `zones=0` kind — would have put two spellings of one
  idea back into the serialiser, which is exactly what NAV6/LAY4 existed to end.
- **V4** — **The property map's services are bounded by the ring, not by the zoom.** The macro
  map's per-category zoom floors (`SRV_CAT[k].zoom`, `SRV_TGROUP[g].zoom`) exist for one reason: a
  national viewport would otherwise ask for ~95 000 bus stops. Two kilometres around one address is
  a few hundred points at most — 39 at the test pin with the default filter — so the floors are
  switched off on this map (`srvLegendHtml({floors: false})`) and the legend says "N within 2 000 m
  of the pin" instead of "N drawn in view". A reader who zooms the mini map out therefore keeps
  their services rather than watching them vanish at zoom 12.
- **V4** — **`AN_SRV_M` is 2 000 m, the same reach as the public buildings on this map.** The cards
  below count public buildings and schools inside 1 000 m (`AN_RING_M`); the *map* draws twice that
  (`AN_PUB_MAP_M`) so the ring has a context to sit in. Services follow the map's rule, not the
  card's, because there is no services card to disagree with.
- **V4** — **The pin is not a switchable layer; its rings are.** `anMapInit()` used to put the
  marker and the three dashed rings in one group. They are now separate (`LF.anPinG` /
  `LF.anRingG`): the marker is the page and cannot be switched off, the rings are a drawn layer and
  must be (DK P10 §3). The opening frame is computed from the outermost ring's radius
  (`anRingBounds`) rather than measured off a Leaflet circle, so the map opens on the same box
  whether the rings are on or off.
- **V4** — **`TP` now carries the pin on the property route too.** Before tonight `TP.lat` was set
  only by the map's `pin=`, so on `#property` the radius control wrote `rad=` into the URL and
  `tpWithin()` — which is what the radius actually filters with — was never armed. `parseHash()`'s
  property branch now fills `TP.lat/lon/label` from `p=`, which makes TP10 a real filter on this
  page and costs nothing elsewhere: the map's own `tpParse(q)` clears `TP` when a map link carries
  no `pin=`, and `pinCard()` still renders on `#map` only.
- **V4** — **The property picker is the area picker of the place the pin fell in, not a flat
  superset.** `pickCtx()` handed the property `IND ∪ IND_OSA` with `inherits: () => false`, which
  listed every kunta figure as if the osa-alue published it. It now takes `tpEntity()`'s `inds` and
  the area page's own `inherits()`, so the pin's finest level's indicators come first and the rest
  land under **From the municipality** with the `muni` tag (DK P10 §4). `curInds()` got the same
  branch — otherwise `parseHash()`'s "is this indicator selectable here" guard would have reset an
  osa-alue-only `ind=` the picker had just offered. While the kunta rings are still loading nobody
  knows the pin's level, so both fall back to `IND_ANY`, the union — a link's `ind=` must survive
  the wait.
- **V4** — **The flood zones on the property mini map are the same WMS the macro map draws, not a
  second rendering.** `climLayers()` stays the macro map's; the property adds its own tile layer in
  its own `climPane` inside `anMapOverlays()` (`LF.anClimL`), because every layer on this map is
  redrawn from `ANL`/`MK.clim` in that one function and a layer that bypassed it would be exactly
  the "async loader re-adds a layer that is off" bug DK P10 §3 is about. `zones=0` works on both
  routes now and means the same thing on both.
- **V4** — **`tests/ui_v2.spec.py` now also reads its phase and filter from `argv`.** It took
  `PHASE` / `ONLY` / `SHOTS` from the environment only, and the night's tool allowlist admits the
  file by name, not with a variable in front of it — so a phase could run the whole suite or
  nothing. `tests/ui_v2.spec.py V4 V4-` is the same two settings as positional arguments; the
  environment still wins nothing and loses nothing, and `make ui` is untouched.
- **V5** — **The two study-row pages are rendered in three blocks, and the wrappers are
  `display:contents`.** `areaRefresh()` / `tpRefresh()` need something to address, so `vArea()` and
  `vAnalysis()` now emit `#artop` · the study row · `#arsecs` (`#tptop` / `#tpsecs`). `#body` is a
  flex column with a `gap`, so a plain wrapper would have turned two cards into one flex child and
  eaten the gap between the identity card and the toolbar. `display:contents` keeps every card a
  direct flex child and the column's spacing is byte-for-byte what it was; the wrappers exist only
  for `getElementById().innerHTML`.
- **V5** — **`indSet()` stops navigating on the area page and the Test property.** Everywhere else
  it still ends in `go(hashFor())`; on those two it writes the hash with `syncHash()` and calls
  `areaRefresh()` / `tpRefresh()`. The difference is deliberate and narrow: `go()` pushes a history
  entry, and DK's `pickInd()` does not push one either, but changing it on the map and Charts as
  well would have changed what the back button does on four routes to fix a problem that exists on
  two. Both refreshers return false anywhere else, so every call site still falls back to
  `renderKeep()`.
- **V5** — **The flood zones on the *area* mini map have no switch and no `zones=0`.** MM6 asks for
  the zones; LAY3's hide toggle lives in `Layers ▾`, and the area toolbar is `Indicator ▾ · Period`
  and nothing else (AC-M1/AC-P1 — DK's area page has no `Layers ▾` at all). Adding one for a single
  row would have been new surface, so the zones are derived from `ind=` here exactly as `clim=` is
  derived on the map, and the area route writes no `zones=` key. `parseHash()` sets `MK.clim` for
  the area view for the same reason it does for the property: `climLegendHtml()` reads it.
  `arMapZones()` is the area's own tile layer in its own `climPane` (`LF.amClimL`), never
  `climLayers()`, which stays the macro map's — the rule V4 set for `LF.anClimL`.
- **V5** — **Finland's public-building register publishes no key, so one is derived in the loader.**
  Every `data-pubsheet` in this build read `undefined`: `dist/public/<kunta>.json` carries
  `cat · kind · name · address · lat · lon · src · sub` and neither an `id` nor a `kom`, so
  `#public/<kunta>/<id>` was unreachable and `pubPopup()` threw on `b.id.slice(0, 8)`. `pubStamp()`
  now sets `kom` and `id = <slug of the name>@<lat>,<lon>` — the two things that identify a building
  in that register, so the link survives a rebuild. No data file was touched; this is a UI-side
  key over what the publisher already gives.
- **V5** — **The public-building list and sheet were rewritten against the fields Finland
  publishes.** They were still the Danish BBR sheet: floor area, year built, permit case, owner,
  "6 Opført", a use code — none of which Palvelukartta or OpenStreetMap publish, so the list drew
  four columns of `–` and the sheet three tiles of `–`. That is filler, which AC-SH1 forbids, and
  it is also a claim the sources do not support. What is shown now is what is published: category,
  service type, address, municipality, the postal code and osa-alue found from the coordinate, the
  publisher and the record id — and one sentence saying plainly that Finland's register has no
  floor area, no year built and no permit case. The list's postal-code and osa-alue filters are
  answered from the published rings for the same reason: the register states no postal code.
- **V5** — **The climate exposure file names a return period, never a year.** Denmark's
  `climate_exposure.csv` is level × horizon (2070, 2120). Finland's is level × **return period**,
  because a return period is a probability and not a date (D13): the column reads `1/100a`, the
  hazard sits in a column of its own (`sea flood` · `river flood` · `radon`), and a check asserts no
  value in it ever matches four digits.
- **V5** — **Two earlier checks were widened, not weakened.** `P1-sources-fetched` read the Fetched
  column by a fixed index; EXP8 adds a Publisher column, and an index would silently have started
  asserting on As-of instead, so the check now finds the column by its header — it can no longer
  pass by reading the wrong one. `P7-menu` asserted the export menu is exactly five items; EXP10
  adds a sixth, so it now asserts the five v2.0 items are still there in their old order and that
  `climate` is the only addition.
