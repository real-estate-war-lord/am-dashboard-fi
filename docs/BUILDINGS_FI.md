# Buildings, zoning and the population grid

## 1. The buildings layer — Ryhti

| | |
|---|---|
| Route | `https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/wfs`, `avoimet_rakennukset` |
| Nationally | **3 799 740 buildings**, 653 MB of CSV |
| Drawn | **250 785** — those with at least 2 dwellings |
| Licence | **CC BY 4.0** — Lähde: Ryhti-rakennustietojärjestelmä (Suomen ympäristökeskus) |

The register carries saunas, sheds and bell towers. A layer that drew all 3.8 million would be
a grey smear that said nothing about housing, so it is cut at **2 dwellings** using the
register's own `huoneistojen_lukumaara`, and the count left out is reported rather than lost.
One lazy file per kunta; the largest, Helsinki, is 1.9 MB with 23 935 buildings.

### What Ryhti publishes, and only that

| Shown | Register field |
|---|---|
| Completion year | `valmistumispaivamaara` |
| Dwellings | `huoneistojen_lukumaara` |
| Floor area per dwelling | `kerrosala / huoneistojen_lukumaara` |
| Storeys | `kerrosluku` |
| Recorded as not in use | `kaytossaolo = Tyhjillään` |

**Floor area per dwelling is a building average**, and `kerrosala` is *gross* floor area, so it
includes stairwells and common space. It is not comparable with Paavo's average dwelling size,
which is living area, and the indicator says so.

### What it does not publish

- **Tenure.** Nothing says whether a dwelling is rented or owned. The Danish layer's "Rented
  dwellings" indicator has no Finnish equivalent, so it is not offered — and neither is the
  rent filter that went with it.
- **Per-dwelling area or room counts.** Only the building's total, so a "small dwellings under
  50 m²" share cannot be built either.
- **A finer use class than seven codes.** `avoin_rakennusluokitus` separates a detached house
  from a block of flats and stops there; `07 Julkinen rakennus` covers a school, a health
  centre and a concert hall alike.

### Two area indicators

Both are plain shares of published fields, counted **in dwellings**:

| Indicator | Definition |
|---|---|
| `dw_pre1980` | dwellings in buildings completed before 1980, over dwellings in buildings whose completion year is published |
| `bld_m2_per_dwelling` | published `kerrosala` over published dwellings, summed over the area |

A building whose completion year the register does not publish is left out of **both** the
numerator and the denominator, rather than counted as new.

## 2. Energy certificates — not built

ARA's energy-certificate register is reachable only through Suomi.fi Palveluväylä (X-Road) as a
**single-building lookup**. Its own catalogue entry states the service is *maksullinen* and
requires a **tietolupa** granted by ARA, a separate agreement, a connection fee and an annual
fee. `avoindata.fi` returns **0 datasets** for "energiatodistus", and
`energiatodistusrekisteri.fi/tilastot` is a JavaScript application with no bulk export.

**There is no energy-class share in this dashboard**, and there is no way to build one without
paying for access. The spec asked for it; this paragraph is the answer.

## 3. Zoning — an overlay, but no indicator

The **Zoning overlay** draws Suomen ympäristökeskus's Ryhti index of **detailed plans in
force** (`pub_valid_ld_plan_ix_gs`) live from its own WMS, the same way the flood overlay does.

There is **no `planned_floor_area_1000` indicator**, and the spec's condition is the reason:
*"only if the floor area is published"*. It is not, anywhere:

| Asked | Answer |
|---|---|
| Ryhti `pub_prep_ld_plan_ix_gs` (detailed plans in preparation) | **0 features nationally** |
| Ryhti `pub_prep_lm_plan_ix_gs` (master plans in preparation) | **0 features nationally** |
| Ryhti valid-plan index | carries status and geometry, **no floor-area attribute** |
| Helsinki `avoindata:Kaavayksikot` | 40 081 units, 62.0 million k-m² of `rakennusoikeus` — but **every one is `Voimassa`**, i.e. already in force |
| Helsinki `Kaavahakemisto_alue_kaava_vireilla` | 78 plan areas in preparation, and **no floor-area field at all** |

So Finland publishes building rights that already exist, and publishes no floor area for
anything in preparation. An indicator called "planned floor area" built from plans already in
force would be a different quantity wearing the name of the one the spec asked for, and it is
not built. The overlay ships; the indicator does not.

## 4. The 1 km population grid

An optional overlay, drawn live from Tilastokeskus's own WMS:
`https://geo.stat.fi/geoserver/vaestoruutu/wms`, layer **`vaestoruutu:vaki2025_1km`** —
**96 904 populated cells**, 2025, CC BY 4.0. Cells below the publisher's disclosure threshold
carry `-1` in the data; the overlay is the publisher's own rendering, not a recolouring of it.

## 5. How to rebuild

    python3 -m pip install -r requirements-services.txt
    make buildings     # scripts/fetch_buildings.py && scripts/build_micro.py

The fetch is resumable and asserts every kunta's row count against the server's own
`resultType=hits`. `data/processed/micro/` is committed, so `make build` needs neither shapely
nor a network.
