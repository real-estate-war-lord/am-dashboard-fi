# Geography — levels, vintages and traps

**Probed live on 2026-09-24** (`docs/PROBE_FI.md`). Nothing below is assumed; every layer
name, feature count and field name in this file came back from a real request.

## 1. The three levels the page draws

| Level | Count | Layer | File | Licence |
|---|---|---|---|---|
| Maakunta (region) | 19 | `tilastointialueet:maakunta1000k_2026` | `data/geo/maakunnat.geojson` | CC BY 4.0 |
| **Kunta** | **308** | `tilastointialueet:kunta1000k_2026` | `data/geo/kunnat.geojson` | CC BY 4.0 |
| **Postinumeroalue** | **3 018** | `postialue:pno_tilasto_2026` | `data/geo/postinumerot.geojson` | CC BY 4.0 |
| **Osa-alue** (Helsinki region) | 306 over 4 kunnat | `taustakartat_ja_aluejaot:seutukartta_pien_2021` (HSY) | `data/geo/osa_alueet.geojson` | CC BY 4.0 |

Service endpoints:

```
https://geo.stat.fi/geoserver/tilastointialueet/wfs   maakunta, kunta, seutukunta, hyvinvointialue
https://geo.stat.fi/geoserver/postialue/wfs           pno_tilasto_<year>, pno_<year>, pno_meri_<year>
https://kartta.hsy.fi/geoserver/wfs                   seutukartta_suur_2021 / _tila_2021 / _pien_2021
https://kartta.hel.fi/ws/geoserver/avoindata/wfs      Piirijako_suurpiiri / _peruspiiri / _osaalue / _pienalue
```

All of them answer `outputFormat=application/json` and `srsName=EPSG:4326`. **Ask for 4326
explicitly** — the services' native CRS is ETRS-TM35FIN (EPSG:3067) and the default output
is in metres, not degrees.

## 2. Vintages — the part that silently corrupts a join

A Finnish statistical table names its area classification *with the classification's own
date in the variable name*. Two tables on different vintages are two different universes.

| Where | Area variable / layer | Vintage | Universe |
|---|---|---|---|
| Boundaries, kunta | `kunta1000k_2026` | **kuntajako 2026** | 308 kunnat |
| Boundaries, postal | `pno_tilasto_2026` | **pno 2026** | 3 018 areas · statistics year **2024** |
| `ashi/13mt`, `ashi/13mu` (prices) | `postinumeroalue_4_20220101` | **2022** | **1 724** areas |
| `asvu/13eb` (rents, archive) | `Postinumero` | no vintage in the name | **580** areas |
| `ashi/13mx` (prices, kunta) | `kunta_1_20150101` | 2015 | 301, codes `091` |
| `vaerak`, `muutl`, `asku` | `alue_23_20260101` | 2026 | codes `KU091` |
| `tjt` (income) | `alue_23_20250101` | 2025 | codes `KU091` |
| `vaenn` (projection 2024) | `alue_23_20240101` | 2024 | codes `KU091` |
| `rpk` (crime) | `alue_23_20230101` | 2023 | codes `KU091` |
| HSY sub-areas | `seutukartta_*_2021` | **2021** | frozen — no 2022+ version exists |

**How this repo handles it.** Each source entry in `config/indicators.json` records its
area variable verbatim, including the vintage suffix. `scripts/build_makro.py` joins a
value to a polygon only when the code exists on the polygon's own vintage; a code that does
not exist there is dropped and counted, never guessed onto a neighbour. Every drop is
printed by the build and listed in `docs/BUILD_LOG.md`.

The three postal-code universes (1 724 price areas, 580 rent areas, 3 018 Paavo areas) are
**not** reconciled into one. A postal area drawn from `pno_tilasto_2026` shows a price only
if its own code is in the 2022 price universe, and a rent only if its own code is in the
rent universe. The rest read `–`, and the indicator's coverage line says how many areas
actually carry a figure. Filling the gaps would mean inventing numbers.

Two code shapes coexist and are both strings: the bare three-digit kunta code (`"091"`,
used by `ashi/13mx` and by every boundary layer's `kunta` field) and the prefixed form
(`"KU091"`, used by `vaerak`, `muutl`, `asku`, `tjt`, `vaenn`, `rpk`). `build_makro.py`
normalises to the bare form and **never casts to int** — `int("091")` is `91`, and `91` is
Jokioinen, not Helsinki.

## 3. Known geometry facts

- **Kunta polygons are already land-only.** The 308 polygons of `kunta1000k_2026` sum to
  337 766 km² (Finland including inland waters); Helsinki's bbox stops at the shoreline.
  No sea clipping is needed at kunta level.
- **`pno_tilasto_<year>` is the land version**; `pno_meri_<year>` is the one extended over
  the sea. We use `pno_tilasto`, so the postal layer is land-clipped by the publisher.
- **There is no coastline / land-mask layer on geo.stat.fi** (all 423 layers across 9
  workspaces were listed). Where a land mask is needed it is the dissolved kunta layer.
- **No kunta → maakunta mapping exists in any boundary layer.** `kunta1000k_2026` carries
  `kunta`, `nimi`, `namn`, `name` and nothing else. The mapping comes from a separate
  classification source — recorded in `docs/SOURCES.md` once wired in phase 2.
- **Paavo's statistics year lags the layer year by two.** `pno_tilasto_2026` carries
  statistics for **2024**; confirmed by matching the WFS value for 00100 `he_vakiy`
  (18 492) against the PxWeb table for 2024. The UI labels Paavo figures with the
  statistics year, never the layer year.
- **HSY's sub-area division is frozen at 2021.** Helsinki publishes a fresher set of its
  own (`Piirijako_osaalue`, 148 areas, updated 2026-09-23), and the two agree exactly for
  Helsinki (intersection 148, difference 0). Espoo, Vantaa and Kauniainen have no
  2026-current source, so their osa-alue boundaries are the 2021 HSY vintage and the UI
  says so. 179 of HSY's 824 features have a blank name, including all 9 in Kauniainen.

## 4. Simplification

Raw downloads land in `data/geo/raw/` (git-ignored). The committed GeoJSON is simplified
with `mapshaper -simplify keep-shapes` so no polygon collapses and no area loses a hole —
Kauniainen is a hole inside Espoo, and dropping it would put every Kauniainen pin in Espoo.
`scripts/fetch_geo_fi.py` records the simplification percentage and the before/after byte
counts in `data/geo/ATTRIBUTION.txt` next to the licence text.
