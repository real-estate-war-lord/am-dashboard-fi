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
