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

---

## Phase 1 — Probe

| Check | Result |
|---|---|
| `make probe` (84 routes) | 74 answered, 10 ✗ — every ✗ is kept in `docs/PROBE_FI.md` with what replaced it |
| Reference values | 5 of 5 answer: Helsinki 694 392 · 00100 price 7 167 €/m² (35 sales) · 00100 rent 29,43 €/m² (746 obs) · Helsinki free rent 26,73 · Helsinki ARA rent 18,48 |
| `make validate` | ✓ (still no indicators registered — phase 3) |
| `make test` | ✓ 22 python + 15 node |
| `make build`, `make fixture` | ✓ |

### Decisions logged in phase 1

| ⚠ | Decision |
|---|---|
| No PxWebApi v2 exists (three candidate hosts, all 404) | `scripts/statfin.py` stays a v1 client and the docstring records the probe. |
| `ras`, `asas`, `rakke`, `astuki` all return HTTP 400 — the four database names in the spec are gone | Replaced by `raku` and `asku`; the frozen originals are reachable in `StatFin_Passiivi` and are used where the live table has no history. Every substitution is in `docs/PROBE_FI.md` §"What the probe changed about the plan". |
| `asvu/13eb` — postal-code rent, the indicator that made Finland's market layer unique — is **gone from live StatFin** and frozen at 2025Q4 | Both are carried: the frozen postal series (labelled with its own end date, 2025Q4, and never extended) and the live kunta-level `asvu/15fa`. Phase 4 decides which is the headline; neither is silently spliced into the other. |
| `asvu/15fa` publishes ARA rent as funding code `2`, the archive `11x4` as code `0` — the codes are **inverted** | Both recorded verbatim in the config. Never assume a funding code means the same thing in two tables. |
| `ashi/12dg` (new dwellings by sub-area) returns null for all 24 sub-areas | Not registered. A table of nulls is not a source. |
| `raku/156f` and `raku/15f7` are maakunta-level only — no kunta-level construction exists anywhere | Logged as gap 1. Phase 4 either publishes it at maakunta level with the level stated, or drops it. |
| `rpk/13ex` takes ~10 s per small request | Phase 6 chunks by year; the client already throttles. |
| Partial probe runs were overwriting the full table in the doc | `probe_fi.py --only …` now prints instead of writing unless `--force` is given, and the generated block is spliced between markers so the hand-written findings survive a re-run. |
| StatFin returned HTTP 429 mid-probe and the first run reported live tables as missing | `get()` now waits out a 429/503 and retries up to four times; a rate limit can no longer be reported as a dead route. |
