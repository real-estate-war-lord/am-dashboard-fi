#!/usr/bin/env python3
"""Verohallinto — property-tax percentages and the municipal income-tax rate per kunta.

    python3 scripts/import_verohallinto.py [--force]

Writes two committed CSVs and their stamps:
    data/external/vero_kiinteistovero.csv   property-tax % per kunta per category, 2014–2026
    data/external/vero_tulovero.csv         municipal income-tax % per kunta, current year

Two different routes, because the publisher treats the two figures differently:

**Property tax** is a statistic, published through Verohallinto's own PxWeb at
`vero2.stat.fi` (keyless), table `kive_202` "Kiinteistöveroprosentin mukaiset
kiinteistöverotiedot". The applied percentage is read straight from it — `Tiedot =
Veroprosentti` — for the categories the dashboard shows.

**The municipal income-tax rate is not a statistic anywhere.** No PxWeb table in StatFin,
in Verohallinto's own database or on avoindata.fi carries it: Verohallinto publishes it as
an annual *decision*. Its page renders the table from JSON embedded in a `:rows=` attribute,
and that JSON is what is read here. The URL is pinned in config/sources.json. Rows carry the
municipality's name, not its code, so they are matched by name against kuntajako 2026 and
**every unmatched name is printed and counted** — a silent name mismatch would drop a
municipality's tax rate without anyone noticing.

Licence: Verohallinto publishes no open-licence statement on the tax-rate pages. The figures
are used with the attribution "Lähde: Verohallinto" and are not republished as an
open-licensed dataset. See docs/SOURCES.md.
"""
import argparse
import csv
import datetime as dt
import html
import json
import pathlib
import re
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXT = ROOT / "data" / "external"
GEO = ROOT / "data" / "geo"
SRC = json.loads((ROOT / "config" / "sources.json").read_text(encoding="utf-8"))
UA = "am-dashboard-fi/1.0 (open-data dashboard)"

# the categories the dashboard shows, in the publisher's own wording
CATEGORIES = {
    "2": ("vakituinen_asuinrakennus", "Vakituisen asumisen %"),
    "3": ("muu_asuinrakennus", "Muun kuin vakituisen asumisen %"),
    "7": ("yleinen_rakennus", "Yleinen kiinteistövero-% (rakennus)"),
    "11": ("yleinen_maapohja", "Yleinen kiinteistövero-% (maapohja)"),
    "13": ("rakentamaton_rakennuspaikka", "Rakentamattoman rakennuspaikan %"),
}


def fetch(url, data=None, ctype=None, tries=4):
    for attempt in range(tries):
        time.sleep(1.0 if attempt == 0 else 5 * attempt)
        h = {"User-Agent": UA}
        if ctype:
            h["Content-Type"] = ctype
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h),
                                        timeout=180) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            print(f"  · retry after {e}")
    return b""


def kunnat():
    """{normalised name: code} and {code: name}, from the boundary vintage."""
    p = GEO / "kunnat.geojson"
    if not p.exists():
        sys.exit("✗ data/geo/kunnat.geojson missing — run `make geo` first")
    by_name, by_code = {}, {}
    for f in json.loads(p.read_text(encoding="utf-8"))["features"]:
        pr = f["properties"]
        by_code[pr["kunta"]] = pr["name"]
        by_name[norm(pr["name"])] = pr["kunta"]
        if pr.get("name_sv"):
            by_name.setdefault(norm(pr["name_sv"]), pr["kunta"])
        # a bilingual kunta is named "Maarianhamina - Mariehamn" in the boundary layer and
        # "Maarianhamina" on the tax decision; both halves are registered as aliases
        for half in str(pr["name"]).split("-"):
            if half.strip():
                by_name.setdefault(norm(half), pr["kunta"])
    return by_name, by_code


def norm(s):
    return re.sub(r"[^a-zåäö]", "", str(s).lower())


def property_tax(force):
    cfg = SRC["verohallinto_kiinteistovero"]
    url = cfg["api"]
    meta = json.loads(fetch(url))
    vars_ = {v["code"]: v for v in meta["variables"]}
    cat_var = next(c for c in vars_ if "kiinteistövero" in c.lower())
    years = vars_["Vuosi"]["values"]
    query = {"query": [
        {"code": "Alue", "selection": {"filter": "all", "values": ["*"]}},
        {"code": cat_var, "selection": {"filter": "item", "values": list(CATEGORIES)}},
        {"code": "Vuosi", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "Tiedot", "selection": {"filter": "item", "values": ["Veroprosentti"]}},
    ], "response": {"format": "json-stat2"}}
    ds = json.loads(fetch(url, json.dumps(query).encode(), "application/json"))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import statfin  # noqa: E402
    rows = statfin.rows(ds)
    _by_name, by_code = kunnat()
    out, skipped = [], set()
    for r in rows:
        code = str(r["Alue"])
        if code not in by_code:          # the table also carries maakunnat and a national total
            skipped.add(code)
            continue
        key = CATEGORIES[str(r[cat_var])][0]
        out.append({"kunta": code, "name": by_code[code], "year": str(r["Vuosi"]),
                    "category": key, "pct": r["value"]})
    out.sort(key=lambda x: (x["year"], x["kunta"], x["category"]))
    dest = EXT / "vero_kiinteistovero.csv"
    with dest.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["year", "kunta", "name", "category", "pct"], delimiter=";")
        w.writeheader()
        w.writerows(out)
    covered = len({r["kunta"] for r in out})
    dest.with_suffix(".csv.meta.json").write_text(json.dumps({
        "source": cfg["label"], "api": url, "verify_at_source": cfg["page"],
        "table": "kive_202", "measure": "Veroprosentti — the applied property-tax percentage",
        "categories": {k: v[1] for k, v in CATEGORIES.items()},
        "years": f"{years[0]}–{years[-1]}", "kunnat": covered, "rows": len(out),
        "not_a_kunta": sorted(skipped)[:12],
        "fetched": dt.date.today().isoformat(),
        "publisher": cfg["publisher"], "licence": cfg["licence"], "note": cfg["note"],
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {dest.relative_to(ROOT)} ({len(out):,} rows · {covered} kunnat · "
          f"{years[0]}–{years[-1]})")
    hel = [r for r in out if r["kunta"] == "091" and r["year"] == years[-1]]
    for r in hel:
        print(f"  · Helsinki {years[-1]} {r['category']:30} {r['pct']}")
    return covered


def income_tax(force):
    cfg = SRC["verohallinto_tulovero"]
    out, problems = [], []
    by_name, by_code = kunnat()
    for year, url in sorted(cfg["history"].items()):
        body = fetch(url).decode("utf-8", "replace")
        m = re.search(r':rows="([^"]+)"', body)
        if not m:
            problems.append(f"{year}: the page no longer embeds a :rows= table — re-probe it")
            continue
        rows = json.loads(html.unescape(m.group(1)))
        unmatched = []
        for r in rows:
            name = (r.get("column_0") or {}).get("text", "").strip()
            raw = (r.get("column_1") or {}).get("text", "").strip()
            code = by_name.get(norm(name))
            if not code:
                unmatched.append(name)
                continue
            try:
                pct = float(raw.replace(",", ".").replace("\xa0", "").replace(" ", ""))
            except ValueError:
                unmatched.append(f"{name} ({raw!r})")
                continue
            out.append({"year": year, "kunta": code, "name": by_code[code], "pct": pct})
        print(f"  · {year}: {len(rows)} rows on the page, {len(out)} matched to kuntajako 2026"
              + (f", {len(unmatched)} unmatched" if unmatched else ""))
        if unmatched:
            problems.append(f"{year}: unmatched names — {', '.join(unmatched[:10])}")
    out.sort(key=lambda x: (x["year"], x["kunta"]))
    dest = EXT / "vero_tulovero.csv"
    with dest.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["year", "kunta", "name", "pct"], delimiter=";")
        w.writeheader()
        w.writerows(out)
    covered = len({r["kunta"] for r in out})
    dest.with_suffix(".csv.meta.json").write_text(json.dumps({
        "source": cfg["label"], "route": cfg["route"], "verify_at_source": cfg["page"],
        "pages": cfg["history"], "measure": "kunnallisveroprosentti (column_1 of the decision table)",
        "years": sorted(cfg["history"]), "kunnat": covered, "rows": len(out),
        "unmatched": problems, "fetched": dt.date.today().isoformat(),
        "publisher": cfg["publisher"], "licence": cfg["licence"], "note": cfg["note"],
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {dest.relative_to(ROOT)} ({len(out)} rows · {covered} kunnat)")
    hel = [r for r in out if r["kunta"] == "091"]
    if hel:
        print(f"  · Helsinki {hel[-1]['year']}: {hel[-1]['pct']} %")
    return covered, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    print("property tax (Verohallinto PxWeb, kive_202)")
    n1 = property_tax(args.force)
    print("municipal income tax (Verohallinto decision page)")
    n2, problems = income_tax(args.force)
    if n1 < 290 or n2 < 290:
        print(f"⚠ coverage looks wrong: {n1} kunnat with a property-tax rate, {n2} with an "
              f"income-tax rate, out of 308")
        sys.exit(1)
    if problems:
        print("⚠ " + "; ".join(problems))
        sys.exit(1)
    print("\n✓ tax rates imported")


if __name__ == "__main__":
    main()
