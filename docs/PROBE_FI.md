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

<!-- PROBE:BEGIN — generated by scripts/probe_fi.py, do not edit between the markers -->

## Routes probed — run 2026-09-24

Every row below is a real request made by `scripts/probe_fi.py` on the Mac. `e` after a variable's value count means the API can eliminate it (leave it out and get the total); `T` marks the time variable. A ✗ row is kept, not deleted: knowing that a route is dead is the point of a probe.


## StatFin PxWeb

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [PxWebApi v2? pxdata.stat.fi/PxWeb/api/v2/](https://pxdata.stat.fi/PxWeb/api/v2/) | 404 | 1.34 | 0 | HTTP 404 — not live, v1 only |
| [PxWebApi v2? pxdata.stat.fi/PxWeb/api/v2-beta/](https://pxdata.stat.fi/PxWeb/api/v2-beta/) | 404 | 1.26 | 0 | HTTP 404 — not live, v1 only |
| [PxWebApi v2? statfin.stat.fi/api/v2/](https://statfin.stat.fi/api/v2/) | 404 | 1.26 | 0 | HTTP 404 — not live, v1 only |
| [db StatFin/vaerak](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/) | 200 | 1.25 | 4,614 | 32 tables · 11ra, 11rb, 11rc, 11rd, 11re, 11rf, 11rg, 11rh, 11rk, 11rl, 11rm, 11rp |
| [db StatFin/tjt](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tjt/) | 200 | 1.31 | 4,239 | 25 tables · 118w, 11py, 11wh, 11x3, 122s, 128c, 128j, 12ci, 12eb, 12ew, 12g4, 12g9 |
| [db StatFin/tyonv](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tyonv/) | 200 | 1.25 | 13,297 | 72 tables · 12r5, 12t8, 12t9, 12ta, 12tb, 12tc, 12td, 12te, 12tf, 12tg, 12th, 12ti |
| [db StatFin/muutl](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/muutl/) | 200 | 1.24 | 2,951 | 19 tables · 119z, 11a1, 11a2, 11a3, 11a4, 11a5, 11a6, 11a7, 11a8, 11a9, 11aa, 11ab |
| [db StatFin/vaenn](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaenn/) | 200 | 1.25 | 1,090 | 7 tables · 128t, 139e, 14wx, 14wy, 14wz, 14x1, 14x2 |
| [db StatFin/rpk](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/rpk/) | 200 | 1.25 | 10,132 | 52 tables · 11yy, 13ex, 13f1, 13f3, 13f4, 13f7, 13fr, 13g1, 13ga, 13gj, 13gw, 13h4 |
| [db StatFin/asku](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asku/) | 200 | 1.29 | 733 | 4 tables · 15fd, 157s, 15fh, 15fi |
| [db StatFin/raku](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/) | 200 | 1.25 | 1,047 | 7 tables · 156f, 156g, 156h, 156i, 15er, 15f6, 15f7 |
| [db StatFin/ashi](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/) | 200 | 1.25 | 3,784 | 19 tables · 12dd, 12de, 12dg, 12fv, 12fw, 13mq, 13mt, 13mu, 13mw, 13mv, 13mx, 13mz |
| [db StatFin/asvu](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/) | 200 | 1.25 | 345 | 2 tables · 15fa, 15fc |
| [db StatFin/ras](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ras/) | 400 | 1.25 | 0 | HTTP 400 — database does not exist (discontinued? check StatFin_Passiivi) |
| [db StatFin/asas](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asas/) | 400 | 1.3 | 0 | HTTP 400 — database does not exist (discontinued? check StatFin_Passiivi) |
| [db StatFin/rakke](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/rakke/) | 400 | 1.25 | 0 | HTTP 400 — database does not exist (discontinued? check StatFin_Passiivi) |
| [db StatFin/astuki](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/astuki/) | 400 | 1.25 | 0 | HTTP 400 — database does not exist (discontinued? check StatFin_Passiivi) |
| [db StatFin_Passiivi/asvu](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/) | 200 | 1.25 | 1,272 | 7 tables · statfinpas_asvu_pxt_11x4_2025q4, statfinpas_asvu_pxt_11x5_2025, statfinpas_asvu_pxt_12d4_2025q4, statfinpas_asvu_pxt_12ee_2025q4, statfinpas_asvu_pxt_13eb_2025q4, statfinpas_asvu_pxt_001_2018q4, statfinpas_asvu_pxt_901_2014q3 |
| [db StatFin_Passiivi/asas](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asas/) | 200 | 1.25 | 2,979 | 15 tables · statfinpas_asas_pxt_115a_2024, statfinpas_asas_pxt_115y_2024, statfinpas_asas_pxt_115z_2024, statfinpas_asas_pxt_116a_2024, statfinpas_asas_pxt_116b_2024, statfinpas_asas_pxt_116d_2024, statfinpas_asas_pxt_116e_2024, statfinpas_asas_pxt_116f_2024, statfinpas_asas_pxt_13ui_2024q4, statfinpas_asas_pxt_001_201700, statfinpas_asas_pxt_002_201700, statfinpas_asas_pxt_003_201700 |
| [db StatFin_Passiivi/ras](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/ras/) | 200 | 1.29 | 1,827 | 12 tables · statfinpas_ras_pxt_12fy_202412, statfinpas_ras_pxt_12fz_202412, statfinpas_ras_pxt_13m4_202411, statfinpas_ras_pxt_13m5_202411, statfinpas_ras_pxt_118r_2020m01, statfinpas_ras_pxt_118t_2020m01, statfinpas_ras_pxt_001_201806, statfinpas_ras_pxt_002_201806, statfinpas_ras_pxt_901_201412_en, statfinpas_ras_pxt_902_201412, statfinpas_ras_pxt_903_2014q4_en, statfinpas_ras_pxt_904_2014q4_en |
| [population by age, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/11re.px) | 200 | 1.25 | 8,280 | 1972–2025 · alue_23_20260101[309e] ikaryhma_10_20180101[102e] sukupuoli_9_20180101[3e] timeperiod_y[54T] contentscode[1] |
| [population key figures, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/11ra.px) | 200 | 1.33 | 18,039 | 1990–2025 · alue_23_20260101[568e] contentscode[43] timeperiod_y[36T] |
| [population by language, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/11rm.px) | 200 | 1.28 | 9,820 | 1990–2025 · alue_23_20260101[309e] kieli_15_20180102[169e] sukupuoli_9_20180101[3e] timeperiod_y[36T] contentscode[1] |
| [household-dwelling units, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asku/15fh.px) | 200 | 1.25 | 7,259 | 2005–2025 · alue_23_20260101[309e] talotyyppi_4_20210101[5e] timeperiod_y[21T] asuntokuntakoko_3_20190101[5e] huoneluku_2_20190101[9e] contentscode[2] |
| [dwelling floor area per unit / person](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asku/15fd.px) | 200 | 1.25 | 7,568 | 2005–2025 · alue_23_20260101[328e] timeperiod_y[21T] contentscode[10] |
| [income of household-dwelling units](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tjt/118w.px) | 200 | 1.25 | 12,289 | 1995–2024 · contentscode[39] timeperiod_y[30T] alue_23_20250101[420e] |
| [median income of inhabitants](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tjt/14ww.px) | 200 | 1.31 | 12,247 | 1995–2024 · alue_23_20250101[420] contentscode[26] timeperiod_y[30T] |
| [unemployment rate, kunta, monthly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/tyonv/12tf.px) | 200 | 1.25 | 13,903 | 2009M01–2026M08 · Alue[421e] timeperiod_m[212T] contentscode[3] |
| [migration, kunta, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/muutl/11ae.px) | 200 | 1.25 | 7,525 | 1990–2025 · timeperiod_y[36T] alue_23_20260101[309e] contentscode[21] |
| [migration, kunta, monthly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/muutl/12w7.px) | 200 | 1.33 | 15,662 | 1990M01–2025M12 · alue_23_20260101[309e] contentscode[21] timeperiod_m[432T] |
| [population projection 2024](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaenn/14wx.px) | 200 | 1.25 | 7,895 | 2024–2045 · alue_23_20240101[310e] timeperiod_y[22T] sukupuoli_9_20180101[3e] ikaryhma_10_20180101[102e] contentscode[1] |
| [offences, kunta, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/rpk/13ex.px) | 200 | 1.25 | 21,928 | 1980–2025 · timeperiod_y[46T] alue_23_20230101[311e] rikokset_74_20211209[209e] contentscode[14] |
| [offences, kunta, monthly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/rpk/13it.px) | 200 | 1.25 | 24,254 | 2009M01–2026M06 · timeperiod_m[210T] alue_23_20230101[311e] rikokset_74_20211209[209] contentscode[1] |
| [old dwelling prices, postal, quarterly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mt.px) | 200 | 1.35 | 71,906 | 2009Q1–2026Q1 · timeperiod_q[69T] postinumeroalue_4_20220101[1724] talotyyppi_6_20131021[4] contentscode[2] |
| [old dwelling prices, postal, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mu.px) | 200 | 1.27 | 70,895 | 2009–2025 · timeperiod_y[17T] postinumeroalue_4_20220101[1724] talotyyppi_6_20131021[4] contentscode[2] |
| [old dwelling prices, kunta, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mx.px) | 200 | 1.31 | 6,176 | 2006–2025 · timeperiod_y[20T] kunta_1_20150101[301] talotyyppi_5_20111209[3e] contentscode[3] |
| [old dwelling prices, quarterly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mv.px) | 200 | 1.27 | 4,181 | 2006Q1–2026Q1 · timeperiod_q[81T] alue_43_20220407[87] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] contentscode[3] |
| [price index old dwellings 2025=100](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/15is.px) | 200 | 1.25 | 3,678 | 2025Q1–2026Q2 · alue_43_20260625[87e] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] timeperiod_q[6T] contentscode[8] |
| [price index old dwellings, long chain](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/15it.px) | 200 | 1.25 | 6,744 | 1988Q1–2026Q2 · alue_43_20260625[87e] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] timeperiod_q[154T] contentscode[14] |
| [price index old dwellings 2020=100](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mq.px) | 200 | 1.25 | 2,978 | 2020–2025 · timeperiod_y[6T] alue_43_20220407[87] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] contentscode[7] |
| [new dwelling prices by sub-area](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/12dg.px) | 200 | 37.46 | 1,920 | 2015–2025 · alue_3_20181009[27] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] timeperiod_y[11T] contentscode[2] |
| [new dwelling prices by plot ownership](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/12dd.px) | 200 | 1.25 | 2,203 | 2015Q1–2026Q1 · alue_3_20181009[15] vuokratontti_1_20191126[3e] talotyyppi_5_20111209[3e] huoneluku_1_20111212[4e] timeperiod_q[45T] contentscode[2] |
| [price index new dwellings 2025=100](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/15iw.px) | 200 | 1.24 | 1,159 | 2025Q1–2026Q2 · alue_43_20260625[11e] timeperiod_q[6T] contentscode[4] |
| [rents incl. ARA, index + EUR/m2](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/15fa.px) | 200 | 1.25 | 3,152 | 2025Q1–2026Q2 · rahoitus_2_20260101[3] huoneluku_5_20260101[4] alue_44_20260101[85] timeperiod_q[6T] contentscode[7] |
| [free-market rents by postal code](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/13eb.px) | 400 | 1.25 | 0 | HTTP 400 — table not in this database |
| [free-market rents by postal code (archive)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_13eb_2025q4.px) | 200 | 1.33 | 26,564 | 2015Q1–2025Q4 · Vuosineljännes[44T] Postinumero[580] Huoneluku[3] Tiedot[2] |
| [rents (archive, long history)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_11x4_2025q4.px) | 200 | 1.25 | 3,582 | 2015Q1–2025Q4 · Vuosineljännes[44T] Alue[84] Huoneluku[4e] Rahoitusmuoto[3e] Tiedot[8] |
| [building and dwelling production](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/156f.px) | 200 | 1.24 | 10,194 | 1995M01–2026M07 · rakennusvaihe_1_20250101[3] alue_23_20260101[20] timeperiod_m[379T] rakennus_6_20180101[24e] contentscode[8] |
| [dwelling stock incl. unoccupied, kunta](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/15f6.px) | 200 | 1.25 | 7,119 | 2025–2025 · alue_23_20260101[309e] talotyyppi_4_20210101[5e] rak_valm_v_10_20210101[12e] asunnon_kaytolo_3_20190101[3e] timeperiod_y[1T] contentscode[1] |
| [dwelling stock by tenure (archive)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asas/statfinpas_asas_pxt_115y_2024.px) | 200 | 1.25 | 7,295 | 2005–2024 · Alue[309e] Hallintaperuste[7e] Talotyyppi[5e] Huoneita[6e] Vuosi[20T] Tiedot[2] |
| [rent distributions, sub-areas of large cities](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/15fc.px) | 200 | 1.28 | 1,693 | 2025Q1–2026Q2 · huoneluku_5_20260101[3] alue_44_20260101[49] timeperiod_q[6T] contentscode[4] |
| [building stock by use and year](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/15er.px) | 200 | 1.25 | 7,842 | 2025–2025 · alue_23_20260101[309e] rakennus_6_20180101[18e] timeperiod_y[1T] rak_valm_v_10_20210101[12e] polttoaineet_12_20260101[8e] contentscode[2] |
| [new production, yearly](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/raku/15f7.px) | 200 | 1.24 | 2,364 | 2005–2025 · alue_23_20260101[20e] rakennus_6_20180101[18e] polttoaineet_12_20260101[8e] timeperiod_y[21T] contentscode[2] |
| [household-dwelling units by tenure?](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asku/15fi.px) | 200 | 1.33 | 7,346 | 2005–2025 · alue_23_20260101[309e] talotyyppi_4_20210101[5e] timeperiod_y[21T] asuntokuntakoko_3_20190101[5e] sukupuoli_15_20190101[3e] ikaryhma_27_20220101[4e] contentscode[1] |
| [dwelling production (archive, kunta, monthly)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/ras/statfinpas_ras_pxt_12fy_202412.px) | 200 | 1.3 | 9,604 | 1995M01–2024M12 · Rakennusvaihe[3] Alue[20e] Kuukausi[360T] Käyttötarkoitus[24e] Tiedot[8] |

## Geometry (WFS)

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [Paavo capabilities](https://geo.stat.fi/geoserver/postialue/wfs?service=WFS&request=GetCapabilities&version=1.0.0) | 200 | 1.32 | 33,632 | 40 layers |
| [Paavo pno_tilasto layers](https://geo.stat.fi/geoserver/postialue/wfs) | 200 | 0.0 | 0 | 12 vintages, latest postialue:pno_tilasto_2026 |
| [Paavo sample postialue:pno_tilasto_2026](https://geo.stat.fi/geoserver/postialue/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=postialue%3Apno_tilasto_2026&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.24 | 8,550 | 3018 features · 113 props · id, postinumeroalue, nimi, namn, euref_x, euref_y, pinta_ala, vuosi, kunta, he_vakiy, he_naiset, he_miehet, he_kika, he_0_2 |
| [tilastointialueet capabilities](https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS&request=GetCapabilities&version=1.0.0) | 200 | 1.24 | 100,954 | 228 layers |
| [kunta1000k_* layers](https://geo.stat.fi/geoserver/tilastointialueet/wfs) | 200 | 0.0 | 0 | 14 vintages, latest tilastointialueet:kunta1000k_2026 |
| [sample tilastointialueet:kunta1000k_2026](https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=tilastointialueet%3Akunta1000k_2026&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.24 | 4,338 | 308 features · 6 props · id, kunta, vuosi, nimi, namn, name |
| [maakunta1000k_* layers](https://geo.stat.fi/geoserver/tilastointialueet/wfs) | 200 | 0.0 | 0 | 14 vintages, latest tilastointialueet:maakunta1000k_2026 |
| [sample tilastointialueet:maakunta1000k_2026](https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=tilastointialueet%3Amaakunta1000k_2026&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.37 | 1,074,839 | 19 features · 6 props · id, maakunta, vuosi, nimi, namn, name |
| [HSY capabilities](https://kartta.hsy.fi/geoserver/wfs?service=WFS&request=GetCapabilities&version=1.0.0) | 200 | 1.29 | 189,017 | 398 layers |
| [HSY seutukartta_pien_2021](https://kartta.hsy.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=taustakartat_ja_aluejaot%3Aseutukartta_pien_2021&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.4 | 5,304 | 824 features · 8 props · kokotun, kunta, suur, tila, pien, nimi, nimi_iso, mtryhm |
| [HSY seutukartta_tila_2021](https://kartta.hsy.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=taustakartat_ja_aluejaot%3Aseutukartta_tila_2021&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.3 | 5,977 | 336 features · 7 props · kokotun, kunta, suur, tila, nimi, nimi_iso, mtryhm |
| [HSY seutukartta_suur_2021](https://kartta.hsy.fi/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=taustakartat_ja_aluejaot%3Aseutukartta_suur_2021&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.29 | 10,824 | 67 features · 6 props · kokotun, kunta, suur, nimi, nimi_iso, mtryhm |
| [Helsinki avoindata capabilities](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&request=GetCapabilities&version=1.0.0) | 200 | 1.29 | 112,906 | 305 layers |
| [Helsinki Piirijako_osaalue](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3APiirijako_osaalue&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.28 | 10,548 | 148 features · 12 props · id, aluejako, kunta, tunnus, nimi_fi, nimi_se, yhtluontipvm, yhtmuokkauspvm, yhtdatanomistaja, kokotunnus, paivitetty_tietopalveluun, datanomistaja |
| [Helsinki Piirijako_peruspiiri](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3APiirijako_peruspiiri&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.27 | 31,701 | 34 features · 12 props · aluejako, datanomistaja, id, kokotunnus, kunta, nimi_fi, nimi_se, paivitetty_tietopalveluun, tunnus, yhtdatanomistaja, yhtluontipvm, yhtmuokkauspvm |
| [Helsinki Piirijako_suurpiiri](https://kartta.hel.fi/ws/geoserver/avoindata/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=avoindata%3APiirijako_suurpiiri&count=2&srsName=EPSG:4326&outputFormat=application/json) | 200 | 1.49 | 22,456 | 8 features · 12 props · id, aluejako, kunta, tunnus, nimi_fi, nimi_se, yhtluontipvm, yhtmuokkauspvm, yhtdatanomistaja, kokotunnus, paivitetty_tietopalveluun, datanomistaja |

## Aluesarjat

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [root https://stat.hel.fi/api/v1/en/Aluesarjat/](https://stat.hel.fi/api/v1/en/Aluesarjat/) | 200 | 1.42 | 82 | 2 folders · vrm, tul |
| [root https://stat.hel.fi/api/v1/fi/Aluesarjat/](https://stat.hel.fi/api/v1/fi/Aluesarjat/) | 200 | 1.24 | 337 | 7 folders · asu, his, kou, rak, tul, tyo, vrm |
| [root https://api.aluesarjat.fi/](https://api.aluesarjat.fi/) | 0 | 21.22 | 0 | no response (host does not resolve or does not answer) |

## File sources

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [Kelasto WebFOCUS report list](https://raportit.kela.fi/ibi_apps/WFServlet?IBIF_ex=NIT100AL) | 200 | 3.17 | 50,661 | HTTP 200 |
| [Kela open data landing](https://www.kela.fi/avoin-data) | 404 | 1.29 | 0 | HTTP 404 |
| [Verohallinto statistics landing](https://www.vero.fi/tietoa-verohallinnosta/tilastot/) | 200 | 1.35 | 108,563 | HTTP 200 |
| [avoindata.fi API — dataset search 'kiinteistövero'](https://www.avoindata.fi/data/api/3/action/package_search?q=kiinteist%C3%B6veroprosentit&rows=5) | 200 | 1.7 | 222 | 0 datasets ·  |
| [avoindata.fi API — dataset search 'kunnallisvero'](https://www.avoindata.fi/data/api/3/action/package_search?q=kunnallisveroprosentti&rows=5) | 200 | 1.61 | 222 | 0 datasets ·  |

## Reference values

| Name | HTTP | s | bytes | Result |
|---|---:|---:|---:|---|
| [Helsinki (091) population, latest year](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/vaerak/11re.px) | 200 | 1.39 | 3,036 | vaerak/11re → [694392] (persons, 31 Dec 2025) |
| [00100 price EUR/m2, blocks of flats 2-room, latest quarter](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mt.px) | 200 | 1.95 | 4,368 | ashi/13mt → [7167, 35] (EUR/m2 and number of sales) |
| [00100 rent EUR/m2/month, 1-room, latest quarter (archive)](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/statfinpas_asvu_pxt_13eb_2025q4.px) | 200 | 1.36 | 2,920 | StatFin_Passiivi:asvu/13eb_2025q4 → [746, 29.43] (observation count and EUR/m2/month) |
| [Helsinki (091) free-market rent, 1-room, live table](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/15fa.px) | 200 | 1.27 | 3,665 | asvu/15fa → [26.73, 19543] (EUR/m2/month and observation count — the live replacement for 13eb, kunta level only) |
| [Helsinki (091) ARA rent, 1-room, live table](https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/asvu/15fa.px) | 200 | 1.27 | 3,671 | asvu/15fa → [18.48, 7587] (government-subsidised (ARA) rent, EUR/m2/month) |

**74 of 84 routes answered.**

<!-- PROBE:END -->
