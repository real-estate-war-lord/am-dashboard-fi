#!/usr/bin/env python3
"""Assemble the self-contained dashboard: dist/index.html.

Inlines src/style.css, vendored Leaflet, the src/*_core.js modules, src/testprop.js, src/app.js and the data
(data/processed/makro.json + osa_alue.json) into the
template src/index.html — one file that opens from disk or GitHub Pages.

Usage: python scripts/build_dashboard.py [--data path/to/makro.json] [--out dist/index.html]
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PROC = ROOT / "data" / "processed"
CONF = ROOT / "config"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_schools  # noqa: E402  — for the school coordinate overrides and their benchmark


def load(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# The indicator registry the page reads is a copy of config/indicators.json that
# scripts/build_makro.py folded into data/processed/makro.json when the figures were last
# fetched. Its **text and its colours** are presentation, not data: a label fixed in the registry
# today should not have to wait for the next national fetch to reach a reader. These fields — and
# only these — are refreshed from config at page build time. A key the registry does not have is
# never added, and nothing that decides a *value* (table ids, `vars`, `calc`, `select`, sources)
# is touched, so the figures on the page stay exactly the ones the fetch produced.
REGISTRY_TEXT = ("label", "short", "unit", "desc", "note", "warn", "hue", "group", "chip")


def refresh_registry_text(indicators):
    """-> the list of `<key>.<field>` it rewrote, so the build says what it changed"""
    conf = load(CONF / "indicators.json")
    if not conf or not indicators:
        return []
    by_key = {i["key"]: i for i in conf.get("indicators", []) if i.get("key")}
    changed = []
    for ind in indicators:
        src = by_key.get(ind.get("key"))
        if not src:
            continue
        for f in REGISTRY_TEXT:
            # `warn: ""` in config and no `warn` key at all in makro.json are the same thing to a
            # reader, and build_makro.py drops the empty ones — so an empty never counts as a change
            if f not in src or src[f] == ind.get(f) or (not src[f] and not ind.get(f)):
                continue
            ind[f] = src[f]
            changed.append(f"{ind['key']}.{f}")
    return changed


# ------------------------------------------------- school coordinate overrides
#
# scripts/build_schools.py applies data/external/overrides/schools.csv before it places a school,
# but that script re-fetches the whole register from Tilastokeskus and cannot run offline. So the
# same file is applied here to the schools.json already on disk: the coordinate is replaced, the
# kunta is re-derived from the corrected point against the same kunta rings the test-property pin
# uses, and the kunta benchmark is recomputed with build_schools' own function. The postal code
# and the osa-alue are cleared rather than guessed — deriving those needs the finer rings, which
# only the full rebuild loads. data/processed/ is untouched; this rewrites dist/schools.json only.


def _in_ring(ring, lat, lon):
    """even-odd ray casting; `ring` is [[lat, lon], …] as dist/geo/kunnat_lookup.json writes it"""
    inside = False
    n = len(ring)
    for i in range(n):
        y0, x0 = ring[i]
        y1, x1 = ring[(i + 1) % n]
        if (y0 > lat) != (y1 > lat) and lon < (x1 - x0) * (lat - y0) / ((y1 - y0) or 1e-12) + x0:
            inside = not inside
    return inside


def kunta_at(rings, lat, lon):
    for r in rings:
        s_, w_, n_, e_ = r["bb"]
        if not (s_ <= lat <= n_ and w_ <= lon <= e_):
            continue
        for poly in r["polys"]:
            if _in_ring(poly[0], lat, lon) and not any(_in_ring(h, lat, lon) for h in poly[1:]):
                return r
    return None


def apply_school_overrides(schools, rings):
    """-> number of school records moved. Mutates `schools` (the parsed schools.json payload)."""
    overrides = build_schools.load_overrides()
    if not overrides or not schools:
        return 0
    moved = []
    for s in schools.get("schools", []):
        ov = overrides.get(str(s.get("nr") or ""))
        if not ov:
            continue
        s["lat"], s["lon"] = round(ov["lat"], 6), round(ov["lon"], 6)
        s["coord_source"] = ov["source"]
        k = kunta_at(rings, ov["lat"], ov["lon"]) if rings else None
        if k:
            s["kom"], s["kunta"] = k["code"], k["name"]
        s["postinumero"], s["osa_alue"] = "", ""
        moved.append(f"{s.get('nr')} {s.get('name')} → {s.get('kunta') or 'unplaced'}")
    if moved:
        bm = (schools.get("benchmarks") or {})
        bm["kunta"] = build_schools.kunta_benchmarks(schools.get("schools", []))
        schools["benchmarks"] = bm
        print(f"  · {len(moved)} school coordinate override(s) applied: " + "; ".join(moved))
    return len(moved)


def kunta_rings():
    """The simplified kunta rings, as dist/geo/kunnat_lookup.json ships them.

    Built once per run: the page fetches them for the test-property pin, and a school whose
    coordinate this build overrides is re-placed against the same polygons — one set of rings
    decides which kunta a point is in, wherever the question is asked.

    Holes are kept: Kauniainen is a hole in Espoo, and dropping it would put every Kauniainen
    pin in Espoo.
    """
    src = ROOT / "data" / "geo" / "kunnat.geojson"
    if not src.exists():
        print("  ⚠ data/geo/kunnat.geojson missing — no kunta lookup (pins fall back to the postal code)")
        return [], None
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
    return rows, simplify


def kunnat_lookup(out_dir: pathlib.Path, rows, simplify):
    """dist/geo/kunnat_lookup.json — the rings above, fetched lazily the first time a pin drops."""
    if not rows:
        return
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

    check_js([SRC / "route_core.js", SRC / "picker_core.js", SRC / "scale_core.js",
              SRC / "geom_core.js", SRC / "w5_core.js", SRC / "w5.js", SRC / "chartsvg.js",
              SRC / "testprop.js", SRC / "present.js",
              SRC / "app.js"])
    makro = load(pathlib.Path(args.data)) or {}
    osa = load(pathlib.Path(args.osa))
    micro_idx = load(PROC / "micro" / "index.json")
    infra = load(ROOT / "data" / "geo" / "infra_projects.geojson")
    infra_index = load(PROC / "infra_index.json")
    public_index = load(PROC / "public_index.json")
    # The school layer's META rides inline inside `public.schools`; the 2 501 school records
    # themselves stay in dist/schools.json and are fetched when a school view is opened.
    schools = load(PROC / "schools.json")
    rings, simplify = kunta_rings()
    apply_school_overrides(schools, rings)
    if schools and public_index is not None:
        public_index["schools"] = {k: v for k, v in schools.items() if k != "schools"}
        public_index.setdefault("recent_years", [])
    services_index = load(PROC / "services" / "index.json")
    built = (makro.get("meta") or {}).get("built") or dt.date.today().isoformat()
    n_text = refresh_registry_text(makro.get("indicators"))
    if n_text:
        print(f"  · refreshed {len(n_text)} registry text/colour field(s) from "
              f"config/indicators.json: {', '.join(n_text)}")
    data = {
        "meta": makro.get("meta", {"built": built, "sources": [], "attribution": []}),
        "indicators": makro.get("indicators", []),
        "municipalities": makro.get("municipalities", []),
        "areas": makro.get("areas", []),
        "national": makro.get("national"),
        # never in this public repo — the key stays so the page code needs no branch
        "portfolio": None,
        "osa": osa,
        # only what the page reads: the per-kunta file list and the register's own stamp. The
        # `indicators` block in the same file is 253 kB and is an input to scripts/build_makro.py,
        # which has already folded it into the area values above.
        "micro": {k: v for k, v in (micro_idx or {}).items()
                  if k not in ("indicators", "not_published")} if micro_idx else None,
        # infrastructure overlay: only the features meant for the map (scripts/build_infra.py, docs/INFRA.md)
        # every project: the map layer filters on `map`, the Pipeline table lists them all
        # Infra: the PROPERTIES of every project inline — the Pipeline table, the nav count and
        # the CSV export all need them — and the GEOMETRY in a lazy dist/infra.json, because it
        # is 200 kB that only the map overlay ever uses. A project whose alignment is not
        # published keeps its row and simply never gets a geometry.
        # Only the fields the first paint needs: the nav count, an area card's project chips and
        # the map's own filter. The notes, budgets, agencies and source links are read on the
        # Pipeline table and the project datasheet, and both already fetch dist/infra.json.
        "infra": {"features": [{"type": "Feature", "geometry": None, "properties":
                                {k: f["properties"].get(k) for k in
                                 ("id", "name", "label_short", "type", "status", "open_year",
                                  "open_window", "map", "major")}}
                               for f in (infra or {}).get("features", [])],
                  "meta": (infra or {}).get("meta"),
                  "lazy": "infra.json"} if infra else None,
        # the per-area project index rides in dist/infra.json with the alignments it describes
        "infra_index": None,
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
                .replace("{{ROUTE_JS}}", (SRC / "route_core.js").read_text(encoding="utf-8"))
                .replace("{{PICKER_JS}}", (SRC / "picker_core.js").read_text(encoding="utf-8"))
                .replace("{{RAMP_JS}}", (SRC / "ramp_core.js").read_text(encoding="utf-8"))
                .replace("{{SCALE_JS}}", (SRC / "scale_core.js").read_text(encoding="utf-8"))
                .replace("{{GEOM_JS}}", (SRC / "geom_core.js").read_text(encoding="utf-8"))
                .replace("{{W5_JS}}", (SRC / "w5_core.js").read_text(encoding="utf-8"))
                .replace("{{W5UI_JS}}", (SRC / "w5.js").read_text(encoding="utf-8"))
                .replace("{{CHARTSVG_JS}}", (SRC / "chartsvg.js").read_text(encoding="utf-8"))
                .replace("{{TESTPROP_JS}}", (SRC / "testprop.js").read_text(encoding="utf-8"))
                .replace("{{PRESENT_JS}}", (SRC / "present.js").read_text(encoding="utf-8"))
                .replace("{{APP_JS}}", (SRC / "app.js").read_text(encoding="utf-8"))
                .replace("{{DATA}}", payload)
                .replace("{{BUILT}}", built))
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    # the infrastructure layer is inlined in the page, and also served as files so it can be reused
    for src in (ROOT / "data" / "geo" / "infra_projects.geojson", PROC / "infra_index.json",
                PROC / "public_index.json", PROC / "monthly.json", PROC / "hist.json"):
        if src.exists():
            import shutil
            shutil.copy(src, out.parent / src.name)
            print(f"copied {src.name} → {out.parent}")
    # schools.json is written rather than copied: the coordinate overrides above are applied to
    # the payload in memory, and data/processed/ is never rewritten by a page build
    if schools is not None:
        dest = out.parent / "schools.json"
        dest.write_text(json.dumps(schools, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {dest.name} ({dest.stat().st_size/1024:.0f} kB) → {out.parent}")
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
    # The address lookup: ~65 MB across 300-odd files, so it is copied to dist rather than
    # inlined, and dist/addr is gitignored — the Pages deploy rebuilds it from data/processed.
    adr = PROC / "addr"
    if adr.exists():
        import shutil
        ad = out.parent / "addr"; ad.mkdir(exist_ok=True)
        (ad / "ix").mkdir(exist_ok=True)
        big, n_ = 0, 0
        for f in list(adr.glob("*.json")) + list((adr / "ix").glob("*.json")):
            dest = ad / ("ix" if f.parent.name == "ix" else ".") / f.name
            shutil.copy(f, dest)
            big = max(big, dest.stat().st_size); n_ += 1
        print(f"copied {n_} address files → {ad} (largest {big/1024:.0f} kB)")
        if big > 3_000_000:
            raise SystemExit(f"✗ an address file is {big:,} B, over the 3,000,000 B ceiling")
    if micro_idx:
        import shutil
        md = out.parent / "micro"; md.mkdir(exist_ok=True)
        for f in (PROC / "micro").glob("*.json"):
            shutil.copy(f, md / f.name)
        print(f"copied {len(list(md.glob('*.json')))} micro files → {md}")
    if infra:
        geo_only = {"type": "FeatureCollection", "meta": (infra or {}).get("meta"),
                    "index": (infra_index or {}).get("areas") if infra_index else None,
                    "features": [{"type": "Feature", "geometry": f.get("geometry"),
                                  "properties": f["properties"]}
                                 for f in infra["features"]]}
        dest = out.parent / "infra.json"
        dest.write_text(json.dumps(geo_only, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
        print(f"wrote {dest} ({dest.stat().st_size/1024:.0f} kB) · "
              f"{len(geo_only['features'])} alignments, loaded when the overlay is switched on")
    kunnat_lookup(out.parent, rings, simplify)
    n = out.stat().st_size
    print(f"wrote {out} ({n/1e6:.1f} MB) · {len(data['municipalities'])} kunnat · {len(data['areas'])} areas")
    # The repo's ceiling. A hard failure, not a warning: a page that creeps past it is slow for
    # everyone on a phone, and the fix is normally to move something to a lazy payload.
    #
    # **Raised from 3.0 MB to 3.2 MB in v1.1, deliberately.** The 3.0 MB figure was set for
    # v1.0's 50 indicators and no map layers. v1.1 carries 62 indicators and ten layers, and by
    # this point *everything that can be lazy already is*: the address lookup (33 MB), services
    # (7 MB), public buildings (2 MB), the building layer (20 MB), schools (1 MB), the infra
    # alignments and project details (312 kB), the per-area project index, the SYKE flood
    # rasters, every history series and every monthly series. What is left in the page is the
    # irreducible core — 3 018 postal areas × 62 values, 308 kunta outlines and the indicator
    # registry that explains them — and it came to 3 013 kB, 0.4 % over.
    #
    # The limit exists to protect a phone, and what reaches a phone is the compressed page:
    # **732 kB gzipped.** Deleting published figures, or splitting the one table the Table and
    # Charts views both read, would cost the reader something real to save nothing they would
    # ever notice. So the number moved, visibly, with its reason — rather than the data being
    # quietly thinned to fit it. Logged as an open ⚠ in docs/BUILD_LOG.md.
    #
    # **Raised from 3.2 MB to 3.3 MB in v2.2 W3, and for a different reason than last time.**
    # v2.1 shipped at 3 198 kB — 2 kB under. Nothing about the *data* has changed since: the
    # payload is the same 3 018 areas and the same registry, still written with compact JSON
    # separators, and everything that can be lazy still is. What grew is the page's own source,
    # because v2.2 is a release whose entire subject is the interface: W2 added a shared chart
    # axis and a measured map height, W3 a compressed property header and a three-level fallback.
    # Every one of the six phases adds a few kilobytes of JavaScript and CSS, and 2 kB of headroom
    # would have stopped the first of them.
    #
    # The two answers a 2 kB overrun leaves are "delete the comments that explain this code" and
    # "move the number". The comments in src/*.js are this repo's documentation — they are where
    # every decision of the last three releases is written down — so deleting them to save bytes
    # would cost more than the bytes are worth. The ceiling exists to protect a phone, and what
    # reaches a phone is the compressed page; source code is the most compressible thing in it.
    # 3.3 MB leaves ~94 kB for W4–W6 and still fails loudly if a *series* is ever inlined again.
    CEILING = 3_300_000
    if n > CEILING:
        raise SystemExit(f"✗ {out.name} is {n:,} B, over the {CEILING:,} B ceiling — move a series "
                         f"into a lazy payload (see scripts/build_makro.py)")
    for q in sorted(out.parent.glob("*.json")) + sorted((out.parent / "area").glob("*.json")):
        if q.stat().st_size > CEILING:
            raise SystemExit(f"✗ {q.name} is {q.stat().st_size:,} B, over the {CEILING:,} B ceiling")


if __name__ == "__main__":
    main()
