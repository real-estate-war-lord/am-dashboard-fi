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
| Licence | **Open for both non-commercial and commercial use.** Attribution required |
| Licence page | `https://kaupunkitieto.hel.fi/fi/helsingin-tilastotietokannat/aluesarjat` (read 2026-09-24) |
| Used for | every osa-alue indicator, and Helsingin kaupunki's own population projection by area |
| Attribution | Lähde: Helsingin seudun aluesarjat -tilastokanta ja Tilastokeskus |

**Correction to v1.0.** Batch 1 recorded this layer as non-commercial-use-only. That was
wrong. Helsingin kaupunkitietokeskus's own terms page says, verbatim:

> "Tietoaineistoa saa vapaasti kopioida, levittää, näyttää ja esittää sekä käyttää aineistoa
> osana muuta teosta."
>
> "**Tietoaineistoa voi käyttää sekä ei-kaupallisiin että kaupallisiin tarkoituksiin.**"
>
> "Ehtona käytölle on, että tietoaineiston tekijä on ilmoitettava."
>
> "Tilastokanta ja tietoaineiston tekijä ilmoitetaan viittaamalla Helsingin seudun aluesarjat
> -tilastokantaan ja tietoaineistokohtaisiin lähteisiin." — example: "Helsingin seudun
> aluesarjat -tilastokanta ja Tilastokeskus"
>
> "Tietoaineiston tekijää ei saa ilmoittaa siten, että ilmoitus viittaisi tietoaineiston
> tekijän tukevan tietoaineiston käyttäjää tai tietoaineiston käyttötapaa."

— https://kaupunkitieto.hel.fi/fi/helsingin-tilastotietokannat/aluesarjat, read 2026-09-24.

So there is **no commercial restriction anywhere in this dashboard.** What the terms do
require is a *two-part* attribution — the database **and** the underlying source — and that
the wording must not suggest the publisher endorses the user or the use. That is what the
layer's `meta.licence`, the Sources view and the footer now carry. Tables used:
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
| Status | **Last published 2021 — series discontinued by publisher.** HSY has published no later `seutukartta_pien` vintage, so Espoo, Vantaa and Kauniainen have no current sub-area boundary. Helsinki's own `Piirijako_osaalue` is current. See `docs/GEO.md` §3 |

## 5. Kela — housing allowance (Kelasto)

| | |
|---|---|
| Route | `https://raportit.kela.fi/ibi_apps/WFServlet` (WebFOCUS) |
| Licence | Kela's open statistics, free reuse with attribution "Lähde: Kela" |
| Status | **no JSON/REST API.** A stateful WebFOCUS form; direct POSTs return "Error Executing". The export route and what we do about it are recorded in `docs/PROBE_FI.md` and the phase-3 decision in `docs/BUILD_LOG.md` |

## 6. Verohallinto — municipal tax rates

| | |
|---|---|
| Property tax % | `https://vero2.stat.fi/PXWeb/api/v1/fi/Vero/Kiinteistoverot/kive_202.px` (PxWeb, keyless, 2014–2026) |
| Income tax % | the annual decision page on `https://www.vero.fi`, table read from the JSON its own front end renders |
| Licence | **Licence not stated by publisher — public official figures.** Attribution "Lähde: Verohallinto" |
| Handling | the parsed CSV is committed and the URL pinned in `config/sources.json` |

**What the publisher does and does not say (checked 2026-09-24).** Verohallinto *does* have
an open-data page, `https://vero.fi/tietoa-verohallinnosta/tilastot/avoin_dat/`, and it
states: "Aineistoon sovelletaan Creative Commons 4.0 Nimeä -lisenssin käyttöehtoja."
**But that statement is scoped to the datasets that page lists** — the public corporate
income-tax data (`yhteisöjen tuloverotuksen julkiset tiedot`, tax years 2020–2024) and its
amendment data. It does not name the property-tax rates or the municipal income-tax rates,
and neither `https://www.vero.fi/tietoa-verohallinnosta/tilastot/` nor the `vero2.stat.fi`
PxWeb table carries any licence statement at all.

We therefore do **not** claim CC BY 4.0 for these two series. They are labelled
**"Licence not stated by publisher — public official figures"**: statutory tax rates decided
by each municipal council and published by the tax authority, used with attribution and not
redistributed as an open-licensed dataset. If Verohallinto extends its CC BY 4.0 statement
to cover them, this is the one line to change.

## 6b. Frozen series — what has stopped being published

A series the publisher has stopped updating is kept only where nothing replaces it, and it
is labelled with the same sentence everywhere it appears — in the indicator's ⓘ tooltip, on
its summary line, and in the Status column of the Sources view:

> **Last published *&lt;period&gt;* — series discontinued by publisher**

| Series | Last published | Why it is kept |
|---|---|---|
| `rent_pno` — free-market rent by postal code (`StatFin_Passiivi:asvu/13eb`) | **2025Q4** | Nothing replaces rent below kunta level. Never extended, never blended with the live kunta-level rent |
| HSY `seutukartta_pien` sub-area boundaries | **2021** | The only published sub-area division for Espoo, Vantaa and Kauniainen |

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
