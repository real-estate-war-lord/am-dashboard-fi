#!/usr/bin/env python3
"""Live endpoint probe for every source the Finland edition uses → docs/PROBE_FI.md.

Nothing in this repository may name a table, a variable or a URL that has not answered a
real request. This script is how that is established and re-established: it fetches every
route, records `name | HTTP | seconds | bytes | result`, pulls three reference values whose
correctness is checkable by hand, and writes the whole thing to docs/PROBE_FI.md.

Usage:
  python3 scripts/probe_fi.py                 # everything
  python3 scripts/probe_fi.py --only statfin  # one group: statfin | geo | alue | files | ref
                                              #            climate | ryhti | services | infra
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


# ================================================================== batch 2: the map layers
#
# Everything below was added for the layer phases (docs/PLAN.md §6, phases 9–15). The rule is
# the batch-1 rule: this repository may not name a host, a layer, a collection or a field that
# has not answered a real request. Several of these probes are expected to come back negative —
# a publisher that does not publish something is a finding, and the row is kept to prove it.

RYHTI_BUILD = "https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building"
RYHTI_PLAN = "https://paikkatiedot.ymparisto.fi/geoserver/ryhti_plan"
SYKE_NZ = "https://paikkatiedot.ymparisto.fi/geoserver/inspire_nz/wfs"
HEL_WFS = "https://kartta.hel.fi/ws/geoserver/avoindata/wfs"
HSY_WFS = "https://kartta.hsy.fi/geoserver/wfs"


def head(group, name, url):
    """A HEAD for the big files — a probe must not pull 700 MB to learn a size."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    t0 = time.time()
    time.sleep(THROTTLE)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            n = int(r.headers.get("Content-Length") or 0)
            lm = r.headers.get("Last-Modified") or ""
            record(group, name, url, r.status, n, time.time() - t0,
                   f"{n:,} bytes" + (f" · Last-Modified {lm}" if lm else "")
                   + (f" · {r.headers.get('Content-Type')}" if r.headers.get("Content-Type") else ""))
            return n
    except urllib.error.HTTPError as e:
        record(group, name, url, e.code, 0, time.time() - t0,
               "HTTP 429 — the publisher rate-limited this HEAD; the file itself answers 200 "
               "when asked on its own" if e.code == 429 else f"HTTP {e.code}")
    except Exception as e:  # noqa: BLE001
        record(group, name, url, 0, 0, time.time() - t0, str(e)[:90])
    return 0


def wfs_hits(group, name, base, layer, cql=None):
    """resultType=hits — the feature count without the features."""
    url = (f"{base}?service=WFS&version=2.0.0&request=GetFeature"
           f"&typeNames={urllib.parse.quote(layer)}&resultType=hits")
    if cql:
        url += "&CQL_FILTER=" + urllib.parse.quote(cql)
    st, n, s, body = get(url)
    if st != 200:
        record(group, name, url, st, n, s, f"HTTP {st}")
        return None
    txt = body.decode("utf-8", "replace")
    m = None
    for key in ("numberMatched=\"", "numberOfFeatures=\""):
        i = txt.find(key)
        if i >= 0:
            m = txt[i + len(key):txt.find("\"", i + len(key))]
            break
    record(group, name, url, st, n, s, f"{m} features" if m else "200 but no count in the response")
    return m


def ogc_collections(group, name, base):
    """OGC API Features /collections -> the collection ids, verbatim."""
    url = f"{base}/ogc/features/v1/collections?f=application/json"
    st, n, s, body = get(url)
    if st != 200:
        record(group, name, url, st, n, s, f"HTTP {st}")
        return []
    try:
        ids = [c.get("id") for c in json.loads(body).get("collections", [])]
    except Exception:  # noqa: BLE001
        record(group, name, url, st, n, s, "200 but not a collection list")
        return []
    record(group, name, url, st, n, s, f"{len(ids)} collections · " + ", ".join(ids))
    return ids


def ogc_item(group, name, base, coll, cql=None, limit=1):
    """One real feature out of an OGC API collection — its fields, not a guess at them."""
    url = f"{base}/ogc/features/v1/collections/{coll}/items?limit={limit}&f=application/json"
    if cql:
        url += "&filter=" + urllib.parse.quote(cql)
    st, n, s, body = get(url)
    if st != 200:
        record(group, name, url, st, n, s, f"HTTP {st}")
        return None
    try:
        gj = json.loads(body)
    except Exception:  # noqa: BLE001
        record(group, name, url, st, n, s, "200 but not JSON")
        return None
    fs = gj.get("features") or []
    props = list((fs[0].get("properties") or {}).keys()) if fs else []
    total = gj.get("numberMatched", gj.get("totalFeatures", "?"))
    geom = (fs[0].get("geometry") or {}).get("type", "-") if fs else "-"
    record(group, name, url, st, n, s,
           f"{total:,} features · {geom} · {len(props)} fields · " + ", ".join(props[:16])
           if isinstance(total, int) else f"{total} features · {geom} · " + ", ".join(props[:16]))
    return gj


def caps_grep(group, name, base, words, service="WFS"):
    """Fetch a capabilities document and report which of `words` appear in a layer name.

    This is how an ABSENCE is established: "no layer in HSY's 397 contains 'tulva'" is a
    result, and the row proves the question was actually asked of the server.
    """
    url = f"{base}?service={service}&version={'1.3.0' if service == 'WMS' else '2.0.0'}&request=GetCapabilities"
    st, n, s, body = get(url)
    if st != 200:
        record(group, name, url, st, n, s, f"HTTP {st}")
        return []
    txt = body.decode("utf-8", "replace")
    names, i = [], 0
    while True:
        a = txt.find("<Name>", i)
        if a < 0:
            a = txt.find("<ows:Name>", i)
            if a < 0:
                break
            b = txt.find("</ows:Name>", a)
            names.append(txt[a + 10:b])
        else:
            b = txt.find("</Name>", a)
            names.append(txt[a + 6:b])
        i = b + 1
    bits = []
    for w in words:
        hit = sorted({x for x in names if w.lower() in x.lower()})
        bits.append(f"{w}: {len(hit)}" + (f" ({', '.join(hit[:3])})" if hit else " — none"))
    record(group, name, url, st, n, s, f"{len(names)} layers · " + " · ".join(bits))
    return names


# ---------------------------------------------------------------- climate

def probe_climate():
    g = "Climate (phase 11)"
    caps = caps_grep(g, "SYKE INSPIRE_Syke_Luonnonriskialueet capabilities", SYKE_NZ,
                     ["Tulvavaaravyohykkeet", "Tulvavaarakartoitetut", "Merkittavat_tulvariski"])
    zones = sorted(x for x in caps if "Tulvavaaravyohykkeet" in x)
    if zones:
        record(g, "flood-hazard zone layers", SYKE_NZ, 200, 0, 0.0,
               f"{len(zones)} layers — return period is in the LAYER NAME, not only an attribute: "
               + ", ".join(zones))
    # the two return periods the dashboard needs, for both hazard types
    for kind in ("Vesistotulva", "Meritulva"):
        for per in ("100", "1000"):
            lay = f"inspire_nz:NZ.Tulvavaaravyohykkeet_{kind}_1_{per}a"
            if zones and lay not in zones:
                record(g, f"{kind} 1/{per}a", SYKE_NZ, 0, 0, 0.0, "layer not listed in capabilities")
                continue
            wfs_sample(g, f"{kind} 1/{per}a sample", SYKE_NZ, lay)
            wfs_hits(g, f"{kind} 1/{per}a national count", SYKE_NZ, lay)
    # the mapped-area extent: everything outside it is "Not mapped", never "no flood risk"
    for kind in ("Vesistotulva", "Meritulva"):
        lay = f"inspire_nz:NZ.Tulvavaarakartoitetut_alueet_{kind}"
        wfs_hits(g, f"mapped extent — {kind}", SYKE_NZ, lay)
    # the bulk downloads, which are what a whole-country area share is actually computed from
    for kind in ("meri", "vesisto"):
        head(g, f"SYKE bulk zip — tulvavaaravyohykkeet_{kind}",
             f"https://sykedata.ymparisto.fi/gisdata-1/tulva/tulvavaaravyohykkeet/tulvavaaravyohykkeet_{kind}.zip")
    # sea level
    wfs_sample(g, "Helsinki — FMI site flood height 2100 (points)", HEL_WFS,
               "avoindata:FMI_Paikkakohtainen_tulvakorkeus_vuonna_2100_piste")
    for name, url in (
        ("avoindata.fi search — merenpinnan nousu",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=merenpinnan+nousu&rows=5"),
        ("avoindata.fi search — tulvavaaravyöhyke",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=tulvavaaravy%C3%B6hyke&rows=5"),
        ("avoindata.fi search — hulevesitulva",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=hulevesitulva&rows=5"),
        ("avoindata.fi search — radon",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=radon&rows=5"),
    ):
        st, n, s, body = get(url)
        result = f"HTTP {st}"
        if st == 200:
            try:
                d = json.loads(body)["result"]
                result = (f"{d['count']} datasets" + (" · " + "; ".join(x["title"][:44] for x in d["results"][:3])
                                                     if d["results"] else " — nothing published"))
            except Exception:  # noqa: BLE001
                result = "200, unexpected payload"
        record(g, name, url, st, n, s, result)
    # stormwater: asked of both publishers, and the answer is written down
    caps_grep(g, "HSY WFS — any hulevesi/tulva layer?", HSY_WFS, ["hulevesi", "tulva"])
    caps_grep(g, "Helsinki WFS — any hulevesi/tulva layer?", HEL_WFS, ["hulevesi", "tulva"])
    # radon
    for area in ("kunta_ja_koko_suomi", "postinumero"):
        head(g, f"STUK radon {area} 2023 (xlsx)",
             f"https://stuk.fi/documents/150192312/157590338/radontilasto_pientalot_{area}_2023.xlsx")


# ---------------------------------------------------------------- buildings, addresses, zoning

def probe_ryhti():
    g = "Buildings, addresses and zoning (phases 10, 15)"
    colls = ogc_collections(g, "Ryhti ryhti_building collections", RYHTI_BUILD)
    for c in ("avoimet_rakennukset", "avoimet_lupa_rakennukset", "open_address"):
        if colls and c not in colls:
            record(g, f"{c}", RYHTI_BUILD, 0, 0, 0.0, "collection not listed")
            continue
        ogc_item(g, f"{c} — one feature", RYHTI_BUILD, c)
    # municipality filtering: the plain query parameter is silently ignored, CQL is not
    ogc_item(g, "avoimet_rakennukset — CQL kuntanumero='091'", RYHTI_BUILD, "avoimet_rakennukset",
             cql="kuntanumero='091'")
    # the same question asked through classic WFS, which is what the fetchers use: it accepts
    # propertyName and CSV, so an address pull is ~130 bytes a row instead of ~1,100
    url = (f"{RYHTI_BUILD}/wfs?service=WFS&version=2.0.0&request=GetFeature"
           "&typeNames=ryhti_building:open_address&count=3&outputFormat=csv&srsName=EPSG:4326"
           "&propertyName=address_name_fin,address_name_swe,number_part_of_address_number,"
           "subdivision_letter_of_address_number,municipality_number,postal_code,location_geometry_data"
           "&CQL_FILTER=" + urllib.parse.quote("municipality_number='091'"))
    st, n, s, body = get(url)
    head_row = body.decode("utf-8", "replace").splitlines()[0] if st == 200 and body else ""
    record(g, "open_address via WFS — CSV + propertyName + CQL (the fetch route)", url, st, n, s,
           f"columns: {head_row}" if head_row else f"HTTP {st}")
    wfs_hits(g, "open_address — Helsinki (091) count", f"{RYHTI_BUILD}/wfs",
             "ryhti_building:open_address", cql="municipality_number='091'")
    wfs_hits(g, "open_address — national count", f"{RYHTI_BUILD}/wfs", "ryhti_building:open_address")
    # zoning
    pc = ogc_collections(g, "Ryhti ryhti_plan collections", RYHTI_PLAN)
    for c in ("pub_valid_ld_plan_ix_gs", "pub_valid_lm_plan_ix_gs",
              "pub_prep_ld_plan_ix_gs", "pub_prep_lm_plan_ix_gs"):
        if pc and c not in pc:
            record(g, c, RYHTI_PLAN, 0, 0, 0.0, "collection not listed")
            continue
        ogc_item(g, f"{c} — one feature", RYHTI_PLAN, c)
    # Helsinki's own kaava data, which is the one route that publishes building rights in k-m2
    for lay in ("avoindata:Kaavayksikot", "avoindata:Kaavahakemisto_alue_kaava_voimassa",
                "avoindata:Kaavahakemisto_alue_kaava_vireilla"):
        wfs_sample(g, f"Helsinki {lay.split(':')[-1]}", HEL_WFS, lay, count=1)
    # the DVV bulk file the spec expected — discontinued, and the readme is the evidence
    head(g, "DVV osoiteet_2025.shp (legacy bulk file)",
         "https://ftp.csc.fi/index/geodata/dvv/osoitteet/2025/osoiteet_2025.shp")
    st, n, s, body = get("https://ftp.csc.fi/index/geodata/dvv/osoitteet/2025/rakennukset_readme.txt")
    txt = body.decode("utf-8", "replace") if st == 200 else ""
    stop = next((ln.strip() for ln in txt.splitlines() if "jakelu" in ln.lower() and "paatty" in
                 ln.lower().replace("ä", "a")), "")
    record(g, "DVV readme — is the file still maintained?",
           "https://ftp.csc.fi/index/geodata/dvv/osoitteet/2025/rakennukset_readme.txt", st, n, s,
           stop or (f"HTTP {st}" if st != 200 else "readme fetched, no end-of-distribution line found"))
    # 1 km population grid
    grid = caps_grep(g, "Tilastokeskus vaestoruutu capabilities",
                     f"{GEOSTAT}/vaestoruutu/wfs", ["vaki", "_1km"])
    km = sorted(x for x in grid if x.endswith("_1km"))
    if km:
        wfs_sample(g, f"1 km grid sample {km[-1]}", f"{GEOSTAT}/vaestoruutu/wfs", km[-1])
        wfs_hits(g, f"1 km grid count {km[-1]}", f"{GEOSTAT}/vaestoruutu/wfs", km[-1])
    # ARA energy certificates: asked, and the answer is a paid X-Road service
    for name, url in (
        ("ARA energiatodistusrekisteri — Suomi.fi service catalogue entry",
         "https://liityntakatalogi.suomi.fi/dataset/energiatodistusrekisteri-ara-svc"),
        ("avoindata.fi search — energiatodistus",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=energiatodistus&rows=5"),
    ):
        st, n, s, body = get(url)
        result = f"HTTP {st}"
        if st == 200 and "package_search" in url:
            try:
                d = json.loads(body)["result"]
                result = (f"{d['count']} datasets" + (" · " + "; ".join(x["title"][:44] for x in d["results"][:3])
                                                     if d["results"] else " — nothing published"))
            except Exception:  # noqa: BLE001
                result = "200, unexpected payload"
        elif st == 200:
            t = body.decode("utf-8", "replace")
            result = ("200 · page names a fee ('maksullinen') and an ARA data permit ('tietolupa')"
                      if "maksullinen" in t and "tietolupa" in t else "200")
        record(g, name, url, st, n, s, result)


# ---------------------------------------------------------------- services and transport

def probe_services_layer():
    g = "Services and transport (phase 12)"
    head(g, "HSL static GTFS (keyless mirror)", "https://dev.hsl.fi/gtfs/hsl.zip")
    st, n, s, body = get("https://api.digitransit.fi/routing-data/v3/finland/", timeout=30)
    record(g, "Digitransit national routing data (needs a subscription key?)",
           "https://api.digitransit.fi/routing-data/v3/finland/", st, n, s,
           "401 — a free but REGISTERED subscription key is required, so it is out for a keyless build"
           if st == 401 else f"HTTP {st}")
    for name, url in (
        ("FINAP / Fintraffic catalogue — schedule services",
         "https://finap.fi/ote/service-search?sub_types=schedule"),
        ("Palvelukartta — one unit", "https://api.hel.fi/servicemap/v2/unit/?page_size=1"),
        ("Palvelukartta — service nodes, page 1", "https://api.hel.fi/servicemap/v2/service_node/?page_size=1"),
        ("Palvelukartta — units in Helsinki", "https://api.hel.fi/servicemap/v2/unit/?municipality=helsinki&page_size=1"),
        ("LIPAS — sports-site categories", "https://api.lipas.fi/v2/sports-site-categories"),
        ("LIPAS — one sports site", "https://api.lipas.fi/v2/sports-sites?page-size=1"),
    ):
        st, n, s, body = get(url)
        result = f"HTTP {st}"
        if st == 200:
            try:
                d = json.loads(body)
                if isinstance(d, dict) and "count" in d:
                    first = (d.get("results") or [{}])[0]
                    result = f"{d['count']:,} · fields: " + ", ".join(list(first.keys())[:14])
                elif isinstance(d, list):
                    result = f"{len(d)} entries · " + ", ".join(
                        str((d[0] or {}).get(k)) for k in list((d[0] or {}).keys())[:4]) if d else "0 entries"
            except Exception:  # noqa: BLE001
                result = f"HTTP {st}, {n:,} bytes (not JSON — an HTML catalogue page)"
        record(g, name, url, st, n, s, result)
    head(g, "Geofabrik finland-latest.osm.pbf", "https://download.geofabrik.de/europe/finland-latest.osm.pbf")


# ---------------------------------------------------------------- infra and schools

def probe_infra_schools():
    g = "Infra and schools (phases 13, 14)"
    VAYLA = "https://avoinapi.vaylapilvi.fi/vaylatiedot/ows"
    caps_grep(g, "Väylävirasto vaylatiedot capabilities", VAYLA, ["hanketiedot", "suunnitelma"])
    # the project layers themselves: these are Väylävirasto's own hanke records, with the
    # schedule and the cost estimate the agency publishes — not a guess at either
    for lay in ("hanketiedot:tiehankkeet", "hanketiedot:ratahankkeet", "hanketiedot:vesivaylahankkeet",
                "hanketiedot:tiesuunnitelmat", "hanketiedot:ratasuunnitelmat"):
        wfs_sample(g, f"Väylä {lay.split(':')[-1]} sample", VAYLA, lay, count=1)
        wfs_hits(g, f"Väylä {lay.split(':')[-1]} count", VAYLA, lay)
    # the official school register, with coordinates — no geocoding needed
    OPPI = f"{GEOSTAT}/oppilaitokset/wfs"
    wfs_sample(g, "Tilastokeskus oppilaitokset sample", OPPI, "oppilaitokset:oppilaitokset", count=1)
    wfs_hits(g, "Tilastokeskus oppilaitokset count", OPPI, "oppilaitokset:oppilaitokset")
    # YTL: the national tables are PDFs, but the candidate-level microdata CSV is open and
    # carries the school code, so school-level figures are plain arithmetic on published rows
    for yr, term in ((2026, "K"), (2025, "S"), (2025, "K")):
        head(g, f"YTL microdata FT{yr}{term}D4001.csv",
             f"https://tiedostot.ylioppilastutkinto.fi/ext/data/FT{yr}{term}D4001.csv")
    for name, url in (
        ("Väylävirasto — project list page", "https://vayla.fi/hankkeet"),
        ("Väylävirasto — ohjelmakokonaisuus (the investment programme moved here in autumn 2025)", "https://vayla.fi/ohjelmakokonaisuus"),
        ("YTL — statistics landing", "https://www.ylioppilastutkinto.fi/tietopalvelut/tilastot"),
        ("Vipunen — open statistics service", "https://vipunen.fi/"),
        ("avoindata.fi search — oppilaitokset",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=oppilaitokset&rows=5"),
        ("avoindata.fi search — ylioppilastutkinto",
         "https://www.avoindata.fi/data/api/3/action/package_search?q=ylioppilastutkinto&rows=5"),
        ("Väylävirasto — all projects (hankehaku)", "https://vayla.fi/kaikki-hankkeet"),
    ):
        st, n, s, body = get(url)
        result = f"HTTP {st}"
        if st == 200 and "package_search" in url:
            try:
                d = json.loads(body)["result"]
                result = (f"{d['count']} datasets" + (" · " + "; ".join(x["title"][:44] for x in d["results"][:3])
                                                     if d["results"] else " — nothing published"))
            except Exception:  # noqa: BLE001
                result = "200, unexpected payload"
        elif st == 200:
            result = f"200 · {n:,} bytes"
        record(g, name, url, st, n, s, result)
    # school points from Palvelukartta, which is the Helsinki-region route
    for node, what in (("1097", "basic education"), ("1257", "upper secondary"), ("869", "daycare")):
        url = f"https://api.hel.fi/servicemap/v2/unit/?service_node={node}&page_size=1"
        st, n, s, body = get(url)
        result = f"HTTP {st}"
        if st == 200:
            try:
                result = f"service_node {node} ({what}) → {json.loads(body).get('count', '?'):,} units"
            except Exception:  # noqa: BLE001
                result = "200, unexpected payload"
        record(g, f"Palvelukartta service_node {node} — {what}", url, st, n, s, result)


GROUPS = {"statfin": probe_statfin, "geo": probe_geo, "alue": probe_alue,
          "files": probe_files, "ref": probe_ref,
          "climate": probe_climate, "ryhti": probe_ryhti,
          "services": probe_services_layer, "infra": probe_infra_schools}


def report():
    today = dt.date.today().isoformat()
    out = [f"## Routes probed — run {today}\n",
           "Every row below is a real request made by `scripts/probe_fi.py` on the Mac. `e` after a "
           "variable's value count means the API can eliminate it (leave it out and get the total); `T` "
           "marks the time variable. A ✗ row is kept, not deleted: knowing that a route is dead is the "
           "point of a probe.\n"]
    for gname in ["StatFin PxWeb", "Geometry (WFS)", "Aluesarjat", "File sources", "Reference values",
                  "Climate (phase 11)", "Buildings, addresses and zoning (phases 10, 15)",
                  "Services and transport (phase 12)", "Infra and schools (phases 13, 14)"]:
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
