# Verification — v1.1

**Run 2026-09-24** by `scripts/verify.py`, which re-queries the publisher, redoes the arithmetic from the returned cells, and compares the result with what `data/processed/makro.json` actually carries. It does **not** read the build's own cached pulls: if the build were taking the wrong cell, dividing by the wrong denominator or joining the wrong vintage, these checks would disagree and the cached pulls would not.

`88` checks · **88 agree**

Full export: `docs/verification/v1_1.csv` — 16,788 rows, 308 kunnat × 60 indicators, long format (level; code; name; parent; indicator; label; unit; value; period; inherited_from; source; tables).


## Kunnat — 5 × 4 indicators

| Area | Indicator | Source | Recomputed how | Recomputed | On the page | |
|---|---|---|---|---:|---:|:--:|
| Helsinki (091) | income_med | Paavo 12f8 hr_mtu 2024 | the published cell | 29 159 | 29 159 | ✓ |
| Helsinki (091) | renters | Paavo 12f8 2024 | te_vuok_as 194095 ÷ te_taly 359689 × 100 | 53.96 | 53.96 | ✓ |
| Helsinki (091) | unemp | Paavo 12f8 2024 | pt_tyott 44735 ÷ (pt_tyoll + pt_tyott) 370847 × 100 | 12.06 | 12.06 | ✓ |
| Helsinki (091) | flats | Paavo 12f8 2024 | ra_kt_as 345655 ÷ ra_asunn 398541 × 100 | 86.73 | 86.73 | ✓ |
| Tampere (837) | income_med | Paavo 12f8 hr_mtu 2024 | the published cell | 25 038 | 25 038 | ✓ |
| Tampere (837) | renters | Paavo 12f8 2024 | te_vuok_as 80927 ÷ te_taly 146347 × 100 | 55.30 | 55.30 | ✓ |
| Tampere (837) | unemp | Paavo 12f8 2024 | pt_tyott 17686 ÷ (pt_tyoll + pt_tyott) 135571 × 100 | 13.05 | 13.05 | ✓ |
| Tampere (837) | flats | Paavo 12f8 2024 | ra_kt_as 122430 ÷ ra_asunn 158593 × 100 | 77.20 | 77.20 | ✓ |
| Turku (853) | income_med | Paavo 12f8 hr_mtu 2024 | the published cell | 24 314 | 24 314 | ✓ |
| Turku (853) | renters | Paavo 12f8 2024 | te_vuok_as 64305 ÷ te_taly 116430 × 100 | 55.23 | 55.23 | ✓ |
| Turku (853) | unemp | Paavo 12f8 2024 | pt_tyott 14639 ÷ (pt_tyoll + pt_tyott) 105433 × 100 | 13.88 | 13.88 | ✓ |
| Turku (853) | flats | Paavo 12f8 2024 | ra_kt_as 98746 ÷ ra_asunn 130132 × 100 | 75.88 | 75.88 | ✓ |
| Oulu (564) | income_med | Paavo 12f8 hr_mtu 2024 | the published cell | 25 996 | 25 996 | ✓ |
| Oulu (564) | renters | Paavo 12f8 2024 | te_vuok_as 50157 ÷ te_taly 110889 × 100 | 45.23 | 45.23 | ✓ |
| Oulu (564) | unemp | Paavo 12f8 2024 | pt_tyott 14762 ÷ (pt_tyoll + pt_tyott) 109367 × 100 | 13.50 | 13.50 | ✓ |
| Oulu (564) | flats | Paavo 12f8 2024 | ra_kt_as 67789 ÷ ra_asunn 120808 × 100 | 56.11 | 56.11 | ✓ |
| Jyväskylä (179) | income_med | Paavo 12f8 hr_mtu 2024 | the published cell | 24 711 | 24 711 | ✓ |
| Jyväskylä (179) | renters | Paavo 12f8 2024 | te_vuok_as 41172 ÷ te_taly 81042 × 100 | 50.80 | 50.80 | ✓ |
| Jyväskylä (179) | unemp | Paavo 12f8 2024 | pt_tyott 11252 ÷ (pt_tyoll + pt_tyott) 74304 × 100 | 15.14 | 15.14 | ✓ |
| Jyväskylä (179) | flats | Paavo 12f8 2024 | ra_kt_as 57630 ÷ ra_asunn 89222 × 100 | 64.59 | 64.59 | ✓ |
| Helsinki (091) | radon_mean | STUK radontilasto_pientalot_kunta_ja_koko_suomi_2023.xlsx | column 'Keskiarvo Bq/m3' for Helsinki, read from the publisher's own file | 155.00 | 155.00 | ✓ |
| Tampere (837) | radon_mean | STUK radontilasto_pientalot_kunta_ja_koko_suomi_2023.xlsx | column 'Keskiarvo Bq/m3' for Tampere, read from the publisher's own file | 347.00 | 347.00 | ✓ |
| Turku (853) | radon_mean | STUK radontilasto_pientalot_kunta_ja_koko_suomi_2023.xlsx | column 'Keskiarvo Bq/m3' for Turku, read from the publisher's own file | 90.00 | 90.00 | ✓ |
| Oulu (564) | radon_mean | STUK radontilasto_pientalot_kunta_ja_koko_suomi_2023.xlsx | column 'Keskiarvo Bq/m3' for Oulu, read from the publisher's own file | 45.00 | 45.00 | ✓ |
| Jyväskylä (179) | radon_mean | STUK radontilasto_pientalot_kunta_ja_koko_suomi_2023.xlsx | column 'Keskiarvo Bq/m3' for Jyväskylä, read from the publisher's own file | 160.00 | 160.00 | ✓ |
| Helsinki (091) | flood_sea_100 | SYKE WMS tiles in data/raw/syke_flood/ | flood-class pixels ÷ land pixels at 25 m, recounted from the publisher's own tiles | 5.26 | 5.26 | ✓ |
| Espoo (049) | flood_sea_100 | SYKE WMS tiles in data/raw/syke_flood/ | flood-class pixels ÷ land pixels at 25 m, recounted from the publisher's own tiles | 3.02 | 3.02 | ✓ |
| Turku (853) | flood_sea_100 | SYKE WMS tiles in data/raw/syke_flood/ | flood-class pixels ÷ land pixels at 25 m, recounted from the publisher's own tiles | 5.37 | 5.37 | ✓ |
| Oulu (564) | flood_sea_100 | SYKE WMS tiles in data/raw/syke_flood/ | flood-class pixels ÷ land pixels at 25 m, recounted from the publisher's own tiles | 3.57 | 3.57 | ✓ |
| Helsinki (091) | dw_pre1980 | Ryhti avoimet_rakennukset, data/raw/ryhti_bld/ | dwellings in buildings completed before 1980 ÷ dwellings in buildings with a published year, buildings with ≥ 2 dwellings, recounted from the raw CSV | 55.40 | 55.40 | ✓ |
| Espoo (049) | dw_pre1980 | Ryhti avoimet_rakennukset, data/raw/ryhti_bld/ | dwellings in buildings completed before 1980 ÷ dwellings in buildings with a published year, buildings with ≥ 2 dwellings, recounted from the raw CSV | 26.50 | 26.50 | ✓ |
| Tampere (837) | dw_pre1980 | Ryhti avoimet_rakennukset, data/raw/ryhti_bld/ | dwellings in buildings completed before 1980 ÷ dwellings in buildings with a published year, buildings with ≥ 2 dwellings, recounted from the raw CSV | 41.48 | 41.48 | ✓ |
| Turku (853) | dw_pre1980 | Ryhti avoimet_rakennukset, data/raw/ryhti_bld/ | dwellings in buildings completed before 1980 ÷ dwellings in buildings with a published year, buildings with ≥ 2 dwellings, recounted from the raw CSV | 55.06 | 55.06 | ✓ |
| Oulu (564) | dw_pre1980 | Ryhti avoimet_rakennukset, data/raw/ryhti_bld/ | dwellings in buildings completed before 1980 ÷ dwellings in buildings with a published year, buildings with ≥ 2 dwellings, recounted from the raw CSV | 31.79 | 31.79 | ✓ |
| Helsinki (091) | services_points | data/processed/services/<kunta>.json | points counted in the file itself against the index's claim | 5 516.00 | 5 516.00 | ✓ |
| Espoo (049) | services_points | data/processed/services/<kunta>.json | points counted in the file itself against the index's claim | 2 455.00 | 2 455.00 | ✓ |
| Tampere (837) | services_points | data/processed/services/<kunta>.json | points counted in the file itself against the index's claim | 3 694.00 | 3 694.00 | ✓ |
| Turku (853) | services_points | data/processed/services/<kunta>.json | points counted in the file itself against the index's claim | 4 019.00 | 4 019.00 | ✓ |
| Oulu (564) | services_points | data/processed/services/<kunta>.json | points counted in the file itself against the index's claim | 2 389.00 | 2 389.00 | ✓ |

## Postal codes — 5 × price, sales, rent, income, unemployment

| Area | Indicator | Source | Recomputed how | Recomputed | On the page | |
|---|---|---|---|---:|---:|:--:|
| Helsinki keskusta – Etu-Töölö (00100) | price_m2 | ashi 13mu 2025 | Σ(price × sales) ÷ Σ(sales) over the three room-count classes = 7371×136 + 7254×152 + 7353×132 ÷ 420 | 7 323.00 | 7 323.00 | ✓ |
| Helsinki keskusta – Etu-Töölö (00100) | price_sales | ashi 13mu 2025 | Σ(sales) over the three room-count classes | 420.00 | 420 | ✓ |
| Helsinki keskusta – Etu-Töölö (00100) | rent_pno | asvu 13eb 2025Q4 (discontinued) | Σ(rent × observations) ÷ Σ(observations) = 1175 observations | 27.01 | 27.01 | ✓ |
| Helsinki keskusta – Etu-Töölö (00100) | income_med | Paavo 12f7 hr_mtu 2024 | the published cell | 34 408 | 34 408 | ✓ |
| Helsinki keskusta – Etu-Töölö (00100) | unemp | Paavo 12f7 2024 | pt_tyott 834 ÷ 10941 × 100 | 7.62 | 7.62 | ✓ |
| Sörnäinen (00500) | price_m2 | ashi 13mu 2025 | Σ(price × sales) ÷ Σ(sales) over the three room-count classes = 5302×166 + 5173×73 + 5032×19 ÷ 258 | 5 245.62 | 5 246.00 | ✓ |
| Sörnäinen (00500) | price_sales | ashi 13mu 2025 | Σ(sales) over the three room-count classes | 258.00 | 258 | ✓ |
| Sörnäinen (00500) | rent_pno | asvu 13eb 2025Q4 (discontinued) | Σ(rent × observations) ÷ Σ(observations) = 1672 observations | 25.91 | 25.91 | ✓ |
| Sörnäinen (00500) | income_med | Paavo 12f7 hr_mtu 2024 | the published cell | 25 961 | 25 961 | ✓ |
| Sörnäinen (00500) | unemp | Paavo 12f7 2024 | pt_tyott 1036 ÷ 8332 × 100 | 12.43 | 12.43 | ✓ |
| Tapiola (02100) | price_m2 | ashi 13mu 2025 | Σ(price × sales) ÷ Σ(sales) over the three room-count classes = 5702×34 + 5773×60 + 5647×112 ÷ 206 | 5 692.78 | 5 693.00 | ✓ |
| Tapiola (02100) | price_sales | ashi 13mu 2025 | Σ(sales) over the three room-count classes | 206.00 | 206 | ✓ |
| Tapiola (02100) | rent_pno | asvu 13eb 2025Q4 (discontinued) | Σ(rent × observations) ÷ Σ(observations) = 186 observations | 25.12 | 25.12 | ✓ |
| Tapiola (02100) | income_med | Paavo 12f7 hr_mtu 2024 | the published cell | 34 967 | 34 967 | ✓ |
| Tapiola (02100) | unemp | Paavo 12f7 2024 | pt_tyott 277 ÷ 3660 × 100 | 7.57 | 7.57 | ✓ |
| Tampere keskus (33100) | price_m2 | ashi 13mu 2025 | Σ(price × sales) ÷ Σ(sales) over the three room-count classes = 4256×97 + 3960×157 + 3811×119 ÷ 373 | 3 989.44 | 3 989.00 | ✓ |
| Tampere keskus (33100) | price_sales | ashi 13mu 2025 | Σ(sales) over the three room-count classes | 373.00 | 373 | ✓ |
| Tampere keskus (33100) | rent_pno | asvu 13eb 2025Q4 (discontinued) | Σ(rent × observations) ÷ Σ(observations) = 1144 observations | 17.90 | 17.90 | ✓ |
| Tampere keskus (33100) | income_med | Paavo 12f7 hr_mtu 2024 | the published cell | 25 290 | 25 290 | ✓ |
| Tampere keskus (33100) | unemp | Paavo 12f7 2024 | pt_tyott 1181 ÷ 10265 × 100 | 11.51 | 11.51 | ✓ |
| Turku keskus (20100) | price_m2 | ashi 13mu 2025 | Σ(price × sales) ÷ Σ(sales) over the three room-count classes = 3999×179 + 3376×203 + 3353×197 ÷ 579 | 3 560.78 | 3 561.00 | ✓ |
| Turku keskus (20100) | price_sales | ashi 13mu 2025 | Σ(sales) over the three room-count classes | 579.00 | 579 | ✓ |
| Turku keskus (20100) | rent_pno | asvu 13eb 2025Q4 (discontinued) | Σ(rent × observations) ÷ Σ(observations) = 3213 observations | 17.41 | 17.41 | ✓ |
| Turku keskus (20100) | income_med | Paavo 12f7 hr_mtu 2024 | the published cell | 24 798 | 24 798 | ✓ |
| Turku keskus (20100) | unemp | Paavo 12f7 2024 | pt_tyott 1879 ÷ 17817 × 100 | 10.55 | 10.55 | ✓ |

## Osa-alueet — 3 × 4 indicators

| Area | Indicator | Source | Recomputed how | Recomputed | On the page | |
|---|---|---|---|---:|---:|:--:|
| Kruununhaka (091010) | pop | Aluesarjat 004r 2025 | the published cell | 7 465 | 7 465 | ✓ |
| Kruununhaka (091010) | foreign | Aluesarjat 004p 2025 | Muu kieli 636 ÷ yhteensä 7465 × 100 | 8.52 | 8.52 | ✓ |
| Kruununhaka (091010) | young_19_34 | Aluesarjat 004p 2025 | 19–34 2072 ÷ yhteensä 7465 × 100 | 27.76 | 27.76 | ✓ |
| Kruununhaka (091010) | single | Aluesarjat 005d 2025 | 1 henkilö 1987 ÷ yhteensä 4111 × 100 | 48.33 | 48.33 | ✓ |
| Tapanila (091392) | pop | Aluesarjat 004r 2025 | the published cell | 6 769 | 6 769 | ✓ |
| Tapanila (091392) | foreign | Aluesarjat 004p 2025 | Muu kieli 1042 ÷ yhteensä 6769 × 100 | 15.39 | 15.39 | ✓ |
| Tapanila (091392) | young_19_34 | Aluesarjat 004p 2025 | 19–34 1182 ÷ yhteensä 6769 × 100 | 17.46 | 17.46 | ✓ |
| Tapanila (091392) | single | Aluesarjat 005d 2025 | 1 henkilö 1578 ÷ yhteensä 3386 × 100 | 46.60 | 46.60 | ✓ |
| Espoo, Suvela (049111) | pop | Aluesarjat 004r 2025 | the published cell | 6 894 | 6 894 | ✓ |
| Espoo, Suvela (049111) | foreign | Aluesarjat 004p 2025 | Muu kieli 2502 ÷ yhteensä 6894 × 100 | 36.29 | 36.29 | ✓ |
| Espoo, Suvela (049111) | young_19_34 | Aluesarjat 004p 2025 | 19–34 1892 ÷ yhteensä 6894 × 100 | 27.44 | 27.44 | ✓ |
| Espoo, Suvela (049111) | single | Aluesarjat 005d 2025 | 1 henkilö 1958 ÷ yhteensä 3713 × 100 | 52.73 | 52.73 | ✓ |

---

## What a ✓ means here

The figure on the page equals the figure recomputed from the publisher's own cells, to within rounding. It does **not** mean the publisher is right, that the definition is the one a reader assumes, or that the area's classification vintage matches the map's — those are `docs/GEO.md` and each indicator's own caveat.

