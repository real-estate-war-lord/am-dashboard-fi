#!/usr/bin/env python3
"""Major Finnish transport projects → data/geo/infra_projects.geojson (phase 13).

Two inputs, in this order of authority:

  `data/external/infra_fi.csv` — the hand-curated list of the big named projects, each row
  carrying the page its figures were read from and, where a publisher gives two or three
  different cost estimates for the same project, **all of them in the notes**. Lentorata has
  two and Länsirata has three; none is averaged and none is silently preferred.

  **Väylävirasto's own project layers** at `https://avoinapi.vaylapilvi.fi/vaylatiedot/ows`
  (`hanketiedot:tiehankkeet`, `:ratahankkeet`, `:vesivaylahankkeet`, CC BY 4.0). These are the
  agency's own hanke records, with the agency's own schedule and the agency's own published
  alignment. Every distinct project it publishes and the curated list does not already name is
  appended, so the layer is the state's list rather than a personal selection of it.

**Geometry is never drawn by hand.** `geometry_source` in the CSV takes:

    vayla:<layer>:<name>   the agency's own published alignment, all segments of that project merged
    (empty)                no geometry — the project keeps its data, its datasheet and its
                           Pipeline row, and simply is not drawn

An alignment that is only a plan on a consultant's map is **not** open data and is not invented
here. Kruunusillat, Lentorata, Länsirata, Itärata and Tampere's phase 2 therefore have no line:
`map: false`, and the reason is in each row's notes.

Outputs
  data/geo/infra_projects.geojson   FeatureCollection, WGS84
  data/processed/infra_index.json   which projects touch each kunta / postal area / osa-alue,
                                    plus the points within 1 200 m of an area, which is what the
                                    stations_planned_1200m growth signal counts

Needs shapely. Output committed, so `make build` needs neither it nor a network.
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import io
import json
import math
import pathlib
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_IN = ROOT / "data" / "external" / "infra_fi.csv"
RAW = ROOT / "data" / "raw" / "vayla"
OUT = ROOT / "data" / "geo" / "infra_projects.geojson"
IDX = ROOT / "data" / "processed" / "infra_index.json"
GEO = ROOT / "data" / "geo"

VAYLA = "https://avoinapi.vaylapilvi.fi/vaylatiedot/ows"
LAYERS = ("tiehankkeet", "ratahankkeet", "vesivaylahankkeet")
UA = "am-dashboard-fi/1.1 (open-data dashboard; infra layer)"
LICENCE = "CC BY 4.0 — Lähde: Väylävirasto"
VERIFY = "https://vayla.fi/kaikki-hankkeet"
NEAR_M = 1200          # the radius the stations_planned_1200m signal counts within
TYPE_OF = {"tiehankkeet": "road", "ratahankkeet": "rail", "vesivaylahankkeet": "waterway"}


def fetch_layer(layer, force=False):
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / f"{layer}.geojson"
    if dest.exists() and not force:
        print(f"  · cached {layer} ({dest.stat().st_size:,} B)")
        return json.loads(dest.read_text(encoding="utf-8"))
    url = (f"{VAYLA}?service=WFS&version=2.0.0&request=GetFeature"
           f"&typeNames=hanketiedot:{layer}&srsName=EPSG:4326&outputFormat=application/json")
    time.sleep(1.2)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
    dest.write_bytes(body)
    print(f"  · {layer} {len(body):,} B")
    return json.loads(body.decode("utf-8"))


def year_of(v):
    """'2029' or '2026-03-01T13:50:38Z' -> 2029 | None. Never guesses a year that is not there."""
    s = str(v or "").strip()
    if len(s) >= 4 and s[:4].isdigit():
        y = int(s[:4])
        if 1990 <= y <= 2100:
            return y
    return None


def status_of(start, end):
    """The agency publishes dates, not a status word, so the status is read off the dates."""
    now = dt.date.today().year
    s, e = year_of(start), year_of(end)
    if e is not None and e < now:
        return "opened"
    if s is not None and s <= now:
        return "construction"
    return "decided"


def round_coords(obj, nd=5):
    """5 decimals is ~1 m. Shapely hands back full float precision, which is seventeen digits
    of noise per coordinate and, across 274 projects, most of the file."""
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(float(x), nd) for x in obj]
        return [round_coords(x, nd) for x in obj]
    if isinstance(obj, dict):
        return {k: (round_coords(v, nd) if k == "coordinates" else v) for k, v in obj.items()}
    return obj


def merge_geoms(feats):
    """All segments of one project, merged. Points stay points; lines become one MultiLineString."""
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
    geoms = [shape(f["geometry"]) for f in feats if f.get("geometry")]
    if not geoms:
        return None
    lines = [g for g in geoms if g.geom_type in ("LineString", "MultiLineString")]
    if lines:
        u = unary_union(lines)
        # ~40 m. These are corridors drawn to be read at a municipal zoom, not survey lines,
        # and the whole layer has to fit in a page with a 3 MB ceiling.
        u = u.simplify(0.0004, preserve_topology=True)
        return round_coords(mapping(u))
    polys = [g for g in geoms if g.geom_type in ("Polygon", "MultiPolygon")]
    if polys:
        return round_coords(mapping(unary_union(polys).simplify(0.0004, preserve_topology=True)))
    return round_coords(mapping(unary_union(geoms)))


def hav_m(a_lat, a_lon, b_lat, b_lon):
    R = 6371008.8
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = p2 - p1
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(h)))


def build_index(features):
    """{'kunta:091': [ids…], …} plus the ids whose geometry comes within NEAR_M of the area."""
    from shapely.geometry import shape
    from shapely.strtree import STRtree
    areas = []
    for name, key, fname in (("kunta", "kunta", "kunnat.geojson"),
                             ("postinumero", "nr", "postinumerot.geojson"),
                             ("osa_alue", "code", "osa_alueet.geojson")):
        p = GEO / fname
        if not p.exists():
            continue
        for f in json.loads(p.read_text(encoding="utf-8"))["features"]:
            areas.append((f"{name}:{f['properties'][key]}", shape(f["geometry"]).buffer(0)))
    geoms = [g for _, g in areas]
    tree = STRtree(geoms)
    # NEAR_M in degrees of latitude, which is the conservative direction in Finland: a degree of
    # longitude is shorter here, so the buffer reaches slightly further east-west than 1 200 m.
    buf = NEAR_M / 111320.0
    out = collections.defaultdict(lambda: {"in": [], "near": []})
    for f in features:
        if not f.get("geometry"):
            continue
        g = shape(f["geometry"])
        pid = f["properties"]["id"]
        gb = g.buffer(buf)
        for i in tree.query(gb):
            key, poly = areas[i]
            if poly.intersects(g):
                out[key]["in"].append(pid)
            elif poly.intersects(gb):
                out[key]["near"].append(pid)
    return {k: v for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download the Väylä layers")
    ap.add_argument("--no-vayla", action="store_true", help="curated rows only")
    args = ap.parse_args()
    try:
        import shapely  # noqa: F401
    except ImportError:
        print("shapely is needed here: python3 -m pip install -r requirements-services.txt",
              file=sys.stderr)
        return 1

    print("Väylävirasto project layers:")
    wfs = {} if args.no_vayla else {L: fetch_layer(L, args.force) for L in LAYERS}
    by_name = collections.defaultdict(list)
    for layer, gj in wfs.items():
        for f in gj["features"]:
            n = (f["properties"].get("nimi") or "").strip()
            if n:
                by_name[(layer, n)].append(f)
    print(f"  · {sum(len(v) for v in by_name.values()):,} features "
          f"in {len(by_name)} distinct projects")

    today = dt.date.today().isoformat()
    features, curated_names = [], set()

    # ---- the curated list
    if CSV_IN.exists():
        with CSV_IN.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh, delimiter=";"):
                src = (row.get("geometry_source") or "").strip()
                geom = None
                if src.startswith("vayla:"):
                    _, layer, want = src.split(":", 2)
                    hit = [f for (L, n), fs in by_name.items() if L == layer and want.lower() in n.lower()
                           for f in fs]
                    if hit:
                        geom = merge_geoms(hit)
                        curated_names.update((layer, n) for (L, n) in by_name if L == layer and want.lower() in n.lower())
                    else:
                        print(f"  ⚠ {row['id']}: no Väylä feature matching {want!r} in {layer}")
                elif src:
                    print(f"  ⚠ {row['id']}: unknown geometry_source {src!r} — no geometry")
                budget = row.get("budget_meur") or ""
                features.append({"type": "Feature", "geometry": geom, "properties": {
                    "id": row["id"], "name": row["name"],
                    "label_short": row.get("label_short") or row["name"],
                    "type": row.get("type") or "rail",
                    "status": row.get("status") or "study",
                    "open_year": year_of(row.get("open_year")),
                    "open_window": row.get("open_window") or None,
                    "budget_meur": float(budget) if budget else None,
                    "price_base": row.get("price_base") or None,
                    "agency": row.get("agency") or "",
                    "curated": True,
                    "major": True,
                    "schematic": False,
                    "map": (row.get("map") or "").strip().lower() == "true" and geom is not None,
                    "source_url": row.get("source_url") or "",
                    "source_doc": row.get("source_doc") or None,
                    "geometry_source": src or "none published",
                    "updated": today,
                    "notes": row.get("notes") or "",
                }})
        print(f"curated: {len(features)} projects "
              f"({sum(1 for f in features if f['geometry'])} with a published alignment)")

    # ---- every other project the agency publishes
    added = 0
    dropped_finished = 0
    for (layer, name), fs in sorted(by_name.items()):
        if (layer, name) in curated_names:
            continue
        p0 = fs[0]["properties"]
        # A project that finished before this year and that the agency never gave a page to is a
        # completed maintenance record — a bridge repainted, a culvert replaced. It is not a
        # pipeline and it is not a growth signal, and 105 of them cost 136 kB in a page with a
        # 3 MB ceiling. The rule is the agency's own two facts, its end date and whether it
        # wrote a project page; nothing is hand-picked. The layer's meta says so.
        if (status_of(p0.get("aloitus"), p0.get("lopetus")) == "opened"
                and not (p0.get("linkki") or "").strip().startswith("http")):
            dropped_finished += 1
            continue
        geom = merge_geoms(fs)
        pid = "vayla-" + "".join(c if c.isalnum() else "-" for c in name.lower())[:48].strip("-")
        features.append({"type": "Feature", "geometry": geom, "properties": {
            "id": pid, "name": name, "label_short": name[:28],
            "type": TYPE_OF.get(layer, "road"),
            "status": status_of(p0.get("aloitus"), p0.get("lopetus")),
            "open_year": year_of(p0.get("lopetus")), "open_window": None,
            # The agency's `kustannusarvio` field is empty on every feature it publishes, so no
            # budget is claimed for these rows rather than a zero being written.
            "budget_meur": None, "price_base": None,
            "agency": p0.get("tilaajaorganisaatio") or "Väylävirasto",
            "curated": False, "schematic": False, "map": geom is not None,
            # `major` decides what the growth signal counts. The agency's list runs from a
            # multi-year rail programme down to repainting one bridge, and counting a repaint as
            # a growth signal would be misleading. The rule is the agency's own behaviour, not a
            # judgement of ours: it wrote a project page for this one. 46 of its 267 qualify.
            "major": bool((p0.get("linkki") or "").strip().startswith("http")),
            "source_url": (p0.get("linkki") or "").strip() or VERIFY,
            "source_doc": None,
            "geometry_source": f"vayla:{layer}",
            "updated": today,
            # the same sentence on 162 projects is 18 kB of the page; it belongs in the meta,
            # which the UI shows once, not on every row
            "notes": (p0.get("kuvaus") or "").strip(),
        }})
        added += 1
    print(f"Väylävirasto: {added} further projects appended · "
          f"{dropped_finished} finished maintenance records left out")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "type": "FeatureCollection",
        "meta": {"built": today, "source_csv": "data/external/infra_fi.csv",
                 "licence": LICENCE, "verify_at_source": VERIFY,
                 "attribution": ["Väylävirasto — hanketiedot (CC BY 4.0)",
                                 "Project owners' own pages, cited per project"],
                 "vayla_note": ("A project without notes of its own is Väylävirasto's own record: "
                                "its schedule and its alignment, exactly as the agency publishes them."),
                 "note": ("Alignments are Väylävirasto's own where it publishes one; a project "
                          "whose alignment is not open data has no geometry and no line, rather "
                          "than a drawn guess. Where a publisher gives more than one cost "
                          "estimate, all of them are in the project's notes. `major` is true for "
                          "every curated project and for every Väylävirasto project the agency "
                          "itself gave a project page; the growth signals count only those, "
                          "because the agency's list runs down to repainting a single bridge. "
                          "A Väylävirasto project that had already finished AND never got a "
                          "project page is left out entirely: a completed culvert replacement "
                          "is not a pipeline. Everything still under way, decided or studied is "
                          "kept whether or not it is major.")},
        "features": features,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} B · {len(features)} projects)")

    print("index:")
    idx = build_index(features)
    major = sorted(f["properties"]["id"] for f in features if f["properties"].get("major"))
    opened = sorted(f["properties"]["id"] for f in features if f["properties"].get("status") == "opened")
    IDX.write_text(json.dumps({"built": today, "near_m": NEAR_M, "major": major,
                               "opened": opened, "areas": idx},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {IDX.relative_to(ROOT)} ({IDX.stat().st_size:,} B · {len(idx)} areas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
