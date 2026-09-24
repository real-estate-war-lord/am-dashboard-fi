# Endpoint probe — Finland edition

**Probed live on 2026-09-24 from the Mac.** Nothing in this repository names a table, a
variable or a URL that has not answered a request recorded here. Re-run with
`make probe`; the generated tables below are replaced and everything outside the markers,
including this section, survives.

## What the probe changed about the plan

`docs/DATA_MAP_FI.md` was desk research. Seven of its assumptions did not survive contact
with the live API. Each is recorded here with the route that replaced it.

| Spec said | Live reality | Decision |
|---|---|---|
| "Check whether a PxWebApi **v2** exists and prefer it" | `/PxWeb/api/v2/`, `/PxWeb/api/v2-beta/` and `statfin.stat.fi/api/v2/` all **404** | v1 only. `scripts/statfin.py` is a v1 client and says so. |
| `ras` (building and dwelling production) | **HTTP 400 — discontinued.** Lives on in `StatFin_Passiivi/ras` | Replaced by **`raku/156f`** (monthly, 1995M01–2026M07). But see the gap below: `raku/156f` is **region-level only (20 areas)**. |
| `asas` / `rakke` (dwelling stock) | **HTTP 400 — discontinued.** `asas` lives on in `StatFin_Passiivi` | Replaced by **`raku/15f6`** (stock incl. unoccupied, 309 kunnat, but **one year only: 2025**) and **`asku/15fh` / `15fd` / `15fi`** (2005–2025). Tenure survives only in the archive, `StatFin_Passiivi/asas/115y_2024` (2005–2024). |
| `astuki` (housing allowance) | **HTTP 400 — no such database.** No StatFin table publishes recipient households by kunta | Kela's Kelasto is the only route, and it is a stateful WebFOCUS form with no JSON/REST API. Decision in phase 3. |
| `asvu` **13eb**, free-market rent €/m² **by postal code**, quarterly | **HTTP 400 in live StatFin.** Live `asvu` has exactly **two** tables (`15fa`, `15fc`). 13eb survives frozen at **2025Q4** in `StatFin_Passiivi/asvu/statfinpas_asvu_pxt_13eb_2025q4.px`, 580 postal areas | **The single biggest loss in the Finland edition.** Postal-code rent is a frozen series ending 2025Q4; the live replacement `asvu/15fa` is **kunta level and city sub-areas only**. Both are carried, each labelled with its own end date. Phase 4 decides which is the headline. |
| `vaenn` **14wy** for the 2024 projection | `14wy` is *Vital statistics* and has no age variable | **`vaenn/14wx`** — population by age × year × kunta, 2024–2045. Publication date of the 2024 edition: **2024-10-24** (the json-stat2 `updated` field; the table-list stamp is a bulk re-stamp and is not a release date). |
| Area variable is `alue_2026` | It is **`alue_23_20260101`** in `vaerak`/`muutl`/`asku`/`raku`, **`alue_23_20250101`** in `tjt`, **`alue_23_20240101`** in `vaenn`, **`alue_23_20230101`** in `rpk`, and a bare **`Alue`** in `tyonv` | Every vintage is recorded verbatim in `config/indicators.json`. See `docs/GEO.md` §2. |

## Reference values — the three (now five) figures a human can check by hand

| Figure | Value | Table | Period |
|---|---|---|---|
| Helsinki (091) population | **694 392** | `vaerak/11re` | 31 Dec 2025 |
| 00100 price €/m², blocks of flats, 2-room | **7 167 €/m²** on **35** sales | `ashi/13mt` | 2026Q1* |
| 00100 free-market rent, 1-room | **29,43 €/m²/month** on **746** observations | `StatFin_Passiivi:asvu/13eb_2025q4` | 2025Q4 (last ever) |
| Helsinki (091) free-market rent, 1-room | **26,73 €/m²/month** on 19 543 observations | `asvu/15fa` | 2026Q1 |
| Helsinki (091) ARA rent, 1-room | **18,48 €/m²/month** on 7 587 observations | `asvu/15fa` | 2026Q1 |

The two Helsinki rents are not comparable with the 00100 figure: one is a postal area in the
city centre, the other the whole municipality, and they come from different tables with
different universes. They are listed together only because each is a separate check that its
own route still answers.

## Gaps this probe found, and what the dashboard will say about them

1. **No municipality-level construction data exists anywhere.** `raku/156f` and `raku/15f7`
   are published by maakunta (20 areas). The archive `ras/12fy` was the same. Dwellings
   started / completed / permitted **per kunta cannot be shown**, so the indicator becomes a
   maakunta-level one and says so, or it is dropped. Phase 4 decides and logs it.
2. **No postal-code rent after 2025Q4.** See the table above.
3. **`ashi/12dg` (new dwellings by sub-area) is empty.** All 24 sub-area codes return null
   for every year and building type; only the three national aggregates carry values. The
   table is unusable for area comparison and is not registered.
4. **Three incompatible postal-code universes**: 1 724 (prices, 2022 vintage), 580 (rents,
   no vintage), 3 018 (Paavo, 2026 vintage). They are never reconciled — see `docs/GEO.md` §2.
5. **`ashi/13mt` and `13mu` have no "blocks of flats total" and no "all types" code.** A
   building-type total has to be computed as a **sales-weighted mean** over the room-count
   codes using `lkm_julk20`. That is plain arithmetic on published cells, so it is allowed —
   and it is written down here so nobody later mistakes it for a plain average.
6. **`raku/15f6` is a one-year snapshot** (2025 only). Unoccupied-dwelling share has no
   history from this table; the archive `asas` tables carry 2005–2024 on a different vintage.
7. **`api.aluesarjat.fi` does not answer** (no response after 20 s). Aluesarjat is reached at
   `https://stat.hel.fi/api/v1/fi/Aluesarjat/` — and note the **Finnish** tree has 7 folders
   while the English tree has only 2, so the Finnish one is the one to walk.
8. **avoindata.fi's CKAN search returns 0 datasets** for both `kiinteistöveroprosentit` and
   `kunnallisveroprosentti`. The tax rates are not on the national open-data portal; the
   route is Verohallinto's own published file. Phase 5 pins it in `config/sources.json`.
9. **`rpk/13ex` is slow** — ~10 s for one kunta × one year × 9 offence codes. A full
   308-kunta pull must be chunked; `scripts/statfin.py` throttles anyway, and phase 6 splits
   the request by year.
10. **HSY's sub-area division is frozen at 2021** and 179 of its 824 features have a blank
    name, including all 9 in Kauniainen. See `docs/GEO.md` §3.

---

# Batch 2 — the map layers (phases 9–15)

**Probed live 2026-09-24.** Same rule as above: no host, layer, collection or field is named
anywhere in this repository unless it answered a request recorded in the generated tables
below. Several of these came back negative. A publisher that does not publish something is a
finding, and the row is kept to prove the question was asked.

## What answered, and on which exact route

| What | Verdict | Route |
|---|---|---|
| SYKE flood-hazard zones | **USABLE** | WFS `https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs`, WMS `.../inspire_nz/wms` |
| SYKE mapped-extent layers | **USABLE** | `inspire_nz:NZ.Tulvavaarakartoitetut_alueet_{Vesistotulva,Meritulva}` — 113 and 8 features |
| Sea-level scenarios, national | **NOT AVAILABLE as data** | prose only, see below |
| Sea-level, Helsinki | **PARTIAL** | `avoindata:FMI_Paikkakohtainen_tulvakorkeus_vuonna_2100_piste`, 453 points, Helsinki only |
| Stormwater (hulevesi) flood maps | **NOT PUBLISHED** | asked of both HSY (397 layers) and Helsinki (304 layers) — see below |
| STUK radon by kunta and by postal area | **USABLE** | two `.xlsx` on `stuk.fi`, 2023 |
| Ryhti buildings | **USABLE** | OGC API `https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1`, 3 799 798 features |
| Ryhti addresses | **USABLE** | collection `open_address`, 3 861 495 features — the live replacement for the DVV bulk file |
| Ryhti kaavat | **PARTIAL** | `ryhti_plan` — status and geometry yes, **no floor area**, in-preparation collections empty |
| Helsinki kaavayksiköt | **USABLE** | `avoindata:Kaavayksikot`, 40 081 features, **carries `rakennusoikeus` in k-m²** |
| ARA energy certificates | **NOT AVAILABLE keyless** | paid X-Road service, ARA data permit required |
| Tilastokeskus 1 km grid | **USABLE** | `vaestoruutu:vaki2025_1km`, 96 904 cells |
| HSL GTFS | **USABLE** | `https://dev.hsl.fi/gtfs/hsl.zip`, 80 MB, keyless |
| National GTFS | **NOT AVAILABLE keyless** | Digitransit's national feed answers **401** without a registered subscription key |
| Helsinki Palvelukartta | **USABLE** | `https://api.hel.fi/servicemap/v2/`, 21 506 units, keyless |
| Geofabrik Finland extract | **USABLE** | `finland-latest.osm.pbf`, 767 MB, ODbL |
| LIPAS | **USABLE** | `https://api.lipas.fi/v2/`, keyless |
| Väylävirasto project layers | **USABLE** | `https://avoinapi.vaylapilvi.fi/vaylatiedot/ows` — `hanketiedot:tiehankkeet` (311), `:ratahankkeet` (166) |
| Tilastokeskus school register | **USABLE** | `https://geo.stat.fi/geoserver/oppilaitokset/wfs` — 2 501 schools **with coordinates** |
| YTL matriculation results | **PARTIAL** | national tables are PDFs; candidate-level microdata CSV carries the school code |

## Nine things the spec assumed and the layer APIs refused

1. **The host is `paikkatiedot`, plural, not `paikkatieto`.** `paikkatieto.ymparisto.fi`
   answers 200 with an **IIS default page** and its `/geoserver/` is a 404 — it looks alive
   and is not. Every SYKE route in this repository uses `paikkatiedot.ymparisto.fi`.
2. **Flood return periods are separate LAYERS, not an attribute to filter on.** There are 16:
   `inspire_nz:NZ.Tulvavaaravyohykkeet_{Meritulva|Vesistotulva}_1_{2|5|10|20|50|100|250|1000}a`.
   Each feature *also* carries a `toistuvuus` attribute, but picking a return period means
   picking a layer.
3. **The flood zones cannot be downloaded as vectors.** The national counts are
   **3 412 672** features (vesistötulva 1/100a) and **4 014 394** (meritulva 1/100a); a
   Helsinki-sized bbox alone returns **8.9 MB** and **12.7 MB** of GeoJSON, and the meritulva
   request hit GeoServer's 10 000-feature cap. Whole-country vectors for the four layers we
   need would be on the order of **15–20 GB**. SYKE's own bulk zips are worse:
   **5.59 GB** (meri) and **5.65 GB** (vesistö), measured by HEAD. *Decision (phase 11): the
   area share is computed from the publisher's own **WMS raster**, tiled per kunta, with the
   **mapped-extent layers pulled as vectors** (113 + 8 features) to separate "no flood zone"
   from "not mapped". The raster resolution is recorded with every figure.*
4. **Finland publishes no national sea-level-rise scenario dataset.** `avoindata.fi` returns
   **0 datasets** for "merenpinnan nousu". The only quantified figures are prose in an
   Ilmatieteen laitos article (RCP2.6/SSP1-2.6 and RCP4.5/SSP2-4.5 ranges *per sea basin*,
   not per location). The one machine-readable thing that exists is Helsinki's republished
   FMI layer of site-specific year-2100 flood heights — **453 points, Helsinki only, one
   value per point, no scenario selector.** *Decision: no national sea-level indicator. The
   Helsinki layer is carried as what it is, and every other area reads "Not mapped".*
5. **Neither HSY nor Helsinki publishes a stormwater flood map.** Asked of both: HSY's WFS
   lists **397** layers, of which **one** matches "hulevesi" — `vesihuolto:vh_hulevesiviemaroity_alue`,
   which is *sewer-network coverage*, not flooding — and **zero** match "tulva". Helsinki's
   WFS lists **304** layers with **zero** "hulevesi" matches. *Decision: the stormwater
   indicator is not built. Every area would read "Not mapped", which is a column of nothing.*
6. **The DVV bulk address file is discontinued.** Its own readme says the distribution ended
   **14.3.2025**. (The CSC mirror also fails TLS verification from here — hostname mismatch —
   so the probe records it as unreachable, which is a second reason not to depend on it.)
   *Decision: addresses come from Ryhti `open_address`, which is the same register, live
   (`modified_timestamp_utc` 2026-09-01 on the sampled row) and keyless.*
7. **Ryhti's OGC API ignores a plain municipality query parameter.** `?kuntanumero=091`
   returns the full 3 799 798 — silently, with no error. Only `?filter=kuntanumero='091'`
   (CQL) actually filters, and returns 53 160. **A filter that is ignored rather than
   rejected is the most dangerous kind**, so every Ryhti fetch in this repository goes
   through the CQL form and asserts the returned count against a `resultType=hits`.
8. **Ryhti's OGC API also ignores `properties=`**, returning all 21 fields at ~1.1 kB a row —
   4.2 GB for the national address set. The **classic WFS** on the same workspace accepts
   both `propertyName=` and `outputFormat=csv`, which brings a row to ~130 bytes.
   *Decision: bulk pulls use the WFS/CSV route, single-feature checks use the OGC API.*
9. **Ryhti's plan index carries no floor area, and its in-preparation collections are empty.**
   `pub_prep_ld_plan_ix_gs` and `pub_prep_lm_plan_ix_gs` both return **0 features
   nationally**. Helsinki's own `avoindata:Kaavayksikot` does carry `rakennusoikeus` in k-m².
   *Decision (phase 15): `planned_floor_area_1000` can only be built where the floor area is
   published — Helsinki — and is not invented anywhere else.*

## Two sources that are open but not open enough

- **ARA energy certificates.** The register is reachable only through Suomi.fi Palveluväylä
  (X-Road) as a single-building lookup. Its own catalogue page states the service is
  *maksullinen* and requires a *tietolupa* from ARA plus a separate agreement, a connection
  fee and an annual fee. `avoindata.fi` has **0 datasets** for "energiatodistus".
  *Decision (phase 15): the energy-class indicator is not built. Logged, not worked around.*
- **A national GTFS feed.** Digitransit's aggregated national routing data answers **401**
  without a registered subscription key. Fintraffic's FINAP is keyless but is a *catalogue*
  of ~292 separate operator feeds of uneven quality, not one file. HSL's own
  `https://dev.hsl.fi/gtfs/hsl.zip` is keyless and current. *Decision (phase 12): GTFS stops
  come from HSL for the Helsinki region; everywhere else stops come from OpenStreetMap, and
  every point says which it is.*

## What this means for the build, in one line each

| Phase | Built from | Not built, and why |
|---|---|---|
| 11 Climate | SYKE WMS raster + mapped-extent vectors; STUK radon xlsx | sea level (no national data), stormwater (not published) |
| 12 Services | OSM (Geofabrik) + HSL GTFS + Palvelukartta | national GTFS (needs a key) |
| 13 Infra | Väylävirasto `hanketiedot:*` + hand-curated named projects | — |
| 14 Schools | Tilastokeskus `oppilaitokset` + YTL microdata | comprehensive-school results (Finland publishes none) |
| 15 Buildings | Ryhti `avoimet_rakennukset`; Helsinki `Kaavayksikot` for k-m² | energy certificates (paid), national floor area (not published) |

<!-- PROBE:BEGIN — generated by scripts/probe_fi.py, do not edit between the markers -->

## Routes probed — run 2026-09-24

Every row below is a real request made by `scripts/probe_fi.py` on the Mac. `e` after a variable's value count means the API can eliminate it (leave it out and get the total); `T` marks the time variable. A ✗ row is kept, not deleted: knowing that a route is dead is the point of a probe.


## StatFin PxWeb

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [PxWebApi v2? pxdata.stat.fi/PxWeb/api/v2/](https://pxdata.stat.fi/PxWeb/api/v2/) | 404 | 1.26 | 0 | HTTP 404 — not live, v1 only |
| [PxWebApi v2? pxdata.stat.fi/PxWeb/api/v2-beta/](https://pxdata.stat.fi/PxWeb/api/v2-beta/) | 404 | 1.24 | 0 | HTTP 404 — not live, v1 only |
| [PxWebApi v2? statfin.stat.fi/api/v2/](https://statfin.stat.fi/api/v2/) | 404 | 2.29 | 0 | HTTP 404 — not live, v1 only |
| [db StatFin/vaerak](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/) | 200 | 1.36 | 4,614 | 32 tables · 11ra, 11rb, 11rc, 11rd, 11re, 11rf, 11rg, 11rh, 11rk, 11rl, 11rm, 11rp |
| [db StatFin/tjt](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tjt/) | 200 | 1.39 | 4,239 | 25 tables · 118w, 11py, 11wh, 11x3, 122s, 128c, 128j, 12ci, 12eb, 12ew, 12g4, 12g9 |
| [db StatFin/tyonv](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tyonv/) | 200 | 1.42 | 13,297 | 72 tables · 12r5, 12t8, 12t9, 12ta, 12tb, 12tc, 12td, 12te, 12tf, 12tg, 12th, 12ti |
| [db StatFin/muutl](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/muutl/) | 200 | 1.34 | 2,951 | 19 tables · 119z, 11a1, 11a2, 11a3, 11a4, 11a5, 11a6, 11a7, 11a8, 11a9, 11aa, 11ab |
| [db StatFin/vaenn](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaenn/) | 200 | 1.42 | 1,090 | 7 tables · 128t, 139e, 14wx, 14wy, 14wz, 14x1, 14x2 |
| [db StatFin/rpk](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/rpk/) | 200 | 1.35 | 10,132 | 52 tables · 11yy, 13ex, 13f1, 13f3, 13f4, 13f7, 13fr, 13g1, 13ga, 13gj, 13gw, 13h4 |
| [db StatFin/asku](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asku/) | 200 | 1.46 | 733 | 4 tables · 15fd, 157s, 15fh, 15fi |
| [db StatFin/raku](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/) | 200 | 1.36 | 1,047 | 7 tables · 156f, 156g, 156h, 156i, 15er, 15f6, 15f7 |
| [db StatFin/ashi](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/) | 200 | 1.36 | 3,784 | 19 tables · 12dd, 12de, 12dg, 12fv, 12fw, 13mq, 13mt, 13mu, 13mw, 13mv, 13mx, 13mz |
| [db StatFin/asvu](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/) | 200 | 1.34 | 345 | 2 tables · 15fa, 15fc |
| [db StatFin/ras](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ras/) | 400 | 1.36 | 0 | HTTP 400 — database does not exist (discontinued? check StatFin_Passiivi) |
| [db StatFin/asas](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asas/) | 400 | 1.34 | 0 | HTTP 400 — database does not exist (discontinued? check StatFin_Passiivi) |
| [db StatFin/rakke](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/rakke/) | 400 | 1.41 | 0 | HTTP 400 — database does not exist (discontinued? check StatFin_Passiivi) |
| [db StatFin/astuki](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/astuki/) | 400 | 1.35 | 0 | HTTP 400 — database does not exist (discontinued? check StatFin_Passiivi) |
| [db StatFin_Passiivi/asvu](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/) | 200 | 1.41 | 1,272 | 7 tables · statfinpas_asvu_pxt_11x4_2025q4, statfinpas_asvu_pxt_11x5_2025, statfinpas_asvu_pxt_12d4_2025q4, statfinpas_asvu_pxt_12ee_2025q4, statfinpas_asvu_pxt_13eb_2025q4, statfinpas_asvu_pxt_001_2018q4, statfinpas_asvu_pxt_901_2014q3 |
| [db StatFin_Passiivi/asas](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asas/) | 200 | 1.5 | 2,979 | 15 tables · statfinpas_asas_pxt_115a_2024, statfinpas_asas_pxt_115y_2024, statfinpas_asas_pxt_115z_2024, statfinpas_asas_pxt_116a_2024, statfinpas_asas_pxt_116b_2024, statfinpas_asas_pxt_116d_2024, statfinpas_asas_pxt_116e_2024, statfinpas_asas_pxt_116f_2024, statfinpas_asas_pxt_13ui_2024q4, statfinpas_asas_pxt_001_201700, statfinpas_asas_pxt_002_201700, statfinpas_asas_pxt_003_201700 |
| [db StatFin_Passiivi/ras](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/ras/) | 200 | 1.51 | 1,827 | 12 tables · statfinpas_ras_pxt_12fy_202412, statfinpas_ras_pxt_12fz_202412, statfinpas_ras_pxt_13m4_202411, statfinpas_ras_pxt_13m5_202411, statfinpas_ras_pxt_118r_2020m01, statfinpas_ras_pxt_118t_2020m01, statfinpas_ras_pxt_001_201806, statfinpas_ras_pxt_002_201806, statfinpas_ras_pxt_901_201412_en, statfinpas_ras_pxt_902_201412, statfinpas_ras_pxt_903_2014q4_en, statfinpas_ras_pxt_904_2014q4_en |
| [population by age, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/11re.px) | 200 | 1.36 | 8,280 | 1972–2025 · alue_23_20260101[309e] ikaryhma_10_20180101[102e] sukupuoli_9_20180101[3e] timeperiod_y[54T] contentscode[1] |
| [population key figures, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/11ra.px) | 200 | 1.36 | 18,039 | 1990–2025 · alue_23_20260101[568e] contentscode[43] timeperiod_y[36T] |
| [population by language, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/11rm.px) | 200 | 1.35 | 9,820 | 1990–2025 · alue_23_20260101[309e] kieli_15_20180102[169e] sukupuoli_9_20180101[3e] timeperiod_y[36T] contentscode[1] |
| [household-dwelling units, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asku/15fh.px) | 200 | 1.35 | 7,259 | 2005–2025 · alue_23_20260101[309e] talotyyppi_4_20210101[5e] timeperiod_y[21T] asuntokuntakoko_3_20190101[5e] huoneluku_2_20190101[9e] contentscode[2] |
| [dwelling floor area per unit / person](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asku/15fd.px) | 200 | 1.39 | 7,568 | 2005–2025 · alue_23_20260101[328e] timeperiod_y[21T] contentscode[10] |
| [income of household-dwelling units](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tjt/118w.px) | 200 | 1.35 | 12,289 | 1995–2024 · contentscode[39] timeperiod_y[30T] alue_23_20250101[420e] |
| [median income of inhabitants](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tjt/14ww.px) | 200 | 1.35 | 12,247 | 1995–2024 · alue_23_20250101[420] contentscode[26] timeperiod_y[30T] |
| [unemployment rate, kunta, monthly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tyonv/12tf.px) | 200 | 1.36 | 13,903 | 2009M01–2026M08 · Alue[421e] timeperiod_m[212T] contentscode[3] |
| [migration, kunta, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/muutl/11ae.px) | 200 | 1.37 | 7,525 | 1990–2025 · timeperiod_y[36T] alue_23_20260101[309e] contentscode[21] |
| [migration, kunta, monthly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/muutl/12w7.px) | 200 | 1.4 | 15,662 | 1990M01–2025M12 · alue_23_20260101[309e] contentscode[21] timeperiod_m[432T] |
| [population projection 2024](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaenn/14wx.px) | 200 | 1.42 | 7,895 | 2024–2045 · alue_23_20240101[310e] timeperiod_y[22T] sukupuoli_9_20180101[3e] ikaryhma_10_20180101[102e] contentscode[1] |
| [offences, kunta, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/rpk/13ex.px) | 200 | 1.35 | 21,928 | 1980–2025 · timeperiod_y[46T] alue_23_20230101[311e] rikokset_74_20211209[209e] contentscode[14] |
| [offences, kunta, monthly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/rpk/13it.px) | 200 | 1.47 | 24,254 | 2009M01–2026M06 · timeperiod_m[210T] alue_23_20230101[311e] rikokset_74_20211209[209] contentscode[1] |
| [old dwelling prices, postal, quarterly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mt.px) | 200 | 1.39 | 71,906 | 2009Q1–2026Q1 · timeperiod_q[69T] postinumeroalue_4_20220101[1724] talotyyppi_6_20131021[4] contentscode[2] |
| [old dwelling prices, postal, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mu.px) | 200 | 1.38 | 70,895 | 2009–2025 · timeperiod_y[17T] postinumeroalue_4_20220101[1724] talotyyppi_6_20131021[4] contentscode[2] |
| [old dwelling prices, kunta, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mx.px) | 200 | 1.41 | 6,176 | 2006–2025 · timeperiod_y[20T] kunta_1_20150101[301] talotyyppi_5_20111209[3e] contentscode[3] |
| [old dwelling prices, quarterly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mv.px) | 200 | 1.24 | 4,181 | 2006Q1–2026Q1 · timeperiod_q[81T] alue_43_20220407[87] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] contentscode[3] |
| [price index old dwellings 2025=100](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/15is.px) | 200 | 1.35 | 3,678 | 2025Q1–2026Q2 · alue_43_20260625[87e] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] timeperiod_q[6T] contentscode[8] |
| [price index old dwellings, long chain](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/15it.px) | 200 | 1.43 | 6,744 | 1988Q1–2026Q2 · alue_43_20260625[87e] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] timeperiod_q[154T] contentscode[14] |
| [price index old dwellings 2020=100](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mq.px) | 200 | 1.35 | 2,978 | 2020–2025 · timeperiod_y[6T] alue_43_20220407[87] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] contentscode[7] |
| [new dwelling prices by sub-area](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/12dg.px) | 200 | 1.39 | 1,920 | 2015–2025 · alue_3_20181009[27] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] timeperiod_y[11T] contentscode[2] |
| [new dwelling prices by plot ownership](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/12dd.px) | 200 | 1.34 | 2,203 | 2015Q1–2026Q1 · alue_3_20181009[15] vuokratontti_1_20191126[3e] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] timeperiod_q[45T] contentscode[2] |
| [price index new dwellings 2025=100](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/15iw.px) | 200 | 1.35 | 1,159 | 2025Q1–2026Q2 · alue_43_20260625[11e] timeperiod_q[6T] contentscode[4] |
| [rents incl. ARA, index + EUR/m2](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/15fa.px) | 200 | 13.43 | 3,152 | 2025Q1–2026Q2 · rahoitus_2_20260101[3] huoneluku_5_20260101[4] alue_44_20260101[85] timeperiod_q[6T] contentscode[7] |
| [free-market rents by postal code](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/13eb.px) | 400 | 1.34 | 0 | HTTP 400 — table not in this database |
| [free-market rents by postal code (archive)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_13eb_2025q4.px) | 200 | 1.51 | 26,564 | 2015Q1–2025Q4 · Vuosineljännes[44T] Postinumero[580] Huoneluku[3] Tiedot[2] |
| [rents (archive, long history)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_11x4_2025q4.px) | 200 | 1.41 | 3,582 | 2015Q1–2025Q4 · Vuosineljännes[44T] Alue[84] Huoneluku[4e] Rahoitusmuoto[3e] Tiedot[8] |
| [building and dwelling production](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/156f.px) | 200 | 1.38 | 10,194 | 1995M01–2026M07 · rakennusvaihe_1_20250101[3] alue_23_20260101[20] timeperiod_m[379T] rakennus_6_20180101[24e] contentscode[8] |
| [dwelling stock incl. unoccupied, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/15f6.px) | 200 | 1.35 | 7,119 | 2025–2025 · alue_23_20260101[309e] talotyyppi_4_20210101[5e] rak_valm_v_10_20210101[12e] asunnon_kaytolo_3_20190101[3e] timeperiod_y[1T] contentscode[1] |
| [dwelling stock by tenure (archive)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asas/statfinpas_asas_pxt_115y_2024.px) | 200 | 1.41 | 7,295 | 2005–2024 · Alue[309e] Hallintaperuste[7e] Talotyyppi[5e] Huoneita[6e] Vuosi[20T] Tiedot[2] |
| [rent distributions, sub-areas of large cities](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/15fc.px) | 200 | 1.35 | 1,693 | 2025Q1–2026Q2 · huoneluku_5_20260101[3] alue_44_20260101[49] timeperiod_q[6T] contentscode[4] |
| [building stock by use and year](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/15er.px) | 200 | 1.47 | 7,842 | 2025–2025 · alue_23_20260101[309e] rakennus_6_20180101[18e] timeperiod_y[1T] rak_valm_v_10_20210101[12e] polttoaineet_12_20260101[8e] contentscode[2] |
| [new production, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/15f7.px) | 200 | 1.35 | 2,364 | 2005–2025 · alue_23_20260101[20e] rakennus_6_20180101[18e] polttoaineet_12_20260101[8e] timeperiod_y[21T] contentscode[2] |
| [household-dwelling units by tenure?](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asku/15fi.px) | 200 | 1.36 | 7,346 | 2005–2025 · alue_23_20260101[309e] talotyyppi_4_20210101[5e] timeperiod_y[21T] asuntokuntakoko_3_20190101[5e] sukupuoli_15_20190101[3e] ikaryhma_27_20220101[4e] contentscode[1] |
| [dwelling production (archive, kunta, monthly)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/ras/statfinpas_ras_pxt_12fy_202412.px) | 200 | 1.58 | 9,604 | 1995M01–2024M12 · Rakennusvaihe[3] Alue[20e] Kuukausi[360T] Käyttötarkoitus[24e] Tiedot[8] |

## Geometry (WFS)

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [Paavo capabilities](https://geo.stat.fi/geoserver/postialue/wfs?service=WFS&request=GetCapabilities&version=1.0.0) | 200 | 1.29 | 33,632 | 40 layers |
| [Paavo pno_tilasto layers](https://geo.stat.fi/geoserver/postialue/wfs) | 200 | 0.0 | 0 | 12 vintages, latest postialue:pno_tilasto_2026 |
| [Paavo sample postialue:pno_tilasto_2026](https://geo.stat.fi/geoserver/postialue/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=postialue%3Apno_tilasto_2026&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.26 | 8,550 | 3018 features · 113 props · id, postinumeroalue, nimi, namn, euref_x, euref_y, pinta_ala, vuosi, kunta, he_vakiy, he_naiset, he_miehet, he_kika, he_0_2 |
| [tilastointialueet capabilities](https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS&request=GetCapabilities&version=1.0.0) | 200 | 1.33 | 100,954 | 228 layers |
| [kunta1000k_* layers](https://geo.stat.fi/geoserver/tilastointialueet/wfs) | 200 | 0.0 | 0 | 14 vintages, latest tilastointialueet:kunta1000k_2026 |
| [sample tilastointialueet:kunta1000k_2026](https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=tilastointialueet%3Akunta1000k_2026&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.24 | 4,338 | 308 features · 6 props · id, kunta, vuosi, nimi, namn, name |
| [maakunta1000k_* layers](https://geo.stat.fi/geoserver/tilastointialueet/wfs) | 200 | 0.0 | 0 | 14 vintages, latest tilastointialueet:maakunta1000k_2026 |
| [sample tilastointialueet:maakunta1000k_2026](https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=tilastointialueet%3Amaakunta1000k_2026&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.39 | 1,074,839 | 19 features · 6 props · id, maakunta, vuosi, nimi, namn, name |
| [HSY capabilities](https://kartta.hsy.fi/geoserver/wfs?service=WFS&request=GetCapabilities&version=1.0.0) | 200 | 1.29 | 189,017 | 398 layers |
| [HSY seutukartta_pien_2021](https://kartta.hsy.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=taustakartat_ja_aluejaot%3Aseutukartta_pien_2021&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.38 | 5,304 | 824 features · 8 props · kokotun, kunta, suur, tila, pien, nimi, nimi_iso, mtryhm |
| [HSY seutukartta_tila_2021](https://kartta.hsy.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=taustakartat_ja_aluejaot%3Aseutukartta_tila_2021&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.29 | 5,977 | 336 features · 7 props · kokotun, kunta, suur, tila, nimi, nimi_iso, mtryhm |
| [HSY seutukartta_suur_2021](https://kartta.hsy.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=taustakartat_ja_aluejaot%3Aseutukartta_suur_2021&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.36 | 10,824 | 67 features · 6 props · kokotun, kunta, suur, nimi, nimi_iso, mtryhm |
| [Helsinki avoindata capabilities](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&request=GetCapabilities&version=1.0.0) | 200 | 1.3 | 112,906 | 305 layers |
| [Helsinki Piirijako_osaalue](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3APiirijako_osaalue&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.3 | 10,548 | 148 features · 12 props · id, aluejako, kunta, tunnus, nimi_fi, nimi_se, yhtluontipvm, yhtmuokkauspvm, yhtdatanomistaja, kokotunnus, paivitetty_tietopalveluun, datanomistaja |
| [Helsinki Piirijako_peruspiiri](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3APiirijako_peruspiiri&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.26 | 31,701 | 34 features · 12 props · aluejako, datanomistaja, id, kokotunnus, kunta, nimi_fi, nimi_se, paivitetty_tietopalveluun, tunnus, yhtdatanomistaja, yhtluontipvm, yhtmuokkauspvm |
| [Helsinki Piirijako_suurpiiri](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3APiirijako_suurpiiri&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.52 | 22,456 | 8 features · 12 props · id, aluejako, kunta, tunnus, nimi_fi, nimi_se, yhtluontipvm, yhtmuokkauspvm, yhtdatanomistaja, kokotunnus, paivitetty_tietopalveluun, datanomistaja |

## Aluesarjat

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [root https://stat.hel.fi/api/v1/en/Aluesarjat/](https://stat.hel.fi/api/v1/en/Aluesarjat/) | 200 | 1.4 | 82 | 2 folders · vrm, tul |
| [root https://stat.hel.fi/api/v1/fi/Aluesarjat/](https://stat.hel.fi/api/v1/fi/Aluesarjat/) | 200 | 1.31 | 337 | 7 folders · asu, his, kou, rak, tul, tyo, vrm |
| [root https://api.aluesarjat.fi/](https://api.aluesarjat.fi/) | 0 | 21.21 | 0 | no response (host does not resolve or does not answer) |

## File sources

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [Kelasto WebFOCUS report list](https://raportit.kela.fi/ibi_apps/WFServlet?IBIF_ex=NIT100AL) | 200 | 2.29 | 50,661 | HTTP 200 |
| [Kela open data landing](https://www.kela.fi/avoin-data) | 404 | 1.34 | 0 | HTTP 404 |
| [Verohallinto statistics landing](https://www.vero.fi/tietoa-verohallinnosta/tilastot/) | 200 | 1.35 | 108,563 | HTTP 200 |
| [avoindata.fi API — dataset search 'kiinteistövero'](https://www.avoindata.fi/data/api/3/action/package_search?q=kiinteist%C3%B6veroprosentit&rows=5) | 200 | 2.7 | 222 | 0 datasets ·  |
| [avoindata.fi API — dataset search 'kunnallisvero'](https://www.avoindata.fi/data/api/3/action/package_search?q=kunnallisveroprosentti&rows=5) | 200 | 2.21 | 222 | 0 datasets ·  |

## Reference values

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [Helsinki (091) population, latest year](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/11re.px) | 200 | 1.37 | 3,036 | vaerak/11re → [694392] (persons, 31 Dec 2025) |
| [00100 price EUR/m2, blocks of flats 2-room, latest quarter](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mt.px) | 200 | 2.14 | 4,368 | ashi/13mt → [7167, 35] (EUR/m2 and number of sales) |
| [00100 rent EUR/m2/month, 1-room, latest quarter (archive)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_13eb_2025q4.px) | 200 | 1.33 | 2,920 | StatFin_Passiivi:asvu/13eb_2025q4 → [746, 29.43] (observation count and EUR/m2/month) |
| [Helsinki (091) free-market rent, 1-room, live table](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/15fa.px) | 200 | 1.26 | 3,665 | asvu/15fa → [26.73, 19543] (EUR/m2/month and observation count — the live replacement for 13eb, kunta level only) |
| [Helsinki (091) ARA rent, 1-room, live table](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/15fa.px) | 200 | 1.34 | 3,671 | asvu/15fa → [18.48, 7587] (government-subsidised (ARA) rent, EUR/m2/month) |

## Climate (phase 11)

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [SYKE INSPIRE_Syke_Luonnonriskialueet capabilities](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetCapabilities) | 200 | 1.39 | 148,988 | 24 layers · Tulvavaaravyohykkeet: 16 (inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_1000a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_100a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_10a) · Tulvavaarakartoitetut: 2 (inspire_nz:NZ.Tulvavaarakartoitetut_alueet_Meritulva, inspire_nz:NZ.Tulvavaarakartoitetut_alueet_Vesistotulva) · Merkittavat_tulvariski: 1 (inspire_nz:NZ.Merkittavat_tulvariskialueet) |
| [flood-hazard zone layers](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs) | 200 | 0.0 | 0 | 16 layers — return period is in the LAYER NAME, not only an attribute: inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_1000a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_100a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_10a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_20a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_250a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_2a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_50a, inspire_nz:NZ.Tulvavaaravyohykkeet_Meritulva_1_5a, inspire_nz:NZ.Tulvavaaravyohykkeet_Vesistotulva_1_1000a, inspire_nz:NZ.Tulvavaaravyohykkeet_Vesistotulva_1_100a, inspire_nz:NZ.Tulvavaaravyohykkeet_Vesistotulva_1_10a, inspire_nz:NZ.Tulvavaaravyohykkeet_Vesistotulva_1_20a, inspire_nz:NZ.Tulvavaaravyohykkeet_Vesistotulva_1_250a, inspire_nz:NZ.Tulvavaaravyohykkeet_Vesistotulva_1_2a, inspire_nz:NZ.Tulvavaaravyohykkeet_Vesistotulva_1_50a, inspire_nz:NZ.Tulvavaaravyohykkeet_Vesistotulva_1_5a |
| [Vesistotulva 1/100a sample](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaaravyohykkeet_Vesistotulva_1_100a&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.34 | 4,007 | 3412672 features · 23 props · objectid, kohdenro, nimi, tulvakartoitustyyppi, toistuvuus, syvsuojluokka_id, syvsuojluokka, syvvyohluokka_id, syvvyohluokka, tulvasuojluokka_id, tulvasuojluokka, silta_id, silta, maarityswmenetelma |
| [Vesistotulva 1/100a national count](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaaravyohykkeet_Vesistotulva_1_100a&resultType=hits) | 200 | 1.36 | 780 | 3412672 features |
| [Vesistotulva 1/1000a sample](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaaravyohykkeet_Vesistotulva_1_1000a&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.38 | 4,695 | 4599961 features · 23 props · objectid, kohdenro, nimi, tulvakartoitustyyppi, toistuvuus, syvsuojluokka_id, syvsuojluokka, syvvyohluokka_id, syvvyohluokka, tulvasuojluokka_id, tulvasuojluokka, silta_id, silta, maarityswmenetelma |
| [Vesistotulva 1/1000a national count](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaaravyohykkeet_Vesistotulva_1_1000a&resultType=hits) | 200 | 2.57 | 781 | 4599961 features |
| [Meritulva 1/100a sample](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaaravyohykkeet_Meritulva_1_100a&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.41 | 33,500 | 4014394 features · 16 props · objectid, kohdenro, toistuvuus, syvsuojluokka_id, syvsuojluokka, tulvasuojluokka_id, syvvyohluokka_id, silta_id, korkeusain_id, korkeusainnro, korkeusvirhe_m, digorg, muutospvm, shape_length |
| [Meritulva 1/100a national count](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaaravyohykkeet_Meritulva_1_100a&resultType=hits) | 200 | 1.35 | 777 | 4014394 features |
| [Meritulva 1/1000a sample](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaaravyohykkeet_Meritulva_1_1000a&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.36 | 49,063 | 4759149 features · 16 props · objectid, kohdenro, toistuvuus, syvsuojluokka_id, syvsuojluokka, tulvasuojluokka_id, syvvyohluokka_id, silta_id, korkeusain_id, korkeusainnro, korkeusvirhe_m, digorg, muutospvm, shape_length |
| [Meritulva 1/1000a national count](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaaravyohykkeet_Meritulva_1_1000a&resultType=hits) | 200 | 1.37 | 778 | 4759149 features |
| [mapped extent — Vesistotulva](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaarakartoitetut_alueet_Vesistotulva&resultType=hits) | 200 | 1.27 | 777 | 113 features |
| [mapped extent — Meritulva](https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=inspire_nz%3ANZ.Tulvavaarakartoitetut_alueet_Meritulva&resultType=hits) | 200 | 1.27 | 772 | 8 features |
| [SYKE bulk zip — tulvavaaravyohykkeet_meri](https://sykedata.ymparisto.fi/gisdata-1/tulva/tulvavaaravyohykkeet/tulvavaaravyohykkeet_meri.zip) | 200 | 1.23 | 5,590,049,509 | 5,590,049,509 bytes · Last-Modified Tue, 25 Nov 2025 07:10:37 GMT · application/x-zip-compressed |
| [SYKE bulk zip — tulvavaaravyohykkeet_vesisto](https://sykedata.ymparisto.fi/gisdata-1/tulva/tulvavaaravyohykkeet/tulvavaaravyohykkeet_vesisto.zip) | 200 | 1.23 | 5,649,081,834 | 5,649,081,834 bytes · Last-Modified Thu, 19 Mar 2026 11:35:27 GMT · application/x-zip-compressed |
| [Helsinki — FMI site flood height 2100 (points)](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3AFMI_Paikkakohtainen_tulvakorkeus_vuonna_2100_piste&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.64 | 800 | 453 features · 5 props · id, tk, mittauspiste, datanomistaja, paivitetty_tietopalveluun |
| [avoindata.fi search — merenpinnan nousu](https://www.avoindata.fi/data/api/3/action/package_search?q=merenpinnan+nousu&rows=5) | 200 | 1.58 | 222 | 0 datasets — nothing published |
| [avoindata.fi search — tulvavaaravyöhyke](https://www.avoindata.fi/data/api/3/action/package_search?q=tulvavaaravy%C3%B6hyke&rows=5) | 200 | 1.73 | 222 | 0 datasets — nothing published |
| [avoindata.fi search — hulevesitulva](https://www.avoindata.fi/data/api/3/action/package_search?q=hulevesitulva&rows=5) | 200 | 1.73 | 58,304 | 3 datasets · Purkupisteet ja osavaluma-alueet; Tulvariskialueet; Uomakorjaus: rumpujen kaiverrus (korkeusmall |
| [avoindata.fi search — radon](https://www.avoindata.fi/data/api/3/action/package_search?q=radon&rows=5) | 200 | 1.61 | 222 | 0 datasets — nothing published |
| [HSY WFS — any hulevesi/tulva layer?](https://kartta.hsy.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetCapabilities) | 200 | 1.29 | 349,909 | 397 layers · hulevesi: 1 (vesihuolto:vh_hulevesiviemaroity_alue) · tulva: 0 — none |
| [Helsinki WFS — any hulevesi/tulva layer?](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetCapabilities) | 200 | 1.37 | 305,680 | 304 layers · hulevesi: 0 — none · tulva: 1 (avoindata:FMI_Paikkakohtainen_tulvakorkeus_vuonna_2100_piste) |
| [STUK radon kunta_ja_koko_suomi 2023 (xlsx)](https://stuk.fi/documents/150192312/157590338/radontilasto_pientalot_kunta_ja_koko_suomi_2023.xlsx) | 200 | 1.43 | 25,913 | 25,913 bytes · Last-Modified Thu, 04 Apr 2024 09:54:44 GMT · application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| [STUK radon postinumero 2023 (xlsx)](https://stuk.fi/documents/150192312/157590338/radontilasto_pientalot_postinumero_2023.xlsx) | 429 | 1.24 | 0 | HTTP 429 — the publisher rate-limited this HEAD; the file itself answers 200 when asked on its own |

## Buildings, addresses and zoning (phases 10, 15)

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [Ryhti ryhti_building collections](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1/collections?f=application/json) | 200 | 3.27 | 20,793 | 5 collections · avoimet_lupa_rakennukset, avoimet_rakennukset, open_address, open_address_deleted, open_building |
| [avoimet_rakennukset — one feature](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1/collections/avoimet_rakennukset/items?limit=1&f=application/json) | 200 | 1.85 | 1,421 | 3,799,798 features · Point · 25 fields · rakennusavain, pysyva_rakennustunnus, sijaintikiinteisto, valmistumispaivamaara, paaasiallinen_kayttotarkoitus, kuntanumero, kaytossaolo, purkamispaivamaara, julkisivumateriaali, lammitystapa, lammitysenergian_lahde, kantavien_rakenteiden_rakennusaine, rakentamistapa, tilavuus, kerrosluku, kerrosala |
| [avoimet_lupa_rakennukset — one feature](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1/collections/avoimet_lupa_rakennukset/items?limit=1&f=application/json) | 200 | 1.61 | 1,727 | 2,738,706 features · Point · 33 fields · rakennusavain, pysyva_rakennustunnus, pysyva_lupatunnus, kuntanumero, sijaintikiinteisto, dvv_lupatunnus, paatospaivamaara, toimenpiteen_laji, toimenpiteen_tila, aloittamispaivamaara, rakennustyot_aloitettava_jatkoa_asti, valmistumispaivamaara, raukeamispaivamaara, paaasiallinen_kayttotarkoitus, kaytossaolo, purkamispaivamaara |
| [open_address — one feature](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1/collections/open_address/items?limit=1&f=application/json) | 200 | 1.37 | 1,348 | 3,861,495 features · Point · 21 fields · address_key, building_key, address_fin, address_swe, postal_office_fin, postal_office_swe, address_number, address_name_fin, address_name_swe, number_part_of_address_number, number_part_of_address_number2, municipality_number, subdivision_letter_of_address_number, subdivision_letter_of_address_number2, postal_code, location_srid |
| [avoimet_rakennukset — CQL kuntanumero='091'](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1/collections/avoimet_rakennukset/items?limit=1&f=application/json&filter=kuntanumero%3D%27091%27) | 200 | 1.36 | 1,461 | 53,160 features · Point · 25 fields · rakennusavain, pysyva_rakennustunnus, sijaintikiinteisto, valmistumispaivamaara, paaasiallinen_kayttotarkoitus, kuntanumero, kaytossaolo, purkamispaivamaara, julkisivumateriaali, lammitystapa, lammitysenergian_lahde, kantavien_rakenteiden_rakennusaine, rakentamistapa, tilavuus, kerrosluku, kerrosala |
| [open_address via WFS — CSV + propertyName + CQL (the fetch route)](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=ryhti_building:open_address&count=3&outputFormat=csv&srsName=EPSG:4326&propertyName=address_name_fin,address_name_swe,number_part_of_address_number,subdivision_letter_of_address_number,municipality_number,postal_code,location_geometry_data&CQL_FILTER=municipality_number%3D%27091%27) | 200 | 1.31 | 707 | columns: FID,address_key,address_name_fin,address_name_swe,number_part_of_address_number,municipality_number,subdivision_letter_of_address_number,postal_code,location_geometry_data |
| [open_address — Helsinki (091) count](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=ryhti_building%3Aopen_address&resultType=hits&CQL_FILTER=municipality_number%3D%27091%27) | 200 | 1.37 | 802 | 66640 features |
| [open_address — national count](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=ryhti_building%3Aopen_address&resultType=hits) | 200 | 1.38 | 757 | 3861495 features |
| [Ryhti ryhti_plan collections](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_plan/ogc/features/v1/collections?f=application/json) | 200 | 1.27 | 17,024 | 4 collections · pub_prep_ld_plan_ix_gs, pub_prep_lm_plan_ix_gs, pub_valid_ld_plan_ix_gs, pub_valid_lm_plan_ix_gs |
| [pub_valid_ld_plan_ix_gs — one feature](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_plan/ogc/features/v1/collections/pub_valid_ld_plan_ix_gs/items?limit=1&f=application/json) | 200 | 1.27 | 3,064 | 5,635 features · Polygon · 33 fields · id, plan_key, permanent_plan_identifier, producer_plan_identifier, plan_type, plan_type_name_fin, original_administrative_area_identifiers, administrative_area_identifiers, name_fin, name_swe, name_eng, name_smn, name_sms, name_sme, description_fin, description_swe |
| [pub_valid_lm_plan_ix_gs — one feature](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_plan/ogc/features/v1/collections/pub_valid_lm_plan_ix_gs/items?limit=1&f=application/json) | 200 | 1.26 | 6,716 | 647 features · Polygon · 33 fields · id, plan_key, permanent_plan_identifier, producer_plan_identifier, plan_type, plan_type_name_fin, original_administrative_area_identifiers, administrative_area_identifiers, name_fin, name_swe, name_eng, name_smn, name_sms, name_sme, description_fin, description_swe |
| [pub_prep_ld_plan_ix_gs — one feature](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_plan/ogc/features/v1/collections/pub_prep_ld_plan_ix_gs/items?limit=1&f=application/json) | 200 | 1.32 | 147 | 0 features · - · 0 fields ·  |
| [pub_prep_lm_plan_ix_gs — one feature](https://paikkatiedot.ymparisto.fi/geoserver/ryhti_plan/ogc/features/v1/collections/pub_prep_lm_plan_ix_gs/items?limit=1&f=application/json) | 200 | 1.26 | 147 | 0 features · - · 0 fields ·  |
| [Helsinki Kaavayksikot](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3AKaavayksikot&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.56 | 1,065 | 40081 features · 17 props · id, kaavayksikkotunnus, kaavatunnus, kunta, sijaintialue, ryhma, yksikko, luokka, rakennusoikeus, kayttotarkoitusluokka, kayttotarkoitusluokka_koodi, rekisteriala, pa_maartapa, osoite |
| [Helsinki Kaavahakemisto_alue_kaava_voimassa](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3AKaavahakemisto_alue_kaava_voimassa&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.53 | 1,517 | 4391 features · 16 props · id, tyyppi, kaavatunnus, luokka, alkuperainen, pintaala, korkeusjarjestelma, sijaintialue, hyvaksymispvm, lainvoimaisuuspvm, voimaantulopvm, vahvistamispvm, luontipvm, muokkauspvm |
| [Helsinki Kaavahakemisto_alue_kaava_vireilla](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3AKaavahakemisto_alue_kaava_vireilla&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.35 | 1,235 | 78 features · 16 props · id, tyyppi, kaavatunnus, luokka, alkuperainen, pintaala, korkeusjarjestelma, sijaintialue, hyvaksymispvm, lainvoimaisuuspvm, voimaantulopvm, vahvistamispvm, luontipvm, muokkauspvm |
| [DVV osoiteet_2025.shp (legacy bulk file)](https://ftp.csc.fi/index/geodata/dvv/osoitteet/2025/osoiteet_2025.shp) | 0 | 1.22 | 0 | <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismat |
| [DVV readme — is the file still maintained?](https://ftp.csc.fi/index/geodata/dvv/osoitteet/2025/rakennukset_readme.txt) | 0 | 1.22 | 0 | HTTP 0 |
| [Tilastokeskus vaestoruutu capabilities](https://geo.stat.fi/geoserver/vaestoruutu/wfs?service=WFS&version=2.0.0&request=GetCapabilities) | 200 | 1.32 | 141,095 | 51 layers · vaki: 51 (vaestoruutu:vaki2005_1km, vaestoruutu:vaki2005_1km_kp, vaestoruutu:vaki2005_5km) · _1km: 34 (vaestoruutu:vaki2005_1km, vaestoruutu:vaki2005_1km_kp, vaestoruutu:vaki2010_1km) |
| [1 km grid sample vaestoruutu:vaki2025_1km](https://geo.stat.fi/geoserver/vaestoruutu/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=vaestoruutu%3Avaki2025_1km&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.24 | 1,239 | 96904 features · 12 props · oid, grd_id, id_nro, xkoord, ykoord, kunta, vaesto, miehet, naiset, ika_0_14, ika_15_64, ika_65_ |
| [1 km grid count vaestoruutu:vaki2025_1km](https://geo.stat.fi/geoserver/vaestoruutu/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=vaestoruutu%3Avaki2025_1km&resultType=hits) | 200 | 1.33 | 735 | 96904 features |
| [ARA energiatodistusrekisteri — Suomi.fi service catalogue entry](https://liityntakatalogi.suomi.fi/dataset/energiatodistusrekisteri-ara-svc) | 200 | 1.45 | 17,628 | 200 · page names a fee ('maksullinen') and an ARA data permit ('tietolupa') |
| [avoindata.fi search — energiatodistus](https://www.avoindata.fi/data/api/3/action/package_search?q=energiatodistus&rows=5) | 200 | 1.65 | 222 | 0 datasets — nothing published |

## Services and transport (phase 12)

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [HSL static GTFS (keyless mirror)](https://dev.hsl.fi/gtfs/hsl.zip) | 200 | 1.43 | 80,535,403 | 80,535,403 bytes · Last-Modified Thu, 24 Sep 2026 03:03:02 GMT · application/zip |
| [Digitransit national routing data (needs a subscription key?)](https://api.digitransit.fi/routing-data/v3/finland/) | 401 | 1.28 | 0 | 401 — a free but REGISTERED subscription key is required, so it is out for a keyless build |
| [FINAP / Fintraffic catalogue — schedule services](https://finap.fi/ote/service-search?sub_types=schedule) | 200 | 2.36 | 205,412 | HTTP 200, 205,412 bytes (not JSON — an HTML catalogue page) |
| [Palvelukartta — one unit](https://api.hel.fi/servicemap/v2/unit/?page_size=1) | 200 | 1.44 | 3,740 | 21,506 · fields: id, connections, entrances, accessibility_properties, identifiers, department, root_department, provider_type, organizer_type, contract_type, picture_url, organizer_name, organizer_business_id, picture_entrance_url |
| [Palvelukartta — service nodes, page 1](https://api.hel.fi/servicemap/v2/service_node/?page_size=1) | 200 | 1.51 | 544 | 1,593 · fields: id, children, name, last_modified_time, level, parent, keywords, related_services, period_enabled, root, unit_count |
| [Palvelukartta — units in Helsinki](https://api.hel.fi/servicemap/v2/unit/?municipality=helsinki&page_size=1) | 200 | 1.46 | 3,762 | 12,452 · fields: id, connections, entrances, accessibility_properties, identifiers, department, root_department, provider_type, organizer_type, contract_type, picture_url, organizer_name, organizer_business_id, picture_entrance_url |
| [LIPAS — sports-site categories](https://api.lipas.fi/v2/sports-site-categories) | 200 | 1.28 | 1,019,497 | 141 entries · {'fi': 'Luisteluun, jääkiekkoon, kaukalopalloon, curlingiin tai muuhun jääurheiluun tarkoitettu kaukalo. Käytössä talvikaudella.', 'se': 'Rink avsedd för skridskoåkning, ishockey, rinkbandy osv. Används under vintersäsongen.', 'en': 'Rink intended for ice-skating, ice hockey, rink bandy, etc.'}, {'fi': ['jääkiekkokaukalo']}, {'fi': 'Kaukalo', 'se': 'Rink', 'en': 'Rink'}, 1530 |
| [LIPAS — one sports site](https://api.lipas.fi/v2/sports-sites?page-size=1) | 200 | 1.35 | 123,571 | HTTP 200 |
| [Geofabrik finland-latest.osm.pbf](https://download.geofabrik.de/europe/finland-latest.osm.pbf) | 200 | 1.26 | 767,442,456 | 767,442,456 bytes · Last-Modified Wed, 23 Sep 2026 23:47:37 GMT · application/octet-stream |

## Infra and schools (phases 13, 14)

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [Väylävirasto vaylatiedot capabilities](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetCapabilities) | 200 | 1.87 | 376,045 | 330 layers · hanketiedot: 17 (hanketiedot:inkoo_turvalaitteet_view, hanketiedot:koverhar_turvalaitteet_view, hanketiedot:paallystetty_tie_soratieksi_2025) · suunnitelma: 3 (hanketiedot:ratasuunnitelmat, hanketiedot:tiesuunnitelmat, hanketiedot:vesivaylasuunnitelmat) |
| [Väylä tiehankkeet sample](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Atiehankkeet&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.59 | 50,961 | 311 features · 13 props · id, nimi, tieosoite, tilaajaorganisaatio, aloitus, lopetus, kustannusarvio, kuvaus, linkki, irrotus_pvm, kunta, oid, length |
| [Väylä tiehankkeet count](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Atiehankkeet&resultType=hits) | 200 | 1.42 | 718 | 311 features |
| [Väylä ratahankkeet sample](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Aratahankkeet&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.45 | 2,020 | 166 features · 10 props · id, nimi, tilaajaorganisaatio, aloitus, lopetus, kustannusarvio, kuvaus, linkki, irrotus_pvm, oid |
| [Väylä ratahankkeet count](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Aratahankkeet&resultType=hits) | 200 | 1.46 | 719 | 166 features |
| [Väylä vesivaylahankkeet sample](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Avesivaylahankkeet&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.49 | 963 | 4 features · 9 props · id, nimi, tilaajaorganisaatio, aloitus, lopetus, kustannusarvio, kuvaus, linkki, irrotus_pvm |
| [Väylä vesivaylahankkeet count](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Avesivaylahankkeet&resultType=hits) | 200 | 1.45 | 722 | 4 features |
| [Väylä tiesuunnitelmat sample](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Atiesuunnitelmat&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.44 | 17,426 | 573 features · 17 props · id, nimi, tieosoite, tila, vaihe, tilaaja, kuvaus, kust_arvio, maku, suunnittelu_alkaa, suunnittelu_loppuu, arvioitu_toteutus, kohdesivu, ha_kortti |
| [Väylä tiesuunnitelmat count](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Atiesuunnitelmat&resultType=hits) | 200 | 1.43 | 722 | 573 features |
| [Väylä ratasuunnitelmat sample](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Aratasuunnitelmat&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.51 | 1,521 | 271 features · 17 props · id, nimi, vaihe, tila, tilaajaorganisaatio, kuvaus, kustannusarvio, maku_indeksi, kohdesivu, hankesivu, ratanumero, ha_kortti, suunnittelu_alkaa, suunnittelu_loppuu |
| [Väylä ratasuunnitelmat count](https://avoinapi.vaylapilvi.fi/vaylatiedot/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hanketiedot%3Aratasuunnitelmat&resultType=hits) | 200 | 1.46 | 723 | 271 features |
| [Tilastokeskus oppilaitokset sample](https://geo.stat.fi/geoserver/oppilaitokset/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=oppilaitokset%3Aoppilaitokset&count=1&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.24 | 637 | 2501 features · 9 props · id, oltyp_nimi, til_vuosi, tunn, onimi, olo, oltyp, euref_x, euref_y |
| [Tilastokeskus oppilaitokset count](https://geo.stat.fi/geoserver/oppilaitokset/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=oppilaitokset%3Aoppilaitokset&resultType=hits) | 200 | 1.31 | 739 | 2501 features |
| [YTL microdata FT2026KD4001.csv](https://tiedostot.ylioppilastutkinto.fi/ext/data/FT2026KD4001.csv) | 200 | 1.26 | 2,450,790 | 2,450,790 bytes · Last-Modified Wed, 02 Sep 2026 07:58:15 GMT · text/csv |
| [YTL microdata FT2025SD4001.csv](https://tiedostot.ylioppilastutkinto.fi/ext/data/FT2025SD4001.csv) | 200 | 1.22 | 493,228 | 493,228 bytes · Last-Modified Fri, 30 Jan 2026 03:15:20 GMT · text/csv |
| [YTL microdata FT2025KD4001.csv](https://tiedostot.ylioppilastutkinto.fi/ext/data/FT2025KD4001.csv) | 200 | 1.23 | 2,388,240 | 2,388,240 bytes · Last-Modified Tue, 02 Sep 2025 05:20:18 GMT · text/csv |
| [Väylävirasto — project list page](https://vayla.fi/hankkeet) | 200 | 2.33 | 386,369 | 200 · 386,369 bytes |
| [Väylävirasto — ohjelmakokonaisuus (the investment programme moved here in autumn 2025)](https://vayla.fi/ohjelmakokonaisuus) | 200 | 1.84 | 312,599 | 200 · 312,599 bytes |
| [YTL — statistics landing](https://www.ylioppilastutkinto.fi/tietopalvelut/tilastot) | 200 | 1.36 | 200,970 | 200 · 200,970 bytes |
| [Vipunen — open statistics service](https://vipunen.fi/) | 403 | 1.32 | 0 | HTTP 403 |
| [avoindata.fi search — oppilaitokset](https://www.avoindata.fi/data/api/3/action/package_search?q=oppilaitokset&rows=5) | 200 | 1.72 | 98,446 | 7 datasets · Oppilaitokset; Opintotuen saajat ja maksetut tuet; Helsingin Seudun Liikenteen (HSL) Reittioppa |
| [avoindata.fi search — ylioppilastutkinto](https://www.avoindata.fi/data/api/3/action/package_search?q=ylioppilastutkinto&rows=5) | 200 | 1.65 | 222 | 0 datasets — nothing published |
| [Väylävirasto — all projects (hankehaku)](https://vayla.fi/kaikki-hankkeet) | 200 | 1.45 | 386,369 | 200 · 386,369 bytes |
| [Palvelukartta service_node 1097 — basic education](https://api.hel.fi/servicemap/v2/unit/?service_node=1097&page_size=1) | 200 | 1.53 | 4,008 | service_node 1097 (basic education) → 537 units |
| [Palvelukartta service_node 1257 — upper secondary](https://api.hel.fi/servicemap/v2/unit/?service_node=1257&page_size=1) | 200 | 1.48 | 5,206 | service_node 1257 (upper secondary) → 65 units |
| [Palvelukartta service_node 869 — daycare](https://api.hel.fi/servicemap/v2/unit/?service_node=869&page_size=1) | 200 | 1.36 | 3,388 | service_node 869 (daycare) → 892 units |

**150 of 165 routes answered.**

<!-- PROBE:END -->
