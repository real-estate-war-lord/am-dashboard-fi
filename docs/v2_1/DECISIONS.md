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
