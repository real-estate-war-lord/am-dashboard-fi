#!/usr/bin/env python3
"""data/raw/syke_flood/ + STUK radon → data/processed/climate.json (phase 11).

Two published sources, measured area by area:

  **Flood hazard.** For every kunta that SYKE has flood-mapped, the publisher's own zone
  polygons are read at 25 m/px — rendered flat and filtered to an explicit list of SYKE's own
  `syvsuojluokka` classes, so a pixel means "a flood class covers this", not "something was
  drawn here" — and our own area rings are rasterised onto exactly the same grid. The share
  reported is *land inside the zone ÷ the area's land*, in per cent. Why a raster and not the
  vectors is argued in scripts/fetch_flood.py and in docs/PROBE_FI.md, batch-2 finding 3.

  **Radon.** STUK's two published spreadsheets, by kunta and by postal code, carried through
  as published: mean, median and the share of measured detached-house dwellings over
  200 / 300 / 1 000 Bq/m³. A blank in the source is **suppressed, not zero**, and stays null.

**"Not mapped" is not "no risk".** SYKE maps flood hazard for designated areas only. An area
that lies outside every mapped extent carries no flood figure at all and the page says so.
An area that is partly mapped carries its share *of the whole area* together with
`flood_mapped`, the share of it that has been assessed, so a reader can see how much of the
answer is an answer. Nothing here fills a gap with a zero.

Needs numpy and pillow (requirements-geo.txt); `make build` does not, because the output is
committed.

    python3 scripts/build_climate.py
    python3 scripts/build_climate.py --only 091 049
"""
import argparse
import collections
import datetime as dt
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
RAW = ROOT / "data" / "raw" / "syke_flood"
EXT = ROOT / "data" / "external"
GEO = ROOT / "data" / "geo"
OUT = ROOT / "data" / "processed" / "climate.json"

FLOOD_LICENCE = "CC BY 4.0 — Lähde: Suomen ympäristökeskus (Syke), tulvavaaravyöhykkeet"
FLOOD_VERIFY = ("https://www.avoindata.fi/data/fi/dataset/"
                "tulvavaaravyohykkeet-perusskenaariot-flood-hazard-zones-basic-scenarios")
RADON_LICENCE = "CC BY 4.0 — Lähde: Säteilyturvakeskus (STUK)"
RADON_PAGE = "https://stuk.fi/pientalojen-radonpitoisuudet-kunnittain"
RADON_PAGE_PNO = "https://stuk.fi/pientalojen-radonpitoisuudet-postinumeroalueittain"
RADON_FILES = {
    "kunta": ("radon_kunta_2023.xlsx",
              "https://stuk.fi/documents/150192312/157590338/"
              "radontilasto_pientalot_kunta_ja_koko_suomi_2023.xlsx"),
    "postinumero": ("radon_pno_2023.xlsx",
                    "https://stuk.fi/documents/150192312/157590338/"
                    "radontilasto_pientalot_postinumero_2023.xlsx"),
}
RADON_YEAR = "2023"


# ---------------------------------------------------------------- flood

def load_grid(entry):
    """The index's stored grid -> everything the rasteriser needs."""
    return {"w": entry["w"], "s": entry["s"], "e": entry["e"], "n": entry["n"],
            "nx": entry["nx"], "ny": entry["ny"],
            "dlon": entry["dlon"], "dlat": entry["dlat"], "res_m": entry["res_m"],
            "tiles": entry["tiles"]}


def zone_mask(np, code, hazard, tag, grid):
    """The publisher's own classes, rendered flat, stitched back into one boolean array.

    The tiles are not pictures: scripts/fetch_flood.py asks for a flat fill, filtered by CQL to
    an explicit list of the publisher's own `syvsuojluokka` values, with anti-aliasing off. So
    every pixel is 0 or 255 and means exactly "a feature of one of those classes covers this
    pixel". `tag` is a return period ("100", "1000") or "land", the assessed-land mask.
    """
    from PIL import Image
    mask = np.zeros((grid["ny"], grid["nx"]), dtype=bool)
    missing = 0
    for t in grid["tiles"]:
        p = RAW / f"{code}_{hazard}_{tag}_{t['i']:03d}.png"
        if not p.exists():
            missing += 1
            continue
        with Image.open(p) as im:
            a = np.array(im.convert("RGBA"))[:, :, 3] > 0
        if a.shape != (t["h"], t["w"]):
            raise RuntimeError(f"{p.name}: tile is {a.shape}, the index says {(t['h'], t['w'])}")
        mask[t["y"]:t["y"] + t["h"], t["x"]:t["x"] + t["w"]] = a
    return mask, missing


def rasterise(np, rings, grid):
    """Our own polygons on the publisher's grid. Holes are punched, not ignored.

    **Each polygon is rasterised on its own and OR-ed in.** Drawing them all into one image
    would let one polygon's hole erase another polygon's fill wherever the two overlap — which
    is not a hypothetical: SYKE's two Helsinki sea-flood extents ("Helsingin ja Espoon
    meritulvakartta" and "Rannikkoalueen meritulvakartta") cover the same water, and drawing
    them together erased the mapped extent over central Helsinki, so every postal area there
    read "not mapped" while carrying a flood share. A hole belongs to its own polygon and to
    nothing else.

    Polygons whose bounding box misses the grid are skipped, which is what keeps the national
    extent layers cheap to draw onto one small kunta's grid.
    """
    from PIL import Image, ImageDraw
    w, n, dlon, dlat = grid["w"], grid["n"], grid["dlon"], grid["dlat"]
    nx, ny = grid["nx"], grid["ny"]
    acc = np.zeros((ny, nx), dtype=bool)

    def px(ring):
        return [((q[1] - w) / dlon, (n - q[0]) / dlat) for q in ring]

    for poly in rings:
        if not poly:
            continue
        outer = poly[0] if isinstance(poly[0][0], (list, tuple)) else poly
        holes = poly[1:] if isinstance(poly[0][0], (list, tuple)) else []
        if len(outer) < 3:
            continue
        pts = px(outer)
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        if max(xs) < 0 or min(xs) > nx or max(ys) < 0 or min(ys) > ny:
            continue                       # this polygon does not reach the grid at all
        img = Image.new("1", (nx, ny), 0)
        d = ImageDraw.Draw(img)
        d.polygon(pts, fill=1)
        for h in holes:
            if len(h) >= 3:
                d.polygon(px(h), fill=0)
        acc |= np.array(img, dtype=bool)
    return acc


def norm_rings(rings):
    """data/geo stores either [ring, …] or [[outer, hole, …], …]; normalise to the latter."""
    out = []
    for poly in rings or []:
        if not poly:
            continue
        if isinstance(poly[0][0], (list, tuple)):
            out.append([list(r) for r in poly])
        else:
            out.append([list(poly)])
    return out


def geom_rings(geom):
    """GeoJSON geometry -> [[outer, hole, …], …] as [lat, lon] pairs."""
    t, c = geom["type"], geom["coordinates"]
    polys = c if t == "MultiPolygon" else [c]
    return [[[[y, x] for x, y in ring] for ring in poly] for poly in polys]


def ring_area_km2(rings):
    """Spherical polygon area of [[outer, hole, …], …], holes subtracted. Same maths as geo_common."""
    R = 6371.0088
    total = 0.0
    for poly in rings:
        for i, ring in enumerate(poly):
            if len(ring) < 3:
                continue
            s = 0.0
            for j in range(len(ring)):
                lat1, lon1 = math.radians(ring[j][0]), math.radians(ring[j][1])
                lat2, lon2 = math.radians(ring[(j + 1) % len(ring)][0]), math.radians(ring[(j + 1) % len(ring)][1])
                s += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
            a = abs(s * R * R / 2.0)
            total += a if i == 0 else -a
    return total


def flood_for_kunta(np, code, grid_by_hazard, areas, kunta_rings):
    """-> {area key: {indicator: value}} for one kunta's areas, from the rasters.

    **Everything is counted on land.** A sea-flood zone covers the sea as well as the land
    below the flood level — the whole Gulf of Finland renders in the shallowest depth class,
    because it is of course below sea level. Our postal rings are land-clipped but simplified,
    so they overlap the water by a few per cent along an intricate coast, and every one of
    those pixels would otherwise be counted as flooded. The kunta's own land polygon is the
    mask; an area is measured over `area ∩ kunta land`, numerator and denominator alike, so
    the coastline slop cancels instead of inflating the shore.
    """
    out = collections.defaultdict(dict)
    for hazard, entry in grid_by_hazard.items():
        grid = load_grid(entry)
        px_km2 = (grid["res_m"] / 1000.0) ** 2
        land = rasterise(np, kunta_rings, grid)
        # SYKE's own assessed-land mask ('kuiva maa' plus every flood class): the difference
        # between "no flood hazard here" and "nobody has looked", which are not the same thing
        mapped, missing = zone_mask(np, code, hazard, "land", grid)
        if missing:
            raise RuntimeError(f"{code} {hazard} land mask: {missing} tiles missing — "
                               f"re-run scripts/fetch_flood.py")
        mapped &= land
        zones = {}
        for period in ("100", "1000"):
            m, missing = zone_mask(np, code, hazard, period, grid)
            if missing:
                raise RuntimeError(f"{code} {hazard} 1/{period}a: {missing} tiles missing — "
                                   f"re-run scripts/fetch_flood.py")
            zones[period] = m & land
        for key, rings, _unused in areas:
            a = rasterise(np, rings, grid) & land
            if not a.any():
                continue                       # this area does not reach this kunta's land grid
            out[key][f"_grid_km2_{hazard}"] = float(np.count_nonzero(a)) * px_km2
            out[key][f"flood_mapped_{hazard}"] = float(np.count_nonzero(a & mapped)) * px_km2
            for period, m in zones.items():
                out[key][f"flood_{hazard}_{period}"] = float(np.count_nonzero(a & m)) * px_km2
    return out


# ---------------------------------------------------------------- radon

def radon_rows(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    head = [str(h or "").strip() for h in rows[0]]
    return head, rows[1:]


def num(v):
    """A blank is STUK's suppression, not a zero. It stays null all the way to the page."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def kunta_matcher(kunnat):
    """STUK writes kunta names its own way; kuntajako 2026 writes them ours.

    A bilingual kunta is "Maarianhamina - Mariehamn" here and "Maarianhamina" there, so both
    halves of a hyphenated name are accepted, in both languages. What is NOT done is reassigning
    a kunta that no longer exists: Pertunmaa merged out of kuntajako 2026, and its 2023 radon
    figure cannot be folded into Mäntyharju's without the underlying measurements. It is
    reported as unmatched, with the reason, and left out.
    """
    m = {}

    def add(name, code):
        n = (name or "").strip().lower()
        if n:
            m.setdefault(n, code)

    for f in kunnat:
        p = f["properties"]
        code = p["kunta"]
        for name in (p.get("name"), p.get("name_sv")):
            add(name, code)
            for half in (name or "").split(" - "):
                add(half, code)
    return m


def build_radon(kunta_name_to_code):
    out = {"kunta": {}, "postinumero": {}}, {}
    values, meta = out
    for level, (fname, url) in RADON_FILES.items():
        p = EXT / "raw" / fname
        if not p.exists():
            print(f"  ⚠ {p} missing — skipping radon at {level} level "
                  f"(download it from {url})", file=sys.stderr)
            continue
        head, rows = radon_rows(p)
        unmatched = []
        for r in rows:
            if not r or r[0] is None:
                continue
            first = str(r[0]).strip()
            if level == "kunta":
                if first.lower() in ("koko suomi", "hela finland", "whole country"):
                    meta["finland"] = {"radon_n": num(r[1]), "radon_mean": num(r[2]),
                                       "radon_median": num(r[3]), "radon_over200": num(r[4]),
                                       "radon_over300": num(r[5]), "radon_over1000": num(r[6])}
                    continue
                code = kunta_name_to_code.get(first.strip().lower())
                if not code:
                    unmatched.append(first)
                    continue
            else:
                code = first.zfill(5)
            values[level][code] = {
                "radon_n": num(r[1]), "radon_mean": num(r[2]), "radon_median": num(r[3]),
                "radon_over200": num(r[4]), "radon_over300": num(r[5]), "radon_over1000": num(r[6]),
            }
        if unmatched:
            # A name that is not in kuntajako 2026 is a merged or renamed kunta. It is reported
            # here and carried into the payload's meta, never quietly folded into a neighbour.
            meta.setdefault("unmatched", {})[level] = sorted(unmatched)
            print(f"  ⚠ radon {level}: {len(unmatched)} name(s) not in kuntajako 2026 — "
                  f"left out, not reassigned: {', '.join(sorted(unmatched)[:8])}", file=sys.stderr)
        print(f"  · radon {level}: {len(values[level]):,} areas from {fname}")
    return values, meta


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    try:
        import numpy as np
        import PIL  # noqa: F401
    except ImportError:
        print("numpy and pillow are needed here: "
              "python3 -m pip install -r requirements-geo.txt", file=sys.stderr)
        return 1

    idx_path = RAW / "index.json"
    if not idx_path.exists():
        print(f"no {idx_path} — run scripts/fetch_flood.py first", file=sys.stderr)
        return 1
    idx = json.loads(idx_path.read_text(encoding="utf-8"))

    kunnat = json.loads((GEO / "kunnat.geojson").read_text(encoding="utf-8"))["features"]
    postal = json.loads((GEO / "postinumerot.geojson").read_text(encoding="utf-8"))["features"]
    osa = json.loads((GEO / "osa_alueet.geojson").read_text(encoding="utf-8"))["features"]
    by_kunta_postal = collections.defaultdict(list)
    for f in postal:
        by_kunta_postal[f["properties"]["kunta"]].append(f)
    by_kunta_osa = collections.defaultdict(list)
    for f in osa:
        by_kunta_osa[str(f["properties"].get("kunta", ""))].append(f)

    flood_year = ""
    for hazard in ("river", "sea"):
        fp = RAW / f"extent_{hazard}.geojson"
        if fp.exists():
            for ft in json.loads(fp.read_text(encoding="utf-8"))["features"]:
                d_ = (ft["properties"] or {}).get("muutospvm") or ""
                flood_year = max(flood_year, str(d_)[:4])

    codes = set(args.only) if args.only else None
    flood = {"kunta": {}, "postinumero": {}, "osa_alue": {}}
    coverage = {"kunta": [], "postinumero": [], "osa_alue": []}
    done = 0
    for f in kunnat:
        code = f["properties"]["kunta"]
        if codes and code not in codes:
            continue
        entry = idx["kunnat"].get(code)
        if not entry:
            continue                      # not flood-mapped at all — the finding, not a gap
        areas = [(("kunta", code), geom_rings(f["geometry"]), ring_area_km2(geom_rings(f["geometry"])))]
        for a in by_kunta_postal[code]:
            r = geom_rings(a["geometry"])
            areas.append((("postinumero", a["properties"]["nr"]), r, ring_area_km2(r)))
        for a in by_kunta_osa[code]:
            r = geom_rings(a["geometry"])
            areas.append((("osa_alue", str(a["properties"]["code"])), r, ring_area_km2(r)))
        got = flood_for_kunta(np, code, entry, areas, geom_rings(f["geometry"]))
        for (level, key), vals in got.items():
            cur = flood[level].setdefault(key, {})
            for k, v in vals.items():
                cur[k] = cur.get(k, 0.0) + v
        done += 1
        print(f"  · {code} {f['properties']['name']:<22} "
              f"{sum(len(v['tiles']) for v in entry.values()):>3} tiles · {len(areas):>3} areas")

    # km² -> per cent of the area's own land, which is what the page shows.
    # The denominator is the land the raster actually measured, so the numerator and the
    # denominator come out of the same rasterisation and the rounding cancels.
    drop = []
    for level, m in flood.items():
        for key, vals in m.items():
            land = max(vals.get(f"_grid_km2_{h}", 0.0) for h in ("river", "sea"))
            if land <= 0:
                drop.append((level, key))
                continue
            mapped = vals.get("flood_mapped_river", 0.0) + vals.get("flood_mapped_sea", 0.0)
            mapped_pct = round(min(100.0, mapped / land * 100.0), 2)
            out = {"flood_mapped": mapped_pct, "land_km2": round(land, 3)}
            # An area SYKE has not assessed gets NO zone figure. A 0 there would read as "no
            # flood hazard", which is a different and much stronger claim than "nobody looked" —
            # and it is the claim this whole indicator exists to avoid making.
            if mapped_pct > 0:
                for hazard in ("river", "sea"):
                    # a hazard whose own mask never reached this area was not assessed for it
                    if vals.get(f"flood_mapped_{hazard}", 0.0) <= 0:
                        continue
                    for period in ("100", "1000"):
                        v = vals.get(f"flood_{hazard}_{period}")
                        if v is None:
                            continue
                        out[f"flood_{hazard}_{period}"] = round(min(100.0, v / land * 100.0), 2)
            m[key] = out
            coverage[level].append(key)
    for level, key in drop:
        flood[level].pop(key, None)

    print("radon:")
    radon, radon_meta = build_radon(kunta_matcher(kunnat))

    payload = {
        "built": dt.date.today().isoformat(),
        "flood": flood,
        "radon": radon,
        "meta": {
            "flood": {
                "source": "Suomen ympäristökeskus (Syke) — tulvavaaravyöhykkeet, perusskenaariot",
                "licence": FLOOD_LICENCE, "verify_at_source": FLOOD_VERIFY,
                "method": (f"Measured from the publisher's own WMS rendering of its zone polygons at "
                           f"{idx['res_m']:.0f} m per pixel, with this dashboard's own area rings "
                           f"rasterised onto the identical grid. The zones are published as millions "
                           f"of raster-derived polygon fragments (3.4 M and 4.0 M features for the two "
                           f"1/100a layers) and cannot be fetched as vectors at any usable size."),
                "res_m": idx["res_m"],
                "year": flood_year,
                "kunnat_mapped": done,
                "periods": ["1/100a", "1/1000a"],
                "hazards": {"river": "vesistötulva", "sea": "meritulva"},
                "not_mapped": ("SYKE flood-maps designated areas, not the whole country. An area with "
                               "no figure is NOT MAPPED, which is not the same as no flood hazard. "
                               "`flood_mapped` is the share of the area that has been assessed."),
            },
            "radon": {
                "source": f"Säteilyturvakeskus (STUK) — radon pientaloissa {RADON_YEAR}",
                "licence": RADON_LICENCE, "verify_at_source": RADON_PAGE,
                "year": RADON_YEAR,
                "finland": radon_meta.get("finland"),
                "unmatched": radon_meta.get("unmatched", {}),
                "note": ("Measured in detached houses (pientalot) only, so it describes the ground "
                         "and the building stock that sits on it, not a block of flats. A blank in "
                         "STUK's own table is a suppressed figure, not a zero, and stays empty here. "
                         "`unmatched` lists kunnat STUK published in 2023 that no longer exist in "
                         "kuntajako 2026; their figures are left out rather than folded into the "
                         "kunta they merged with."),
            },
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(text, encoding="utf-8")
    print(f"\nwrote {OUT} ({len(text.encode()):,} B)")
    print(f"  flood: {len(flood['kunta'])} kunnat · {len(flood['postinumero'])} postal areas "
          f"· {len(flood['osa_alue'])} osa-alueet")
    print(f"  radon: {len(radon['kunta'])} kunnat · {len(radon['postinumero'])} postal areas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
