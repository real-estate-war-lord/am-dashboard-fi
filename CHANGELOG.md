# Changelog

All notable changes to the Finland edition. Dates are the build date, not the data's.

## [Unreleased] — v1.0 build

Batch 1 in progress (`docs/PLAN.md`). The release notes are written at phase 8.

### Phase 0 — plan and clean skeleton
- Repository re-founded on the Danish edition's UI, calc engine, overlay framework and
  Analysis sheet, with every Danish-only code path, data file and document removed.
- Levels renamed throughout to **kunta / postinumero / osa_alue** (and `peruspiiri` for the
  coarse sub-city level); the osa-alue layer generalised from one hard-coded municipality
  to a list read from the data, so Helsinki, Espoo, Vantaa and Kauniainen all fit.
- National macro dropped from scope: the Danish **Market** panel is gone and **Sources** is
  now a view of its own.
- Map re-centred on Finland (59.7–70.1 N, 19.0–31.6 E) with camera-only quick jumps —
  Helsinki **H**, Tampere **T**, Turku **U**, Oulu **O**, Finland **F**. Zooming never
  changes the selection.
- `scripts/statfin.py`: a throttled, retrying, stamped StatFin PxWeb client.
