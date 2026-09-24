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


---

## The batch-2 layers — when to rebuild each

Nothing below is refreshed by the monthly workflow: each one is a large pull, and each one's
publisher issues a new edition on its own schedule. `make refresh` covers the StatFin series;
these are run by hand.

| Command | Pulls | When |
|---|---|---|
| `make addr` | 3.9 M addresses (~600 MB) | Ryhti updates continuously; once or twice a year is ample for a search index |
| `make climate` | 1 680 SYKE WMS tiles + 2 STUK spreadsheets | when SYKE issues a new flood-map edition (the `muutospvm` on the extent layers) or STUK a new radon year |
| `make services` | 767 MB OSM extract, 80 MB HSL GTFS, Palvelukartta | quarterly is generous; OSM changes daily but the picture does not |
| `make buildings` | 3.8 M Ryhti buildings (~650 MB) | twice a year |
| `make schools` | school register + 9 YTL sessions | **after each exam session is published** — spring results appear in the autumn |
| `make infra` | Väylävirasto project layers | monthly is cheap; the workflow already does it |

Each fetch is **resumable** and skips what is already on disk, and each asserts its row count
against the publisher's own `resultType=hits`, so an interrupted run costs nothing and a short
pull is never written as if it were complete.

Everything they produce is **committed**, so `make build` and the Pages deploy never need the
network, shapely, numpy, pillow, osmium or openpyxl.
