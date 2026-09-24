#!/usr/bin/env python3
"""The osa-alue layer: Helsinki, Espoo, Vantaa and Kauniainen, from Aluesarjat.

    python3 scripts/build_osa.py [--force] [--quiet]

Fetches what it needs into data/raw/aluesarjat/ (git-ignored, stamped) and writes:

    data/processed/osa_alue.json        inlined in the page: identity, latest values, and
                                        the indicator registry for this level
    data/processed/area/<kunta>.json    amended in place with that kunta's osa-alue rings
                                        and their history, beside its postal areas

It runs after scripts/build_makro.py, which writes the per-kunta files it amends.

**Licence.** Aluesarjat is open for **both non-commercial and commercial use**; the only
condition is attribution naming the database and the underlying source, worded so as not to
imply endorsement. That is recorded in the layer's own meta, shown in the UI's Sources view,
and written in docs/SOURCES.md. (v1.0 wrongly recorded it as non-commercial-only.)

**The join.** Aluesarjat's ten-digit area code is exactly Helsingin kaupunki's `kokotunnus`,
which data/geo/osa_alueet.geojson stores verbatim, so areas join on it directly — 296 of
306. The ten that do not are Kauniainen's nine sub-areas, which Aluesarjat publishes as one
municipality, and Helsinki's territorial-sea polygon, which has no residents. They keep
their geometry and show the kunta's figure, marked °, exactly as a postal area does.

**Definitions that differ from the kunta level** get their own key, never the kunta key with
a different meaning behind it: `young_19_34` (Aluesarjat's band is 19–34, not 20–34),
`rented_dw` (rented *dwellings*, where the kunta figure is *households* in rented dwellings)
and `higher_ed_15` (of everyone 15 or over, where the kunta figure is of everyone 18 or
over). Keys that do mean the same thing — growth, foreign, single, flats, vacant — are
shared, so the area page can put an osa-alue beside its kunta honestly.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import aluesarjat as A  # noqa: E402
import geo_common as G  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "aluesarjat"
PROC = ROOT / "data" / "processed"
OUT = PROC / "osa_alue.json"
QUIET = False
YEARS = 12                     # years of history carried in the lazy per-kunta file
HELSINKI = "091"
FORECAST_VINTAGE = "PER26"     # the city's current base projection

HUE = {"demo": [10, 88, 70], "stock": [40, 84, 128], "jobs": [166, 88, 24],
       "size": [90, 60, 150], "warn": [166, 42, 22]}
NC = ("Aluesarjat is open for both non-commercial and commercial use. Attribution must name "
      "the database and the underlying source — \"Helsingin seudun aluesarjat -tilastokanta ja "
      "Tilastokeskus\" — and must not imply the publisher endorses the use.")

# table path -> the selection to pull. Every dimension is named: a variable left out of an
# Aluesarjat query is eliminated to its total, silently.
PULLS = {
    "pop":      ("vrm/vaerak/alu_vaerak_004r", {"Ikä": ["ALL"], "Vuosi": ["*"], "Tiedot": ["lkm"]}),
    "lang":     ("vrm/vaerak/alu_vaerak_004p", {"Äidinkieli": ["ALL", "3"], "Ikä": ["ALL", "19-34"],
                                                "Vuosi": ["*"], "Tiedot": ["lkm"]}),
    "hh":       ("asu/asas/alu_asas_005d", {"Asuntokunnan koko": ["ALL", "1"], "Vuosi": ["*"],
                                            "Tiedot": ["lkm_askun"]}),
    "dwell":    ("asu/askan/alu_askan_005q", {"Käytössäolotilanne": ["ALL", "2"],
                                              "Talotyyppi": ["ALL", "3"],
                                              "Hallintaperuste": ["ALL", "3_4", "5"],
                                              "Vuosi": ["*"], "Tiedot": ["aslkm"]}),
    "edu":      ("kou/alu_kou_005n", {"Koulutusaste": ["ALL", "5-6", "7-8"], "Ikä": ["ALL"],
                                      "Sukupuoli": ["ALL"], "Vuosi": ["*"], "Tiedot": ["lkm_15v-"]}),
    "forecast": ("vrm/vaenn/alu_vaenn_006c", {"Laatimisvuosi ja vaihtoehto": ["TOT", FORECAST_VINTAGE],
                                              "Äidinkieli": ["ALL"], "Ikä": ["ALL"],
                                              "Vuosi": ["*"], "Tiedot": ["lkm"]}),
}


def say(*a):
    if not QUIET:
        print(*a)


def fetch_all(force):
    """{name: (dataset, stamp)} — pulled once, cached on disk."""
    got = {}
    for name, (path, sel) in PULLS.items():
        dest = RAW / f"{name}.json"
        if dest.exists() and not force:
            got[name] = (json.loads(dest.read_text(encoding="utf-8")), A.stamp(dest))
            say(f"  · cached {name} ({dest.stat().st_size:,} B)")
            continue
        m = A.meta(path)
        sel = dict(sel)
        sel[A.area_var(m)] = ["*"]
        ds = A.pull(path, sel, dest, note=f"osa-alue layer: {name}")
        got[name] = (ds, A.stamp(dest))
        say(f"  · fetched {name} · {path} · {len(ds.get('value') or []):,} cells "
            f"· {dest.stat().st_size:,} B")
    return got


def index(ds, keep):
    """{area code: {year: {cell key: value}}}, the cell key built from `keep` in order."""
    ids = ds["id"]
    avar = next(v for v in ids if v in ("Alue", "Osa-alue"))
    tvar = next(v for v in ids if v == "Vuosi")
    out = {}
    for r in A.rows(ds):
        key = "|".join(str(r[k]) for k in keep if k in r)
        out.setdefault(str(r[avar]), {}).setdefault(str(r[tvar]), {})[key] = r["value"]
    return out


def share(num, den):
    if num is None or den in (None, 0):
        return None
    return num / den * 100.0


def series(rows, fn):
    """{year: value} for one area, dropping the years the publisher did not publish."""
    out = {}
    for year in sorted(rows):
        v = fn(rows[year])
        if v is not None:
            out[year] = round(v, 3)
    return out


def yoy(pop):
    ys = sorted(pop)
    return {ys[i]: round((pop[ys[i]] / pop[ys[i - 1]] - 1) * 100, 3)
            for i in range(1, len(ys)) if pop[ys[i - 1]]}


def load_climate():
    """The osa-alue block of data/processed/climate.json, if scripts/build_climate.py has run.

    Only the Helsinki-region kunnat have an osa-alue layer, and they are exactly the coastal
    ones where a sea-flood figure means something, so this is the level where it earns its
    place. Stdlib only: the raster work happened in build_climate.py.
    """
    p = PROC / "climate.json"
    if not p.exists():
        say("  · no data/processed/climate.json — osa-alue climate skipped (run `make climate`)")
        return {}, {}
    d = json.loads(p.read_text(encoding="utf-8"))
    block = (d.get("flood") or {}).get("osa_alue") or {}
    say(f"  · climate: {len(block)} osa-alueet carry a flood figure")
    return block, (d.get("meta") or {}).get("flood") or {}


def climate_indicators(meta):
    """The same four zones and the coverage row as the kunta level, worded for this level."""
    src = meta.get("source", "Suomen ympäristökeskus (Syke)")
    yr = meta.get("year", "")
    res = meta.get("res_m", 25)
    common = (f"Measured from Suomen ympäristökeskus's own flood-hazard polygons at {res:.0f} m per "
              f"pixel, counted inside this osa-alue's land. The zones are published as millions of "
              f"raster-derived fragments and cannot be fetched as vectors at a usable size — the "
              f"method is in docs/CLIMATE_FI.md.")
    warn = ("SYKE flood-maps designated areas, not the whole country. An osa-alue with no figure is "
            "NOT MAPPED, which is not the same as no flood hazard. Screening indicators for "
            "comparing areas, not a property-level risk assessment.")

    def ci(key, label, short, desc, direction="lower_better", hue="warn"):
        return {"key": key, "label": label, "short": short, "unit": "% of land", "fmt": "pct1",
                "group": "Climate", "direction": direction, "level": "osa_alue", "hue": HUE[hue],
                "desc": desc, "note": common, "warn": warn,
                "source": src + (f" — edition {yr}" if yr else "")}
    return [
        ci("flood_sea_100", "Sea flood hazard zone — 1/100a", "Sea flood 1/100a",
           "Share of the osa-alue's land inside the sea flood hazard zone for a 1-in-100-year "
           "flood. A return period is a probability, not a date."),
        ci("flood_sea_1000", "Sea flood hazard zone — 1/1000a", "Sea flood 1/1000a",
           "Share of the osa-alue's land inside the sea flood hazard zone for a 1-in-1000-year "
           "flood — the rarer extreme, which always contains the 1/100a zone."),
        ci("flood_river_100", "Watercourse flood hazard zone — 1/100a", "River flood 1/100a",
           "Share of the osa-alue's land inside the watercourse flood hazard zone for a "
           "1-in-100-year flood: rivers and lakes, not the sea."),
        ci("flood_river_1000", "Watercourse flood hazard zone — 1/1000a", "River flood 1/1000a",
           "Share of the osa-alue's land inside the watercourse flood hazard zone for a "
           "1-in-1000-year flood."),
        ci("flood_mapped", "Flood-mapped share of the area", "Flood-mapped",
           "Share of the osa-alue's land that SYKE has flood-mapped at all. A coverage figure, "
           "not a hazard figure: where it is 0 nobody has assessed the area, and where it is "
           "high a 0 above is a real 0.", direction="neutral", hue="size"),
    ]


def indicators():
    def ind(key, label, short, unit, fmt, group, direction, desc, hue, note):
        return {"key": key, "label": label, "short": short, "unit": unit, "fmt": fmt,
                "group": group, "direction": direction, "level": "osa_alue", "hue": HUE[hue],
                "desc": desc, "note": note + " " + NC, "warn": "",
                "source": "Aluesarjat (Helsingin kaupunki / Uudenmaan liitto)"}
    A_ = "Counted for the osa-alue itself, not inherited from the kunta."
    return [
        ind("growth", "Population growth", "Growth", "% / yr", "signpct1", "Demographics",
            "higher_better", "Change in the number of inhabitants of the osa-alue over one "
            "year, %.", "demo", A_),
        ind("young_19_34", "Share aged 19–34", "19–34", "%", "pct1", "Demographics", "neutral",
            "Inhabitants aged 19–34 as a share of all inhabitants. Aluesarjat's published age "
            "band is 19–34, one year wider at the bottom than the 20–34 band used at kunta "
            "level, so the two are shown as different indicators rather than as one.",
            "demo", A_),
        ind("foreign", "Foreign-language speakers", "Foreign lang.", "%", "pct1", "Demographics",
            "neutral", "Inhabitants whose mother tongue is neither Finnish, Sami nor Swedish, "
            "as a share of all inhabitants — the same definition as the kunta figure.",
            "demo", A_),
        ind("single", "One-person households", "1-person", "%", "pct1", "Demographics", "neutral",
            "One-person household-dwelling units as a share of all households.", "demo", A_),
        ind("rented_dw", "Rented dwellings", "Rented", "%", "pct1", "Housing stock", "neutral",
            "Dwellings held on a rental basis — government-subsidised (arava or korkotuki) plus "
            "other rented — as a share of all dwellings. The kunta-level figure counts "
            "*households living in* a rented dwelling, which is a different thing, so this has "
            "its own name.", "stock", A_),
        ind("flats", "Dwellings in blocks of flats", "Kerrostalo", "%", "pct1", "Housing stock",
            "neutral", "Dwellings in blocks of flats as a share of all dwellings — the same "
            "definition as the kunta figure.", "stock", A_),
        ind("vacant", "Dwellings with no permanent residents", "Unoccupied", "%", "pct1",
            "Housing stock", "neutral", "Dwellings not in permanent occupation as a share of "
            "all dwellings — the same definition as the kunta figure.", "warn", A_),
        ind("higher_ed_15", "Tertiary education (15+)", "Tertiary", "%", "pct1", "Income & jobs",
            "higher_better", "People with a tertiary degree as a share of everyone aged 15 or "
            "over. The kunta-level figure is of everyone aged 18 or over, so the two are shown "
            "as different indicators.", "jobs", A_),
    ]


def forecast(ds, codes):
    """{area: {year: population}} for the city's own projection, and the observed series."""
    ids = ds["id"]
    avar = next(v for v in ids if v in ("Alue", "Osa-alue"))
    vvar = "Laatimisvuosi ja vaihtoehto"
    obs, proj = {}, {}
    for r in A.rows(ds):
        a, y, v = str(r[avar]), str(r["Vuosi"]), r["value"]
        if v is None:
            continue
        (obs if r[vvar] == "TOT" else proj).setdefault(a, {})[y] = v
    return obs, proj


def main():
    global QUIET
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    QUIET = args.quiet

    geo = ROOT / "data" / "geo" / "osa_alueet.geojson"
    if not geo.exists():
        sys.exit("✗ data/geo/osa_alueet.geojson missing — run `make geo` first")
    feats = json.loads(geo.read_text(encoding="utf-8"))["features"]
    say(f"osa-alue layer · {len(feats)} areas")

    say("Aluesarjat pulls")
    got = fetch_all(args.force)

    pop = index(got["pop"][0], [])
    lang = index(got["lang"][0], ["Äidinkieli", "Ikä"])
    hh = index(got["hh"][0], ["Asuntokunnan koko"])
    dw = index(got["dwell"][0], ["Käytössäolotilanne", "Talotyyppi", "Hallintaperuste"])
    edu = index(got["edu"][0], ["Koulutusaste"])
    obs_fc, proj_fc = forecast(got["forecast"][0], None)

    inds = indicators()
    climate, climate_meta = load_climate()
    if climate:
        inds.extend(climate_indicators(climate_meta))
    areas, matched, unmatched = [], 0, []
    for f in feats:
        p = f["properties"]
        code10 = p.get("kokotun") or ""
        rings = G.rings_of(f["geometry"])
        row = {"code": p["code"], "name": p["name"], "muni": p["kunta"],
               "peruspiiri": p.get("peruspiiri", ""), "peruspiiri_code": p.get("peruspiiri_code", ""),
               "bb": [round(x, 4) for x in p["bb"]], "kokotun": code10,
               "source": p.get("source", "")}
        hist = {}
        if code10 in pop:
            matched += 1
            popser = {y: v for y, v in ((y, c.get("")) for y, c in pop[code10].items()) if v is not None}
            if popser:
                row["pop"] = popser[max(popser)]
                row["pop_year"] = max(popser)
                hist["growth"] = yoy(popser)
            if code10 in lang:
                hist["foreign"] = series(lang[code10], lambda c: share(c.get("3|ALL"), c.get("ALL|ALL")))
                hist["young_19_34"] = series(lang[code10],
                                             lambda c: share(c.get("ALL|19-34"), c.get("ALL|ALL")))
            if code10 in hh:
                hist["single"] = series(hh[code10], lambda c: share(c.get("1"), c.get("ALL")))
            if code10 in dw:
                hist["rented_dw"] = series(dw[code10], lambda c: share(
                    None if c.get("ALL|ALL|3_4") is None and c.get("ALL|ALL|5") is None
                    else (c.get("ALL|ALL|3_4") or 0) + (c.get("ALL|ALL|5") or 0), c.get("ALL|ALL|ALL")))
                hist["flats"] = series(dw[code10], lambda c: share(c.get("ALL|3|ALL"), c.get("ALL|ALL|ALL")))
                hist["vacant"] = series(dw[code10], lambda c: share(c.get("2|ALL|ALL"), c.get("ALL|ALL|ALL")))
            if code10 in edu:
                hist["higher_ed_15"] = series(edu[code10], lambda c: share(
                    None if c.get("5-6") is None and c.get("7-8") is None
                    else (c.get("5-6") or 0) + (c.get("7-8") or 0), c.get("ALL")))
        else:
            unmatched.append(p["code"])
        hist = {k: v for k, v in hist.items() if v}
        for k, s in hist.items():
            row[k] = s[max(s)]
        # the city's own forecast, for the areas it covers
        if code10 in proj_fc:
            row["fc_pop"] = {y: v for y, v in sorted(proj_fc[code10].items())}
            a0, a1 = "2026", "2040"
            p0, p1 = proj_fc[code10].get(a0), proj_fc[code10].get(a1)
            if p0 and p1 is not None:
                row["fc_growth"] = round((p1 / p0 - 1) * 100, 2)
        if code10 in obs_fc:
            row["pop_hist"] = {y: v for y, v in sorted(obs_fc[code10].items())[-30:]}
        # Climate: not a series. A flood-hazard map has an edition, not an annual observation,
        # so the figure is attached flat and the source line carries the edition year.
        cl = climate.get(row["code"])
        if cl:
            for k, v in cl.items():
                if k != "land_km2" and v is not None:
                    row[k] = v
        row["_hist"] = {k: {y: v for y, v in list(sorted(s.items()))[-YEARS:]} for k, s in hist.items()}
        row["_rings"] = rings
        areas.append(row)
    say(f"  · {matched} areas matched Aluesarjat by kokotunnus, {len(unmatched)} without "
        f"(they show the kunta value, marked °): {', '.join(unmatched[:10])}")

    fc_ind = {"key": "fc_growth", "label": "Projected population change 2026→2040",
              "short": "Outlook 2040", "unit": "%", "fmt": "signpct1", "group": "Outlook",
              "direction": "neutral", "level": "osa_alue", "hue": HUE["size"],
              "desc": "Helsingin kaupunki's own population projection for the area, from 2026 to "
                      "2040. This is the city's forecast, not Tilastokeskus's: the two are "
                      "different runs with different assumptions and are never combined.",
              "note": "Helsinki only — Espoo and Vantaa publish their own area projections on "
                      "different vintages and to different end years, which are not shown here "
                      "rather than being stretched to match. " + NC,
              "warn": "Helsingin kaupunki's own projection, base alternative " + FORECAST_VINTAGE
                      + ". A different run from Tilastokeskus's municipal projection.",
              "source": "Aluesarjat alu_vaenn_006c (Helsingin väestöennuste, " + FORECAST_VINTAGE + ")",
              "proj": {"publisher": "Helsingin kaupunki", "vintage": FORECAST_VINTAGE,
                       "table": "alu_vaenn_006c", "from": "2026", "to": "2040",
                       "relative_label": "vs Helsinki",
                       "caveat": "The city's own projection reflects its housing plans as well as "
                                 "births, deaths and migration. It is a scenario, not a promise."}}
    if any("fc_growth" in a for a in areas):
        inds.append(fc_ind)

    stamps = [s for _ds, s in got.values() if s]
    years = sorted({y for a in areas for s in a["_hist"].values() for y in s})
    meta = {
        "built": dt.date.today().isoformat(), "years": years,
        "latest_year": years[-1] if years else "",
        "level": "osa_alue", "kunnat": sorted({a["muni"] for a in areas}),
        # The terms ask for the database AND the underlying source, both named (docs/SOURCES.md §3)
        "attribution": "Lähde: Helsingin seudun aluesarjat -tilastokanta ja Tilastokeskus · "
                       "boundaries Helsingin kaupunki ja HSY (CC BY 4.0)",
        "licence": A.LICENCE, "licence_url": A.LICENCE_URL,
        "note": "Osa-alue figures come from Aluesarjat, which is open for both non-commercial "
                "and commercial use against a named attribution. Where an indicator's definition "
                "differs from the kunta level it carries its own name rather than the kunta's.",
        "sources": [{"key": s.get("table"), "label": s.get("label") or s.get("table"),
                     "url": s.get("verify_at_source"), "tables": s.get("table"),
                     "asof": (s.get("updated") or "")[:10], "fetched": s.get("fetched"),
                     "licence": s.get("licence")} for s in stamps],
        "lazy": "rings and history ride in area/<kunta>.json",
    }
    # the city's own projection for Helsinki as a whole, so the kunta strip can put it beside
    # Tilastokeskus's and state the gap instead of averaging the two away (§4)
    city = {}
    city_code = HELSINKI + "0000000"
    if city_code in proj_fc:
        p0, p1 = proj_fc[city_code].get("2026"), proj_fc[city_code].get("2040")
        if p0 and p1 is not None:
            city = {"kunta": HELSINKI, "publisher": "Helsingin kaupunki",
                    "vintage": FORECAST_VINTAGE, "table": "alu_vaenn_006c",
                    "from": "2026", "to": "2040", "pop_from": p0, "pop_to": p1,
                    "fc_growth": round((p1 / p0 - 1) * 100, 2)}
            say(f"  · Helsinki city projection {FORECAST_VINTAGE}: {p0:,} → {p1:,} "
                f"= {city['fc_growth']:+.2f} %")
    light = []
    per_kunta = {}
    for a in areas:
        rings, hist = a.pop("_rings"), a.pop("_hist")
        per_kunta.setdefault(a["muni"], []).append(
            {"code": a["code"], "rings": rings, "hist": hist,
             "pop_hist": a.pop("pop_hist", None), "fc_pop": a.pop("fc_pop", None)})
        light.append(a)
    PROC.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"meta": meta, "indicators": inds, "areas": light,
                               "city_forecast": city or None},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    say(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} B · {len(light)} areas · "
        f"{len(inds)} indicators)")

    adir = PROC / "area"
    amended = 0
    for kunta, rows_ in sorted(per_kunta.items()):
        p = adir / f"{kunta}.json"
        doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"kunta": kunta, "areas": []}
        doc["osa"] = [{k: v for k, v in r.items() if v} for r in rows_]
        p.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        amended += 1
        say(f"  · {p.relative_to(ROOT)} +{len(rows_)} osa-alueet ({p.stat().st_size:,} B)")
    say(f"amended {amended} per-kunta files")


if __name__ == "__main__":
    main()
