#!/usr/bin/env python3
"""Kela — general housing allowance (yleinen asumistuki), recipient households per kunta.

    python3 scripts/import_kela.py [--force]

Writes data/external/kela_asumistuki.csv (committed) and a .meta.json stamp.

Route. Kela's own Kelasto reports are a stateful WebFOCUS form with no JSON or REST API
(probed 2026-09-24: a direct POST answers "Error Executing"). The same figures are
published as open data on avoindata.suomi.fi through CKAN's datastore SQL endpoint, under
**CC BY 4.0**, refreshed monthly. That is the route used here.

    GET https://avoindata.suomi.fi/data/api/3/action/datastore_search_sql?sql=…
    resource a3be1d46-1c33-4a59-84d4-66a348b1551c
    columns: aikatyyppi, vuosi, kuukausi_nro, vuosikuukausi, kunta_nro, kunta_nimi,
             etuus, saaja_lkm, saaja_laskenta_lkm, maksettu_eur

Two traps, both handled here and stated in the indicator's note:
  1. `aikatyyppi = 'Vuosi'` rows are **distinct households during the year**, not a stock,
     and are several times larger than any single month. Only 'Kuukausi' rows are read, and
     a year's value is its **December** figure — a stock at a point in time, like the
     household count it is divided by.
  2. `saaja_lkm` for yleinen asumistuki counts **ruokakunta** (benefit households), which is
     close to but not the same concept as Statistics Finland's **asuntokunta**.
"""
import argparse
import csv
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external" / "kela_asumistuki.csv"
API = "https://avoindata.suomi.fi/data/api/3/action/datastore_search_sql"
RESOURCE = "a3be1d46-1c33-4a59-84d4-66a348b1551c"
DATASET = "https://avoindata.suomi.fi/data/fi/dataset/kelan-etuuksien-saajat-ja-maksetut-etuudet"
# the CKAN package the resource belongs to: "Kelan etuuksien saajat ja maksetut etuudet",
# licence cc-by-4.0, confirmed through package_show on 2026-09-24
BENEFIT = "Yleinen asumistuki"
UA = "am-dashboard-fi/1.0 (open-data dashboard)"


def sql(q, tries=4):
    url = API + "?sql=" + urllib.parse.quote(q)
    for attempt in range(tries):
        time.sleep(1.0 if attempt == 0 else 6 * attempt)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            if not d.get("success"):
                raise RuntimeError(d.get("error"))
            return d["result"]["records"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < tries - 1:
                continue
            raise
    raise RuntimeError("gave up")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if OUT.exists() and not args.force:
        print(f"· {OUT.relative_to(ROOT)} exists — pass --force to refresh")

    # December of every year, per kunta: a stock at a point in time, comparable with the
    # household count it is divided by. December is the month, not the annual row.
    q = (f"SELECT vuosi, vuosikuukausi, kunta_nro, kunta_nimi, saaja_lkm, maksettu_eur "
         f"FROM \"{RESOURCE}\" "
         f"WHERE etuus = '{BENEFIT}' AND aikatyyppi = 'Kuukausi' AND kuukausi_nro = 12 "
         f"ORDER BY vuosi, kunta_nro")
    print("· December stock per kunta, every year")
    rows = sql(q)
    print(f"  {len(rows):,} rows")

    # and the newest month there is, whatever month that is, so the dashboard is not a year behind
    newest = sql(f"SELECT max(vuosikuukausi) AS m FROM \"{RESOURCE}\" "
                 f"WHERE etuus = '{BENEFIT}' AND aikatyyppi = 'Kuukausi'")[0]["m"]
    print(f"· newest published month {newest}")
    latest = sql(f"SELECT vuosi, vuosikuukausi, kunta_nro, kunta_nimi, saaja_lkm, maksettu_eur "
                 f"FROM \"{RESOURCE}\" WHERE etuus = '{BENEFIT}' AND aikatyyppi = 'Kuukausi' "
                 f"AND vuosikuukausi = {newest} ORDER BY kunta_nro")
    print(f"  {len(latest):,} kunnat in {newest}")

    seen, out = set(), []
    for r in list(rows) + list(latest):
        code = str(r["kunta_nro"]).zfill(3)          # a string, always: int('091') is Jokioinen
        key = (str(r["vuosikuukausi"]), code)
        if key in seen or not code.isdigit() or len(code) != 3:
            continue
        seen.add(key)
        out.append({"period": str(r["vuosikuukausi"]), "year": str(r["vuosi"]), "kunta": code,
                    "name": r["kunta_nimi"], "households": r["saaja_lkm"],
                    "paid_eur": r["maksettu_eur"]})
    out.sort(key=lambda x: (x["period"], x["kunta"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["period", "year", "kunta", "name", "households", "paid_eur"],
                           delimiter=";")
        w.writeheader()
        w.writerows(out)
    periods = sorted({r["period"] for r in out})
    OUT.with_suffix(".csv.meta.json").write_text(json.dumps({
        "source": "Kela — yleinen asumistuki, saajaruokakunnat kunnittain",
        "route": API + "?sql=… (CKAN datastore SQL)", "resource": RESOURCE, "dataset": DATASET,
        "benefit": BENEFIT, "measure": "saaja_lkm — recipient households (ruokakunta) at the end of the month",
        "selection": "aikatyyppi='Kuukausi'; December of every year, plus the newest published month",
        "why_not_annual": "aikatyyppi='Vuosi' counts distinct households during the year, which is a "
                          "flow several times larger than the month-end stock; it is not comparable "
                          "with a household count at a point in time.",
        "periods": f"{periods[0]}–{periods[-1]}", "months": len(periods),
        "kunnat": len({r['kunta'] for r in out}), "rows": len(out),
        "latest": newest, "fetched": dt.date.today().isoformat(),
        "publisher": "Kela", "licence": "CC BY 4.0 — Lähde: Kela",
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,} B · {len(out):,} rows · "
          f"{len({r['kunta'] for r in out})} kunnat · {periods[0]}–{periods[-1]})")
    hel = [r for r in out if r["kunta"] == "091"]
    if hel:
        print(f"  · Helsinki (091), {hel[-1]['period']}: {hel[-1]['households']:,} households")
    if len({r["kunta"] for r in out}) < 290:
        print("⚠ fewer than 290 kunnat — check the resource id against docs/PROBE_FI.md")
        sys.exit(1)


if __name__ == "__main__":
    main()
