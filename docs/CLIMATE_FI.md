# Climate risk — what is measured, and what is not

**Screening indicators for comparing areas, not a property-level risk assessment.** That
sentence is on the overlay legend, on the Analysis sheet and on every indicator's caveat, and
it is meant literally: nothing here can tell you whether a particular building floods.

Two sources survived the probe. Two did not, and saying which is half the point of this file.

| | Source | Level | Verdict |
|---|---|---|---|
| Flood hazard | Suomen ympäristökeskus (Syke) — tulvavaaravyöhykkeet | kunta · postinumero · osa-alue | **built** |
| Radon | Säteilyturvakeskus (STUK) — radon pientaloissa 2023 | kunta · postinumero | **built** |
| Sea-level scenarios | — | — | **not built** — Finland publishes none as data |
| Stormwater flooding | — | — | **not built** — neither HSY nor Helsinki publishes one |

---

## 1. Flood hazard

### The route, and why it is a raster

SYKE publishes the zones through
`https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/` — **`paikkatiedot`, plural**; the
singular host answers HTTP 200 with an IIS default page and its `/geoserver/` is a 404.

Return periods are **separate layers**, not an attribute to filter:

    inspire_nz:NZ.Tulvavaaravyohykkeet_{Meritulva|Vesistotulva}_1_{2|5|10|20|50|100|250|1000}a

The dashboard carries **1/100a and 1/1000a**, for both sea (meritulva) and watercourse
(vesistötulva).

They cannot be fetched as vectors. The probe measured:

| | Features, nationally |
|---|---:|
| `Vesistotulva_1_100a` | 3 412 672 |
| `Meritulva_1_100a` | 4 014 394 |
| `Meritulva_1_1000a` | 4 759 149 |

A Helsinki-sized bbox alone returns **8.9 MB** and **12.7 MB** of GeoJSON and hits GeoServer's
10 000-feature cap. SYKE's own bulk downloads are **5.59 GB** (meri) and **5.65 GB** (vesistö),
measured by HEAD. The four layers would be 15–20 GB of polygon fragments — which is what they
are: fragments of a depth raster exported as polygons.

So the measurement is taken from the publisher's own rendering of those same polygons, at a
stated ground resolution of **25 m**, and the overlay on the map is SYKE's live WMS. Nothing
is redrawn, reinterpreted or simplified by us.

### The mistake this file exists to record

The first implementation counted **any non-transparent pixel** in the default style. That put
**a quarter of Kallio — a hill — inside a 1/100a sea flood zone**, and Helsinki as a whole at
10.5 %.

The default style is a *cartographic* style and cannot be read as data. Its palest fill,
`#D1FFFF`, is the class **`vesistö`** — the water body. The Gulf of Finland is of course below
sea level, so the whole sea renders as "flooded", and every coastal polygon picked it up.

The publisher's own `GetLegendGraphic` gives the rule list and the WFS gives the values in
`syvsuojluokka`:

| Value | Fill | What it is |
|---|---|---|
| `0 - 0.5 m` | `#7ECCE6` | flooded land, under 0.5 m |
| `0.5 - 1 m` | `#5498CC` | flooded land |
| `1 - 2 m` | `#2B66B3` | flooded land |
| `2 - 3 m` | `#003399` | flooded land |
| `yli 3 m` | `#002673` | flooded land |
| `tulvan peittämä. syvyystieto puuttuu` | `#C19CD6` | flooded, depth not published |
| `tulvasuojeltu …` (two values) | hatched | flooded but protected by structures |
| **`kuiva maa`** | *not drawn* | **dry land inside the mapped area** |
| **`vesistö`** | `#D1FFFF` | **the water body — not flooded land** |

So the mask is built from a **flat SLD plus an explicit CQL list of the publisher's own class
names**, with `format_options=antialias:none` so every pixel is 0 or 255:

- **flood mask** — the eight flood classes above, `kuiva maa` and `vesistö` excluded;
- **assessed-land mask** — the same list *plus* `kuiva maa`, which is SYKE's own statement of
  the land it has looked at.

Colour matching is not used anywhere, hatched classes come out solid instead of striped, and
there are no anti-aliased in-between pixels to adjudicate.

After the fix, Helsinki reads **5.3 %** at 1/100a and **6.6 %** at 1/1000a, the most exposed
postal areas are Kalasatama–Kyläsaari (22.5 %) and Toukola–Kumpula–Vanhakaupunki (23.0 %) —
the Vantaanjoki delta and the low waterfront — and Kallio is not in the top ten.

### The arithmetic

For every kunta whose land meets a mapped extent (**209 of 308**):

1. a grid is laid over `kunta ∩ mapped extent` at 25 m/px, tiled at ≤ 1024 px;
2. the flood mask and the assessed-land mask are fetched for it;
3. this dashboard's own area rings — kunta, postal areas, osa-alueet — are rasterised onto
   **the identical grid**, holes punched, and intersected with the kunta's own land polygon;
4. `flood_<hazard>_<period>` = flood pixels in the area ÷ the area's land pixels;
   `flood_mapped` = assessed-land pixels in the area ÷ the same denominator.

Numerator and denominator come out of the same rasterisation, so the rounding cancels.

Each polygon is rasterised **on its own** and OR-ed in. Drawing them together lets one
polygon's hole erase another's fill — not a hypothetical: SYKE's two Helsinki sea-flood
extents cover the same water, and drawing them together erased the mapped extent over central
Helsinki, so every postal area there read "not mapped" while carrying a flood share.

### "Not mapped" is not "no risk"

SYKE flood-maps designated areas. **An area with no flood figure has not been assessed**, and
the dashboard never writes a 0 there — where `flood_mapped` is 0, the zone rows are blank.
Where `flood_mapped` is high, a 0 in the zone rows is a real 0.

### What a return period is

`1/100a` is a **1-in-100 chance in any given year**, not a flood due in a particular year. The
1/1000a zone always contains the 1/100a zone. The horizon is in the label everywhere the
figure appears, because "1/100a" read as "in 100 years" is the single most common misreading
of a flood map.

### Known limits

- **25 m.** A strip of flooded land narrower than about 25 m is at the edge of what this
  resolution can see. It is a screening figure.
- **The edition is the publisher's.** `muutospvm` on the mapped-extent features gives the
  newest revision year, and that is the period the figure is labelled with — not the day the
  file was built.
- **Flood-protected land counts as inside the zone.** It is inside the hazard zone and
  protected by structures; treating it as outside would assume the structures hold.

---

## 2. Radon

STUK publishes two spreadsheets — [by kunta](https://stuk.fi/pientalojen-radonpitoisuudet-kunnittain) and [by postal code](https://stuk.fi/pientalojen-radonpitoisuudet-postinumeroalueittain) — from measurements in
**detached houses (pientalot)**:

| Column | Carried as |
|---|---|
| Mitattuja pientaloasuntoja | `radon_n` (in the payload, not shown as an indicator) |
| Keskiarvo Bq/m³ | `radon_mean` |
| Mediaani Bq/m³ | `radon_median` |
| 200 / 300 / 1000 Bq/m³ ylitykset % | `radon_over200` / `radon_over300` / `radon_over1000` |

Three become indicators: mean, median and the share over 300 Bq/m³, the action level for an
existing dwelling.

- **A blank in STUK's table is a suppressed figure, not a zero**, and stays blank here.
  Around 660 of the 1 567 postal areas have too few measurements for the exceedance shares.
- **Measurements are voluntary**, so the sample is not a random sample of dwellings.
- **Detached houses only.** The figure describes the ground and the low-rise stock on it, not
  a flat in a block.
- Finland's own mean is **228 Bq/m³** and its median **125 Bq/m³**, from 152 298 measurements.
- **Pertunmaa** appears in STUK's 2023 file and not in kuntajako 2026: it merged. Its figure
  is **left out, not folded into the kunta it merged with**, and it is listed in
  `climate.json` under `meta.radon.unmatched`.

---

## 3. Sea-level scenarios — not built

`avoindata.fi` returns **0 datasets** for "merenpinnan nousu". The only quantified national
figures are prose in an Ilmatieteen laitos article — RCP2.6/SSP1-2.6 and RCP4.5/SSP2-4.5
ranges **per sea basin**, not per location, with no machine-readable form.

One machine-readable thing exists: Helsinki republishes an FMI-derived layer of site-specific
year-2100 flood heights, `avoindata:FMI_Paikkakohtainen_tulvakorkeus_vuonna_2100_piste` —
**453 points, Helsinki only, one value per point, no scenario selector.** That cannot be made
into an area indicator that is comparable across Finland, and 307 of 308 kunnat would read
"Not mapped".

**Decision: no sea-level indicator.** An indicator that is blank almost everywhere is not an
indicator, and inventing coastal values from a basin-level prose range would be a model of our
own — which this dashboard does not do.

## 4. Stormwater (hulevesi) flooding — not built

Asked of both publishers, and the answer was written down:

- **HSY's WFS** lists **397** layers. One matches "hulevesi": `vesihuolto:vh_hulevesiviemaroity_alue`,
  the area served by stormwater sewers — network coverage, not flooding. **Zero** match "tulva".
- **Helsinki's WFS** lists **304** layers, **zero** matching "hulevesi".

**Decision: not built.** Every area would read "Not mapped", which is a column of nothing.

---

## 5. Where it appears

| Where | What |
|---|---|
| Group **Climate** | 8 indicators: 4 flood zones, flood-mapped coverage, 3 radon rows |
| Overlay **Climate risk** | SYKE's live WMS, one return period at a time, with SYKE's own depth legend |
| Analysis sheet | its own **Climate** card, with the "not mapped" sentence and the return-period sentence |
| osa-alue level | the five flood rows, built by `scripts/build_osa.py` from the same `climate.json` |

## 6. How to rebuild

    python3 -m pip install -r requirements-geo.txt
    make climate      # scripts/fetch_flood.py && scripts/build_climate.py

`fetch_flood.py` is resumable and skips tiles already on disk. `data/processed/climate.json`
is committed, so `make build` and the Pages deploy never need numpy, pillow or a network.
