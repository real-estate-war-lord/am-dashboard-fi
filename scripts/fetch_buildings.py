#!/usr/bin/env python3
"""Ryhti's building register, one kunta at a time → data/raw/ryhti_bld/ (phase 15).

    https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/wfs
    typeNames=ryhti_building:avoimet_rakennukset      3 799 798 buildings (probed 2026-09-24)

The same route, and the same two traps, as scripts/fetch_addresses.py:

1. Ryhti's OGC API **silently ignores** `?kuntanumero=091` and returns all 3.8 million rows.
   Only `CQL_FILTER` filters, so every pull here goes through it *and* asserts the row count
   against a `resultType=hits` asked of the same server in the same run.
2. The OGC API ignores `properties=` too, at ~1.1 kB a row. The **classic WFS** honours
   `propertyName=` and `outputFormat=csv`, which is what makes a national pull possible at all.

**What the register does and does not say.** `paaasiallinen_kayttotarkoitus` is the *open*
classification, `avoin_rakennusluokitus`, and it has exactly seven codes — the codelist is
titled "Building use classified at a general level". It separates a detached house from a block
of flats, and it does **not** separate a school from a concert hall: `Julkinen rakennus` is one
bucket. Nothing in this repository pretends otherwise (see scripts/build_services.py).

Stdlib only. Resumable: a kunta whose CSV matches the server's own count is skipped.

    python3 scripts/fetch_buildings.py
    python3 scripts/fetch_buildings.py --only 091 049
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

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ryhti_bld"
GEO = ROOT / "data" / "geo" / "kunnat.geojson"

WFS = "https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/wfs"
LAYER = "ryhti_building:avoimet_rakennukset"
UA = "am-dashboard-fi/1.1 (open-data dashboard; building layer)"
LICENCE = "CC BY 4.0 — Lähde: Ryhti-rakennustietojärjestelmä (Suomen ympäristökeskus)"
VERIFY = ("https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1"
          "/collections/avoimet_rakennukset/items?limit=10&f=application/json")
COLS = ("pysyva_rakennustunnus,paaasiallinen_kayttotarkoitus,valmistumispaivamaara,"
        "kerrosluku,kerrosala,huoneistojen_lukumaara,kaytossaolo,kuntanumero,"
        "sijaintikeskipisteen_geometria")
PAGE = 50_000
THROTTLE = 1.2
TIMEOUT = 900
RETRIES = 4


def get(url, timeout=TIMEOUT):
    for attempt in range(RETRIES):
        time.sleep(THROTTLE if attempt == 0 else 15 * attempt)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                return body
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < RETRIES - 1:
                print("    · rate limited, waiting")
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < RETRIES - 1:
                print(f"    · {type(e).__name__}, retrying")
                continue
            raise
    raise RuntimeError("unreachable")


def hits(code):
    url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature&typeNames={urllib.parse.quote(LAYER)}"
           f"&resultType=hits&CQL_FILTER=" + urllib.parse.quote(f"kuntanumero='{code}'"))
    txt = get(url, timeout=180).decode("utf-8", "replace")
    key = 'numberMatched="'
    i = txt.find(key)
    if i < 0:
        raise RuntimeError(f"no numberMatched for {code}")
    return int(txt[i + len(key):txt.find('"', i + len(key))])


def page(code, start, count):
    url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature&typeNames={urllib.parse.quote(LAYER)}"
           f"&outputFormat=csv&srsName=EPSG:4326&propertyName={COLS}"
           f"&count={count}&startIndex={start}&sortBy=pysyva_rakennustunnus"
           f"&CQL_FILTER=" + urllib.parse.quote(f"kuntanumero='{code}'"))
    return get(url).decode("utf-8-sig", "replace")


def pull(code, expect):
    out, header, got = [], None, 0
    while got < expect:
        lines = [ln for ln in page(code, got, PAGE).splitlines() if ln.strip()]
        if not lines:
            break
        if header is None:
            header = lines[0]
            out.append(header)
        elif lines[0] != header:
            raise RuntimeError(f"{code}: the CSV header changed between pages")
        rows = lines[1:]
        if not rows:
            break
        out.extend(rows)
        got += len(rows)
        if expect > PAGE:
            print(f"    · {got:,} / {expect:,}")
    return "\n".join(out) + "\n", got


def kunta_codes():
    feats = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    return sorted({str(f["properties"]["kunta"]) for f in feats})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    codes = args.only or kunta_codes()
    total, skipped, failed = 0, 0, []
    for n, code in enumerate(codes, 1):
        dest = RAW / f"{code}.csv"
        try:
            want = hits(code)
        except Exception as e:  # noqa: BLE001
            print(f"[{n}/{len(codes)}] {code}  hits failed: {e}")
            failed.append((code, str(e)))
            continue
        if dest.exists() and not args.force:
            have = sum(1 for _ in dest.open(encoding="utf-8")) - 1
            if have == want:
                print(f"[{n}/{len(codes)}] {code}  cached {have:,}")
                skipped += 1
                total += have
                continue
        print(f"[{n}/{len(codes)}] {code}  {want:,} buildings")
        if want == 0:
            dest.write_text("", encoding="utf-8")
        else:
            try:
                txt, got = pull(code, want)
            except Exception as e:  # noqa: BLE001
                print(f"    ! {e}")
                failed.append((code, str(e)))
                continue
            if got != want:
                print(f"    ! got {got:,}, server said {want:,} — not written")
                failed.append((code, f"short pull {got} != {want}"))
                continue
            dest.write_text(txt, encoding="utf-8")
        (RAW / f"{code}.csv.meta.json").write_text(json.dumps({
            "source": "Ryhti-rakennustietojärjestelmä — avoimet_rakennukset",
            "publisher": "Suomen ympäristökeskus (Syke) / Ryhti",
            "layer": LAYER, "wfs": WFS, "verify_at_source": VERIFY, "licence": LICENCE,
            "kunta": code, "rows": want, "columns": COLS.split(","), "crs": "EPSG:4326",
            "fetched": dt.date.today().isoformat(),
            "classification": ("paaasiallinen_kayttotarkoitus is the open classification "
                               "avoin_rakennusluokitus: seven codes, 'Julkinen rakennus' "
                               "undivided."),
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        total += want
    print(f"\n{total:,} buildings in {len(codes) - len(failed)} kunnat ({skipped} cached)")
    if failed:
        print(f"{len(failed)} kunnat failed:")
        for code, why in failed:
            print(f"  {code}  {why[:110]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
