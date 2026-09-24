#!/usr/bin/env python3
"""Live endpoint probe for every source the Finland edition uses → docs/PROBE_FI.md.

Nothing in this repository may name a table, a variable or a URL that has not answered a
real request. This script is how that is established and re-established: it fetches every
route, records `name | HTTP | seconds | bytes | result`, pulls three reference values whose
correctness is checkable by hand, and writes the whole thing to docs/PROBE_FI.md.

Usage:
  python3 scripts/probe_fi.py                 # everything
  python3 scripts/probe_fi.py --only statfin  # one group: statfin | geo | alue | files | ref
  python3 scripts/probe_fi.py --out -         # print instead of writing the doc

It is deliberately slow: THROTTLE seconds between calls, because these are somebody else's
free servers. It never writes to data/ — a probe reads, it does not fetch.
"""
import argparse
import datetime as dt
import gzip
import io
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import statfin  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "PROBE_FI.md"
UA = "am-dashboard-fi/1.0 (endpoint probe; open-data dashboard)"
TIMEOUT = 120
THROTTLE = 1.2

STATFIN = "https://pxdata.stat.fi/PxWeb/api/v1/en"
GEOSTAT = "https://geo.stat.fi/geoserver"
RESULTS = []


def get(url, data=None, ctype=None, timeout=TIMEOUT):
    """-> (status, bytes, seconds, body|error string). Never raises.

    A 429 is the publisher saying "slow down", not a dead route: it is waited out and
    retried, so a rate limit can never be reported as a missing table.
    """
    headers = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    if ctype:
        headers["Content-Type"] = ctype
    t0 = time.time()
    for attempt in range(4):
        time.sleep(THROTTLE if attempt == 0 else 12 * attempt)
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                return r.status, len(body), time.time() - t0, body
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                continue
            return e.code, 0, time.time() - t0, (e.read()[:300] if hasattr(e, "read") else b"")
        except Exception as e:  # noqa: BLE001
            return 0, 0, time.time() - t0, str(e).encode("utf-8", "replace")
    return 429, 0, time.time() - t0, b"rate limited after 4 attempts"


def record(group, name, url, status, nbytes, secs, result):
    RESULTS.append({"group": group, "name": name, "url": url, "http": status,
                    "bytes": nbytes, "s": round(secs, 2), "result": result})
    mark = "✓" if 200 <= status < 300 else "✗"
    print(f"{mark} {name[:52]:52} {status:>4} {secs:6.2f}s {nbytes:>10,}  {result[:70]}")


# ---------------------------------------------------------------- StatFin

def px_meta(group, name, table):
    """GET the table metadata and summarise its variables."""
    url = statfin.table_url(table)
    st, n, s, body = get(url)
    if st != 200:
        record(group, name, url, st, n, s,
               f"HTTP {st} — " + ("rate limited, retry" if st == 429 else "table not in this database"))
        return None
    m = json.loads(body)
    parts = []
    for v in m["variables"]:
        flag = "T" if v.get("time") else ("e" if v.get("elimination") else "")
        parts.append(f"{v['code']}[{len(v['values'])}{flag}]")
    tvar = next((v for v in m["variables"] if v.get("time")), None)
    span = f"{tvar['values'][0]}–{tvar['values'][-1]}" if tvar else "no time variable"
    record(group, name, url, st, n, s, f"{span} · " + " ".join(parts))
    return m


def px_db(group, db, database="StatFin"):
    url = f"{STATFIN}/{database}/{db}/"
    st, n, s, body = get(url)
    if st != 200:
        record(group, f"db {database}/{db}", url, st, n, s,
               f"HTTP {st} — database does not exist (discontinued? check StatFin_Passiivi)")
        return []
    lst = json.loads(body)
    record(group, f"db {database}/{db}", url, st, n, s,
           f"{len(lst)} tables · " + ", ".join(x["id"].replace(".px", "") for x in lst[:12]))
    return lst


def probe_statfin():
    g = "StatFin PxWeb"
    # is a PxWebApi v2 live? the spec asks; the answer decides the whole client.
    for u in ("https://pxdata.stat.fi/PxWeb/api/v2/", "https://pxdata.stat.fi/PxWeb/api/v2-beta/",
              "https://statfin.stat.fi/api/v2/"):
        st, n, s, _ = get(u)
        record(g, f"PxWebApi v2? {urllib.parse.urlparse(u).netloc}{urllib.parse.urlparse(u).path}",
               u, st, n, s, "live — prefer it" if st == 200 else f"HTTP {st} — not live, v1 only")
    for db in ("vaerak", "tjt", "tyonv", "muutl", "vaenn", "rpk", "asku", "raku", "ashi", "asvu"):
        px_db(g, db)
    # the databases the spec named that no longer exist in live StatFin
    for db in ("ras", "asas", "rakke", "astuki"):
        px_db(g, db)
    for db in ("asvu", "asas", "ras"):
        px_db(g, db, database="StatFin_Passiivi")
    tables = [
        ("population by age, kunta", "vaerak/11re"),
        ("population key figures, kunta", "vaerak/11ra"),
        ("population by language, kunta", "vaerak/11rm"),
        ("household-dwelling units, kunta", "asku/15fh"),
        ("dwelling floor area per unit / person", "asku/15fd"),
        ("income of household-dwelling units", "tjt/118w"),
        ("median income of inhabitants", "tjt/14ww"),
        ("unemployment rate, kunta, monthly", "tyonv/12tf"),
        ("migration, kunta, yearly", "muutl/11ae"),
        ("migration, kunta, monthly", "muutl/12w7"),
        ("population projection 2024", "vaenn/14wx"),
        ("offences, kunta, yearly", "rpk/13ex"),
        ("offences, kunta, monthly", "rpk/13it"),
        ("old dwelling prices, postal, quarterly", "ashi/13mt"),
        ("old dwelling prices, postal, yearly", "ashi/13mu"),
        ("old dwelling prices, kunta, yearly", "ashi/13mx"),
        ("old dwelling prices, quarterly", "ashi/13mv"),
        ("price index old dwellings 2025=100", "ashi/15is"),
        ("price index old dwellings, long chain", "ashi/15it"),
        ("price index old dwellings 2020=100", "ashi/13mq"),
        ("new dwelling prices by sub-area", "ashi/12dg"),
        ("new dwelling prices by plot ownership", "ashi/12dd"),
        ("price index new dwellings 2025=100", "ashi/15iw"),
        ("rents incl. ARA, index + EUR/m2", "asvu/15fa"),
        ("free-market rents by postal code", "asvu/13eb"),
        ("free-market rents by postal code (archive)", "StatFin_Passiivi:asvu/13eb_2025q4"),
        ("rents (archive, long history)", "StatFin_Passiivi:asvu/11x4_2025q4"),
        ("building and dwelling production", "raku/156f"),
        ("dwelling stock incl. unoccupied, kunta", "raku/15f6"),
        ("dwelling stock by tenure (archive)", "StatFin_Passiivi:asas/115y_2024"),
        ("rent distributions, sub-areas of large cities", "asvu/15fc"),
        ("building stock by use and year", "raku/15er"),
        ("new production, yearly", "raku/15f7"),
        ("household-dwelling units by tenure?", "asku/15fi"),
        ("dwelling production (archive, kunta, monthly)", "StatFin_Passiivi:ras/12fy_202412"),
    ]
    for name, t in tables:
        px_meta(g, name, t)


# ---------------------------------------------------------------- geometry

def wfs_caps(group, name, base):
    url = f"{base}?service=WFS&request=GetCapabilities&version=1.0.0"
    st, n, s, body = get(url)
    if st != 200:
        record(group, name, url, st, n, s, f"HTTP {st}")
        return []
    txt = body.decode("utf-8", "replace")
    names = []
    i = 0
    while True:
        a = txt.find("<Name>", i)
        if a < 0:
            break
        b = txt.find("</Name>", a)
        names.append(txt[a + 6:b])
        i = b
    record(group, name, url, st, n, s, f"{len(names)} layers")
    return names


def wfs_sample(group, name, base, layer, count=2):
    url = (f"{base}?service=WFS&version=2.0.0&request=GetFeature&typeNames={urllib.parse.quote(layer)}"
           f"&count={count}&srsName=EPSG:4326&outputFormat=application/json")
    st, n, s, body = get(url)
    if st != 200:
        record(group, name, url, st, n, s, f"HTTP {st}")
        return None
    try:
        gj = json.loads(body)
    except Exception:  # noqa: BLE001
        record(group, name, url, st, n, s, "not JSON — check outputFormat")
        return None
    feats = gj.get("features") or []
    props = list((feats[0].get("properties") or {}).keys()) if feats else []
    total = gj.get("totalFeatures") or gj.get("numberMatched") or "?"
    record(group, name, url, st, n, s,
           f"{total} features · {len(props)} props · " + ", ".join(props[:14]))
    return gj


def probe_geo():
    g = "Geometry (WFS)"
    caps = wfs_caps(g, "Paavo capabilities", f"{GEOSTAT}/postialue/wfs")
    pno = sorted(x for x in caps if "pno_tilasto_" in x)
    if pno:
        record(g, "Paavo pno_tilasto layers", f"{GEOSTAT}/postialue/wfs", 200, 0, 0.0,
               f"{len(pno)} vintages, latest {pno[-1]}")
        wfs_sample(g, f"Paavo sample {pno[-1]}", f"{GEOSTAT}/postialue/wfs", pno[-1])
    caps = wfs_caps(g, "tilastointialueet capabilities", f"{GEOSTAT}/tilastointialueet/wfs")
    for pref in ("kunta1000k_", "maakunta1000k_"):
        # the workspace prefix is stripped first: "kunta1000k_" must not match "seutukunta1000k_"
        got = sorted(x for x in caps if x.split(":")[-1].startswith(pref))
        if got:
            record(g, f"{pref}* layers", f"{GEOSTAT}/tilastointialueet/wfs", 200, 0, 0.0,
                   f"{len(got)} vintages, latest {got[-1]}")
            wfs_sample(g, f"sample {got[-1]}", f"{GEOSTAT}/tilastointialueet/wfs", got[-1])
    hsy = wfs_caps(g, "HSY capabilities", "https://kartta.hsy.fi/geoserver/wfs")
    for want in ("seutukartta_pien_2021", "seutukartta_tila_2021", "seutukartta_suur_2021"):
        hit = [x for x in hsy if x.endswith(want)]
        if hit:
            wfs_sample(g, f"HSY {want}", "https://kartta.hsy.fi/geoserver/wfs", hit[0])
        else:
            record(g, f"HSY {want}", "https://kartta.hsy.fi/geoserver/wfs", 0, 0, 0.0, "layer not listed")
    hel = wfs_caps(g, "Helsinki avoindata capabilities", "https://kartta.hel.fi/ws/geoserver/avoindata/wfs")
    for want in ("Piirijako_osaalue", "Piirijako_peruspiiri", "Piirijako_suurpiiri"):
        hit = [x for x in hel if x.endswith(want)]
        if hit:
            wfs_sample(g, f"Helsinki {want}", "https://kartta.hel.fi/ws/geoserver/avoindata/wfs", hit[0])
        else:
            record(g, f"Helsinki {want}", "https://kartta.hel.fi/ws/geoserver/avoindata/wfs", 0, 0, 0.0,
                   "layer not listed")


# ---------------------------------------------------------------- Aluesarjat and file sources

def probe_alue():
    g = "Aluesarjat"
    for base in ("https://stat.hel.fi/api/v1/en/Aluesarjat/", "https://stat.hel.fi/api/v1/fi/Aluesarjat/",
                 "https://api.aluesarjat.fi/"):
        st, n, s, body = get(base, timeout=20)
        result = f"HTTP {st}" if st else "no response (host does not resolve or does not answer)"
        if st == 200:
            try:
                lst = json.loads(body)
                result = f"{len(lst)} folders · " + ", ".join(x.get("id", "?") for x in lst[:10])
            except Exception:  # noqa: BLE001
                result = "200 but not a JSON folder list"
        record(g, f"root {base}", base, st, n, s, result)


def probe_files():
    g = "File sources"
    for name, url in (
        ("Kelasto WebFOCUS report list", "https://raportit.kela.fi/ibi_apps/WFServlet?IBIF_ex=NIT100AL"),
        ("Kela open data landing", "https://www.kela.fi/avoin-data"),
        ("Verohallinto statistics landing", "https://www.vero.fi/tietoa-verohallinnosta/tilastot/"),
        ("avoindata.fi API — dataset search 'kiinteistövero'",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=kiinteist%C3%B6veroprosentit&rows=5"),
        ("avoindata.fi API — dataset search 'kunnallisvero'",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=kunnallisveroprosentti&rows=5"),
    ):
        st, n, s, body = get(url)
        result = f"HTTP {st}"
        if st == 200 and "package_search" in url:
            try:
                d = json.loads(body)["result"]
                result = f"{d['count']} datasets · " + "; ".join(x["title"][:44] for x in d["results"][:3])
            except Exception:  # noqa: BLE001
                result = "200, unexpected payload"
        record(g, name, url, st, n, s, result)


# ---------------------------------------------------------------- reference values

def px_value(table, sel):
    url = statfin.table_url(table)
    q = [{"code": k, "selection": {"filter": "item", "values": [str(x) for x in (v if isinstance(v, list) else [v])]}}
         for k, v in sel.items()]
    body = json.dumps({"query": q, "response": {"format": "json-stat2"}}).encode()
    return url, get(url, body, "application/json")


def probe_ref():
    """Three figures a human can look up by hand and compare. If these move, something moved."""
    g = "Reference values"
    checks = [
        ("Helsinki (091) population, latest year", "vaerak/11re",
         {"alue_23_20260101": "KU091", "ikaryhma_10_20180101": "SSS", "sukupuoli_9_20180101": "SSS",
          "timeperiod_y": "2025", "contentscode": "vaerak-vaesto"}, "persons, 31 Dec 2025"),
        ("00100 price EUR/m2, blocks of flats 2-room, latest quarter", "ashi/13mt",
         {"postinumeroalue_4_20220101": "00100", "talotyyppi_6_20131021": "2", "timeperiod_q": "2026Q1",
          "contentscode": ["keskihinta_aritm_nw", "lkm_julk20"]}, "EUR/m2 and number of sales"),
        ("00100 rent EUR/m2/month, 1-room, latest quarter (archive)",
         "StatFin_Passiivi:asvu/13eb_2025q4",
         {"Postinumero": "00100", "Huoneluku": "01", "Vuosineljännes": "2025Q4",
          "Tiedot": ["lkm_ptno", "keskivuokra"]}, "observation count and EUR/m2/month"),
        ("Helsinki (091) free-market rent, 1-room, live table", "asvu/15fa",
         {"alue_44_20260101": "091", "huoneluku_5_20260101": "1", "rahoitus_2_20260101": "1",
          "timeperiod_q": "2026Q1", "contentscode": ["asvu_keskineliovuokra", "asvu_keskineliovuokra_lkm"]},
         "EUR/m2/month and observation count — the live replacement for 13eb, kunta level only"),
        ("Helsinki (091) ARA rent, 1-room, live table", "asvu/15fa",
         {"alue_44_20260101": "091", "huoneluku_5_20260101": "1", "rahoitus_2_20260101": "2",
          "timeperiod_q": "2026Q1", "contentscode": ["asvu_keskineliovuokra", "asvu_keskineliovuokra_lkm"]},
         "government-subsidised (ARA) rent, EUR/m2/month"),
    ]
    for name, table, sel, unit in checks:
        url, (st, n, s, body) = px_value(table, sel)
        if st != 200:
            record(g, name, url, st, n, s, f"HTTP {st} — selection rejected; re-read the metadata")
            continue
        try:
            ds = json.loads(body)
            vals = ds["value"] if isinstance(ds["value"], list) else list(ds["value"].values())
            record(g, name, url, st, n, s, f"{table} → {vals} ({unit})")
        except Exception as e:  # noqa: BLE001
            record(g, name, url, st, n, s, f"200 but unparseable: {e}")


GROUPS = {"statfin": probe_statfin, "geo": probe_geo, "alue": probe_alue,
          "files": probe_files, "ref": probe_ref}


def report():
    today = dt.date.today().isoformat()
    out = [f"## Routes probed — run {today}\n",
           "Every row below is a real request made by `scripts/probe_fi.py` on the Mac. `e` after a "
           "variable's value count means the API can eliminate it (leave it out and get the total); `T` "
           "marks the time variable. A ✗ row is kept, not deleted: knowing that a route is dead is the "
           "point of a probe.\n"]
    for gname in ["StatFin PxWeb", "Geometry (WFS)", "Aluesarjat", "File sources", "Reference values"]:
        rows = [r for r in RESULTS if r["group"] == gname]
        if not rows:
            continue
        out.append(f"\n## {gname}\n")
        out.append("| Name | HTTP | s | bytes | Result |")
        out.append("|---|---:|---:|---:|---|")
        for r in rows:
            res = r["result"].replace("|", "\\|")
            out.append(f"| [{r['name']}]({r['url']}) | {r['http']} | {r['s']} | {r['bytes']:,} | {res} |")
    ok = sum(1 for r in RESULTS if 200 <= r["http"] < 300)
    out.append(f"\n**{ok} of {len(RESULTS)} routes answered.**\n")
    return "\n".join(out)


BEGIN = "<!-- PROBE:BEGIN — generated by scripts/probe_fi.py, do not edit between the markers -->"
END = "<!-- PROBE:END -->"


def splice(path, generated):
    """Replace only the generated block, so the hand-written findings above and below survive.

    A probe is re-run whenever a source moves; the conclusions drawn from it are written by
    a human (or by the build agent) and must not be thrown away by the next run.
    """
    block = f"{BEGIN}\n\n{generated}\n{END}\n"
    p = pathlib.Path(path)
    if p.exists():
        old = p.read_text(encoding="utf-8")
        if BEGIN in old and END in old:
            head = old[: old.index(BEGIN)]
            tail = old[old.index(END) + len(END):]
            return head + block + tail.lstrip("\n")
    return block


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(GROUPS), action="append")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--force", action="store_true",
                    help="let a partial run (--only) overwrite the generated block in the doc")
    args = ap.parse_args()
    for name in (args.only or list(GROUPS)):
        print(f"\n--- {name} ---")
        GROUPS[name]()
    text = report()
    # a partial run must not replace a full run's table with a fragment of it
    if args.only and args.out != "-" and not args.force:
        print(f"\n--only given: printing instead of rewriting {args.out} (pass --force to overwrite)\n")
        print(text)
        return
    if args.out == "-":
        print(text)
    else:
        p = pathlib.Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(splice(p, text), encoding="utf-8")
        print(f"\nwrote {p} ({len(RESULTS)} rows; hand-written sections preserved)")


if __name__ == "__main__":
    main()
