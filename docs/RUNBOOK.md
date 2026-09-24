# Runbook — Finland edition

## Refresh the data

```bash
make validate        # every table/variable/value code checked against live StatFin metadata
make fetch           # pull every registered StatFin table into data/raw (throttled, resumable)
make build           # raw + geo + external -> data/processed -> dist/index.html
make test            # python + node unit tests
```

`make refresh` is `fetch` then `build`. The monthly GitHub Action
(`.github/workflows/refresh.yml`) runs exactly those steps and commits `data/processed`.

## Refresh the geometry

Geometry is a **pinned vintage** and is not part of the monthly refresh. When Tilastokeskus
publishes a new kuntajako or a new Paavo year:

```bash
make geo             # re-downloads, re-clips and re-simplifies data/geo/*.geojson
```

Then read `docs/GEO.md` §2 before committing: a new vintage changes which codes exist, and
the build will report every code it had to drop. Decide what to do about each one and log
it in `docs/BUILD_LOG.md`. **Never join across vintages silently.**

## Look at it locally

```bash
make build && make serve      # http://localhost:8080
make fixture                  # dist/fixture.html — synthetic numbers, render check only
```

`scripts/shot.sh <page> <out-prefix> <hash>…` takes headless screenshots: it starts a
server on a random free port, shoots, and stops the server. It never leaves one running.

## Release

1. `make validate && make test && make build && make links` — all four clean.
2. Review `dist/index.html` in a browser.
3. Merge the build branch into `main`, tag, push. The `pages` workflow deploys `dist/`.

## When a source breaks

1. `make validate` names the table and the code that moved.
2. Re-probe just that source: `python3 scripts/probe_fi.py --only <name>`.
3. Fix `config/indicators.json`, rerun `make validate`.
4. If the table is gone for good, check `StatFin_Passiivi` for the frozen version, decide
   whether a frozen series is still honest to show, and record the decision in
   `docs/BUILD_LOG.md`. A discontinued series keeps its own end date in the UI — it is never
   extended.
