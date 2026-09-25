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
