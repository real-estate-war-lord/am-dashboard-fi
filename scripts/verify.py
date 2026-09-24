#!/usr/bin/env python3
"""Recompute published figures straight from the source and compare them with the page.

    python3 scripts/verify.py [--out docs/VERIFICATION.md] [--csv docs/verification/v1_0.csv]

This is deliberately **not** a test of the build's own cached pulls. Every check here makes
a fresh request to the publisher, does the arithmetic again from the returned cells, and
compares the result with what `data/processed/makro.json` actually carries. If the build
were reading the wrong cell, or dividing by the wrong denominator, or joining the wrong
vintage, these checks would disagree — the cached pulls would not.

It also writes the full export: every kunta × every indicator, long format, one row per
figure, with the source table and the period beside it.
"""
import argparse
import csv
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import aluesarjat as A  # noqa: E402
import statfin  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
PAAVO_P = "Postinumeroalueittainen_avoin_tieto:uusin/12f7"
PAAVO_K = "Postinumeroalueittainen_avoin_tieto:uusin/12f8"
TOL = 0.02          # a rounding difference, not a disagreement


def load():
    makro = json.loads((PROC / "makro.json").read_text(encoding="utf-8"))
    osa = json.loads((PROC / "osa_alue.json").read_text(encoding="utf-8")) \
        if (PROC / "osa_alue.json").exists() else {"areas": [], "indicators": []}
    return makro, osa


def px(table, sel, keys):
    """One query, folded to {cell key: value}."""
    ds = statfin.query(table, sel)
    out = {}
    for r in statfin.rows(ds):
        out["|".join(str(r[k]) for k in keys if k in r)] = r["value"]
    return out


def alu(path, sel, keys):
    ds = A.query(path, sel)
    out = {}
    for r in A.rows(ds):
        out["|".join(str(r[k]) for k in keys if k in r)] = r["value"]
    return out


CHECKS = []


def check(level, area, name, indicator, expected_from, how, value):
    CHECKS.append({"level": level, "area": area, "name": name, "indicator": indicator,
                   "source": expected_from, "how": how, "recomputed": value})


# ---------------------------------------------------------------- the checks

def kunta_checks(y="2024"):
    """5 kunnat × 4 indicators, each recomputed from its own published cells."""
    for code, name in (("091", "Helsinki"), ("837", "Tampere"), ("853", "Turku"),
                       ("564", "Oulu"), ("179", "Jyväskylä")):
        c = px(PAAVO_K, {"alue_36_20260101": [f"KU{code}"], "timeperiod_y": [y],
                         "contentscode": ["hr_mtu", "te_vuok_as", "te_taly", "pt_tyott",
                                          "pt_tyoll", "ra_kt_as", "ra_asunn"]},
               ["contentscode"])
        check("kunta", code, name, "income_med", f"Paavo 12f8 hr_mtu {y}",
              "the published cell", c.get("hr_mtu"))
        check("kunta", code, name, "renters", f"Paavo 12f8 {y}",
              f"te_vuok_as {c.get('te_vuok_as')} ÷ te_taly {c.get('te_taly')} × 100",
              None if not c.get("te_taly") else c["te_vuok_as"] / c["te_taly"] * 100)
        den = (c.get("pt_tyoll") or 0) + (c.get("pt_tyott") or 0)
        check("kunta", code, name, "unemp", f"Paavo 12f8 {y}",
              f"pt_tyott {c.get('pt_tyott')} ÷ (pt_tyoll + pt_tyott) {den} × 100",
              None if not den else c["pt_tyott"] / den * 100)
        check("kunta", code, name, "flats", f"Paavo 12f8 {y}",
              f"ra_kt_as {c.get('ra_kt_as')} ÷ ra_asunn {c.get('ra_asunn')} × 100",
              None if not c.get("ra_asunn") else c["ra_kt_as"] / c["ra_asunn"] * 100)


def postal_checks(pyear="2025", ryear="2025Q4", paavo_year="2024"):
    """5 postal codes × price, rent, income, unemployment."""
    for nr, name in (("00100", "Helsinki keskusta – Etu-Töölö"), ("00500", "Sörnäinen"),
                     ("02100", "Tapiola"), ("33100", "Tampere keskus"), ("20100", "Turku keskus")):
        pr = px("ashi/13mu", {"postinumeroalue_4_20220101": [nr], "timeperiod_y": [pyear],
                              "talotyyppi_6_20131021": ["1", "2", "3"],
                              "contentscode": ["keskihinta_aritm_nw", "lkm_julk20"]},
                ["talotyyppi_6_20131021", "contentscode"])
        num = den = 0.0
        for t in ("1", "2", "3"):
            p_, n_ = pr.get(f"{t}|keskihinta_aritm_nw"), pr.get(f"{t}|lkm_julk20")
            if p_ is not None and n_:
                num += p_ * n_
                den += n_
        check("postinumero", nr, name, "price_m2", f"ashi 13mu {pyear}",
              "Σ(price × sales) ÷ Σ(sales) over the three room-count classes = "
              + " + ".join(f"{pr.get(f'{t}|keskihinta_aritm_nw')}×{pr.get(f'{t}|lkm_julk20')}"
                           for t in ("1", "2", "3")) + f" ÷ {den:.0f}",
              num / den if den else None)
        check("postinumero", nr, name, "price_sales", f"ashi 13mu {pyear}",
              "Σ(sales) over the three room-count classes", den or None)
        rt = px("StatFin_Passiivi:asvu/13eb_2025q4",
                {"Postinumero": [nr], "Vuosineljännes": [ryear], "Huoneluku": ["01", "02", "03"],
                 "Tiedot": ["keskivuokra", "lkm_ptno"]}, ["Huoneluku", "Tiedot"])
        rn = rd = 0.0
        for t in ("01", "02", "03"):
            v_, n_ = rt.get(f"{t}|keskivuokra"), rt.get(f"{t}|lkm_ptno")
            if v_ is not None and n_:
                rn += v_ * n_
                rd += n_
        check("postinumero", nr, name, "rent_pno", f"asvu 13eb {ryear} (discontinued)",
              f"Σ(rent × observations) ÷ Σ(observations) = {rd:.0f} observations",
              rn / rd if rd else None)
        c = px(PAAVO_P, {"postinumeroalue_4_20260101": [nr], "timeperiod_y": [paavo_year],
                         "contentscode": ["hr_mtu", "pt_tyott", "pt_tyoll"]}, ["contentscode"])
        check("postinumero", nr, name, "income_med", f"Paavo 12f7 hr_mtu {paavo_year}",
              "the published cell", c.get("hr_mtu"))
        den2 = (c.get("pt_tyoll") or 0) + (c.get("pt_tyott") or 0)
        check("postinumero", nr, name, "unemp", f"Paavo 12f7 {paavo_year}",
              f"pt_tyott {c.get('pt_tyott')} ÷ {den2} × 100",
              None if not den2 else c["pt_tyott"] / den2 * 100)


def osa_checks(y="2025"):
    """3 osa-alueet, recomputed from Aluesarjat."""
    for code10, code, name in (("0911101010", "091010", "Kruununhaka"),
                               ("0915503392", "091392", "Tapanila"),
                               ("0491011111", "049111", "Espoo, Suvela")):
        pop = alu("vrm/vaerak/alu_vaerak_004r",
                  {"Osa-alue": [code10], "Ikä": ["ALL"], "Vuosi": [y], "Tiedot": ["lkm"]}, [])
        check("osa_alue", code, name, "pop", f"Aluesarjat 004r {y}", "the published cell",
              pop.get(""))
        lang = alu("vrm/vaerak/alu_vaerak_004p",
                   {"Alue": [code10], "Äidinkieli": ["ALL", "3"], "Ikä": ["ALL", "19-34"],
                    "Vuosi": [y], "Tiedot": ["lkm"]}, ["Äidinkieli", "Ikä"])
        tot = lang.get("ALL|ALL")
        check("osa_alue", code, name, "foreign", f"Aluesarjat 004p {y}",
              f"Muu kieli {lang.get('3|ALL')} ÷ yhteensä {tot} × 100",
              None if not tot else lang["3|ALL"] / tot * 100)
        check("osa_alue", code, name, "young_19_34", f"Aluesarjat 004p {y}",
              f"19–34 {lang.get('ALL|19-34')} ÷ yhteensä {tot} × 100",
              None if not tot else lang["ALL|19-34"] / tot * 100)
        hh = alu("asu/asas/alu_asas_005d",
                 {"Alue": [code10], "Asuntokunnan koko": ["ALL", "1"], "Vuosi": [y],
                  "Tiedot": ["lkm_askun"]}, ["Asuntokunnan koko"])
        check("osa_alue", code, name, "single", f"Aluesarjat 005d {y}",
              f"1 henkilö {hh.get('1')} ÷ yhteensä {hh.get('ALL')} × 100",
              None if not hh.get("ALL") else hh["1"] / hh["ALL"] * 100)


# ---------------------------------------------------------------- reporting

def on_page(makro, osa, level, code, key):
    if level == "kunta":
        o = next((m for m in makro["municipalities"] if m["code"] == code), None)
    elif level == "postinumero":
        o = next((a for a in makro["areas"] if a["nr"] == code), None)
    else:
        o = next((a for a in osa["areas"] if a["code"] == code), None)
    return (o or {}).get(key)


def fmt(v):
    if v is None:
        return "–"
    return f"{v:,.2f}".replace(",", " ") if isinstance(v, float) else f"{v:,}".replace(",", " ")


def export_csv(makro, osa, path):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ind = {i["key"]: i for i in makro["indicators"]}
    rows = []
    for m in makro["municipalities"]:
        for key, i in ind.items():
            if key not in m:
                continue
            rows.append({"level": "kunta", "code": m["code"], "name": m["name"],
                         "parent": m.get("region", ""), "indicator": key, "label": i["label"],
                         "unit": i.get("unit", ""), "value": m[key],
                         "period": (i.get("asof") or {}).get("kunta", ""),
                         "inherited_from": (i.get("inherited") or {}).get("level", "")
                         if key in (m.get("inh") or []) else "",
                         "source": i.get("source", ""),
                         "tables": " · ".join(i.get("tables") or [])})
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["level", "code", "name", "parent", "indicator", "label",
                                          "unit", "value", "period", "inherited_from", "source",
                                          "tables"], delimiter=";")
        w.writeheader()
        w.writerows(rows)
    return len(rows), len({r["code"] for r in rows}), len({r["indicator"] for r in rows})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "VERIFICATION.md"))
    ap.add_argument("--csv", default=str(ROOT / "docs" / "verification" / "v1_0.csv"))
    args = ap.parse_args()
    makro, osa = load()

    print("· kunta checks");    kunta_checks()
    print("· postal checks");   postal_checks()
    print("· osa-alue checks"); osa_checks()

    bad = 0
    for c in CHECKS:
        page = on_page(makro, osa, c["level"], c["area"], c["indicator"])
        c["page"] = page
        if c["recomputed"] is None or page is None:
            c["verdict"] = "–" if c["recomputed"] is None and page is None else "⚠ one side missing"
            if c["verdict"].startswith("⚠"):
                bad += 1
            continue
        d = abs(float(page) - float(c["recomputed"]))
        rel = d / max(1e-9, abs(float(c["recomputed"])))
        c["verdict"] = "✓" if d <= TOL or rel <= 0.001 else f"✗ off by {d:,.3f}"
        if c["verdict"].startswith("✗"):
            bad += 1
        print(f"  {c['verdict'][:1]} {c['level']:12} {c['area']:8} {c['indicator']:12} "
              f"page {fmt(page)} · recomputed {fmt(c['recomputed'])}")

    n, kunnat, inds = export_csv(makro, osa, args.csv)
    today = dt.date.today().isoformat()
    out = [f"# Verification — v1.0\n",
           f"**Run {today}** by `scripts/verify.py`, which re-queries the publisher, redoes the "
           "arithmetic from the returned cells, and compares the result with what "
           "`data/processed/makro.json` actually carries. It does **not** read the build's own "
           "cached pulls: if the build were taking the wrong cell, dividing by the wrong "
           "denominator or joining the wrong vintage, these checks would disagree and the cached "
           "pulls would not.\n",
           f"`{len(CHECKS)}` checks · **{len(CHECKS) - bad} agree**"
           + (f" · **{bad} disagree**" if bad else "") + "\n",
           "Full export: `docs/verification/v1_0.csv` — "
           f"{n:,} rows, {kunnat} kunnat × {inds} indicators, long format "
           "(level; code; name; parent; indicator; label; unit; value; period; inherited_from; "
           "source; tables).\n"]
    for level, title in (("kunta", "Kunnat — 5 × 4 indicators"),
                         ("postinumero", "Postal codes — 5 × price, sales, rent, income, unemployment"),
                         ("osa_alue", "Osa-alueet — 3 × 4 indicators")):
        rows = [c for c in CHECKS if c["level"] == level]
        if not rows:
            continue
        out.append(f"\n## {title}\n")
        out.append("| Area | Indicator | Source | Recomputed how | Recomputed | On the page | |")
        out.append("|---|---|---|---|---:|---:|:--:|")
        for c in rows:
            out.append(f"| {c['name']} ({c['area']}) | {c['indicator']} | {c['source']} | "
                       f"{c['how']} | {fmt(c['recomputed'])} | {fmt(c['page'])} | {c['verdict']} |")
    out.append("\n---\n\n## What a ✓ means here\n")
    out.append("The figure on the page equals the figure recomputed from the publisher's own "
               "cells, to within rounding. It does **not** mean the publisher is right, that the "
               "definition is the one a reader assumes, or that the area's classification vintage "
               "matches the map's — those are `docs/GEO.md` and each indicator's own caveat.\n")
    pathlib.Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out} ({len(CHECKS)} checks, {bad} disagreements)")
    print(f"wrote {args.csv} ({n:,} rows)")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
