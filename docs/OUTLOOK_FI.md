# Outlook — how projections are handled

The Outlook group is the only part of this dashboard that is about the future, so it is the
part with the strictest rules. They are the Danish edition's rules, kept verbatim in
substance and re-pointed at the Finnish sources.

## §1 What is shown

| | Source | Level | Window | Vintage |
|---|---|---|---|---|
| Municipal projection | Tilastokeskus `vaenn/14wx` | kunta | 2026 → 2040 (table runs to 2045) | **Väestöennuste 2024**, published **2024-10-24** |
| City projection | Aluesarjat `alu_vaenn_006c` | Helsinki osa-alue | 2026 → 2040 | **PER26**, Helsingin kaupunki's base alternative |

Espoo (`alu_vaenn_010e`, to 2033) and Vantaa (`alu_vaenn_040o`, to 2035) publish their own
area projections on different vintages and to different end years. They are **not** shown,
because stretching them to a common window would mean inventing the years in between.

## §2 A projection is not a forecast

Every Outlook figure carries the caveat that it is a calculation of what the population
would be if observed trends in births, deaths and migration continued — the publisher's
scenario, not a prediction. The city's own projection additionally reflects Helsinki's
housing plans. Neither takes account of a new employer arriving or a plan being cancelled.

## §3 One vintage, not a series

An Outlook indicator is a single published vintage. It therefore has:

- no year selector — the control is replaced by the projection window ("Projection
  2026→2040 · Tilastokeskus Väestöennuste 2024");
- no history to scroll; the figure does not change until the publisher issues a new
  projection;
- a **dashed** line for every projected point in every chart, a vertical marker at the last
  observed year labelled "· today", and "— projected" in each projected point's own tooltip.
  A projected point must never read as an actual.

The publication date is read from the table's own `updated` field in the data response, not
from the table listing, which carries a later bulk re-stamp.

## §4 Two projections of the same city are never combined

Helsinki is the one place where both a national and a city projection exist. They are shown
**side by side with the gap between them stated**, and never averaged, blended or
reconciled:

> Outlook 2040 · **Tilastokeskus** +14,8 %
> Outlook 2040 · **Helsingin kaupunki** +16,9 %
> Two different projections of the same city, 2,16 pp apart — the city forecast is the
> higher. They are never combined: different runs, different assumptions.

The publisher of each figure is read from the data, never inferred from which view the
reader is in.

## §5 Arithmetic, and only arithmetic

Every Outlook number is a published cell or plain arithmetic on published cells:

| Indicator | Arithmetic |
|---|---|
| `fc_growth` | `pop[2040] / pop[2026] − 1` |
| `fc_abs` | `pop[2040] − pop[2026]` |
| `fc_growth_5y` | `pop[2031] / pop[2026] − 1` |
| `fc_pop_rate_5y` | `(pop[2031] − pop[2026]) ÷ 5 ÷ pop[2026] × 1000` |
| `fc_0_6`, `fc_7_15`, `fc_20_34`, `fc_80p` | the same ratio on a sum of the projection's own single-year age cells |
| `fc_20_34_rel` | the area's projected 20–34 share minus Finland's, **from the same projection** |

No curve is fitted, no rate is extrapolated, nothing is capped, and nothing is smoothed.

## §6 Persons are not dwellings

`fc_pop_rate_5y` is residents per 1 000 per year. It is never converted into a number of
dwellings, because that conversion needs an assumption about household size, and this layer
makes none. Where a dwelling figure is wanted it comes from a dwelling statistic.

## §7 Age bands follow Finnish practice

**0–6** (before school, the daycare cohort) and **7–15** (comprehensive school), not the
Danish 0–5 / 6–16. Plus 20–34 and 80+. Each band is a sum of the projection's own
single-year cells.
