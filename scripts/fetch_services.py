#!/usr/bin/env python3
"""OpenStreetMap + HSL GTFS + Palvelukartta → data/raw/ (phase 12).

Three sources, because no single one covers Finland:

  **OpenStreetMap**, via the Geofabrik `finland-latest.osm.pbf` extract (767 MB, ODbL). Shops,
  places to eat and pharmacies — the everyday services — everywhere in the country.

  **HSL's static GTFS** (`https://dev.hsl.fi/gtfs/hsl.zip`, keyless). Public-transport stops for
  the Helsinki region, from the operator's own feed.

  **There is no keyless national GTFS.** Digitransit's aggregated national feed answers **401**
  without a registered subscription key, and Fintraffic's FINAP is a catalogue of ~292 separate
  operator feeds of uneven quality rather than one file. So outside the HSL region the stops
  come from OpenStreetMap, every point says which source it came from, and the difference is
  stated in the UI rather than smoothed over. (docs/PROBE_FI.md, batch-2.)

  **Palvelukartta** (`https://api.hel.fi/servicemap/v2/`, keyless) is pulled here too, but it
  feeds the *public buildings* layer rather than services. It covers Helsinki, Espoo, Vantaa and
  Kauniainen only — 21 506 units.

Needs pyosmium for the .pbf (requirements-services.txt). The downloads are resumable: an
existing file of the right size is kept.

    python3 scripts/fetch_services.py            # everything
    python3 scripts/fetch_services.py --only osm
"""
import argparse
import datetime as dt
import gzip
import io
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OSM_PBF = RAW / "osm" / "finland-latest.osm.pbf"
OSM_OUT = RAW / "osm" / "pois.jsonl"
GTFS_ZIP = RAW / "gtfs" / "hsl.zip"
GTFS_OUT = RAW / "gtfs" / "hsl_stops.json"
PK_OUT = RAW / "palvelukartta" / "units.json"

OSM_URL = "https://download.geofabrik.de/europe/finland-latest.osm.pbf"
GTFS_URL = "https://dev.hsl.fi/gtfs/hsl.zip"
PK_API = "https://api.hel.fi/servicemap/v2"
UA = "am-dashboard-fi/1.1 (open-data dashboard; services layer)"
OSM_LICENCE = "ODbL 1.0 — © OpenStreetMap contributors"
GTFS_LICENCE = "CC BY 4.0 — Lähde: Helsingin seudun liikenne (HSL)"
PK_LICENCE = "CC BY 4.0 — Lähde: Helsingin kaupunki, Palvelukartta"

# What a point has to be to earn a place on the map. Every category is an OSM tag the mapper
# actually chose, never an inference: a `shop=supermarket` is a supermarket because somebody
# tagged it one, and a shop with no recognised tag is left out rather than guessed at.
OSM_CATS = {
    "grocery": [("shop", {"supermarket", "convenience", "greengrocer", "grocery", "general"})],
    "food": [("amenity", {"restaurant", "cafe", "fast_food", "bar", "pub"})],
    "pharmacy": [("amenity", {"pharmacy"}), ("healthcare", {"pharmacy"})],
    "school": [("amenity", {"school"})],
    "kindergarten": [("amenity", {"kindergarten"})],
    "health": [("amenity", {"clinic", "doctors", "hospital"}), ("healthcare", {"centre", "hospital", "doctor"})],
    "culture": [("amenity", {"library", "theatre", "arts_centre", "cinema"}), ("tourism", {"museum"})],
    "stop": [("public_transport", {"station", "stop_position"}), ("railway", {"station", "tram_stop", "halt"}),
             ("highway", {"bus_stop"})],
}
# Finland's box, so a stray point outside the extract is dropped rather than drawn in the sea
BOX = {"lat": (59.7, 70.1), "lon": (19.0, 31.6)}


def get(url, timeout=180, tries=4):
    for attempt in range(tries):
        time.sleep(1.0 if attempt == 0 else 12 * attempt)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                return body
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < tries - 1:
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries - 1:
                continue
            raise
    raise RuntimeError("unreachable")


def download(url, dest, force=False):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"  · cached {dest.name} ({dest.stat().st_size:,} B)")
        return dest
    print(f"  · downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=1800) as r, tmp.open("wb") as fh:
        n = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
            n += len(chunk)
    tmp.replace(dest)
    print(f"  · {dest.name} {dest.stat().st_size:,} B")
    return dest


# ---------------------------------------------------------------- OpenStreetMap

def osm_category(tags):
    for cat, rules in OSM_CATS.items():
        for key, values in rules:
            v = tags.get(key)
            if v in values:
                return cat, f"{key}={v}"
    return None, None


def run_osm(force=False):
    try:
        import osmium
    except ImportError:
        print("pyosmium is needed for the .pbf: "
              "python3 -m pip install -r requirements-services.txt", file=sys.stderr)
        return 1
    download(OSM_URL, OSM_PBF, force)
    if OSM_OUT.exists() and not force:
        print(f"  · cached {OSM_OUT.name} ({OSM_OUT.stat().st_size:,} B)")
        return 0
    print("  · scanning the extract (nodes, and the centroid of a tagged way)")
    counts, written = {}, 0
    t0 = time.time()
    with OSM_OUT.open("w", encoding="utf-8") as fh:
        # `with_areas=False` and locations on ways: a shop mapped as a building outline is as
        # real as one mapped as a node, and dropping it would thin out exactly the dense places.
        for obj in osmium.FileProcessor(str(OSM_PBF)).with_locations():
            tags = dict(obj.tags) if obj.tags else {}
            if not tags:
                continue
            cat, why = osm_category(tags)
            if not cat:
                continue
            if obj.is_node():
                lat, lon = obj.location.lat, obj.location.lon
            elif obj.is_way() and len(obj.nodes) > 1:
                pts = []
                for n in obj.nodes:
                    try:
                        pts.append((n.location.lat, n.location.lon))
                    except (osmium.InvalidLocationError, RuntimeError):
                        pass
                if not pts:
                    continue
                lat = sum(p[0] for p in pts) / len(pts)
                lon = sum(p[1] for p in pts) / len(pts)
            else:
                continue
            if not (BOX["lat"][0] <= lat <= BOX["lat"][1] and BOX["lon"][0] <= lon <= BOX["lon"][1]):
                continue
            fh.write(json.dumps({
                "cat": cat, "tag": why,
                "name": tags.get("name") or tags.get("name:fi") or tags.get("name:sv") or "",
                "lat": round(lat, 6), "lon": round(lon, 6),
                "brand": tags.get("brand") or tags.get("operator") or "",
                "id": f"{'n' if obj.is_node() else 'w'}{obj.id}",
            }, ensure_ascii=False) + "\n")
            counts[cat] = counts.get(cat, 0) + 1
            written += 1
    (OSM_OUT.parent / "pois.jsonl.meta.json").write_text(json.dumps({
        "source": "OpenStreetMap — Geofabrik finland-latest extract", "url": OSM_URL,
        "licence": OSM_LICENCE, "verify_at_source": "https://www.openstreetmap.org/",
        "fetched": dt.date.today().isoformat(), "points": written, "by_category": counts,
        "pbf_bytes": OSM_PBF.stat().st_size,
        "note": ("A point is kept only when a mapper chose one of the tags listed in "
                 "scripts/fetch_services.py; nothing is inferred. A feature mapped as a way "
                 "is kept at the mean of its nodes."),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  · {written:,} points in {time.time() - t0:.0f}s · " +
          " · ".join(f"{k} {v:,}" for k, v in sorted(counts.items())))
    return 0


# ---------------------------------------------------------------- HSL GTFS

def run_gtfs(force=False):
    download(GTFS_URL, GTFS_ZIP, force)
    if GTFS_OUT.exists() and not force:
        print(f"  · cached {GTFS_OUT.name} ({GTFS_OUT.stat().st_size:,} B)")
        return 0
    import csv
    stops, modes = [], {}
    with zipfile.ZipFile(GTFS_ZIP) as z:
        names = z.namelist()
        if "stops.txt" not in names:
            print(f"  ! no stops.txt in the feed — it has {names[:8]}", file=sys.stderr)
            return 1
        # route type per stop, so a stop can say whether it is rail, metro, tram, bus or ferry
        try:
            with z.open("routes.txt") as fh:
                rt = {r["route_id"]: r["route_type"] for r in csv.DictReader(io.TextIOWrapper(fh, "utf-8-sig"))}
            with z.open("trips.txt") as fh:
                trip_route = {r["trip_id"]: r["route_id"] for r in csv.DictReader(io.TextIOWrapper(fh, "utf-8-sig"))}
            with z.open("stop_times.txt") as fh:
                for r in csv.DictReader(io.TextIOWrapper(fh, "utf-8-sig")):
                    t = rt.get(trip_route.get(r["trip_id"], ""), "")
                    if t:
                        modes.setdefault(r["stop_id"], set()).add(t)
        except KeyError:
            pass                      # a feed without the optional files still gives us stops
        with z.open("stops.txt") as fh:
            for r in csv.DictReader(io.TextIOWrapper(fh, "utf-8-sig")):
                try:
                    lat, lon = float(r["stop_lat"]), float(r["stop_lon"])
                except (KeyError, ValueError):
                    continue
                if r.get("location_type") in ("2", "3", "4"):
                    continue          # entrances, generic nodes and boarding areas are not stops
                stops.append({"id": r["stop_id"], "name": r.get("stop_name", ""),
                              "lat": round(lat, 6), "lon": round(lon, 6),
                              "code": r.get("stop_code", ""),
                              "parent": r.get("parent_station", ""),
                              "modes": sorted(modes.get(r["stop_id"], []))})
    GTFS_OUT.parent.mkdir(parents=True, exist_ok=True)
    GTFS_OUT.write_text(json.dumps({
        "source": "HSL — static GTFS", "url": GTFS_URL, "licence": GTFS_LICENCE,
        "verify_at_source": "https://www.hsl.fi/hsl/avoin-data",
        "fetched": dt.date.today().isoformat(), "stops": len(stops),
        # HSL uses the EXTENDED GTFS route types (701 local bus, 109 suburban rail, 900 tram …),
        # not only the basic five, so the raw codes are stored as published and the mapping to a
        # mode family lives in scripts/build_services.py where it can be read beside its use.
        "gtfs_route_types_seen": sorted({t for s_ in stops for t in s_["modes"]}),
        "note": ("The Helsinki region only. There is no keyless national GTFS — Digitransit's "
                 "national feed answers 401 without a registered key — so stops elsewhere come "
                 "from OpenStreetMap and say so."),
        "list": stops,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  · {len(stops):,} stops → {GTFS_OUT.name} ({GTFS_OUT.stat().st_size:,} B)")
    return 0


# ---------------------------------------------------------------- Palvelukartta

PK_NODES = {"school": 1097, "upper_secondary": 1257, "kindergarten": 869,
            "health": 991, "library": 324}


def run_pk(force=False):
    if PK_OUT.exists() and not force:
        print(f"  · cached {PK_OUT.name} ({PK_OUT.stat().st_size:,} B)")
        return 0
    units, seen = [], set()
    for cat, node in PK_NODES.items():
        page, got = 1, 0
        while True:
            url = (f"{PK_API}/unit/?service_node={node}&page={page}&page_size=200"
                   f"&only=name,location,municipality,street_address,services,department")
            d = json.loads(get(url))
            for u in d.get("results", []):
                uid = u.get("id")
                loc = (u.get("location") or {}).get("coordinates")
                if not loc or uid in seen:
                    continue
                seen.add(uid)
                name = u.get("name") or {}
                addr = u.get("street_address") or {}
                units.append({"id": uid, "cat": cat,
                              "name": name.get("fi") or name.get("sv") or name.get("en") or "",
                              "lon": round(loc[0], 6), "lat": round(loc[1], 6),
                              "kunta_name": u.get("municipality") or "",
                              "addr": addr.get("fi") or addr.get("sv") or ""})
                got += 1
            if not d.get("next"):
                break
            page += 1
        print(f"  · {cat} (service_node {node}): {got:,} units")
    PK_OUT.parent.mkdir(parents=True, exist_ok=True)
    PK_OUT.write_text(json.dumps({
        "source": "Helsingin kaupunki — Palvelukartta (Service Map API v2)",
        "url": PK_API, "licence": PK_LICENCE,
        "verify_at_source": "https://palvelukartta.hel.fi/",
        "fetched": dt.date.today().isoformat(), "units": len(units),
        "service_nodes": PK_NODES,
        "note": ("Helsinki, Espoo, Vantaa and Kauniainen only. The service_node ids were read "
                 "from the API's own service-node tree, not guessed."),
        "list": units,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  · {len(units):,} units → {PK_OUT.name} ({PK_OUT.stat().st_size:,} B)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["osm", "gtfs", "pk"], action="append")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    rc = 0
    for name in (args.only or ["osm", "gtfs", "pk"]):
        print(f"\n--- {name} ---")
        rc |= {"osm": run_osm, "gtfs": run_gtfs, "pk": run_pk}[name](args.force)
    return rc


if __name__ == "__main__":
    sys.exit(main())
