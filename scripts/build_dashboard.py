#!/usr/bin/env python3
"""Assemble the self-contained dashboard: dist/index.html.

Inlines src/style.css, vendored Leaflet, src/testprop.js, src/app.js and the data
(data/processed/makro.json + osa_alue.json) into the
template src/index.html — one file that opens from disk or GitHub Pages.

Usage: python scripts/build_dashboard.py [--data path/to/makro.json] [--out dist/index.html]
"""
import argparse
import datetime as dt
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PROC = ROOT / "data" / "processed"


def load(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def kunnat_lookup(out_dir: pathlib.Path):
    """dist/geo/kunnat_lookup.json — simplified kunta rings for the test-property pin.

    A postal code can cross a kunta border, so the pin asks these polygons which kunta a
    point is really in. Holes are kept: Kauniainen is a hole in Espoo, and dropping it
    would put every Kauniainen pin in Espoo. The page fetches this lazily, the first
    time a pin is dropped.
    """
    src = ROOT / "data" / "geo" / "kunnat.geojson"
    if not src.exists():
        print("  ⚠ data/geo/kunnat.geojson missing — no kunta lookup (pins fall back to the postal code)")
        return
    gj = load(src)
    try:
        from shapely.geometry import mapping, shape
        simplify = 0.0005
    except ImportError:
        shape = None
        simplify = None
        print("  · shapely not installed — kunta rings shipped unsimplified")
    rows = []
    for f in gj.get("features", []):
        props = f.get("properties") or {}
        geom = f.get("geometry")
        if not geom:
            continue
        if shape is not None:
            g = shape(geom).simplify(simplify, preserve_topology=True)
            if not g.is_empty:
                geom = mapping(g)
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        out, s_, w_, n_, e_ = [], 90.0, 180.0, -90.0, -180.0
        for poly in polys:
            rings = []
            for ring in poly:                      # [outer, hole, hole, ...]
                pts = [[round(y, 5), round(x, 5)] for x, y in ring]
                if len(pts) >= 4:
                    rings.append(pts)
            if not rings:
                continue
            for lat, lon in rings[0]:
                s_, n_ = min(s_, lat), max(n_, lat)
                w_, e_ = min(w_, lon), max(e_, lon)
            out.append(rings)
        if out:
            rows.append({"code": props.get("kunta"), "name": props.get("name"),
                         "bb": [s_, w_, n_, e_], "polys": out})
    gd = out_dir / "geo"
    gd.mkdir(parents=True, exist_ok=True)
    dest = gd / "kunnat_lookup.json"
    dest.write_text(json.dumps({"built": dt.date.today().isoformat(), "source": "Tilastokeskus kuntajako, simplified",
                                "kunnat": rows}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {dest} ({dest.stat().st_size/1024:.0f} kB) · {len(rows)} kunnat"
          + (f" · simplified {simplify}" if simplify else " · not simplified"))


def check_js(paths):
    """Refuse to inline JavaScript that does not parse.

    Without this `make build` happily writes a dist/index.html whose app.js has a syntax
    error — the page then renders nothing and the build still says it succeeded. node is
    optional: if it is not installed the check is skipped rather than failing the build.
    """
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        print("  · node not found — skipping the JavaScript syntax check")
        return
    for p in paths:
        if not p.exists():
            continue
        r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"✗ {p.name} does not parse:\n{(r.stderr or r.stdout).strip()}")
    print(f"  · JavaScript parses ({', '.join(p.name for p in paths if p.exists())})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(PROC / "makro.json"))
    ap.add_argument("--osa", default=str(PROC / "osa_alue.json"))
    ap.add_argument("--out", default=str(ROOT / "dist" / "index.html"))
    args = ap.parse_args()

    check_js([SRC / "app.js", SRC / "testprop.js"])
    makro = load(pathlib.Path(args.data)) or {}
    osa = load(pathlib.Path(args.osa))
    micro_idx = load(PROC / "micro" / "index.json")
    infra = load(ROOT / "data" / "geo" / "infra_projects.geojson")
    infra_index = load(PROC / "infra_index.json")
    public_index = load(PROC / "public_index.json")
    services_index = load(PROC / "services" / "index.json")
    built = (makro.get("meta") or {}).get("built") or dt.date.today().isoformat()
    data = {
        "meta": makro.get("meta", {"built": built, "sources": [], "attribution": []}),
        "indicators": makro.get("indicators", []),
        "municipalities": makro.get("municipalities", []),
        "areas": makro.get("areas", []),
        "national": makro.get("national"),
        # never in this public repo — the key stays so the page code needs no branch
        "portfolio": None,
        "osa": osa,
        "micro": micro_idx,
        # infrastructure overlay: only the features meant for the map (scripts/build_infra.py, docs/INFRA.md)
        # every project: the map layer filters on `map`, the Pipeline table lists them all
        "infra": {"features": (infra or {}).get("features", []), "meta": (infra or {}).get("meta")} if infra else None,
        "infra_index": (infra_index or {}).get("areas") if infra_index else None,
        # public buildings: counts per area inline, the buildings themselves loaded on demand (dist/public/<kunta>.json)
        # public buildings: counts per area inline; the school aggregates ride along in the same areas
        # dict (scripts/build_schools.py), while the school records load on demand from schools.json
        "public": {"areas": public_index["areas"], "built": public_index["built"], "kunnat": public_index["kunnat"],
                   "recent_years": public_index["recent_years"],
                   "schools": public_index.get("schools")} if public_index else None,
        # services: the index only (as-of, vocabulary, per-kunta counts + bbox). The points
        # themselves load on demand from dist/services/<kunta>.json for whatever is in view.
        "services": services_index,
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</script", "<\\/script")
    html = (SRC / "index.html").read_text(encoding="utf-8")
    html = (html.replace("{{LEAFLET_CSS}}", (SRC / "vendor" / "leaflet.css").read_text(encoding="utf-8"))
                .replace("{{APP_CSS}}", (SRC / "style.css").read_text(encoding="utf-8"))
                .replace("{{LEAFLET_JS}}", (SRC / "vendor" / "leaflet.js").read_text(encoding="utf-8"))
                .replace("{{TESTPROP_JS}}", (SRC / "testprop.js").read_text(encoding="utf-8"))
                .replace("{{APP_JS}}", (SRC / "app.js").read_text(encoding="utf-8"))
                .replace("{{DATA}}", payload)
                .replace("{{BUILT}}", built))
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    # the infrastructure layer is inlined in the page, and also served as files so it can be reused
    for src in (ROOT / "data" / "geo" / "infra_projects.geojson", PROC / "infra_index.json",
                PROC / "public_index.json", PROC / "schools.json", PROC / "monthly.json", PROC / "hist.json"):
        if src.exists():
            import shutil
            shutil.copy(src, out.parent / src.name)
            print(f"copied {src.name} → {out.parent}")
    # building-level files are loaded on demand by the page (dist/micro/<kunta>.json)
    pub = PROC / "public"
    if pub.exists():
        import shutil
        pd_ = out.parent / "public"; pd_.mkdir(exist_ok=True)
        for f in pub.glob("*.json"):
            shutil.copy(f, pd_ / f.name)
        print(f"copied {len(list(pd_.glob('*.json')))} public-building files → {pd_}")
    # the per-kunta lazy payload: detailed postal rings and their history, fetched by the page
    # the first time a kunta is opened (scripts/build_makro.py writes them)
    ad = PROC / "area"
    if ad.exists():
        import shutil
        dd = out.parent / "area"
        dd.mkdir(exist_ok=True)
        for f in dd.glob("*.json"):
            f.unlink()
        for f in ad.glob("*.json"):
            shutil.copy(f, dd / f.name)
        files = list(dd.glob("*.json"))
        big = max((f.stat().st_size for f in files), default=0)
        print(f"copied {len(files)} per-kunta area files → {dd} (largest {big/1024:.0f} kB)")
    srv = PROC / "services"
    if srv.exists():
        import shutil
        sd = out.parent / "services"; sd.mkdir(exist_ok=True)
        for f in srv.glob("*.json"):
            shutil.copy(f, sd / f.name)
        print(f"copied {len(list(sd.glob('*.json')))} services files → {sd}")
    if micro_idx:
        import shutil
        md = out.parent / "micro"; md.mkdir(exist_ok=True)
        for f in (PROC / "micro").glob("*.json"):
            shutil.copy(f, md / f.name)
        print(f"copied {len(list(md.glob('*.json')))} micro files → {md}")
    kunnat_lookup(out.parent)
    n = out.stat().st_size
    print(f"wrote {out} ({n/1e6:.1f} MB) · {len(data['municipalities'])} kunnat · {len(data['areas'])} areas")
    # The repo's ceiling. It is a hard failure, not a warning: a page that creeps past it is
    # slow for everyone on a phone, and the fix is always to move something to a lazy payload.
    CEILING = 3_000_000
    if n > CEILING:
        raise SystemExit(f"✗ {out.name} is {n:,} B, over the {CEILING:,} B ceiling — move a series "
                         f"into a lazy payload (see scripts/build_makro.py)")
    for q in sorted(out.parent.glob("*.json")) + sorted((out.parent / "area").glob("*.json")):
        if q.stat().st_size > CEILING:
            raise SystemExit(f"✗ {q.name} is {q.stat().st_size:,} B, over the {CEILING:,} B ceiling")


if __name__ == "__main__":
    main()
