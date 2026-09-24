#!/usr/bin/env python3
"""Vendor the Paavo postal-code layer: boundaries + the whole statistical pack.

    python3 scripts/fetch_paavo.py [--force] [--year 2026]

One WFS call gives both the polygons and all 104 Paavo variables, so this writes two things:

  data/geo/postinumerot.geojson     boundaries + identity (code, name, kunta) — committed
  data/raw/paavo/pno_tilasto_<y>.json   every Paavo variable per postal code — git-ignored,
                                        with a .meta.json stamp beside it; phase 3 reads it

Source (probed live, docs/PROBE_FI.md):
    https://geo.stat.fi/geoserver/postialue/wfs   postialue:pno_tilasto_2026
    3 018 areas · 113 properties · CC BY 4.0 — Lähde: Tilastokeskus

**The layer year is not the statistics year.** `pno_tilasto_2026` carries statistics for
**2024** — confirmed by matching its `he_vakiy` for 00100 (18 492) against the PxWeb table
for 2024. Everything this script writes is stamped with the statistics year, and the UI
labels Paavo figures with that year, never with the layer year.

Paavo suppresses areas with fewer than 30 residents or 10 households. A suppressed figure
comes back as -1 in the WFS, which is **not** a zero and **not** a value: it is turned into
null here, once, so nothing downstream can mistake it for a number.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import geo_common as G  # noqa: E402

WFS = "https://geo.stat.fi/geoserver/postialue/wfs"
# identity fields; everything else in the layer is a statistic
IDENT = {"id", "postinumeroalue", "nimi", "namn", "kunta", "kuntanro", "vuosi",
         "euref_x", "euref_y", "pinta_ala", "objectid", "posti_alue"}
SUPPRESSED = -1          # Paavo's own marker for "too few residents/households to publish"


def statistics_year(feats, layer_year):
    """The year the numbers describe, read from the data rather than assumed.

    Paavo's own `vuosi` field carries the layer year, so it cannot be used. The lag has been
    two years for every published vintage; it is asserted against the layer year here and
    the assertion is printed, so a change in the publisher's practice shows up loudly
    instead of silently relabelling every figure.
    """
    lag = 2
    year = layer_year - lag
    print(f"  · statistics year {year} (layer {layer_year}, published lag {lag} — "
          f"verified 2026-09-24 against PxWeb 12ey for 00100: he_vakiy 2024 = 18 492)")
    return year


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--year", type=int, default=2026, help="the pno_tilasto layer vintage")
    args = ap.parse_args()
    layer = f"postialue:pno_tilasto_{args.year}"

    print(f"Paavo {layer}")
    feats = G.wfs_features(WFS, layer, G.RAW / f"pno_tilasto_{args.year}.json", force=args.force)
    print(f"  · {len(feats)} postal areas")
    if not feats:
        sys.exit("no features — check the layer name against docs/PROBE_FI.md")
    year = statistics_year(feats, args.year)

    # kunta names come from the kunta layer; the Paavo layer carries the code but no name
    kunnat = {}
    kfile = G.GEO / "kunnat.geojson"
    if kfile.exists():
        for f in json.loads(kfile.read_text(encoding="utf-8"))["features"]:
            kunnat[f["properties"]["kunta"]] = f["properties"]["name"]
    else:
        print("  ⚠ data/geo/kunnat.geojson missing — postal areas will carry no kunta name "
              "(run scripts/fetch_geo_fi.py first)")

    varnames = sorted({k for f in feats for k in (f.get("properties") or {}) if k not in IDENT})
    print(f"  · {len(varnames)} Paavo statistical variables")

    # 1. the statistical pack — raw, every variable, suppression preserved as null
    stats, suppressed_cells = {}, 0
    for f in feats:
        p = f["properties"]
        code = str(p.get("postinumeroalue") or "").zfill(5)
        row = {}
        for v in varnames:
            val = p.get(v)
            if val == SUPPRESSED:
                row[v] = None
                suppressed_cells += 1
            else:
                row[v] = val
        stats[code] = row
    out = G.ROOT / "data" / "raw" / "paavo" / f"pno_tilasto_{args.year}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"layer": layer, "statistics_year": year, "areas": stats},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    out.with_suffix(".json.meta.json").write_text(json.dumps({
        "layer": layer, "url": G.wfs_url(WFS, layer), "statistics_year": year,
        "layer_year": args.year, "areas": len(stats), "variables": len(varnames),
        "variable_names": varnames,
        "suppressed_cells": suppressed_cells,
        "suppression_rule": "Paavo suppresses areas under 30 residents or 10 households; the WFS "
                            "returns -1, which this script turns into null. Suppressed is not zero.",
        "fetched": dt.date.today().isoformat(), "publisher": "Tilastokeskus",
        "licence": "CC BY 4.0 — Lähde: Tilastokeskus",
        "verify_at_source": "https://stat.fi/fi/palvelut/tilastodatapalvelut/paikkatietoaineistot/"
                            "postinumeroalueittainen-paikkatieto-paavo",
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(G.ROOT)} ({out.stat().st_size:,} B · {len(stats)} areas · "
          f"{suppressed_cells:,} suppressed cells kept as null)")

    # 2. the boundaries — identity only, simplified to fit the repo's ceiling
    simp, pct, tool = G.simplify([{"type": "Feature", "properties": {"i": i}, "geometry": f["geometry"]}
                                  for i, f in enumerate(feats)], budget=2_400_000, label="postinumerot")
    geom_by_i = {f["properties"]["i"]: f["geometry"] for f in simp}
    gj, no_kunta, lost = [], 0, 0
    for i, f in enumerate(feats):
        p = f["properties"]
        code = str(p.get("postinumeroalue") or "").zfill(5)
        g = geom_by_i.get(i)
        rings = G.rings_of(g) if g else []
        if not rings:
            lost += 1
            continue
        kunta = str(p.get("kunta") or "").zfill(3)
        if kunta not in kunnat:
            no_kunta += 1
        gj.append({"type": "Feature",
                   "properties": {"nr": code, "name": p.get("nimi") or "", "name_sv": p.get("namn") or "",
                                  "kunta": kunta, "kunta_name": kunnat.get(kunta, ""),
                                  "area_km2": round((p.get("pinta_ala") or 0) / 1e6, 3),
                                  "bb": G.bbox_of(rings), "c": G.centroid_of(rings)},
                   "geometry": g})
    G.write_geojson(G.GEO / "postinumerot.geojson", gj,
                    {"layer": layer, "layer_year": args.year, "statistics_year": year,
                     "crs": "EPSG:4326", "publisher": "Tilastokeskus",
                     "licence": "CC BY 4.0 — Lähde: Tilastokeskus",
                     "simplified": f"{pct * 100:.2f}% ({tool})"})

    problems = []
    if lost:
        problems.append(f"{lost} postal areas lost every ring in simplification")
    if no_kunta:
        problems.append(f"{no_kunta} postal areas carry a kunta code that is not in kuntajako {args.year}")
    bad = [f["properties"]["nr"] for f in gj if len(f["properties"]["nr"]) != 5
           or not f["properties"]["nr"].isdigit()]
    if bad:
        problems.append(f"{len(bad)} postal codes are not 5-digit strings: {bad[:8]}")
    leading = sum(1 for f in gj if f["properties"]["nr"].startswith("0"))
    print(f"  · {leading} postal codes start with a zero and kept it (e.g. "
          f"{next((f['properties']['nr'] for f in gj if f['properties']['nr'].startswith('0')), '–')})")
    if problems:
        print(f"\n⚠ {len(problems)} sanity problem(s):")
        for p_ in problems:
            print("  - " + p_)
        sys.exit(1)
    print("\n✓ Paavo checks pass")


if __name__ == "__main__":
    main()
