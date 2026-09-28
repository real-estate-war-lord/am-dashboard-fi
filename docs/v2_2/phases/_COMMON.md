# Common rules for every v2.2 overnight phase (read before your phase file)

You are one of six sequential, unattended Claude Code sessions building **Macro Dashboard — Finland v2.2**:
cleanup, readable maps and charts, a better Test property first screen, a presentation mode, and the Danish
SHOULD list. Live today: FI **v2.1** (tag `v2.1`, branch `main`). You are on branch `v2.2-ui`. Nobody is awake:
when something is ambiguous, choose, append one line to `docs/v2_2/DECISIONS.md` (prefixed with your phase id)
and carry on. Never stop to ask.

## ⚠ The one rule that sank v2.1's last phase
**Never start background jobs, watchers, `&`, `nohup`, or "I'll be re-invoked when it finishes".** This session
ends the moment you send your final reply, and nothing re-invokes you. Run `./overnight.sh gate <PHASE>` in the
foreground and wait for it (it takes 10–15 minutes — that is normal), then commit, then reply. If you reply
before committing, the whole phase is thrown away.

## Read first (do not read app.js end to end)
1. Your phase file below. 2. `docs/v2_1/PARITY_AUDIT.md` (esp. its "Later" table), `docs/v2_1/DECISIONS.md`,
`docs/v2_1/PROGRESS.md`, `docs/UI_PLAN.md`. 3. `docs/v2_2/PROGRESS.md` (earlier v2.2 phases).
4. Danish reference, read-only: `docs/v2_1/ref/UI_SPEC_v3.md`, `ref/dk_src/*`, `ref/dk_tests/*`.
5. Navigate app.js with `grep -n "^function \|^const [A-Z_]* = " src/app.js` and targeted reads.

## Hard principles (never violate)
- Hard data only: official figures or plain arithmetic. No scores, weights, models. Suppressed ≠ 0,
  not covered = "Not covered yet". Every figure traceable (source, table id, as-of, verify link).
- Projections never look like actuals. The v2.1 signed-indicator ramp (green above 0, red below, fixed breaks)
  stays. Zooming never changes the selection. English UI, fi-FI numbers. State in the URL; old links keep working.
- Evolve the look (dark green sidebar, paper background, mono labels) — don't replace it.

## Allowed / forbidden
- Allowed: `src/**`, `tests/**`, `docs/**` (not `docs/v2_1/ref/**`), `Makefile`, `README.md`, `CHANGELOG.md`,
  `scripts/build_dashboard.py` (wiring only). **W1 only** may also edit `config/indicators.json` (text/colour fields,
  never table ids or values), `scripts/build_schools.py` and add files under `data/external/overrides/`.
- Forbidden (the wrapper rolls back): `.github/`, `data/raw|geo|processed/`, any other `config/` or `scripts/` file.
- No network: never run `make fetch/validate/links/verify/refresh/geo/…`, `scripts/fetch_*`, installs.
- Never push, merge, reset or switch branch. New JS: IIFE exposing one `window.X`, wired into `src/index.html`
  and `scripts/build_dashboard.py` in the same commit. Budgets: `src/app.js` ≤ 460 KB, `src/style.css` ≤ 165 KB —
  if you approach them, move code into a new `src/*_core.js` file instead of deleting features.

## Tests you own
- `tests/ui_v2.spec.py`: register every check your phase delivers with `@check("<id>", phase="<YOUR PHASE>")`;
  never weaken an earlier check (unless this plan voids it — say so in PROGRESS.md). The runner serves dist/ itself.
- Pure logic in `src/*_core.js` gets `node --test` tests in `tests/*.test.js`.

## Self-check (foreground, wait for it)
`./overnight.sh gate <PHASE>` → build + node tests + python tests + ui_v2.spec up to <PHASE> + screenshots +
budgets. Then look at `docs/ui_v2/*_1440.png` and `*_390.png` for the views you changed; fix anything broken,
clipped, overlapping or inconsistent even if tests pass.

## Finish (in this order, all in this session)
1. Gate green. 2. Append your section to `docs/v2_2/PROGRESS.md` (create it if missing).
3. Exactly one commit: `git add -A && git commit -m "v2.2 <PHASE>: <scope>"` with trailer
   `Co-Authored-By: Claude <noreply@anthropic.com>`; tree clean. 4. Then reply with a ≤ 10-line summary.
If the gate cannot go green after serious effort: write `docs/v2_2/phases/<PHASE>.FAILED.md` and stop.

## Tool permissions (anything else is denied; don't retry it)
Read, Edit, Write, Glob, Grep; `git status|diff|log|show|add|commit|mv|rm|restore`, `git checkout -- <paths>`,
`./overnight.sh gate <PHASE>`, `python3 scripts/build_dashboard.py`, `python3 tests/ui_v2.spec.py`,
`.venv-ui/bin/python3 tests/ui_v2.spec.py`, `node --test …`, `node --check …`, `ls`, `wc`, `grep`, `head`, `tail`, `mkdir`.
