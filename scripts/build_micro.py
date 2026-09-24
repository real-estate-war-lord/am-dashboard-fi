#!/usr/bin/env python3
"""Ryhti's building register → data/processed/micro/ (phase 15).

3 799 740 buildings in 653 MB of CSV become one small lazy file per kunta, plus two area
indicators that are **plain counts and shares of published fields** and nothing more.

**Only buildings with dwellings.** The register carries saunas, sheds and bell towers; a
"buildings" layer that drew all 3.8 million would be a grey smear and would say nothing about
housing. The filter is the register's own field, `huoneistojen_lukumaara >= MIN_DWELLINGS`, and
the count that was filtered out is reported rather than quietly lost.

**What Ryhti does not publish**, and what is therefore not here:

  · **tenure** — nothing says whether a dwelling is rented or owned. The Danish layer's
    "Rented dwellings" indicator has no Finnish equivalent and is not shown;
  · **per-dwelling floor area or room counts** — only the building's total `kerrosala`, so
    "small dwellings under 50 m²" cannot be built either. Mean floor area *per dwelling* is
    `kerrosala / huoneistojen_lukumaara`, which is arithmetic on two published fields, and is
    labelled as what it is: a building average, not a dwelling measurement;
  · **a finer use class than seven codes** — `avoin_rakennusluokitus` separates a detached
    house from a block of flats and stops there (see scripts/build_services.py).

**ARA's energy certificates are not here either.** The register is reachable only through
Suomi.fi Palveluväylä (X-Road) as a single-building lookup; its own catalogue page states the
service is *maksullinen* and needs a *tietolupa* from ARA plus a separate agreement, a
connection fee and an annual fee, and `avoindata.fi` has **0 datasets** for "energiatodistus".
There is no energy-class share in this dashboard and there is no way to build one without
paying for access. Logged here, not worked around.

Needs shapely, for placing each building in its postal area and osa-alue.

    python3 scripts/build_micro.py
    python3 scripts/build_micro.py --only 091
"""
import argparse
import collections
import csv
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ryhti_bld"
GEO = ROOT / "data" / "geo"
OUT = ROOT / "data" / "processed" / "micro"
MAX_BYTES = 3_000_000

LICENCE = "CC BY 4.0 — Lähde: Ryhti-rakennustietojärjestelmä (Suomen ympäristökeskus)"
VERIFY = ("https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1"
          "/collections/avoimet_rakennukset/items?limit=10&f=application/json")
MIN_DWELLINGS = 2           # the same floor the Danish layer used, and for the same reason
OLD_BEFORE = 1980           # the cut for the "built before" share; stated in the indicator

# The register's seven use codes, mapped onto the four the UI already draws.
MTYPE = {"Pientalo": 1, "Kerrostalo": 3, "Vapaa-ajan asuinrakennus": 1,
         "Toimisto-, tuotanto-, yhdyskuntatekniikan tai muut rakennukset": 4,
         "Julkinen rakennus": 4, "Talousrakennus": 4, "Saunarakennus": 4}
VACANT = "Tyhjillään"       # the register's own word for a building not in use


def inum(v):
    s = (v or "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def point(s):
    if not s or not s.startswith("POINT"):
        return None
    try:
        lon, lat = s[s.index("(") + 1:s.index(")")].split()
        return float(lat), float(lon)
    except (ValueError, IndexError):
        return None


def load_areas():
    from shapely.geometry import shape
    from shapely.strtree import STRtree
    per = collections.defaultdict(list)
    for level, key, fname in (("postinumero", "nr", "postinumerot.geojson"),
                              ("osa_alue", "code", "osa_alueet.geojson")):
        p = GEO / fname
        if not p.exists():
            continue
        for f in json.loads(p.read_text(encoding="utf-8"))["features"]:
            kunta = str(f["properties"].get("kunta") or "")
            per[kunta].append((level, str(f["properties"][key]),
                               shape(f["geometry"]).buffer(0)))
    return {k: (v, STRtree([g for _, _, g in v])) for k, v in per.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    try:
        from shapely.geometry import Point
    except ImportError:
        print("shapely is needed here: python3 -m pip install -r requirements-services.txt",
              file=sys.stderr)
        return 1
    if not RAW.exists():
        print(f"no {RAW} — run scripts/fetch_buildings.py first", file=sys.stderr)
        return 1

    areas = load_areas()
    names = {f["properties"]["kunta"]: f["properties"]["name"]
             for f in json.loads((GEO / "kunnat.geojson").read_text(encoding="utf-8"))["features"]}
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()

    codes = args.only or sorted(names)
    index, per_area = {}, collections.defaultdict(lambda: collections.Counter())
    tot_read, tot_kept, biggest = 0, 0, (0, "")
    for code in codes:
        src = RAW / f"{code}.csv"
        if not src.exists():
            continue
        rows, read, no_point = [], 0, 0
        area_list, tree = areas.get(code, ([], None))
        with src.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                read += 1
                dw = inum(r.get("huoneistojen_lukumaara")) or 0
                if dw < MIN_DWELLINGS:
                    continue
                pt = point(r.get("sijaintikeskipisteen_geometria"))
                if pt is None:
                    no_point += 1
                    continue
                lat, lon = pt
                year = inum((r.get("valmistumispaivamaara") or "")[:4])
                ka = inum(r.get("kerrosala"))
                use = (r.get("paaasiallinen_kayttotarkoitus") or "").strip()
                vacant = (r.get("kaytossaolo") or "").strip() == VACANT
                # mean floor area PER DWELLING: arithmetic on two published fields, and it is a
                # building average, never a measurement of any one dwelling
                per_dw = round(ka / dw) if (ka and dw) else None
                # the row shape the page already reads (scripts/build_dashboard.py copies these
                # files to dist/micro/): [lat, lon, dwellings, -, vacant%, Ø m², year, floors,
                # type, …, register date, address, id]
                rows.append([round(lat, 6), round(lon, 6), dw, None,
                             100 if vacant else 0, per_dw, year,
                             inum(r.get("kerrosluku")), MTYPE.get(use, 4),
                             0, 0, 0, 0, None,
                             (r.get("valmistumispaivamaara") or "")[:4],
                             "", (r.get("pysyva_rakennustunnus") or "").strip()])
                # the area shares, counted in dwellings because that is what the share is about
                keys = [("kunta", code)]
                if tree is not None:
                    p = Point(lon, lat)
                    seen = set()
                    for i in tree.query(p):
                        level, key, poly = area_list[i]
                        if level in seen or not poly.contains(p):
                            continue
                        seen.add(level)
                        keys.append((level, key))
                for k in keys:
                    per_area[k]["dw"] += dw
                    if year is not None and year < OLD_BEFORE:
                        per_area[k]["dw_old"] += dw
                    if year is not None:
                        per_area[k]["dw_year_known"] += dw
                    if ka:
                        per_area[k]["ka"] += ka
                        per_area[k]["dw_ka"] += dw
        if not rows:
            continue
        # `meta` is the shape the page reads (d.meta.n, d.meta.min_dwellings, d.meta.cols);
        # the top-level copies are for anything reading the file on its own.
        meta_row = {"n": len(rows), "min_dwellings": MIN_DWELLINGS,
                    "built": dt.date.today().isoformat(),
                    "source": "Ryhti — avoimet_rakennukset", "licence": LICENCE,
                    "cols": ["lat", "lon", "dwellings", "unused", "not_in_use_pct",
                             "m2_per_dwelling", "year", "floors", "type", "r1", "r2", "r3", "r4",
                             "unused2", "completed", "address", "pysyva_rakennustunnus"]}
        payload = {"kunta": code, "name": names.get(code, ""), "n": len(rows),
                   "min_dwellings": MIN_DWELLINGS, "built": dt.date.today().isoformat(),
                   "source": "Ryhti — avoimet_rakennukset", "licence": LICENCE,
                   "meta": meta_row, "b": rows}
        dest = OUT / f"{code}.json"
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        dest.write_text(text, encoding="utf-8")
        n = len(text.encode())
        if n > biggest[0]:
            biggest = (n, code)
        if n > MAX_BYTES:
            print(f"  ! {code} is {n:,} B, over the {MAX_BYTES:,} B ceiling", file=sys.stderr)
        index[code] = {"file": f"micro/{code}.json", "n": len(rows),
                       "min_dwellings": MIN_DWELLINGS}
        tot_read += read
        tot_kept += len(rows)
        print(f"  · {code} {names.get(code, ''):<22} {read:>7,} buildings → "
              f"{len(rows):>6,} with ≥ {MIN_DWELLINGS} dwellings · {n:>9,} B")

    # the two area indicators, as plain shares of published fields
    ind = {}
    for (level, key), c in per_area.items():
        row = {}
        if c["dw_year_known"]:
            row["dw_pre1980"] = round(c["dw_old"] / c["dw_year_known"] * 100, 2)
        if c["dw_ka"]:
            row["bld_m2_per_dwelling"] = round(c["ka"] / c["dw_ka"], 1)
        if row:
            row["_dwellings"] = c["dw"]
            ind.setdefault(level, {})[key] = row

    meta = {
        "built": dt.date.today().isoformat(),
        "source": "Ryhti-rakennustietojärjestelmä — avoimet_rakennukset",
        "licence": LICENCE, "verify_at_source": VERIFY,
        "min_dwellings": MIN_DWELLINGS, "old_before": OLD_BEFORE,
        "buildings_read": tot_read, "buildings_kept": tot_kept,
        "municipalities": index,
        "indicators": ind,
        "not_published": {
            "tenure": "Ryhti publishes nothing about whether a dwelling is rented or owned.",
            "dwelling_area": ("Only the building's total kerrosala. Floor area per dwelling is "
                              "kerrosala / huoneistojen_lukumaara — a building average, not a "
                              "measurement of any one dwelling — and room counts do not exist, "
                              "so a 'small dwellings' share cannot be built."),
            "energy_certificates": ("ARA's register is a paid X-Road service needing a tietolupa; "
                                    "avoindata.fi has 0 datasets for 'energiatodistus'. No "
                                    "energy-class share exists in this dashboard."),
        },
    }
    (OUT / "index.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")),
                                    encoding="utf-8")
    print(f"\n{tot_read:,} buildings read · {tot_kept:,} kept (≥ {MIN_DWELLINGS} dwellings) "
          f"in {len(index)} kunnat · largest file {biggest[0]:,} B ({biggest[1]})")
    print(f"indicators: {len(ind.get('kunta', {}))} kunnat · "
          f"{len(ind.get('postinumero', {}))} postal areas · {len(ind.get('osa_alue', {}))} osa-alueet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
