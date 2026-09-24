# Services, public buildings and infrastructure — what is on the map, and from whom

Three layers, five publishers, and one rule that runs through all of them: **every point says
which publisher it came from**, because in Finland no single source covers the country.

| Layer | Source | Coverage | Licence |
|---|---|---|---|
| Services — groceries, food & drink, pharmacies | OpenStreetMap (Geofabrik `finland-latest.osm.pbf`) | national | ODbL 1.0 |
| Services — public-transport stops | **HSL** static GTFS in the HSL region, **OpenStreetMap** everywhere else | national | CC BY 4.0 / ODbL 1.0 |
| Public buildings | **Palvelukartta** in the four municipalities it covers, **OpenStreetMap** elsewhere | national | CC BY 4.0 / ODbL 1.0 |
| Infrastructure projects | **Väylävirasto** `hanketiedot:*` + a curated list of the big named projects | national | CC BY 4.0 |

## 1. There is no keyless national GTFS

Digitransit's aggregated national routing data answers **HTTP 401** without a registered
subscription key. Fintraffic's FINAP is keyless but is a *catalogue* of ~292 separate operator
feeds of uneven quality, not one file. HSL's own `https://dev.hsl.fi/gtfs/hsl.zip` is keyless,
current and is the operator's own list.

**Decision.** Stops are HSL's inside the kunnat HSL serves and OpenStreetMap's everywhere else.
The two are never mixed in one kunta: **18 478 OpenStreetMap stops inside the HSL region are
dropped**, not double-counted, and the popup on every stop names its publisher.

HSL publishes the **extended** GTFS route types (701 local bus, 109 suburban rail, 900 tram),
not only the basic five. The mapping to a mode family lives in `scripts/build_services.py`
beside its use; the raw codes are stored as published.

| Counted | |
|---|---|
| OpenStreetMap points extracted | 133 514 |
| Service points placed in a kunta | 113 372 |
| HSL stops | 8 364 |
| OSM stops dropped inside the HSL region | 18 478 |

## 2. Ryhti cannot classify a public building

The spec hoped to build the public-buildings categories from Ryhti's building-use field. It
cannot be done, and the publisher's own codelist is the evidence:
`avoin_rakennusluokitus` has **seven codes**, is titled *"Building use classified at a general
level"*, and `07 Julkinen rakennus` is one undivided bucket covering a school, a health centre
and a concert hall alike.

**Decision.** Public buildings come from Palvelukartta (a register, Helsinki / Espoo / Vantaa /
Kauniainen, 1 696 units) and OpenStreetMap (a map anyone can edit, 6 905 units elsewhere).
Every point says which. The two are **not equally complete**, and the legend says so.

Finland's public buildings also carry **no permit case and no floor area**. The Danish register
published both and the UI's density rule keyed on them, which here drew *nothing at all*. The
rule is now a plain zoom floor, and the existing/open-case toggle is not drawn where no cases
exist rather than offered as a filter that can only hide everything.

## 3. Infrastructure: the state's own list, plus the big named projects

**Väylävirasto publishes its own project records** — `hanketiedot:tiehankkeet` (311 features),
`:ratahankkeet` (166) and `:vesivaylahankkeet` (4) — with the agency's own schedule and the
agency's own **published alignment**. 481 features group into 269 distinct projects.

Two rules trim that to 169:

- A project that had **already finished** and that the agency **never gave a project page** is
  left out: 105 completed maintenance records — a bridge repainted, a culvert replaced. Both
  facts are the agency's own; nothing is hand-picked.
- `major` is true for every curated project and for every Väylävirasto project the agency
  itself gave a project page (**46** of its 267). **The growth signals count only those**,
  because a repaint is not a growth signal.

**The seven big named projects are curated by hand**, in `data/external/infra_fi.csv`, each row
carrying the page its figures were read from:

| Project | Opening | Budget | Alignment |
|---|---|---|---|
| Kruunusillat | 7 Nov 2026 | not published | not open data |
| Vantaan ratikka | autumn 2029 | €606 m (Vantaa's share €414 m) | Väylävirasto's |
| Espoon kaupunkirata | 2029 | €348.8 m | Väylävirasto's |
| Lentorata | mid-2030s at the earliest | **€2 078 m (MAKU 103.9, 2015=100) *and* €2.9 bn (VAT 0%)** | not open data |
| Länsirata / Turun tunnin juna | not published | **€3 bn, €3.8 bn, and a €3.4–4.0 bn range** | not open data |
| Itärata | by the end of the 2030s | €3 bn (planning €79 m) | not open data |
| Tampereen ratikka, phase 2 | early 2032, if state funding is confirmed | not published | not open data |

**Where a publisher gives more than one estimate, all of them are in the project's notes.**
Lentorata's owner publishes two and Länsirata's publishes three. None is averaged, and none is
silently preferred — the budget column carries the lowest published figure and the notes carry
the rest.

**No alignment is ever drawn by hand.** Five of the seven have no published alignment, so they
have no geometry, `map: false`, and a note saying why. They keep their Pipeline row and their
datasheet. The Danish build filtered the project list on `f.geometry`, which was harmless there
— every Danish project had one — and here would have silently dropped the five biggest projects
in the country.

## 4. Size

The alignments are **140 kB** and only the map overlay uses them, so they live in
`dist/infra.json` and are fetched the first time something wants to draw one. Every project's
*properties* stay in the page, because the Pipeline table, the nav count and the CSV export all
need them without a fetch.

## 5. How to rebuild

    python3 -m pip install -r requirements-services.txt
    make services      # scripts/fetch_services.py && scripts/build_services.py
    make infra         # scripts/build_infra.py

`data/processed/services/`, `data/processed/public/` and `data/geo/infra_projects.geojson` are
committed, so `make build` and the Pages deploy need neither the packages nor a network.
