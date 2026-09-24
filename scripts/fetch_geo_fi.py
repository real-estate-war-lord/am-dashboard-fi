#!/usr/bin/env python3
"""Vendor the Finnish boundary layers: maakunta, kunta and Helsinki-region osa-alue.

    python3 scripts/fetch_geo_fi.py [--force]

Writes data/geo/{maakunnat,kunnat,osa_alueet}.geojson in EPSG:4326, plus
data/geo/kunta_maakunta.json (the official correspondence) and ATTRIBUTION.txt.
Raw downloads land in data/geo/raw/ and are git-ignored.

Sources (every one probed live, docs/PROBE_FI.md):
  Tilastokeskus WFS  https://geo.stat.fi/geoserver/tilastointialueet/wfs
      tilastointialueet:kunta1000k_2026      308 kunnat, land-only
      tilastointialueet:maakunta1000k_2026    19 maakunnat
  Tilastokeskus classification API  https://data.stat.fi/api/classifications/v2/
      kunta_1_20260101#maakunta_1_20260101   the kunta -> maakunta mapping, 308 rows
      (no boundary layer carries a region field, so the mapping comes from the
       classification itself rather than from a spatial guess)
  Helsingin kaupunki WFS  https://kartta.hel.fi/ws/geoserver/avoindata/wfs
      avoindata:Piirijako_osaalue   148 osa-alueet, fi+sv names, updated 2026-09-23
      avoindata:Piirijako_peruspiiri 34
  HSY WFS  https://kartta.hsy.fi/geoserver/wfs
      taustakartat_ja_aluejaot:seutukartta_pien_2021   824 areas over 14 kunnat

Why two osa-alue sources: HSY's Seutukartta is the only single layer covering all four
Helsinki-region municipalities, but it is frozen at 2021 and 179 of its 824 features have
no name at all (including all nine in Kauniainen). Helsinki publishes its own, fresher and
fully named. The two were compared code by code for Helsinki and are identical — 148 codes,
zero difference — so Helsinki is taken from its own layer and Espoo, Vantaa and Kauniainen
from HSY, with no risk of a mismatched division. This is stated in docs/GEO.md and in the
UI's source line.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import geo_common as G  # noqa: E402

TILASTO_WFS = "https://geo.stat.fi/geoserver/tilastointialueet/wfs"
HEL_WFS = "https://kartta.hel.fi/ws/geoserver/avoindata/wfs"
HSY_WFS = "https://kartta.hsy.fi/geoserver/wfs"
CLASS_API = "https://data.stat.fi/api/classifications/v2"

KUNTA_LAYER = "tilastointialueet:kunta1000k_2026"
MAAKUNTA_LAYER = "tilastointialueet:maakunta1000k_2026"
VINTAGE = "kuntajako 2026"
OSA_KUNNAT = {"091": "Helsinki", "049": "Espoo", "092": "Vantaa", "235": "Kauniainen"}


def kunta_maakunta(force=False):
    """The official 2026 correspondence: {kunta code: {code, name_fi, name_en}}."""
    url = (f"{CLASS_API}/correspondenceTables/kunta_1_20260101%23maakunta_1_20260101/maps"
           f"?content=data&meta=max&lang=en&format=json")
    rows = json.loads(G.fetch(url, G.RAW / "kunta_maakunta_2026.json", force))
    out = {}
    for r in rows:
        k = r["sourceLocalId"].split("/")[-1]
        m = r["targetLocalId"].split("/")[-1]
        name = ""
        for t in (r.get("targetItem") or {}).get("classificationItemNames", []):
            if t.get("lang") == "en":
                name = t.get("name", "")
        out[k] = {"code": m, "name": name}
    # the API's meta=max payload does not always inline the target names; fill from the
    # maakunta classification itself rather than leaving a region blank
    missing = {v["code"] for v in out.values() if not v["name"]}
    if missing:
        items = json.loads(G.fetch(
            f"{CLASS_API}/classifications/maakunta_1_20260101/classificationItems"
            f"?content=data&meta=max&lang=en&format=json",
            G.RAW / "maakunta_2026_items.json", force))
        names = {}
        for it in items:
            code = it.get("code") or it.get("localId", "").split("/")[-1]
            for t in it.get("classificationItemNames", []):
                if t.get("lang") == "en":
                    names[code] = t["name"]
        for v in out.values():
            if not v["name"]:
                v["name"] = names.get(v["code"], "")
    return out


def build_kunnat(k2m, force):
    feats = G.wfs_features(TILASTO_WFS, KUNTA_LAYER, G.RAW / "kunta1000k_2026.json", force=force)
    print(f"  · {len(feats)} kunta features")
    simp, pct, tool = G.simplify(feats, budget=2_400_000, label="kunnat")
    out, areas = [], 0.0
    for f in simp:
        p = f["properties"]
        code = str(p["kunta"]).zfill(3)          # never an int: int("091") is 91, which is Jokioinen
        rings = G.rings_of(f["geometry"])
        if not rings:
            continue
        mk = k2m.get(code) or {}
        areas += G.ring_area_km2(rings)
        out.append({"type": "Feature",
                    "properties": {"kunta": code, "name": p.get("nimi") or p.get("name") or "",
                                   "name_sv": p.get("namn") or "",
                                   "maakunta": mk.get("code", ""), "region": mk.get("name", ""),
                                   "bb": G.bbox_of(rings), "c": G.centroid_of(rings)},
                    "geometry": f["geometry"]})
    print(f"  · total land area {areas:,.0f} km² (Finland incl. inland waters ≈ 337 800)")
    return out, pct, tool, areas


def build_maakunnat(force):
    feats = G.wfs_features(TILASTO_WFS, MAAKUNTA_LAYER, G.RAW / "maakunta1000k_2026.json", force=force)
    print(f"  · {len(feats)} maakunta features")
    simp, pct, tool = G.simplify(feats, budget=900_000, label="maakunnat")
    out = []
    for f in simp:
        p = f["properties"]
        rings = G.rings_of(f["geometry"])
        if not rings:
            continue
        out.append({"type": "Feature",
                    "properties": {"maakunta": str(p["maakunta"]).zfill(2),
                                   "name": p.get("nimi") or p.get("name") or "",
                                   "name_sv": p.get("namn") or "",
                                   "bb": G.bbox_of(rings), "c": G.centroid_of(rings)},
                    "geometry": f["geometry"]})
    return out, pct, tool


def build_osa_alueet(force):
    """Helsinki from its own layer, the other three from HSY. Codes are kunta + 3 digits."""
    hel = G.wfs_features(HEL_WFS, "avoindata:Piirijako_osaalue", G.RAW / "hel_osaalue.json", force=force)
    helper = G.wfs_features(HEL_WFS, "avoindata:Piirijako_peruspiiri", G.RAW / "hel_peruspiiri.json",
                            force=force)
    hsy = G.wfs_features(HSY_WFS, "taustakartat_ja_aluejaot:seutukartta_pien_2021",
                         G.RAW / "hsy_seutukartta_pien_2021.json", force=force)
    hsy_tila = G.wfs_features(HSY_WFS, "taustakartat_ja_aluejaot:seutukartta_tila_2021",
                              G.RAW / "hsy_seutukartta_tila_2021.json", force=force)
    print(f"  · Helsinki {len(hel)} osa-alueet · {len(helper)} peruspiiriä · "
          f"HSY {len(hsy)} pienalueet · {len(hsy_tila)} tila-alueet")

    # Helsinki's peruspiiri name per osa-alue: the osa-alue's kokotunnus embeds its peruspiiri
    pp = {}
    for f in helper:
        p = f["properties"]
        pp[str(p.get("tunnus") or "")] = p.get("nimi_fi") or p.get("nimi") or ""
    hsy_tila_name = {}
    for f in hsy_tila:
        p = f["properties"]
        hsy_tila_name[f"{p['kunta']}{p['suur']}{p['tila']}"] = p.get("nimi") or ""

    raw = []
    for f in hel:                                    # 091 Helsinki — its own, fresher layer
        p = f["properties"]
        num = str(p.get("tunnus") or "").zfill(3)
        koko = str(p.get("kokotunnus") or "")
        peruspiiri_code = koko[5:8] if len(koko) >= 10 else ""
        raw.append({"kunta": "091", "num": num, "kokotun": koko,
                    "name": p.get("nimi_fi") or "", "name_sv": p.get("nimi_se") or "",
                    "pp_code": peruspiiri_code, "pp_name": pp.get(peruspiiri_code, ""),
                    "src": "Helsingin kaupunki, Piirijako_osaalue (2026)", "geometry": f["geometry"]})
    for f in hsy:                                    # 049 / 092 / 235 — HSY Seutukartta 2021
        p = f["properties"]
        kunta = str(p.get("kunta") or "").zfill(3)
        if kunta not in OSA_KUNNAT or kunta == "091":
            continue
        tila = f"{kunta}{p.get('suur', '')}{p.get('tila', '')}"
        # Vantaa's rows in the pienalue layer are really at tila level: every one of its 61
        # features has pien = "000". Using pien there would collapse all 61 onto one code.
        pien = str(p.get("pien") or "").zfill(3)
        num = pien if pien not in ("000", "") else str(p.get("tila") or "").zfill(3)
        level = "pienalue" if pien not in ("000", "") else "tila-alue"
        raw.append({"kunta": kunta, "num": num,
                    "kokotun": str(p.get("kokotun") or ""),
                    "name": p.get("nimi") or "", "name_sv": "",
                    "pp_code": str(p.get("tila") or ""), "pp_name": hsy_tila_name.get(tila, ""),
                    "src": f"HSY Seutukartta 2021 ({level})", "geometry": f["geometry"]})

    simp, pct, tool = G.simplify([{"type": "Feature", "properties": {"i": i}, "geometry": r["geometry"]}
                                  for i, r in enumerate(raw)], budget=1_200_000, label="osa-alueet")
    geom_by_i = {f["properties"]["i"]: f["geometry"] for f in simp}
    out, unnamed = [], 0
    for i, r in enumerate(raw):
        g = geom_by_i.get(i)
        rings = G.rings_of(g) if g else []
        if not rings:
            continue
        if not r["name"]:
            unnamed += 1
        out.append({"type": "Feature",
                    "properties": {"code": r["kunta"] + r["num"], "kunta": r["kunta"],
                                   "kokotun": r["kokotun"],
                                   "name": r["name"] or f"{OSA_KUNNAT[r['kunta']]} {r['num']}",
                                   "name_sv": r["name_sv"], "named": bool(r["name"]),
                                   "peruspiiri_code": r["kunta"] + r["pp_code"],
                                   "peruspiiri": r["pp_name"], "source": r["src"],
                                   "bb": G.bbox_of(rings), "c": G.centroid_of(rings)},
                    "geometry": g})
    print(f"  · {len(out)} osa-alueet · {unnamed} with no published name "
          f"(shown as '<kunta> <number>' and marked named=false)")
    return out, pct, tool, unnamed


def checks(kunnat, maakunnat, osa):
    """Sanity, printed and non-fatal-but-loud. A silent geometry bug is the worst kind."""
    problems = []
    if len(kunnat) != 308:
        problems.append(f"kunta count is {len(kunnat)}, expected 308 for {VINTAGE}")
    if len(maakunnat) != 19:
        problems.append(f"maakunta count is {len(maakunnat)}, expected 19")
    for f in kunnat:
        c = f["properties"]["kunta"]
        if len(c) != 3 or not c.isdigit():
            problems.append(f"kunta code {c!r} is not a 3-digit string")
        if not f["properties"]["region"]:
            problems.append(f"kunta {c} has no maakunta")
    for f in osa:
        p = f["properties"]
        if p["kunta"] not in OSA_KUNNAT:
            problems.append(f"osa-alue {p['code']} has kunta {p['kunta']!r}, not one of the four")
        if len(p["code"]) != 6:
            problems.append(f"osa-alue code {p['code']!r} is not 6 characters")
    seen = {}
    for f in osa:
        seen[f["properties"]["code"]] = seen.get(f["properties"]["code"], 0) + 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    if dupes:
        problems.append(f"duplicate osa-alue codes: {sorted(dupes)[:8]}")
    by_kunta = {}
    for f in osa:
        by_kunta[f["properties"]["kunta"]] = by_kunta.get(f["properties"]["kunta"], 0) + 1
    print("  · osa-alueet per kunta: " + ", ".join(f"{OSA_KUNNAT[k]} {v}" for k, v in sorted(by_kunta.items())))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download even when a cached file exists")
    args = ap.parse_args()

    print("kunta → maakunta correspondence")
    k2m = kunta_maakunta(args.force)
    (G.GEO / "kunta_maakunta.json").write_text(
        json.dumps({"vintage": "kunta_1_20260101#maakunta_1_20260101",
                    "source": f"{CLASS_API}/correspondenceTables/kunta_1_20260101%23maakunta_1_20260101",
                    "publisher": "Tilastokeskus", "licence": "CC BY 4.0 — Lähde: Tilastokeskus",
                    "map": k2m}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  · {len(k2m)} kunnat mapped to {len({v['code'] for v in k2m.values()})} maakunnat")

    print("kunnat")
    kunnat, kpct, ktool, karea = build_kunnat(k2m, args.force)
    print("maakunnat")
    maakunnat, mpct, mtool = build_maakunnat(args.force)
    print("osa-alueet")
    osa, opct, otool, unnamed = build_osa_alueet(args.force)

    stamp = {"vintage": VINTAGE, "crs": "EPSG:4326", "publisher": "Tilastokeskus",
             "licence": "CC BY 4.0 — Lähde: Tilastokeskus"}
    G.write_geojson(G.GEO / "kunnat.geojson", kunnat,
                    dict(stamp, layer=KUNTA_LAYER, simplified=f"{kpct * 100:.2f}% ({ktool})",
                         land_area_km2=round(karea)))
    G.write_geojson(G.GEO / "maakunnat.geojson", maakunnat,
                    dict(stamp, layer=MAAKUNTA_LAYER, simplified=f"{mpct * 100:.2f}% ({mtool})"))
    G.write_geojson(G.GEO / "osa_alueet.geojson", osa,
                    {"vintage": "Helsinki Piirijako 2026 + HSY Seutukartta 2021", "crs": "EPSG:4326",
                     "publisher": "Helsingin kaupunki · HSY",
                     "licence": "CC BY 4.0", "simplified": f"{opct * 100:.2f}% ({otool})",
                     "unnamed": unnamed,
                     "note": "Helsinki from avoindata:Piirijako_osaalue (2026-09-23); Espoo, Vantaa "
                             "and Kauniainen from HSY Seutukartta 2021, which is the only single "
                             "layer covering all four and is frozen at 2021."})

    problems = checks(kunnat, maakunnat, osa)
    G.attribution([
        "Boundary data in data/geo/ — Finland edition",
        "",
        f"kunnat.geojson     {KUNTA_LAYER} · {VINTAGE} · {len(kunnat)} features",
        f"                   simplified {kpct * 100:.2f}% with {ktool}, keep-shapes",
        f"maakunnat.geojson  {MAAKUNTA_LAYER} · {len(maakunnat)} features",
        f"                   simplified {mpct * 100:.2f}% with {mtool}, keep-shapes",
        "                   © Tilastokeskus, CC BY 4.0 — Lähde: Tilastokeskus",
        "                   https://geo.stat.fi/geoserver/tilastointialueet/wfs",
        "",
        f"osa_alueet.geojson {len(osa)} features over Helsinki, Espoo, Vantaa and Kauniainen",
        "                   Helsinki: avoindata:Piirijako_osaalue, © Helsingin kaupunki, CC BY 4.0",
        "                   Espoo/Vantaa/Kauniainen: taustakartat_ja_aluejaot:seutukartta_pien_2021,",
        "                   © HSY, CC BY 4.0. Frozen at 2021 — no later vintage is published.",
        f"                   simplified {opct * 100:.2f}% with {otool}, keep-shapes",
        "",
        "kunta_maakunta.json Tilastokeskus classification API, kunta_1_20260101#maakunta_1_20260101",
        "                   © Tilastokeskus, CC BY 4.0",
        "",
        "postinumerot.geojson — see scripts/fetch_paavo.py; © Tilastokeskus (Paavo), CC BY 4.0",
        "",
        "Simplification only removes vertices. No boundary was moved, no area merged and no",
        "hole filled: Kauniainen stays a hole inside Espoo. Every ring keeps at least four points.",
    ])
    if problems:
        print(f"\n⚠ {len(problems)} sanity problem(s):")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("\n✓ geometry checks pass")


if __name__ == "__main__":
    main()
