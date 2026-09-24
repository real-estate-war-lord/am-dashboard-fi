# Macro Dashboard — Finland

A single-page map of Finland's housing market and demographics, built only from open
official data: **kunta → postinumeroalue → osa-alue**, with prices, rents, income,
demographics, taxes, safety and the population outlook side by side.

> **Status: v1.0 in progress.** The build plan is `docs/BUILD_PLAN_FI.md` §7 and the live
> checklist is `docs/PLAN.md`. This README is filled in properly at phase 8.

## The rule this project runs on

Every figure is an official published number, or plain arithmetic on official numbers — a
difference, a share, a sum, a per-1 000. Nothing here is modelled, fitted, assumed or
imputed. A suppressed cell is shown as `–` and is never read as zero; an area we do not
cover reads "Not covered yet". Every figure carries its source, its period, the date we
fetched it and a link to the publisher's own table.

## Run it

```bash
make validate    # check every code against live StatFin metadata
make fetch       # pull the tables
make build       # -> dist/index.html
make serve       # http://localhost:8080
make fixture     # synthetic render check (never publish a build from this)
```

Python 3.10+, standard library only. Node is optional and used for the JavaScript syntax
check and the parser unit tests.

## Sources and licences

`docs/SOURCES.md`. The short version: Statistics Finland's StatFin, Paavo and boundary WFS
are CC BY 4.0 and require the attribution **"Lähde: Tilastokeskus"**; Aluesarjat and the
Helsinki-region boundary services are CC BY 4.0; the basemap is © OpenStreetMap
contributors (ODbL). The code in this repository is MIT.

## Honest limits

Filled in at phase 8. The known ones going in: no days-on-market or supply (only the
commercial portals have them), no transaction-level prices, crime only at kunta level, and
Finland publishes no comprehensive-school results.
