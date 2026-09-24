#!/usr/bin/env python3
"""data/raw/{osm,gtfs,palvelukartta} → data/processed/{services,public}/ (phase 12).

Two layers out of three sources, each point carrying the name of the publisher it came from,
because one layer genuinely mixes them:

  **Services** — groceries, food and drink, pharmacies and public-transport stops. OSM
  everywhere; HSL's own GTFS for stops in the Helsinki region, where it is better than OSM and
  is the operator's own list. **An OSM stop in a kunta HSL publishes is dropped**, so the two
  never double-count; everywhere else the stop is OSM's and says so.

  **Public buildings** — education, daycare, health and culture. Palvelukartta in the four
  municipalities it covers, OSM elsewhere.

**Ryhti cannot classify a public building.** The spec hoped to use its building-use field. Its
open classification (`avoin_rakennusluokitus`) has exactly **seven** codes — the codelist is
called "Building use classified at a general level" — and `07 Julkinen rakennus` is one
undivided bucket covering a school, a health centre and a concert hall alike. It cannot drive
an education/daycare/health/culture filter, so it is not used here, and this paragraph is the
record of why.

Needs shapely for point-in-polygon at this scale (requirements-services.txt). The outputs are
committed, so `make build` needs neither it nor a network.
"""
import argparse
import collections
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
GEO = ROOT / "data" / "geo"
SRV_DIR = PROC / "services"
PUB_DIR = PROC / "public"

OSM_ATTRIB = "© OpenStreetMap contributors, ODbL 1.0"
HSL_ATTRIB = "HSL — static GTFS, CC BY 4.0"
PK_ATTRIB = "Helsingin kaupunki — Palvelukartta, CC BY 4.0"

# OSM category -> the dashboard's own category and sub-type. The sub-type keeps the mapper's
# own word wherever the UI has a name for it.
SRV_MAP = {
    "grocery": ("grocery", {"shop=supermarket": "supermarket", "shop=convenience": "convenience",
                            "shop=greengrocer": "convenience", "shop=grocery": "convenience",
                            "shop=general": "convenience"}),
    "food": ("food", {"amenity=restaurant": "restaurant", "amenity=cafe": "cafe",
                      "amenity=fast_food": "fast_food", "amenity=bar": "bar", "amenity=pub": "bar"}),
    "pharmacy": ("pharmacy", {"amenity=pharmacy": "pharmacy", "healthcare=pharmacy": "pharmacy"}),
}
# GTFS route types, basic and extended. HSL publishes 0, 1, 4, 109, 701, 702, 704 and 900.
# https://gtfs.org/documentation/schedule/reference/#routestxt plus the extended list.
def gtfs_mode(code):
    try:
        n = int(code)
    except (TypeError, ValueError):
        return None
    if n in (0,) or 900 <= n <= 906:
        return "light-rail"           # raitiovaunu
    if n in (1,) or 400 <= n <= 405:
        return "metro"
    if n in (2,) or 100 <= n <= 117:
        return "rail"                 # 109 = lähijuna / suburban railway
    if n in (3,) or 700 <= n <= 716 or n == 800:
        return "bus"
    if n in (4,) or 1000 <= n <= 1300:
        return "ferry"
    return None


OSM_STOP_MODE = {
    "railway=station": "rail", "railway=halt": "rail", "railway=tram_stop": "light-rail",
    "highway=bus_stop": "bus", "public_transport=station": "rail",
    "public_transport=stop_position": "bus",
}

PUB_MAP = {                            # OSM category -> the public-buildings category
    "school": "education", "kindergarten": "institutions",
    "health": "health", "culture": "culture",
}
PK_MAP = {                             # Palvelukartta service node -> the same
    "school": "education", "upper_secondary": "education", "kindergarten": "institutions",
    "health": "health", "library": "culture",
}


def load_kunnat():
    from shapely.geometry import shape
    from shapely.strtree import STRtree
    feats = json.loads((GEO / "kunnat.geojson").read_text(encoding="utf-8"))["features"]
    geoms, codes, names = [], [], {}
    for f in feats:
        geoms.append(shape(f["geometry"]).buffer(0))
        codes.append(f["properties"]["kunta"])
        names[f["properties"]["kunta"]] = f["properties"]["name"]
    return STRtree(geoms), geoms, codes, names


def locator(tree, geoms, codes):
    from shapely.geometry import Point

    def where(lat, lon):
        p = Point(lon, lat)
        for i in tree.query(p):
            if geoms[i].contains(p):
                return codes[i]
        return None
    return where


def read_jsonl(path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def build_services(where, names, force=False):
    osm = RAW / "osm" / "pois.jsonl"
    gtfs = RAW / "gtfs" / "hsl_stops.json"
    if not osm.exists():
        print(f"  ! {osm} missing — run scripts/fetch_services.py --only osm", file=sys.stderr)
        return None
    per = collections.defaultdict(list)
    dropped_osm_stops, unplaced = 0, 0

    # HSL first, so the kunnat it covers are known before OSM's stops are considered
    hsl_kunnat, hsl_n = set(), 0
    if gtfs.exists():
        d = json.loads(gtfs.read_text(encoding="utf-8"))
        for s in d["list"]:
            k = where(s["lat"], s["lon"])
            if not k:
                unplaced += 1
                continue
            modes = [m for m in (gtfs_mode(t) for t in s["modes"]) if m]
            # a stop with no trips in the feed is still a stop; it is drawn as a bus stop,
            # which is what the overwhelming majority of them are
            mode = ("rail" if "rail" in modes else "metro" if "metro" in modes
                    else "light-rail" if "light-rail" in modes else "ferry" if "ferry" in modes
                    else "bus")
            per[k].append(["transport", mode, s["lat"], s["lon"], s["name"], "", "hsl"])
            hsl_kunnat.add(k)
            hsl_n += 1
    else:
        print("  ⚠ no HSL GTFS — every stop will be OpenStreetMap's", file=sys.stderr)

    for r in read_jsonl(osm):
        cat = r["cat"]
        if cat == "stop":
            k = where(r["lat"], r["lon"])
            if not k:
                unplaced += 1
                continue
            if k in hsl_kunnat:
                # HSL publishes this kunta's stops itself; keeping OSM's too would double-count
                dropped_osm_stops += 1
                continue
            mode = OSM_STOP_MODE.get(r["tag"])
            if not mode:
                continue
            per[k].append(["transport", mode, r["lat"], r["lon"], r["name"], "", "osm"])
            continue
        if cat not in SRV_MAP:
            continue
        dest, subs = SRV_MAP[cat]
        sub = subs.get(r["tag"])
        if not sub:
            continue
        k = where(r["lat"], r["lon"])
        if not k:
            unplaced += 1
            continue
        # slot 5 is the brand/operator the mapper wrote, slot 6 the publisher of the point
        per[k].append([dest, sub, r["lat"], r["lon"], r["name"], r.get("brand", ""), "osm"])

    SRV_DIR.mkdir(parents=True, exist_ok=True)
    for old in SRV_DIR.glob("*.json"):
        old.unlink()
    index, total = {}, 0
    for k, pts in sorted(per.items()):
        lats = [p[2] for p in pts]
        lons = [p[3] for p in pts]
        by_cat = collections.Counter(p[0] for p in pts)
        (SRV_DIR / f"{k}.json").write_text(json.dumps(
            {"kunta": k, "name": names.get(k, ""), "n": len(pts), "points": pts},
            ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        index[k] = {"bbox": [round(min(lats), 5), round(min(lons), 5),
                             round(max(lats), 5), round(max(lons), 5)],
                    "n": len(pts), "by_cat": dict(by_cat)}
        total += len(pts)
    meta = {
        "built": dt.date.today().isoformat(),
        "asof": dt.date.today().isoformat(),
        "categories": ["grocery", "food", "pharmacy", "transport"],
        "kunnat": index, "n": total,
        "sources": [
            {"label": "OpenStreetMap — Geofabrik finland-latest extract", "licence": OSM_ATTRIB,
             "used_for": "groceries, food & drink, pharmacies, and stops outside the HSL region",
             "url": "https://download.geofabrik.de/europe/finland.html"},
            {"label": "HSL — static GTFS", "licence": HSL_ATTRIB,
             "used_for": f"public-transport stops in the {len(hsl_kunnat)} kunnat HSL serves",
             "url": "https://www.hsl.fi/hsl/avoin-data"},
        ],
        "hsl_kunnat": sorted(hsl_kunnat),
        "note": ("There is no keyless national GTFS: Digitransit's national feed answers 401 "
                 "without a registered subscription key, and Fintraffic's FINAP is a catalogue "
                 "of ~292 separate operator feeds. So stops are HSL's inside the HSL region and "
                 "OpenStreetMap's everywhere else, and every point says which. "
                 f"{dropped_osm_stops:,} OSM stops inside the HSL region were dropped rather "
                 "than double-counted."),
        "coverage_warning": ("OpenStreetMap coverage is not uniform. A rural area with no shop "
                             "mapped is not the same as an area with no shop."),
    }
    print(f"  · {total:,} points in {len(index)} kunnat · {hsl_n:,} HSL stops "
          f"· {dropped_osm_stops:,} OSM stops dropped inside the HSL region · {unplaced:,} unplaced")
    return meta


def build_public(where, names):
    pk = RAW / "palvelukartta" / "units.json"
    osm = RAW / "osm" / "pois.jsonl"
    per = collections.defaultdict(list)
    pk_kunnat, pk_n, osm_n, unplaced = set(), 0, 0, 0

    if pk.exists():
        d = json.loads(pk.read_text(encoding="utf-8"))
        for u in d["list"]:
            k = where(u["lat"], u["lon"])
            if not k:
                unplaced += 1
                continue
            cat = PK_MAP.get(u["cat"])
            if not cat:
                continue
            # `kind` is the UI's own vocabulary: the Danish register split a building into an
            # existing one and an open permit case. Finland's sources publish only buildings
            # that exist, so every row is "existing" — stated, not left blank.
            per[k].append({"cat": cat, "kind": "existing", "name": u["name"],
                           "address": u.get("addr", ""), "lat": u["lat"], "lon": u["lon"],
                           "src": "palvelukartta", "sub": u["cat"]})
            pk_kunnat.add(k)
            pk_n += 1
    else:
        print("  ⚠ no Palvelukartta file — the Helsinki region falls back to OSM", file=sys.stderr)

    if osm.exists():
        for r in read_jsonl(osm):
            cat = PUB_MAP.get(r["cat"])
            if not cat:
                continue
            k = where(r["lat"], r["lon"])
            if not k:
                unplaced += 1
                continue
            if k in pk_kunnat:
                continue              # Palvelukartta is the register here; OSM would duplicate it
            per[k].append({"cat": cat, "kind": "existing", "name": r["name"], "address": "",
                           "lat": r["lat"], "lon": r["lon"], "src": "osm", "sub": r["tag"]})
            osm_n += 1

    PUB_DIR.mkdir(parents=True, exist_ok=True)
    for old in PUB_DIR.glob("*.json"):
        old.unlink()
    areas, total = {}, 0
    for k, rows in sorted(per.items()):
        rows.sort(key=lambda b: (b["cat"], b["name"]))
        (PUB_DIR / f"{k}.json").write_text(json.dumps(
            {"kunta": k, "name": names.get(k, ""), "n": len(rows), "buildings": rows},
            ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        areas[f"kunta:{k}"] = dict(collections.Counter(b["cat"] for b in rows))
        total += len(rows)
    meta = {
        "built": dt.date.today().isoformat(),
        "kunnat": sorted(per), "areas": areas, "n": total,
        # The Danish register published a construction year per public building and the UI has a
        # "recently built" filter on it. Neither Palvelukartta nor OSM publishes one, so the list
        # is empty and the filter simply has nothing to offer — it is not filled with a guess.
        "recent_years": [],
        "categories": {"education": "Education", "institutions": "Daycare / institutions",
                       "health": "Health", "culture": "Culture"},
        "sources": [
            {"label": "Helsingin kaupunki — Palvelukartta", "licence": PK_ATTRIB,
             "used_for": f"{len(pk_kunnat)} municipalities Palvelukartta covers",
             "url": "https://palvelukartta.hel.fi/"},
            {"label": "OpenStreetMap", "licence": OSM_ATTRIB,
             "used_for": "everywhere Palvelukartta does not reach",
             "url": "https://www.openstreetmap.org/"},
        ],
        "not_used": ("Ryhti's building register cannot classify a public building: its open "
                     "classification has seven codes and `07 Julkinen rakennus` covers a school, "
                     "a health centre and a concert hall alike."),
        "coverage_warning": ("Palvelukartta is a register and OpenStreetMap is a map anyone can "
                             "edit. The two are not equally complete, and every point says which "
                             "it came from."),
    }
    print(f"  · {total:,} buildings in {len(per)} kunnat · {pk_n:,} Palvelukartta "
          f"· {osm_n:,} OpenStreetMap · {unplaced:,} unplaced")
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["services", "public"], action="append")
    args = ap.parse_args()
    try:
        import shapely  # noqa: F401
    except ImportError:
        print("shapely is needed here: python3 -m pip install -r requirements-services.txt",
              file=sys.stderr)
        return 1
    tree, geoms, codes, names = load_kunnat()
    where = locator(tree, geoms, codes)
    out = {}
    if not args.only or "services" in args.only:
        print("services:")
        m = build_services(where, names)
        if m is None:
            return 1
        out["services"] = m
    if not args.only or "public" in args.only:
        print("public buildings:")
        out["public"] = build_public(where, names)
    # the two indexes go exactly where scripts/build_dashboard.py looks for them
    if "services" in out:
        SRV_DIR.mkdir(parents=True, exist_ok=True)
        idx = SRV_DIR / "index.json"
        idx.write_text(json.dumps(out["services"], ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")
        print(f"wrote {idx.relative_to(ROOT)} ({idx.stat().st_size:,} B)")
    if "public" in out:
        idx = PROC / "public_index.json"
        idx.write_text(json.dumps(out["public"], ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")
        print(f"wrote {idx.relative_to(ROOT)} ({idx.stat().st_size:,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
