#!/usr/bin/env python3
"""Shared geometry helpers: WFS download, simplification, and writing data/geo.

Stdlib only. Simplification prefers **mapshaper** (`npx mapshaper … -simplify keep-shapes`),
which is what the Danish and Swedish editions used and what docs/BUILD_PLAN_FI.md asks for.
When node is not available it falls back to a Visvalingam pass written here, which keeps the
same promise: no ring is ever dropped and no ring goes below four points, so a small island
or a hole cannot vanish. Kauniainen is a hole inside Espoo — losing it would put every
Kauniainen pin in Espoo.

Nothing here invents geometry. Simplification only removes vertices; it never moves a
boundary onto a neighbour, never merges two areas and never fills a hole.
"""
import gzip
import io
import json
import math
import pathlib
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEO = ROOT / "data" / "geo"
RAW = GEO / "raw"
UA = "am-dashboard-fi/1.0 (open-data dashboard; boundary download)"
TIMEOUT = 600
THROTTLE = 1.0
MAX_BYTES = 3_000_000          # the repo's hard ceiling for a processed/dist file


# ---------------------------------------------------------------- download

def fetch(url, dest, force=False):
    """GET to a file, resumable in the sense that an existing download is reused.

    Boundary layers are tens of megabytes and change once a year; re-downloading them on
    every run would be rude. `--force` on the calling script overrides.
    """
    dest = pathlib.Path(dest)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"  · cached {dest.name} ({dest.stat().st_size:,} B)")
        return dest.read_bytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    time.sleep(THROTTLE)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
    dest.write_bytes(body)
    print(f"  · fetched {dest.name} ({len(body):,} B, {time.time() - t0:.1f}s)")
    return body


def wfs_url(base, layer, srs="EPSG:4326", count=None, start=None):
    q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature",
         "typeNames": layer, "srsName": srs, "outputFormat": "application/json"}
    if count is not None:
        q["count"] = str(count)
    if start is not None:
        q["startIndex"] = str(start)
    return base + "?" + urllib.parse.urlencode(q)


def wfs_features(base, layer, dest, page=None, force=False):
    """Every feature of a layer, in EPSG:4326, cached raw on disk.

    `page` turns on WFS paging for the layers big enough to need it (Paavo). The pages are
    cached individually so an interrupted download resumes where it stopped.
    """
    if page is None:
        body = fetch(wfs_url(base, layer), dest, force)
        return json.loads(body)["features"]
    feats, start = [], 0
    while True:
        part = pathlib.Path(str(dest).replace(".json", f".{start:06d}.json"))
        body = fetch(wfs_url(base, layer, count=page, start=start), part, force)
        got = json.loads(body).get("features", [])
        feats.extend(got)
        if len(got) < page:
            break
        start += page
    return feats


# ---------------------------------------------------------------- simplification

def _area2(ring, i):
    """Twice the triangle area at vertex i — the Visvalingam weight."""
    (x0, y0), (x1, y1), (x2, y2) = ring[i - 1], ring[i], ring[i + 1]
    return abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0))


def _visvalingam(ring, keep):
    """Drop the flattest vertices until `keep` remain. Never goes below 4."""
    keep = max(4, int(keep))
    pts = list(ring)
    closed = pts[0] == pts[-1]
    if closed:
        pts = pts[:-1]
    if len(pts) <= keep:
        return ring
    work = pts[:]
    while len(work) > keep:
        w = [(_area2(work, i), i) for i in range(1, len(work) - 1)]
        if not w:
            break
        _, idx = min(w)
        work.pop(idx)
    if closed:
        work.append(work[0])
    return work


def simplify_python(features, pct):
    """Fallback simplifier: keep `pct` of each ring's vertices, floor 4, drop nothing."""
    out = []
    for f in features:
        g = f.get("geometry")
        if not g:
            continue
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        newpolys = []
        for poly in polys:
            rings = []
            for ring in poly:
                r = _visvalingam(ring, len(ring) * pct)
                if len(r) >= 4:
                    rings.append(r)
            if rings:
                newpolys.append(rings)
        if not newpolys:
            continue
        f = dict(f)
        f["geometry"] = ({"type": "Polygon", "coordinates": newpolys[0]} if len(newpolys) == 1
                         else {"type": "MultiPolygon", "coordinates": newpolys})
        out.append(f)
    return out


def _mapshaper():
    if shutil.which("mapshaper"):
        return ["mapshaper"]
    if shutil.which("npx"):
        return ["npx", "--yes", "mapshaper@0.6.102"]
    return None


def simplify_mapshaper(features, pct, tmpdir):
    """`-simplify <pct>% keep-shapes` — the documented route. Returns None if node is absent."""
    cmd = _mapshaper()
    if not cmd:
        return None
    tmpdir = pathlib.Path(tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)
    src, dst = tmpdir / "in.json", tmpdir / "out.json"
    src.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    r = subprocess.run(cmd + [str(src), "-simplify", f"{pct * 100:.4f}%", "keep-shapes",
                               "-o", "format=geojson", "precision=0.00001", str(dst)],
                       capture_output=True, text=True)
    if r.returncode or not dst.exists():
        print(f"  ⚠ mapshaper failed ({r.returncode}): {(r.stderr or r.stdout).strip()[:200]}")
        return None
    return json.loads(dst.read_text(encoding="utf-8")).get("features", [])


def simplify(features, budget=MAX_BYTES, tmpdir=None, label=""):
    """Simplify until the written size fits the budget. Returns (features, pct, tool).

    The percentage is searched, not guessed: 100 % first, then progressively fewer
    vertices, stopping at the first pass that fits. What was used is printed and recorded
    in ATTRIBUTION.txt, so the simplification is part of the provenance, not a secret.
    """
    tmpdir = pathlib.Path(tmpdir or (RAW / "_tmp"))
    for pct in (1.0, 0.5, 0.3, 0.2, 0.12, 0.08, 0.05, 0.03, 0.02, 0.012, 0.008):
        got, tool = None, "mapshaper"
        if pct < 1.0:
            got = simplify_mapshaper(features, pct, tmpdir)
            if got is None:
                got, tool = simplify_python(features, pct), "visvalingam (python fallback)"
        else:
            got, tool = features, "none"
        n = len(json.dumps({"type": "FeatureCollection", "features": got},
                           ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        print(f"  · {label} simplify {pct * 100:>6.2f}% ({tool}) → {n:,} B")
        if n <= budget:
            return got, pct, tool
    return got, pct, tool


# ---------------------------------------------------------------- rings for the page

def rings_of(geom, nd=5):
    """GeoJSON geometry -> [[[lat, lon], …], …], outer rings and holes alike, lat first.

    The page draws [lat, lon] pairs; GeoJSON stores [lon, lat]. Swapping them here, once,
    is the only place the order changes. Holes are kept: a ring list that loses its holes
    puts Kauniainen inside Espoo.
    """
    if not geom:
        return []
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    out = []
    for poly in polys:
        for ring in poly:
            pts = [[round(y, nd), round(x, nd)] for x, y in ring]
            if len(pts) >= 4:
                out.append(pts)
    return out


def bbox_of(rings):
    s, w, n, e = 90.0, 180.0, -90.0, -180.0
    for r in rings:
        for lat, lon in r:
            s, n = min(s, lat), max(n, lat)
            w, e = min(w, lon), max(e, lon)
    return [round(s, 5), round(w, 5), round(n, 5), round(e, 5)]


def centroid_of(rings):
    """Area-weighted centroid of the largest ring — good enough to place a label."""
    if not rings:
        return None
    big = max(rings, key=len)
    a = cx = cy = 0.0
    for i in range(len(big) - 1):
        y0, x0 = big[i]
        y1, x1 = big[i + 1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(a) < 1e-12:
        return [round(sum(p[0] for p in big) / len(big), 5), round(sum(p[1] for p in big) / len(big), 5)]
    a *= 0.5
    return [round(cy / (6 * a), 5), round(cx / (6 * a), 5)]


def ring_area_km2(rings):
    """Spherical polygon area of the outer rings, minus the holes, in km².

    Used only as a sanity check (Finland should come out near 337 800 km²) and for the
    area shares batch 2 needs. Ring winding decides sign, so holes subtract themselves.
    """
    R = 6371.0088
    total = 0.0
    for ring in rings:
        s = 0.0
        for i in range(len(ring) - 1):
            lat1, lon1 = math.radians(ring[i][0]), math.radians(ring[i][1])
            lat2, lon2 = math.radians(ring[i + 1][0]), math.radians(ring[i + 1][1])
            s += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
        total += abs(s * R * R / 2.0)
    return total


# ---------------------------------------------------------------- writing

def write_geojson(path, features, meta):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"type": "FeatureCollection", "meta": meta, "features": features}
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n = path.stat().st_size
    flag = "" if n <= MAX_BYTES else f"   ⚠ OVER the {MAX_BYTES:,} B ceiling"
    print(f"wrote {path.relative_to(ROOT)} ({n:,} B · {len(features)} features){flag}")
    return n


def attribution(lines):
    p = GEO / "ATTRIBUTION.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {p.relative_to(ROOT)}")
