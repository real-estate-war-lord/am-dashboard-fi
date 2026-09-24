# Sources, licences and attribution

Every figure on the page comes from one of the sources below. Each carries its licence and
the attribution the publisher asks for. Nothing on the page is modelled, fitted or imputed
by us: it is a published cell, or plain arithmetic on published cells.

**Attribution shown in the page footer and in Sources:**

> Lähde: Tilastokeskus · Source: Statistics Finland (CC BY 4.0)

## 1. Statistics Finland — StatFin PxWeb API

| | |
|---|---|
| Endpoint | `https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/<db>/<id>.px` |
| Archive | `https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/<db>/<id>.px` (discontinued tables) |
| Key | none |
| Licence | **CC BY 4.0** — attribution "Lähde: Tilastokeskus" required |
| Terms | ~10 calls / 10 s, a cell cap per request; honoured by `scripts/statfin.py` |
| API version | **v1 only.** `/api/v2/`, `/api/v2-beta/` and `statfin.stat.fi/api/v2/` all answer 404 (probed 2026-09-24) |
| Verify at source | the published table page, `https://pxdata.stat.fi/PxWeb/pxweb/en/StatFin/StatFin__<db>/statfin_<db>_pxt_<id>.px/` |

Databases used (confirmed live 2026-09-24): `vaerak` population, `tjt` income, `tyonv` TEM
employment service, `muutl` migration, `vaenn` population projection 2024, `rpk` offences,
`asku` dwellings and housing conditions, `raku` building stock and new production, `ashi`
dwelling prices, `asvu` rents.

**Databases named in the original spec that no longer exist in live StatFin** — all answer
HTTP 400 and survive only in `StatFin_Passiivi`: `ras`, `asas`, `rakke`, `astuki`. Their
replacements and what is lost are recorded in `docs/PROBE_FI.md` and in the indicator's own
caveat.

## 2. Statistics Finland — Paavo (postal-code statistics) and boundary WFS

| | |
|---|---|
| Paavo WFS | `https://geo.stat.fi/geoserver/postialue/wfs` — `postialue:pno_tilasto_2026` |
| Boundaries WFS | `https://geo.stat.fi/geoserver/tilastointialueet/wfs` — `kunta1000k_2026`, `maakunta1000k_2026` |
| Licence | **CC BY 4.0** — "Lähde: Tilastokeskus" |
| Note | the 2026 layer carries statistics for **2024**; the UI labels the statistics year |

## 3. Aluesarjat (Helsinki-region statistics database)

| | |
|---|---|
| Endpoint | `https://stat.hel.fi/api/v1/fi/Aluesarjat/` (PxWeb v1) — walk the **Finnish** tree; the English one exposes only two of the seven folders, and `api.aluesarjat.fi` does not answer at all |
| Publisher | Helsingin kaupunki / Uudenmaan liitto and the region's municipalities |
| Licence | ⚠ **Non-commercial use only** — "Tietoaineistoa voi käyttää ei-kaupallisiin tarkoituksiin". **This is not CC BY 4.0.** Commercial reuse needs the publisher's permission (tilastotietokannat@hel.fi) |
| Used for | every osa-alue indicator, and Helsingin kaupunki's own population projection by area |
| Attribution | Lähde: Aluesarjat (Helsingin kaupunki ja Uudenmaan liitto) |

**This is the one licence restriction in the whole dashboard, and it is confined to one
layer.** Everything else here is CC BY 4.0 or equivalent. The osa-alue layer carries the
restriction in its own `meta.licence`, in every osa-alue indicator's note, and in the
Sources view, so nobody can lift a figure out of it without seeing the terms. Tables used:
`alu_vaerak_004r` (population by age), `alu_vaerak_004p` (population by language and age),
`alu_asas_005d` (households by size), `alu_askan_005q` (dwellings by occupancy, type and
tenure), `alu_kou_005n` (education), `alu_vaenn_006c` (Helsinki's projection, PER26).

Two traps, both handled in `scripts/aluesarjat.py`: a variable left out of a query is
**eliminated to its total** silently, so every dimension is always named; and the area
variable is spelled `Alue` in some tables and `Osa-alue` in others, where the wrong one is
an HTTP 400.

The ten-digit Aluesarjat area code is exactly Helsingin kaupunki's `kokotunnus`, which
`data/geo/osa_alueet.geojson` stores verbatim, so the join needs no crosswalk: 296 of 306
areas match. The ten that do not are Kauniainen's nine sub-areas, which Aluesarjat publishes
as a single municipality, and Helsinki's territorial-sea polygon, which has no residents.

## 4. HSY and Helsingin kaupunki — sub-area boundaries

| | |
|---|---|
| HSY WFS | `https://kartta.hsy.fi/geoserver/wfs` — `taustakartat_ja_aluejaot:seutukartta_pien_2021` |
| Helsinki WFS | `https://kartta.hel.fi/ws/geoserver/avoindata/wfs` — `avoindata:Piirijako_osaalue` |
| Licence | **CC BY 4.0** (Helsinki Region Infoshare); both services declare Fees NONE, AccessConstraints NONE |
| Note | the HSY division is frozen at 2021 — see `docs/GEO.md` §3 |

## 5. Kela — housing allowance (Kelasto)

| | |
|---|---|
| Route | `https://raportit.kela.fi/ibi_apps/WFServlet` (WebFOCUS) |
| Licence | Kela's open statistics, free reuse with attribution "Lähde: Kela" |
| Status | **no JSON/REST API.** A stateful WebFOCUS form; direct POSTs return "Error Executing". The export route and what we do about it are recorded in `docs/PROBE_FI.md` and the phase-3 decision in `docs/BUILD_LOG.md` |

## 6. Verohallinto — municipal tax rates

| | |
|---|---|
| Route | `https://www.vero.fi` annual published files (property tax %, municipal income tax %) |
| Licence | Verohallinto open data, free reuse with attribution "Lähde: Verohallinto" |
| Handling | the source file is downloaded to `data/external/raw/` (not committed); the parsed CSV is committed and pinned in `config/sources.json` |

## 7. OpenStreetMap (basemap only in v1.0)

| | |
|---|---|
| Tiles | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` |
| Licence | **ODbL 1.0** — © OpenStreetMap contributors |
| Note | basemap only in batch 1; batch 2 adds OSM-derived service points, which carry the same licence |

## 8. Code

The code in this repository is MIT (`LICENSE`). The data is not ours to licence: each
source keeps its own terms as listed above. Redistributing the processed JSON means
carrying the attributions with it.
