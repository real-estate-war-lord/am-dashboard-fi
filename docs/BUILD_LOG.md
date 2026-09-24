# Build log — Finland edition, batch 1

One check table per phase: what was run, what it said, and what was decided about every ⚠.
Phases and their status live in `docs/PLAN.md`; this file is the evidence behind them.

---

## Phase 0 — Plan + clean skeleton

| Check | Result |
|---|---|
| `python3 scripts/validate_config.py` | ✓ "no indicators registered yet" — expected until phase 3 |
| `python3 scripts/check_source_links.py --quick` | ✓ "no verify-at-source links yet" — expected until phase 3 |
| `make test` (python + node) | ✓ see the table below |
| `make fixture` | ✓ `dist/fixture.html`, 0.8 MB, 8 synthetic kunnat · 40 postinumeroalueet · 24 osa-alueet |
| `make build` | ✓ `dist/index.html` assembles with no data (empty map, honest "no data" state) |
| headless screenshots | ✓ `docs/screenshots/fixture-1..3.png` — map, table, sources; server stopped |
| `node --check src/app.js` | ✓ parses after every transform pass |

### Decisions logged in phase 0

| ⚠ / question | Decision |
|---|---|
| The Danish app.js is 3 600 lines of `kommune` / `postnr` / `kvarter` / `bydel` | Renamed mechanically to `kunta` / `postinumero` / `osa_alue` / `peruspiiri` in six reviewed passes, each followed by `node --check`. The JSON container names (`municipalities`, `areas`) keep the Danish shape as the ground rules require; only the level identifiers changed. |
| The Copenhagen quarter layer is hard-coded to one municipality (`CPH_MUNI = "101"`) | Generalised: `OSA_MUNIS` is derived from the data (`[...new Set(OSA.areas.map(a => a.muni))]`) and `isOsaMuni()` / `osaParent()` replace every comparison against a single code. Finland needs four (Helsinki, Espoo, Vantaa, Kauniainen) and adding a fifth is now a data change. |
| National macro is out of scope, but the Danish **Market** view *was* the macro panel | `vMarket()` deleted. `vSources()` promoted from a fold inside Market to its own nav item under "Reference", so the source table, licences and indicator definitions stay reachable. |
| `testprop.js` still carries the Danish bounding box | Left as it is. It is dormant in batch 1, its unit tests are green, and batch 2 phase 10 rewrites it with the Finland box and DVV address search. Changing it now would only break `make test-js` for no gain. |
| The BBR / services / public-buildings / infra / schools code paths | Kept, dormant (each renders nothing while its data key is null), as the ground rules require for batch 2. Every Danish register *name* in their UI text was replaced with a neutral one, so no dormant string can claim a Danish source. |
| `config/indicators.json` starts empty | Deliberate: nothing is registered before it is probed. `validate_config.py` says so explicitly instead of failing. |
| `make build` has no `build_makro.py` yet | The target is `build_dashboard.py` alone in phase 0 and gains `build_makro.py` in phase 3, so `make build` is green in every phase rather than red until the data lands. |
