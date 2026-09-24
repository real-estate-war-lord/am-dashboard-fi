#!/usr/bin/env python3
"""SYKE flood-hazard zones → data/raw/syke_flood/ (phase 11).

    https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/{wfs,wms}
    (note the plural host: `paikkatieto.ymparisto.fi` answers 200 with an IIS default page)

**Why a raster.** The zones cannot be fetched as vectors at any sane size. The probe measured
3 412 672 features for watercourse 1/100a and 4 014 394 for sea 1/100a; a Helsinki-sized bbox
alone returns 8.9 MB and 12.7 MB of GeoJSON and hits GeoServer's 10 000-feature cap, and
SYKE's own bulk zips are **5.59 GB** and **5.65 GB**. The four layers this dashboard needs
would be 15–20 GB of polygon fragments — which is what they are, fragments of a depth raster
exported as polygons. So the area share is measured from the publisher's own WMS rendering of
those same polygons, at a stated ground resolution, which is the arithmetic the fragments were
made from in the first place. `docs/CLIMATE_FI.md` says so beside every figure.

**Only where mapping exists.** SYKE maps flood hazard for designated areas, not for the whole
country. The two mapped-extent layers are small vectors (113 + 8 features) and are pulled as
vectors; they are what separates "no flood hazard here" from **"not mapped"**, which are
completely different statements and must never be collapsed into a 0.

209 of 308 kunnat touch a mapped extent. Only those are rastered, at 25 m/px: two return
periods plus one "assessed land" mask per hazard, about 1 680 requests in total.

Stdlib only, except that it writes PNGs it does not decode. Resumable: an existing tile is
kept. `--force` re-pulls.
"""
import argparse
import datetime as dt
import json
import math
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "syke_flood"
GEO = ROOT / "data" / "geo" / "kunnat.geojson"

WFS = "https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs"
WMS = "https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wms"
UA = "am-dashboard-fi/1.1 (open-data dashboard; flood hazard screening)"
LICENCE = "CC BY 4.0 — Lähde: Suomen ympäristökeskus (Syke), tulvavaaravyöhykkeet"
VERIFY = ("https://www.avoindata.fi/data/fi/dataset/"
          "tulvavaaravyohykkeet-perusskenaariot-flood-hazard-zones-basic-scenarios")

HAZARDS = {"river": "Vesistotulva", "sea": "Meritulva"}
PERIODS = ("100", "1000")            # 1/100a and 1/1000a — the two the dashboard carries
RES_M = 25.0                         # ground resolution of the measurement, in metres
TILE = 1024                          # pixels per GetMap request

# ---------------------------------------------------------------- what counts as flooded
#
# The default style is a *cartographic* one and cannot be read as data. Its palest fill,
# #D1FFFF, is the class `vesistö` — the water body — so counting "any non-transparent pixel"
# counts the whole Gulf of Finland as flooded, which put a quarter of Kallio, a hill, inside
# a 1/100a sea flood zone. The publisher's own GetLegendGraphic gives the rule list, and the
# WFS gives the values in `syvsuojluokka`:
#
#   '0 - 0.5 m' '0.5 - 1 m' '1 - 2 m' '2 - 3 m' 'yli 3 m'   flooded land, by depth
#   'tulvan peittämä. syvyystieto puuttuu'                   flooded, depth not published
#   'tulvasuojeltu …'                                        flooded but protected by structures
#   'kuiva maa'                                              DRY LAND inside the mapped area
#   'vesistö'                                                the water body
#
# So the mask is built from a flat SLD plus an explicit CQL list of the publisher's own class
# names — no colour matching, no anti-aliasing (`antialias:none` makes every pixel 0 or 255),
# and the hatched "protected" classes come out solid instead of striped.
FLOOD_CLASSES = ("0 - 0.5 m", "0.5 - 1 m", "1 - 2 m", "2 - 3 m", "yli 3 m",
                 "tulvan peittämä. syvyystieto puuttuu",
                 "tulvasuojeltu kiinteillä rakenteilla",
                 "tulvasuojeltu ennalta sovituilla tilapäisillä toimenpiteillä")
# `kuiva maa` is SYKE's own land mask: land inside the mapped area that does not flood. With
# the flood classes it gives the assessed LAND, which is what "not mapped" is measured against.
LAND_CLASSES = FLOOD_CLASSES + ("kuiva maa",)

FLAT_SLD = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<StyledLayerDescriptor version="1.0.0" xmlns="http://www.opengis.net/sld">'
            '<NamedLayer><Name>{layer}</Name><UserStyle><FeatureTypeStyle><Rule>'
            '<PolygonSymbolizer><Fill><CssParameter name="fill">#000000</CssParameter>'
            '<CssParameter name="fill-opacity">1</CssParameter></Fill></PolygonSymbolizer>'
            '</Rule></FeatureTypeStyle></UserStyle></NamedLayer></StyledLayerDescriptor>')


def cql(classes):
    return "syvsuojluokka IN (" + ",".join("'" + c.replace("'", "''") + "'" for c in classes) + ")"
THROTTLE = 1.2
TIMEOUT = 300
RETRIES = 4


def get(url, timeout=TIMEOUT):
    for attempt in range(RETRIES):
        time.sleep(THROTTLE if attempt == 0 else 15 * attempt)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < RETRIES - 1:
                print("    · rate limited, waiting")
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < RETRIES - 1:
                continue
            raise
    raise RuntimeError("unreachable")


def fetch_extents(force=False):
    """The mapped-extent polygons, as vectors. Small, and the whole basis of 'Not mapped'."""
    RAW.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, layer in HAZARDS.items():
        dest = RAW / f"extent_{key}.geojson"
        if dest.exists() and not force:
            print(f"  · cached extent_{key} ({dest.stat().st_size:,} B)")
        else:
            url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature"
                   f"&typeNames=inspire_nz:NZ.Tulvavaarakartoitetut_alueet_{layer}"
                   f"&srsName=EPSG:4326&outputFormat=application/json")
            body, _ = get(url)
            dest.write_bytes(body)
            print(f"  · extent_{key} {len(body):,} B")
        out[key] = json.loads(dest.read_text(encoding="utf-8"))
    return out


def tile_grid(bounds):
    """(w,s,e,n) in degrees -> the pixel grid and the list of tiles covering it.

    The grid is defined in degrees but sized from metres, so a tile is about RES_M on the
    ground in both directions at the middle latitude of the box. The exact transform of every
    tile is written to the index, because the builder has to rasterise our own polygons onto
    the identical grid or the two would not line up.
    """
    w, s, e, n = bounds
    midlat = (n + s) / 2.0
    dlat = RES_M / 111320.0
    dlon = RES_M / (111320.0 * max(0.05, math.cos(math.radians(midlat))))
    nx = max(1, int(math.ceil((e - w) / dlon)))
    ny = max(1, int(math.ceil((n - s) / dlat)))
    tiles = []
    for ty in range(int(math.ceil(ny / TILE))):
        for tx in range(int(math.ceil(nx / TILE))):
            x0, y0 = tx * TILE, ty * TILE
            tw, th = min(TILE, nx - x0), min(TILE, ny - y0)
            # y counts down from the north edge, the way an image does
            tiles.append({"i": len(tiles), "x": x0, "y": y0, "w": tw, "h": th,
                          "bbox": [round(w + x0 * dlon, 7), round(n - (y0 + th) * dlat, 7),
                                   round(w + (x0 + tw) * dlon, 7), round(n - y0 * dlat, 7)]})
    return {"w": w, "s": s, "e": e, "n": n, "nx": nx, "ny": ny,
            "dlon": dlon, "dlat": dlat, "res_m": RES_M, "tiles": tiles}


def getmap(layer, bbox, w, h, classes):
    """One GetMap, flat-filled and class-filtered, so the PNG is a mask and not a picture.

    WMS 1.3.0 with EPSG:4326 takes the bbox as min-lat,min-lon,max-lat,max-lon.
    """
    lo_x, lo_y, hi_x, hi_y = bbox
    q = {"service": "WMS", "version": "1.3.0", "request": "GetMap",
         "layers": layer, "styles": "", "crs": "EPSG:4326",
         "bbox": f"{lo_y},{lo_x},{hi_y},{hi_x}",
         "width": str(w), "height": str(h),
         "format": "image/png", "transparent": "true",
         "format_options": "antialias:none",
         "SLD_BODY": FLAT_SLD.format(layer=layer),
         "CQL_FILTER": cql(classes)}
    body, ctype = get(f"{WMS}?{urllib.parse.urlencode(q)}")
    if "png" not in ctype.lower():
        # GeoServer reports an error as XML with a 200; never let that land on disk as a tile
        raise RuntimeError(f"{layer}: expected a PNG, got {ctype}: {body[:200]!r}")
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="kunta codes")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--extents-only", action="store_true")
    args = ap.parse_args()
    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union
    except ImportError:
        print("shapely is needed here: python3 -m pip install -r requirements-geo.txt", file=sys.stderr)
        return 1

    RAW.mkdir(parents=True, exist_ok=True)
    print("mapped extents (vectors):")
    ext_gj = fetch_extents(args.force)
    if args.extents_only:
        return 0
    ext = {k: unary_union([shape(f["geometry"]).buffer(0) for f in gj["features"]])
           for k, gj in ext_gj.items()}

    kunnat = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    codes = set(args.only) if args.only else None
    index, n_tiles, n_new, skipped = {}, 0, 0, 0
    for f in kunnat:
        code = f["properties"]["kunta"]
        if codes and code not in codes:
            continue
        geom = shape(f["geometry"]).buffer(0)
        for key, layer_base in HAZARDS.items():
            inter = geom.intersection(ext[key])
            if inter.is_empty:
                continue            # not mapped for this hazard — and that is the finding
            grid = tile_grid(inter.bounds)
            index.setdefault(code, {})[key] = {k: v for k, v in grid.items() if k != "tiles"}
            index[code][key]["tiles"] = [{k: t[k] for k in ("i", "x", "y", "w", "h")} for t in grid["tiles"]]
            # the two return periods, plus one "assessed land" mask per hazard (taken from the
            # widest return period, since the mapped area is the same for all of them)
            jobs = [(p, f"NZ.Tulvavaaravyohykkeet_{layer_base}_1_{p}a", FLOOD_CLASSES) for p in PERIODS]
            jobs.append(("land", f"NZ.Tulvavaaravyohykkeet_{layer_base}_1_{PERIODS[-1]}a", LAND_CLASSES))
            for tag, layer, classes in jobs:
                for t in grid["tiles"]:
                    dest = RAW / f"{code}_{key}_{tag}_{t['i']:03d}.png"
                    n_tiles += 1
                    if dest.exists() and dest.stat().st_size > 0 and not args.force:
                        skipped += 1
                        continue
                    try:
                        dest.write_bytes(getmap(layer, t["bbox"], t["w"], t["h"], classes))
                        n_new += 1
                        print(f"  · {dest.name} {dest.stat().st_size:,} B "
                              f"({t['w']}×{t['h']} px)")
                    except Exception as e:  # noqa: BLE001
                        print(f"  ! {dest.name}: {e}", file=sys.stderr)
                        return 1
    (RAW / "index.json").write_text(json.dumps({
        "built": dt.date.today().isoformat(),
        "wms": WMS, "wfs": WFS, "licence": LICENCE, "verify_at_source": VERIFY,
        "res_m": RES_M, "tile_px": TILE, "periods": list(PERIODS), "hazards": HAZARDS,
        "flood_classes": list(FLOOD_CLASSES), "land_classes": list(LAND_CLASSES),
        "render": ("flat SLD_BODY + CQL_FILTER on syvsuojluokka + format_options=antialias:none, "
                   "so every pixel is 0 or 255 and means exactly 'a feature of one of these "
                   "published classes covers this pixel'"),
        "note": ("The grid every tile sits on, so scripts/build_climate.py can rasterise our own "
                 "area polygons onto exactly the same pixels. `bbox` is omitted from the stored "
                 "tiles because it is derivable from w/s/n/e, dlon and dlat."),
        "kunnat": index,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n{len(index)} kunnat mapped · {n_tiles:,} tiles ({n_new:,} new, {skipped:,} cached)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
