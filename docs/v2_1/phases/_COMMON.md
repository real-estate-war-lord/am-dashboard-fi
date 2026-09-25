# Common rules for every v2.1 overnight phase (read before your phase file)

You are one of seven sequential, unattended Claude Code sessions building **Macro Dashboard — Finland v2.1**:
the Danish v3.0 UI brought to full parity in this repo, plus the owner's new colour rule. Live today: FI **v2.0**
(tag `v2.0`, branch `main`). You are on branch `v2.1-ui`. Nobody is awake: when something is ambiguous, pick the
option that best fits the Danish spec adapted to Finland, append one line to `docs/v2_1/DECISIONS.md`
(prefixed with your phase id) and carry on. Never stop to ask.

## Read first (in this order; do not read app.js end to end)
1. Your phase file below, then `docs/v2_1/PARITY_AUDIT.md` (written by V1 — the gap list every later phase works from).
2. `docs/v2_1/ref/UI_SPEC_v3.md` — the Danish v3.0 spec. **Its OWNER AMENDMENTS at the top override the rest.**
   Adapt Denmark → Finland: kommune/postnr/kvarter → kunta/postinumero/osa_alue, DKK → EUR, da-DK → fi-FI,
   Copenhagen → Helsinki region, storm-surge horizons → SYKE return periods (1/100a · 1/1000a), no National series tab.
3. `docs/v2_1/ref/DK_P10.md` — the owner's latest review fixes on the Danish build (they apply here too).
4. `docs/v2_1/ref/dk_src/*` and `docs/v2_1/ref/dk_tests/*` — the Danish v3.0 code and tests, READ-ONLY reference.
   Port components and patterns from there instead of re-inventing them; never copy Danish data, names or bounds.
5. `docs/UI_PLAN.md` (how FI v2.0 was built) and `docs/v2_1/PROGRESS.md` (what earlier v2.1 phases did).
6. Navigate app.js with `grep -n "^function \|^const [A-Z_]* = " src/app.js` and targeted reads.

## Hard principles (never violate)
- Hard data only: official figures or plain arithmetic on them. No scores, weights, models. Suppressed ≠ 0,
  not covered = "Not covered yet". Every figure traceable (source, table id, as-of, verify link).
- Projections never look like actuals (purple, dashed, pill). Climate is its own family (blue-ish, see V2 for
  signed indicators). Zooming a map never changes the selection.
- English UI, fi-FI numbers. Shareable state in the URL; one serialiser, one parser. Old links keep working.
- Evolve the existing look (dark green sidebar, paper background, mono labels) — don't replace it.

## Allowed / forbidden
- Allowed: `src/**`, `tests/**`, `docs/**` (except `docs/v2_1/ref/**`, read-only), `Makefile`, `README.md`,
  `CHANGELOG.md`, and `scripts/build_dashboard.py` only to wire a new `src/*.js` file into the page.
- **Forbidden** (the wrapper rolls the phase back if touched): `.github/`, `data/`, `config/`, any other
  `scripts/*` file. No data changes: data issues are surfaced in the UI with a caveat and logged in DECISIONS.md.
- **No network**: never run `make fetch/validate/links/verify/refresh/geo/…`, `scripts/fetch_*`, installs.
- **Never push, merge, reset or switch branch.**
- New JS files: IIFE exposing one `window.X`; wire into `src/index.html` and `scripts/build_dashboard.py` in the
  same commit. Budgets: `src/app.js` ≤ 460 KB, `src/style.css` ≤ 165 KB. Delete dead code you replace.

## Tests you own
- `tests/ui_v2.spec.py` is the acceptance suite. Register every check your phase delivers with
  `@check("<id>", phase="<YOUR PHASE>")`. Never delete or weaken an earlier check unless the spec voids it
  (then say so in PROGRESS.md). The runner serves `dist/` itself on a free port — never use port 8080.
- Pure logic in `src/*_core.js` gets `node --test` tests in `tests/*.test.js`.

## Self-check (the wrapper re-runs it and does not trust your word)
```bash
./overnight.sh gate <PHASE>      # build + node tests + python tests + ui_v2.spec up to <PHASE> + budgets
```
Then look at the screenshots it writes (`docs/ui_v2/*_1440.png`, `*_390.png`) for the views you changed with your
image-reading tool — fix anything broken, clipped, overlapping or inconsistent even if tests pass.

## Finish
1. `./overnight.sh gate <PHASE>` is green.
2. Append a section to `docs/v2_1/PROGRESS.md`: what you built, checks added, deviations, what the next phase must know.
3. Exactly one commit: `git add -A && git commit -m "v2.1 <PHASE>: <scope>"` with the trailer
   `Co-Authored-By: Claude <noreply@anthropic.com>`. Working tree clean afterwards.
4. If you cannot get the gate green after serious effort: write `docs/v2_1/phases/<PHASE>.FAILED.md` (what you tried,
   the failing output, best guess at the fix) and stop. The wrapper saves it and rolls back.

## Tool permissions (no bypass — anything else is denied automatically; don't retry it)
File tools: Read (also images), Edit, Write, Glob, Grep. Shell: `git status|diff|log|show|add|commit|mv|rm|restore`,
`git checkout -- <paths>`, `./overnight.sh gate <PHASE>`, `python3 scripts/build_dashboard.py`,
`python3 tests/ui_v2.spec.py`, `.venv-ui/bin/python3 tests/ui_v2.spec.py`, `node --test …`, `node --check …`,
`ls`, `wc`, `grep`, `head`, `tail`, `mkdir`. For an experiment, write it as a test and run it through these.
