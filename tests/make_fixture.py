#!/usr/bin/env python3
"""SYNTHETIC development fixture — random numbers on box-shaped polygons over Finland.

Only for checking that the template renders; never ship dist/ built from this. Every
figure it writes is made up, and the fixture says so in meta.built and in every source
line, so a fixture render can never be mistaken for the real dashboard.

It prefers the real registry in config/indicators.json and falls back to a small
synthetic list while the registry is still being filled (docs/PLAN.md phases 3–7), so
`make fixture` is a render check in every phase of the build.

Writes tests/fixture_makro.json and tests/fixture_osa.json.
"""
import json
import math
import pathlib
import random

random.seed(7)
ROOT = pathlib.Path(__file__).resolve().parents[1]
HERE = pathlib.Path(__file__).resolve().parent

# (key, label, short, unit, level, fmt, group, direction, lo, hi)
FALLBACK = [
    ("growth",     "Population growth",        "Growth",     "% / yr",        "postinumero", "signpct1", "Demographics",   "higher_better", -1.5, 2.5),
    ("young",      "Share aged 20–34",         "20–34",      "%",             "postinumero", "pct1",     "Demographics",   "neutral",       10, 34),
    ("single",     "One-person households",    "1-person",   "%",             "postinumero", "pct1",     "Demographics",   "neutral",       28, 62),
    ("foreign",    "Foreign-language speakers", "Foreign lang.", "%",          "kunta",       "pct1",     "Demographics",   "neutral",       1, 26),
    ("income_med", "Median income of inhabitants", "Median inc.", "€ / yr",    "postinumero", "eur0",     "Income & jobs",  "higher_better", 18000, 42000),
    ("unemp",      "Unemployment rate",        "Unemp.",     "%",             "postinumero", "pct1",     "Income & jobs",  "lower_better",  3, 20),
    ("higher_ed",  "Tertiary education",       "Tertiary",   "%",             "postinumero", "pct1",     "Income & jobs",  "higher_better", 12, 62),
    ("renters",    "Renter households",        "Renters",    "%",             "postinumero", "pct1",     "Housing stock",  "neutral",       10, 78),
    ("flats",      "Multi-dwelling share",     "Kerrostalo", "%",             "postinumero", "pct1",     "Housing stock",  "neutral",       2, 96),
    ("avg_m2",     "Average dwelling size",    "Ø m²",       "m²",            "postinumero", "m2",       "Housing stock",  "neutral",       52, 118),
    ("vacant",     "Unoccupied dwellings",     "Unoccupied", "%",             "kunta",       "pct1",     "Housing stock",  "lower_better",  3, 26),
    ("price_m2",   "Old flats, price",         "Price",      "€ / m²",        "postinumero", "eur0",     "Market",         "neutral",       900, 8200),
    ("rent",       "Free-market rent",         "Rent",       "€ / m² / month", "postinumero", "eur1",    "Market",         "neutral",       9, 27),
    ("crime_1000", "Reported offences",        "Crime",      "per 1,000 inh.", "kunta",      "per1000",  "Safety",         "lower_better",  40, 160),
]
HUES = [[10, 88, 70], [40, 84, 128], [166, 42, 22], [90, 60, 150], [150, 90, 30], [12, 94, 104]]

# a handful of real kunta codes and rough centroids, so the synthetic map lands on Finland
KUNNAT = [("091", "SYN-Helsinki", "Uusimaa", 60.17, 24.94), ("049", "SYN-Espoo", "Uusimaa", 60.21, 24.66),
          ("092", "SYN-Vantaa", "Uusimaa", 60.29, 25.04), ("837", "SYN-Tampere", "Pirkanmaa", 61.50, 23.79),
          ("853", "SYN-Turku", "Varsinais-Suomi", 60.45, 22.27), ("564", "SYN-Oulu", "Pohjois-Pohjanmaa", 65.01, 25.47),
          ("179", "SYN-Jyväskylä", "Keski-Suomi", 62.24, 25.75), ("398", "SYN-Lahti", "Päijät-Häme", 60.98, 25.66)]
YEARS = [str(y) for y in range(2014, 2027)]


def cfg_inds():
    p = ROOT / "config" / "indicators.json"
    if not p.exists():
        return []
    c = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for i in c.get("indicators", []):
        out.append((i["key"], i.get("label", i["key"]), i.get("short", i["key"]), i.get("unit", ""),
                    i.get("level", "kunta"), i.get("fmt", "pct1"), i.get("group", "Other"),
                    i.get("direction", "neutral"), 0.0, 100.0))
    return out


def ring(lat, lon, rx, ry, n=10):
    return [[round(lat + ry * math.sin(k * 2 * math.pi / n), 5), round(lon + rx * math.cos(k * 2 * math.pi / n), 5)]
            for k in range(n)]


def build(rows, key_prefix=""):
    specs = rows or FALLBACK
    inds = [{"key": k, "label": lab, "short": sh, "unit": u, "level": lv, "fmt": f, "group": g,
             "direction": d, "hue": HUES[n % len(HUES)],
             "desc": "SYNTHETIC FIXTURE — this number is random, not a published figure.",
             "source": "SYNTHETIC FIXTURE", "warn": ""}
            for n, (k, lab, sh, u, lv, f, g, d, _lo, _hi) in enumerate(specs)]
    rng = {k: (lo, hi) for k, _l, _s, _u, _lv, _f, _g, _d, lo, hi in specs}
    return inds, rng


def series(lo, hi):
    base = random.uniform(lo, hi)
    return {y: round(base * (1 + 0.015 * (i - len(YEARS) + 1) + random.uniform(-0.03, 0.03)), 2)
            for i, y in enumerate(YEARS)}


def main():
    inds, rng = build(cfg_inds())
    M, A = [], []
    for code, name, maakunta, lat, lon in KUNNAT:
        m = {"code": code, "name": name, "region": maakunta, "pop": random.randint(20000, 680000), "hist": {}}
        for i in inds:
            lo, hi = rng[i["key"]]
            h = series(lo, hi)
            m[i["key"]] = h[YEARS[-1]]
            m["hist"][i["key"]] = h
        M.append(m)
        for j in range(5):
            cy, cx = lat + (j // 3) * 0.055, lon + (j % 3) * 0.085
            a = {"nr": f"{int(code):03d}{j:02d}"[:5], "name": f"{name} area {j + 1}", "muni": code,
                 "rings": [ring(cy, cx, 0.045, 0.026)], "pop": random.randint(900, 26000), "hist": {}}
            for i in inds:
                if i["level"] != "kunta":
                    lo, hi = rng[i["key"]]
                    h = series(lo, hi)
                    a[i["key"]] = h[YEARS[-1]]
                    a["hist"][i["key"]] = h
            A.append(a)
    meta = {"built": "SYNTHETIC", "years": YEARS, "latest_year": YEARS[-1],
            "sources": [{"key": "synthetic", "label": "SYNTHETIC FIXTURE — not real data", "asof": "n/a",
                         "licence": "n/a", "fetched": "n/a"}],
            "attribution": ["SYNTHETIC FIXTURE — every number on this page is random"],
            "note": "Synthetic numbers on box-shaped polygons. Never publish a build made from this file."}
    (HERE / "fixture_makro.json").write_text(
        json.dumps({"meta": meta, "indicators": inds, "municipalities": M, "areas": A}, ensure_ascii=False),
        encoding="utf-8")
    print(f"fixture_makro.json: {len(M)} kunnat · {len(A)} postinumeroalueet · {len(inds)} indicators")

    # the third level: synthetic osa-alueet inside the four Helsinki-region kunnat
    osa_specs = [s for s in (FALLBACK if not cfg_inds() else FALLBACK) if s[4] != "kunta"][:8]
    oinds, orng = build(osa_specs)
    for i in oinds:
        i["level"] = "osa_alue"
    Q = []
    for code, name, _mk, lat, lon in KUNNAT[:4]:
        for j in range(6):
            cy, cx = lat + (j // 3) * 0.022, lon + (j % 3) * 0.034
            q = {"code": f"{code}{j + 1:03d}", "name": f"{name.replace('SYN-', '')} osa-alue {j + 1}",
                 "peruspiiri": f"{name.replace('SYN-', '')} peruspiiri {j // 3 + 1}",
                 "peruspiiri_code": f"{code}{j // 3 + 1}", "muni": code,
                 "rings": [ring(cy, cx, 0.016, 0.010)], "pop": random.randint(700, 18000), "hist": {}}
            for i in oinds:
                lo, hi = orng[i["key"]]
                h = series(lo, hi)
                q[i["key"]] = h[YEARS[-1]]
                q["hist"][i["key"]] = h
            Q.append(q)
    (HERE / "fixture_osa.json").write_text(json.dumps(
        {"meta": {"built": "SYNTHETIC", "years": YEARS, "latest_year": YEARS[-1],
                  "sources": [{"key": "synthetic", "label": "SYNTHETIC FIXTURE", "asof": "n/a"}],
                  "attribution": "SYNTHETIC FIXTURE"},
         "indicators": oinds, "areas": Q}, ensure_ascii=False), encoding="utf-8")
    print(f"fixture_osa.json: {len(Q)} osa-alueet · {len(oinds)} indicators")


if __name__ == "__main__":
    main()
