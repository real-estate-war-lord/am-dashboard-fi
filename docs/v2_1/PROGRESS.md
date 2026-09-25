# v2.1 — what each phase shipped

Branch `v2.1-ui`, seven sequential unattended phases (V1…V7) bringing the Danish v3.0 UI to full parity
in this repo and adding the owner's colour rule for signed indicators. Live today: FI v2.0 (tag `v2.0`,
branch `main`). **Never pushed, merged or tagged by a phase** — `./overnight.sh release` does that in the
morning.

Read alongside `PARITY_AUDIT.md` (the gap list, written by V1 — phases cite its row ids) and
`DECISIONS.md` (every choice taken in the dark).

---

## V1 — parity audit and the harness ☑

Gate: `./overnight.sh gate V1` green — build ✓, 48 node tests ✓, 70+1 ui checks ✓, budgets
`src/app.js` 400 KB / 460, `src/style.css` 137 KB / 165. (The python unit suite is red on one
pre-existing false positive; the gate treats it as informational — see DECISIONS V1 and audit row GLOB5.)

**Built**

1. **`docs/v2_1/PARITY_AUDIT.md`** — 176 rows in 21 sections, each `DK item · FI status · evidence ·
   target phase · MUST/SHOULD`. Read against `ref/UI_SPEC_v3.md` (with amendments A1–A4),
   `ref/UI_V3.md`, `ref/QA.md` (Q1–Q14, O1–O10), `ref/DK_P10.md` and `ref/dk_src/`, on one side, and
   `docs/UI_PLAN.md`, `src/app.js`, `src/route_core.js`, `src/picker_core.js`, `src/style.css`, the 70
   existing checks and the `docs/ui_v2/` screenshots on the other. Every MUST gap is assigned to V2–V6;
   the rest is a "Later" table at the bottom with a reason per line.
2. **`docs/v2_1/PROGRESS.md`** (this file) and **`docs/v2_1/DECISIONS.md`** created.
3. **Harness** — `PHASES` in `tests/ui_v2.spec.py` already carried V1…V7 (the wrapper added them).
   Added one check, `v21_audit_exists` (phase V1): the audit file exists and still has ≥ 40 rows, so a
   later phase cannot quietly empty the list it is judged against.

**No app code was changed in V1.**

**The headline findings** (full list in the audit)

- **V2, the colour rule.** `docs/ui_v2/map_1440.png` is the case for it: Population growth draws five
  green quantile bins (`> +0,3 %` … `≤ −1,6 %`), so a shrinking municipality is green and zero is
  invisible. One ramp path (`scaleOf()` `src/app.js:944`) feeds the map, both mini maps and the
  distribution strip, so the fix lands everywhere at once — and must be asserted everywhere (RAMP4/5, LEG7).
- **V3, the map.** The pin infrastructure already exists (`pin=`, `pl=`, `rad=` in the map hash;
  `tpLayers()` draws the marker and the rings on the macro map) — a pasted coordinate simply navigates
  away instead of using it (`msPick()` → `tpDrop()` → `go(propLink(…))`). There is no `search-coord`
  test id and no pin card. Separately, the map serialises its layers as `infra=1&public=1&services=1`
  while the property route writes `lay=`: one key, old ones as aliases (NAV6/LAY4).
- **V4, the test property.** The biggest block of work. The property map has a **chip row**
  (`tpMapTools()` `src/app.js:3502`), not the shared `Layers ▾`: no Services layer, no flood zones
  (`wmsLayers()`/`climLayers()` both start `if (!LF.map) return`), no switch for the legends that float
  in the mini map, and the radius lives in a second control. The picker offers the full indicator list
  including Climate, but `pickCtx()` sets `inherits: () => false` on that branch, so there is no
  "From the municipality" heading and no `muni` tag. `Export ▾` is missing from the header, and
  `.anhead .arid{flex:1 1 420px}` (`src/style.css:1639`) is the exact value DK had to change to
  `flex:1 1 100%` to stop the header splitting into two columns at 1536 px.
- **V5, in-place refresh.** `indSet()` ends in `go(hashFor())` → a full `render()`. `renderKeep()`
  restores `#main.scrollTop`, so the AC's letter is met, but the Leaflet map is destroyed and rebuilt:
  the mini map loses its zoom and `⤢` full screen closes on every chip click. DK solves it with
  `pickInd()` → `areaRefresh()` / `tpRefresh()` (`ref/dk_src/app.js:995`, `:2401`) — port those.
- **V6, the sweeps that do not exist yet.** No accessibility check of any kind; `P10-retired-words`
  sweeps six v1.1 control names but not `score` / `weighted` (AC-G1); `tpRadLabel` renders `1.2 km` with
  a `.` decimal under a fi-FI UI (DK Q13); and at 390 the RENT tile clips its own unit
  (`21,3 EUR/m²/mont`, `docs/ui_v2/area_kunta_390.png`).

**What the next phase must know**

- The audit is the contract. V2 is fixed scope (RAMP4, RAMP5, LEG7) and must not drift into other rows.
  Every later phase: do its MUST rows, cite the row ids in `PROGRESS.md`, and register one check per
  delivered row with `@check("<id>", phase="<V…>")`.
- Nothing in `src/` was touched, so V2 starts from a green gate on a clean tree. There is ~60 KB of
  budget headroom in `src/app.js` and ~28 KB in `src/style.css` for V2–V6; a new `src/ramp_core.js` must
  be wired into **both** `src/index.html` and `scripts/build_dashboard.py` in the same commit (a
  colliding top-level `const` blanks the page).
- `docs/v2_1/ref/**` is read-only, and so are `data/`, `config/`, `.github/` and every `scripts/*` file
  except `build_dashboard.py`. Two audit rows (RAMP6, GLOB5) are daytime tasks for exactly that reason.

---

## V2 — the colour rule for signed indicators ☑

Audit rows closed: **RAMP4, RAMP5, LEG7** (the whole of V2's fixed scope). Gate:
`./overnight.sh gate V2` green — build ✓, **67 node tests** ✓ (48 + 19 new), **77 ui checks** ✓
(71 + 6 new), budgets `src/app.js` 403 KB / 460, `src/style.css` 137 KB / 165. The python unit suite
is still red on the one pre-existing false positive (GLOB5) and is still informational.

**Built**

1. **`src/ramp_core.js`** (new, 11 KB, IIFE → `window.RAMP_CORE`, wired into `src/index.html` and
   `scripts/build_dashboard.py` as `{{RAMP_JS}}` in this commit). Everything about the signed ramp
   that is a function of the registry and the numbers, and nothing about the DOM:
   - `SIGNED` — **the one table**: 13 indicator keys, one threshold each. `growth` 0,5 %/yr ·
     `migration` / `migration_dom` 5 per 1 000 · `rent_yoy` 2 % · `crime_trend` 5 % · `fc_growth` /
     `fc_0_6` / `fc_7_15` / `fc_20_34` / `fc_pop_rate_5y` 5 · `fc_growth_5y` / `fc_20_34_rel` 2 ·
     `fc_abs` 500 residents. `fc_80p` is deliberately **not** signed (every kunta is above zero).
   - `signedScale(vals, t, {family, flip, wide})` → fixed breaks `[−t, 0, +t]`, or
     `[−3t, −t, 0, +t, +3t]` when the sixth class is called for. Classification is `>=`, which is
     what puts **exactly 0 in the `0 … +t` class** and makes the extreme classes open-ended.
   - Colours: greens from the observed ramp's own hue, reds from the owner's brick red (taken
     deeper at the extreme so the pair clears 3:1), purples for a projection's positive side.
     `flip: true` (`crime_trend`) swaps the sides and nothing else.
   - `labels()` / `legendNote()` / `LEGEND_FOOTER`, and `contrast()` / `lum()` / `chroma()` /
     `warmth()` so the colour claims are asserted rather than asserted *in prose*.
2. **`src/app.js`** — one shader for every fill, `shadeOf(sc, t, key)` (`:927`), replacing nine
   direct `mkShade()` calls; `scaleOf()` takes the signed branch before quantiles; `darkFill()`
   replaces `t > .55` for map-label contrast (on a signed ramp the darkest class is at the *bottom*
   of the class list, so the old test put light text on a pale green); `legendHtml()` renders the
   signed labels, the `.lgzero` rule on the zero line and the footer; `distStrip()` colours its dot
   from the same scale and draws a zero line. **Deleted**: `divergingScale()`, `mkShade`'s
   `scale === "diverging"` branch and the `.lgmid` / `.lgctr` CSS — dead Danish code, no FI
   indicator carries `scale`.
3. **`signedWide()`** (`src/app.js:938`) — the sixth-class decision, taken **once per indicator**
   over every level the build ships and then reused by every surface. Six classes today:
   `growth`, `crime_trend`, `fc_growth`, `fc_growth_5y`, `fc_7_15`, `fc_20_34_rel`; four for the
   other seven. Numbers per level in DECISIONS V2.
4. **Tests.** `tests/ramp.test.js` — 20 `node --test` cases: the registry, the breaks, the class
   edges, zero, the flip, the ±3t rule (including that exactly 20 % is not "more than 20 %"), the
   `t()` round trip, the labels, and four contrast assertions, two of which run against
   `data/processed/*.json`. Six ui checks under phase V2: `V2-signed-legend`,
   `V2-signed-lower-better`, `V2-signed-not-quantiles`, `V2-same-ramp-everywhere`,
   `V2-dist-strip-dot`, `V2-sequential-untouched`.

**Deviations** (all in DECISIONS.md V2, with the reasoning)

- The owner's "**3:1 against `no data` grey**" is unachievable and his own example colours fail it:
  `#C4CBC4` sits at L = 0,58, so no colour reaches 3:1 from the light side. What is asserted instead:
  3:1 within each side, 3:1 for the darkest class of each side against the grey, and chroma ≥ 24
  against the grey's 7 for every swatch.
- **`rent_yoy` at the owner's t = 2 % is nearly a two-class map** — 290 of 292 kunnat moved less than
  2 %. Shipped as specified; flagged for a morning look (0,5 % would populate four classes).
- Red/green now applies to indicators the registry calls `direction: neutral` (`migration`, the
  Outlook family). The legend wording stays factual ("green above zero, red below"), and the ⓘ
  details keep their "neither end is better" sentence.
- **Charts' Distribution mode was left alone**: it draws `bbr.dist` donuts, shares no code with
  `scaleOf()`, and `distAvail()` is false in this build, so the mode is not offered at all.

**What the next phase must know**

- `src/ramp_core.js` is the third `window.*` core beside `ROUTE_CORE` and `PICKER_CORE`. In
  `src/app.js` it is `RMP`, **not** `RC` — `RC` was already the route core (`:493`), and a second
  top-level `const RC` blanks the page. A new `src/*.js` still needs both `src/index.html` and
  `scripts/build_dashboard.py` in the same commit.
- **Never call `mkShade()` directly from a new fill.** `shadeOf(sc, t, key)` is the one shader; a
  raw `mkShade()` silently draws a signed indicator in the sequential green ramp. Same for
  `darkFill(sc, t)` instead of `t > .55` anywhere a map label sits on a fill. V4 (property layers)
  and V5 (area mini map) will both add fills — use these two.
- `legendHtml()` now has a signed branch. V4/V5 legends that go through `setLegend()` get it for
  free; anything that hand-rolls a legend must not.
- Nothing in the routing, the picker, the period control or the export changed, so V3's map work
  starts from the same surface V1 audited.
- Seen in the screenshots and **not** V2's to fix: at 390 the `Legend ▾` pill overlaps Leaflet's
  attribution line (`docs/ui_v2/map_390.png`), and the RENT tile still clips its unit
  (`21,3 EUR/m²/mont`, audit row TILE5). Both belong to V6.

---

## V3 — the map: the pin stays on the map, and one `lay=` key ☑

Audit rows closed: **SRCH3, SRCH4, SRCH5, SRCH7, SRCH8, NAV6, NAV7, LAY4, MAP7** — every MUST the
audit assigned to V3, plus both of its "if there is room" rows. Gate: `./overnight.sh gate V3`
green — build ✓, **69 node tests** ✓ (67 + 2 new), **86 ui checks** ✓ (77 + 9 new), budgets
`src/app.js` 405 KB / 460, `src/style.css` 138 KB / 165. The python unit suite is still red on the
one pre-existing false positive (GLOB5) and is still informational.

**Built**

1. **A pasted location drops a pin and the reader stays on the map** (DK P10 §1; SRCH3, SRCH5).
   `msPick()` no longer sets `TP.toProp` — the flag is **deleted**, and with it the "sent here by
   the unified search" branch of `tpDrop()`, which now reads simply "on the Test property page the
   box replaces the pin in place; everywhere else the pin lands on the macro map". A coordinate, a
   Google Maps link and a picked address all take the same road. The dropped pin drills to its own
   kunta (`map/<code>[/postinumero]`) carrying `pin=`, `pl=` and `rad=1000` — the 1 km rings the
   owner reads an area at — and `tpLayers()` does `setView(pin, 13)` instead of fitting the
   outermost ring, so the camera no longer moves when the radius does. The marker popup is not
   auto-opened any more: the pin card says what it said.
   The search dropdown's coordinate row is now **"Drop a pin here"** with the coordinates as its
   sub-line and carries **`data-testid=search-coord`** (it had no test id at all); the address row
   ends "— drop a pin here".
2. **The pin card** (`pinCard()`, `data-testid=pin-card`; SRCH4, SRCH7). Label, the coordinates as
   they were read, **osa-alue › postinumero › kunta** finest-first (with the `approx.` tag when the
   kunta came from the postal code), `View test property ›` (`data-testid=pin-open` → `#property?p=…`)
   and `×`. It renders into `#mkpin` **between the info strip and the map**, in the page flow — not
   floating over the map — so there is no width at which it can cover the toolbar or the legend
   stack. It re-renders from `mkRefreshTools()` and when the kunta ring file lands, so the area
   names fill in rather than the card appearing late.
3. **One `lay=` key on the map** (NAV6, LAY4). `hashFor()`/`parseHash()` write and read
   `lay=infra,public,services,buildings` — the Layers ▾ menu's own `data-layer` names, and the same
   key the property route has written since v2.0. `ROUTE_CORE.layerFlags()` converts every old flag
   (`infra=1`, `public=1`, `services=1`, **`micro=1` → `buildings`**) and is idempotent. `mind=`,
   `wms=` and `zones=0` stay keys of their own — see DECISIONS V3 for why. `layerCount()` now reads
   off `mapLayerList()`, so the badge cannot disagree with the URL.
4. **The v1.1 area tabs** (NAV7). `ROUTE_CORE.areaTabs()`: `t=ind|bbr` → `show=figures`,
   `t=sub` → `show=sub`, `g=` dropped. An `#area/kunta/091?t=bbr&g=Rents` bookmark opens the All
   figures section again instead of a page with nothing open.
5. **The test-property radius moved into `Layers ▾`** under a "Test property" heading, and off the
   toolbar. With SRCH3 a pin can be dropped from the map itself, so the old `Within 500 m · 1 km …`
   segment would have appeared on row 1 for the first time — a sixth control on a row AC-M1 fixes at
   four. It counts towards the Layers ▾ badge when it is not "Any".
6. **SRCH8** — the clipped `Search kunta, postinum` was a CSS specificity bug, not a width choice:
   `#mapcard .tools>*{flex:0 0 auto}` outranked `.msearch`'s own `flex`, so the box could never grow
   past an input's intrinsic width however wide the toolbar was. One rule fixes it,
   `#mapcard .tools>.msearch{flex:1 1 200px}` with a 470 px cap, and the placeholder is shorter:
   `Search kunta, postinumero, address or coords…`. The **basis stays at the old 200 px on
   purpose**: a 330 px basis counts towards the flex line and wrapped the 1366 toolbar onto two
   rows, which pushed the map to 237 px and broke `P2-map-top-1366` (AC-S3 allows 200). Growing
   only spends free space, so the row count cannot change at any width. The check measures the
   placeholder in the input's own font rather than asserting a pixel width.

**Checks added** (phase V3, nine): `V3-pin-stays-on-map` (the whole DK P10 §1 round trip, including
`pin-open` landing on `#property?p=60.2448,24.8665`), `V3-pin-removable`, `V3-pin-card-clear-1440`
/ `-1366` / `-390`, `V3-radius-in-layers`, `V3-map-lay-key`, `V3-area-tab-alias`,
`V3-zoom-keeps-selection` (AC-M9 as written: `setZoom(12/9/11)` on `window.__maps[0]`),
`V3-search-fits`. Plus two `node --test` cases in `tests/route.test.js` and 18 new alias-table rows,
and a new `map_pin` route in `SHEET_ROUTES` so the P10 sweeps and the screenshot set cover a map
that has a pin on it.

**Two earlier checks were rewritten because the spec voids them** (logged in DECISIONS V3):
`P2-search-area` asserted that Enter on a coordinate lands on `#property` — DK P10 §1 replaces that
behaviour outright, so it now asserts the hash stays on `map` and carries `pin=`. `P2-layers-menu`
asserted `infra=1` — NAV6 replaces that spelling, so it asserts `lay=infra`. Nothing was weakened:
the old spellings are still readable, and `V3-map-lay-key` is the check that says so.

**What the next phase must know**

- **`lay=` is now one key across both routes.** V4 extends the *property* side of it with `services`
  (TP11) — add the name to `anLayerList()`/`anParseLayers()`, and nowhere else. If V4 adds a map
  layer, add it to `mapLayerList()` **and** to `RC_LAY_FLAGS` in `src/route_core.js` only if it ever
  had a v1.1 flag; a new layer needs no alias.
- **`TP.toProp` no longer exists.** Anything that wants to open the sheet from elsewhere navigates
  to `propLink(...)` itself. `tpDrop()` has exactly two branches now, and `S.view` decides.
- **V4 inherits the radius pattern.** The map's copy is a `lychips` row in `layersMenu()` driven by
  the existing `data-tprad` delegation; TP10 asks for the same on the property, where `tpMapTools()`
  still hand-rolls a `.seg.tprad` next to a `.lychips` row of `data-anlay` chips. Note a real bug
  V3 did **not** fix because it is TP10's: on `#property` the `data-tprad` handler only calls
  `syncHash()` + `mkRefreshTools()` (a no-op there) and `LF.map` is null, so the property radius
  writes the URL without redrawing. Folding that control into the property's `Layers ▾` fixes it.
- **The pin card is the model for V4's own cards**: a block in the flow beats a float over a map
  every time the widths are checked (SRCH7 passed at 1440, 1366 and 390 without a single offset).
- Seen in the V3 screenshots and still **not** fixed: the 390 `Legend ▾` pill over the attribution
  line and the clipped RENT tile — both still V6 (TILE5).

---

## V4 — the Test property: one `Layers ▾`, Services, the full indicator list ☑

Audit rows closed: **LAY6, LAY7, LAY8, TP3, TP10, TP11, TP12, TP13, TP14, TP17, TP18, PICK11** and
**MM6's property half** — every MUST the audit assigned to V4, plus its one "if there is room" row
(TP17). Gate: `./overnight.sh gate V4` green — build ✓, **70 node tests** ✓, **95 ui checks** ✓
(86 + 8 new, and one new sweep route), budgets `src/app.js` 419 KB / 460, `src/style.css` 140 KB / 165.
The python unit suite is still red on the one pre-existing false positive (GLOB5) and is still
informational.

**Built**

1. **One `Layers ▾` on the Test property** (DK P10 §3; LAY6, LAY7, LAY8, TP12). `tpMapTools()` — the
   chip row and the segmented radius control beside the map — is **deleted**, with its CSS.
   `layersBtn()` now sits on the property toolbar (`Layers ▾ · Indicator ▾ · Period`, the map's own
   row 1 order) and `layersMenu()` branches to **`anLayersMenu()`**: one `lyRow()` switch per layer
   the map actually draws — **infra · public buildings · services · buildings · flood zones ·
   radius rings** — each with its filters underneath it, and the radius chips at the bottom. The
   category chips are written once now (`pubCatChips()`, `srvCatChips()`, `tpRadChips()`) and used
   by both menus, so the two cannot drift apart.
   `anLayerToggle()` never re-renders the page: it writes `lay=` and calls `anMapOverlays()`, which
   redraws **every** overlay from `ANL`/`MK.clim`. That one fact is what closes LAY7 — `pubLoad`,
   `srvLoad`, `loadMicro` and `infraLoad` all land back in the same function, so a file arriving
   after the reader switched a layer off cannot put it back.
2. **Services on the property mini map** (DK P10 §2; TP11). `ANL.srv`, `anSrvKoms()` / `anSrvRows()`,
   and `srvMarkers(rows, map)` extracted out of `lfServicesLayers()` so both maps build their
   markers through `amOf(map)` — per-map panes and renderers, never the macro map's (TP16). Same
   four categories, same colours, same popup, same `srv=` filter key, now written on the property
   route too. Default **off**. The set is bounded by a 2 000 m ring around the pin rather than by
   the viewport, so the zoom floors do not apply and the legend counts "within 2 000 m of the pin"
   (DECISIONS V4). `legend-services` joined `TP_LEGENDS`.
3. **The SYKE zones in the property mini map** (TP14, MM6's property half). `anMapOverlays()` adds
   the publisher's own WMS in the map's own `climPane` (`LF.anClimL`) whenever a Climate indicator
   is active, with a **folded** `legend-zones` card — `climLegendHtml(compact)` drops the two long
   captions there, because the sheet's Climate section says them at length one screen below. The
   `zones` row and `zones=0` now work identically on both routes.
4. **The property picker is the area picker of the place the pin fell in** (DK P10 §4; TP13,
   PICK11). `pickCtx()` takes `anEntity()` — `tpEntity()` dressed as an area-page entity — so the
   list is `e.inds` and the rule is the area page's own `inherits()`: the pin's finest level's
   indicators first, everything else under **From the municipality** with the `muni` tag. Climate
   appears as its own group (the osa-alue layer publishes the four flood shares itself).
   `curInds()` got the same branch, or `parseHash()`'s "is this indicator selectable here" guard
   would reset an `ind=` the picker had just offered; both fall back to `IND_ANY` while the kunta
   rings are still in flight.
5. **`Export ▾` in the property header** (TP3) — the last action in `tpHead()`'s `.tools`, the same
   component as the sidebar footer and the Data header, third and last place it is allowed to be.
6. **The radius filter made real** (TP10). `parseHash()`'s property branch now fills `TP.lat/lon`
   from `p=`, which arms `tpWithin()`; before tonight the control wrote `rad=` and nothing moved.
   `anPubRows()` and `anSrvRows()` both honour it, and `anRings()` draws the solid filter ring.
7. **TP18** — `.anhead .arid{flex:1 1 420px}` → `flex:1 1 100%`: at 1536 the header no longer splits
   into two columns with the tiles starting at a different left edge than the title.
   **TP17** — the mini-map note reads `… · rings out to 1,2 km` instead of spelling all three radii
   and wrapping; the three are named once, in the `Radius rings` row of `Layers ▾`.

**Checks added** (phase V4, eight): `V4-property-layers-menu`, `V4-property-services`,
`V4-property-layer-off-sticks`, `V4-property-picker-groups`, `V4-property-climate`,
`V4-property-export`, `V4-property-radius`, `V4-property-head-one-line` (1536×864). Plus one sweep
route, `property_all_layers` (`…&ind=flood_sea_100&lay=infra,public,services,rings`), so the P10
sweeps and the screenshot set cover a property with every layer on.
No earlier check was deleted or weakened.

**Deviations** (all in DECISIONS.md V4, with the reasoning)

- **`rings` is a member of `lay=`**, so a property link written before tonight (`lay=infra,public`)
  opens with the dashed rings off. DK P10 §3 lists the rings among the layers that must each have
  exactly one switch, and `lay=` is the only place a property layer switch is written; a second
  opt-out key would have put two spellings of one idea back into the serialiser.
- **The services zoom floors are off on this map** — they exist to stop a national viewport asking
  for 95 000 bus stops, and 2 km around one address is 39 points at the test pin.
- **`TP` now carries the pin on `#property` too.** Harmless elsewhere: a map link with no `pin=`
  clears it in `tpParse()`, and `pinCard()` still renders on `#map` only.
- **`tests/ui_v2.spec.py` also reads `PHASE` / `ONLY` from `argv`** (`tests/ui_v2.spec.py V4 V4-`),
  so a single phase can be driven from a shell that may run the file only by name.

**What the next phase must know**

- **`anMapOverlays()` is the pattern V5 needs for MM6's area half.** Everything the property map
  draws goes through it, which is why "off means gone" and "an async file cannot re-add it" are one
  statement rather than two. `arMapInit()` still has no zones at all and `climLayers()` still starts
  `if (!LF.map) return` — give the area mini map its own tile layer the way `LF.anClimL` does, do
  **not** widen `climLayers()`.
- **`pickCtx()` and `curInds()` must agree, on every view.** They now do on three (area, property,
  map). If V5's in-place refresh (PICK8) changes where the list comes from, change both.
- **The property no longer re-renders on a layer, filter or radius click**, so V5's `tpRefresh()`
  has less to do than the audit assumed: what is left is the *indicator* change (`indSet()` still
  ends in `go(hashFor())`). `pubSetFilter()` and `srvSetFilter()` already branch on
  `S.view === "property"` — that is the shape `tpRefresh()` should take.
- **`srvMarkers(rows, map)` and `pubMarkers(rows, map, gm)` are the two per-map marker builders.**
  A third map (V5's area mini map) uses those, never `lfServicesLayers()` / `lfPublicLayers()`,
  which are the macro map's own and read `LF.map` throughout.
- Seen in the V4 screenshots and still **not** fixed: the clipped RENT tile at 390
  (`21,3 EUR/m²/mont`) and the 390 `Legend ▾` pill over the attribution line — both V6 (TILE5).

---

## V5 — the area page in place, the sheets, Data and Export ☑

Audit rows closed: **PICK8, AREA4, MM5, TP6** (the in-place refresh), **MM6**'s area half,
**SHEET1**, **SHEET2**, and every one of V5's "if there is room" rows — **AREA5, DATA4, EXP8,
EXP10, SHEET3**. Gate: `./overnight.sh gate V5` green — build ✓, **70 node tests** ✓,
**106 ui checks** ✓ (95 + 11 new, and four new sweep routes), budgets `src/app.js` 434 KB / 460,
`src/style.css` 141 KB / 165. The python unit suite is still red on the one pre-existing false
positive (GLOB5) and is still informational.

**Built**

1. **The study row updates in place** (AC-P4/AC-TP3; PICK8, AREA4, MM5, TP6). `vArea()` and
   `vAnalysis()` now render three blocks — `#artop` (identity card + toolbar) · the study row ·
   `#arsecs` (the toggles + source note), and `#tptop` / `#tpsecs` on the property — and
   **`areaRefresh()` / `tpRefresh()`** repaint the first and the third, the chart panel, the mini
   map's heading and its note, and then **re-paint** the Leaflet map rather than rebuilding it.
   `arMapInit()` was split into `arMapInit()` (the map, once) and **`arMapPaint(fit)`** (the
   polygons, the legend and the zones), the same split V4's `anMapInit()` / `anMapOverlays()`
   already had; `anMapPaint()` is its property twin, extracted out of `anMapInit()`.
   `indSet()` ends in `syncHash()` + a refresh on those two views and still in `go(hashFor())`
   everywhere else (DECISIONS V5); the year select and the `data-arsub` segment take the same road.
   The consequence the audit asked for: a chip click keeps the reader's scroll, the mini map's own
   pan and zoom, and the `⤢` overlay.
2. **The `⤢` overlay got the chips row DK puts in it.** Full screen is a fixed overlay over the
   whole page, so before V5 the toolbar — the only place an indicator could be chosen — was
   underneath it: "full screen survives an indicator change" was a promise about something a
   reader could not do. `miniFull()` now fills a `.mm-chips` row in the card with the shared
   `indChips("ind")`, `areaRefresh()` / `tpRefresh()` keep it current, and `UI.mmFull` is cleared
   by `render()` because the class lives on a card that is about to be replaced.
3. **The SYKE flood zones in the area mini map** (MM6's area half). `arMapZones()` — the area map's
   own WMS tile layer in its own `climPane` (`LF.amClimL`), with a folded `legend-zones` card in
   `AR_LEGENDS`, exactly the shape V4 gave `LF.anClimL`. They follow `ind=` and have **no switch
   and no `zones=0`** on this route: the area toolbar is `Indicator ▾ · Period` and nothing else
   (DECISIONS V5). `parseHash()` derives `MK.clim` for the area view so `climLegendHtml()` has it.
4. **The public-building family was rewritten against the data Finland actually publishes**
   (SHEET1). The sheet was **unreachable**: `dist/public/<kunta>.json` carries no `id` and no
   `kom`, so every `data-pubsheet` read `undefined` and `pubPopup()` threw on `b.id.slice(0, 8)`.
   `pubStamp()` now derives both at load (`<slug of the name>@<lat>,<lon>` — DECISIONS V5), and
   the list, the popup and the sheet show category, service type, address, municipality, the
   postal code and osa-alue found from the coordinate, the publisher and the record id — instead
   of the Danish BBR's floor area, year built, permit case and use code, which Palvelukartta and
   OpenStreetMap do not publish and which drew four columns and three tiles of `–`. One sentence
   on the sheet says so plainly. The list's postal-code and osa-alue filters are answered from the
   published rings, because the register states no postal code.
5. **The project sheet stopped throwing.** `prMapInit()` read `f.geometry.type` before the lazy
   alignments landed — and five of Finland's biggest projects have no open alignment at all — so
   every `#project/…` raised a `pageerror`. It now frames the municipalities the project serves and
   says which of the two cases it is; nothing else on the sheet changed.
6. **`data-testid=tiles` on the three sheets' tile rows** (SHEET3), and a check that no tile row is
   a 1 px grid over `--line` with an empty cell showing through (SHEET1/AC-SH1 — the CSS fix
   itself shipped in v2.0 P6; what was missing was anything asserting it off the area page).
   **Breadcrumbs** (SHEET2): the school, public-building and public-list sheets name the kunta; a
   project is not in one kunta, so its crumb is `Finland › Data › Projects`, and the check says so.
7. **Data › Areas**: every `th` carries `data-col="<key>"` (DATA4, spec §10), the four leading
   columns included, and the active indicator's column is still the highlighted one.
8. **Export ▾**: `sourceRecords()` is now the one set of source rows — Data › Sources **renders**
   it and `exportSourcesCsv()` **writes** it, so the screen and the file cannot disagree (EXP8);
   the table gained a Publisher column and a `–`-never-blank Fetched cell. And a sixth item,
   **`Climate exposure`** (EXP10): every area × every Climate indicator with `hazard` and
   `return_period` in columns of their own — `1/100a`, never a year (DECISIONS V5).
9. **All figures** (AREA5): opening the section scrolls the active indicator's row into view with
   `block: nearest`, DK's own rule; the row was already highlighted and already selected on click.

**Checks added** (phase V5, eleven): `V5-area-refresh-in-place`, `V5-area-fullscreen-survives`,
`V5-property-refresh-in-place`, `V5-area-minimap-zones`, `V5-area-active-row`,
`V5-sheets-no-filler`, `V5-sheet-breadcrumbs`, `V5-public-sheet-reachable`,
`V5-areas-table-col-ids`, `V5-sources-table-is-the-export`, `V5-climate-export`. Plus four sweep
routes — `area_climate`, `project`, `school`, `public` — so P10's error, hash and picker sweeps and
the screenshot set now cover the three detail sheets, which nothing covered before tonight.

**Two earlier checks were widened, not weakened** (logged in DECISIONS V5): `P1-sources-fetched`
found its column by a fixed index and now finds it by its header, so the Publisher column EXP8 adds
cannot make it assert on a different one; `P7-menu` asserted the export menu is exactly five items
and now asserts the five v2.0 items are still there in their old order, with `climate` the only
addition. No check was deleted.

**What the next phase must know**

- **`#artop` / `#arsecs` / `#tptop` / `#tpsecs` are `display:contents`** (`src/style.css`). They
  exist so `innerHTML` has something to address; they must never become boxes, or `#body`'s flex
  gap collapses between the identity card and the toolbar. Anything V6 adds above the study row
  belongs **inside `areaTop()` / `tpTop()`**, not beside them, or the refresh will not reach it.
- **Four functions now build the two pages**: `areaTop` / `areaSections` and `tpTop` / `tpSections`.
  A new section added straight into `vArea()` / `vAnalysis()` would render once and then vanish on
  the first chip click. Same for the mini map: draw through `arMapPaint()` / `anMapPaint()` +
  `anMapOverlays()`, never in the `*MapInit()` body.
- **`UI.mmFull` is state now.** `render()` clears it; `miniFull()` sets it; `mmChipsFill()` is the
  only thing that writes the overlay's chips row. A V6 responsive change to the overlay has to keep
  that row reachable at 390 too — it is the only indicator control a full-screen reader has.
- **The public-building id is derived in the UI**, not published. If a morning task teaches
  `scripts/build_public_*.py` to emit an `id`, `pubStamp()` keeps it (`if (!b.id)`) and nothing
  else has to change.
- Still **not** fixed and still V6's: the clipped RENT tile at 390 (`21,3 EUR/m²/mont`, TILE5), the
  390 `Legend ▾` pill over the attribution line, `tpRadLabel`'s `1.2 km` (NUM8) and the missing
  accessibility sweep (A11Y1–A11Y3). V5 added no `abbr`, no shortcut and no loading state.
