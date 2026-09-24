#!/usr/bin/env python3
"""Pull every building address in Finland, one kunta at a time → data/raw/ryhti_addr/.

    https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/wfs
    typeNames=ryhti_building:open_address        3 861 495 addresses (probed 2026-09-24)

This is what the Test-property address search reads (phase 10). The spec asked for the DVV
bulk address file; **that distribution ended 14.3.2025** — its own readme says so — and the
CSC mirror does not even pass TLS verification from here. Ryhti's `open_address` is the same
register, live (the sampled row carried `modified_timestamp_utc` 2026-09-01) and keyless.
See docs/PROBE_FI.md, batch-2 finding 6.

**Two traps, both proved by the probe and both guarded here.**

1. Ryhti's OGC API **silently ignores** `?kuntanumero=091` and hands back all 3.8 million
   rows. Only the CQL form filters. A filter that is ignored rather than rejected is the
   worst kind, so every pull here goes through `CQL_FILTER` *and* asserts the row count
   against a `resultType=hits` asked of the same server in the same run.
2. The OGC API also ignores `properties=`, so a row costs ~1.1 kB — 4.2 GB nationally. The
   **classic WFS** on the same workspace honours `propertyName=` and `outputFormat=csv`,
   which brings a row to ~130 bytes. That is the route used here.

Stdlib only. Resumable: a kunta whose CSV is already on disk and whose row count matches the
server is skipped, so an interrupted run costs nothing to restart.

    python3 scripts/fetch_addresses.py                # every kunta, skipping what is done
    python3 scripts/fetch_addresses.py --only 091 049 # a few
    python3 scripts/fetch_addresses.py --force        # re-pull everything
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
RAW = ROOT / "data" / "raw" / "ryhti_addr"
GEO = ROOT / "data" / "geo" / "kunnat.geojson"

WFS = "https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/wfs"
LAYER = "ryhti_building:open_address"
UA = "am-dashboard-fi/1.1 (open-data dashboard; address index)"
LICENCE = "CC BY 4.0 — Lähde: Ryhti-rakennustietojärjestelmä (Suomen ympäristökeskus)"
VERIFY = ("https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1"
          "/collections/open_address/items?limit=10&f=application/json")
# The columns the address search needs, and nothing else. `location_geometry_data` is the
# point; asking for it in EPSG:4326 means no projection maths anywhere in this repository.
COLS = ("address_name_fin,address_name_swe,number_part_of_address_number,"
        "subdivision_letter_of_address_number,municipality_number,postal_code,"
        "location_geometry_data")
PAGE = 50_000
THROTTLE = 1.2
TIMEOUT = 600
RETRIES = 4


def get(url, timeout=TIMEOUT):
    """-> bytes. Retries a 429/503 rather than reporting it as a dead route."""
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
                print(f"    · HTTP {e.code}, waiting")
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < RETRIES - 1:
                print(f"    · {type(e).__name__}, retrying")
                continue
            raise
    raise RuntimeError("unreachable")


def hits(code):
    """How many addresses the server says this kunta has — the number every pull is checked against."""
    url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature&typeNames={urllib.parse.quote(LAYER)}"
           f"&resultType=hits&CQL_FILTER=" + urllib.parse.quote(f"municipality_number='{code}'"))
    txt = get(url, timeout=120).decode("utf-8", "replace")
    key = 'numberMatched="'
    i = txt.find(key)
    if i < 0:
        raise RuntimeError(f"no numberMatched in the hits response for {code}")
    return int(txt[i + len(key):txt.find('"', i + len(key))])


def page(code, start, count):
    url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature&typeNames={urllib.parse.quote(LAYER)}"
           f"&outputFormat=csv&srsName=EPSG:4326&propertyName={COLS}"
           f"&count={count}&startIndex={start}"
           f"&sortBy=address_key"                      # a stable order, or paging can repeat a row
           f"&CQL_FILTER=" + urllib.parse.quote(f"municipality_number='{code}'"))
    return get(url).decode("utf-8-sig", "replace")


def pull(code, expect):
    """Every page for one kunta, concatenated, header kept once."""
    out, header, got = [], None, 0
    while got < expect:
        txt = page(code, got, PAGE)
        lines = [ln for ln in txt.splitlines() if ln.strip()]
        if not lines:
            break
        if header is None:
            header = lines[0]
            out.append(header)
        elif lines[0] != header:
            raise RuntimeError(f"{code}: the CSV header changed between pages — {lines[0]!r}")
        rows = lines[1:]
        if not rows:
            break
        out.extend(rows)
        got += len(rows)
        print(f"    · {got:,} / {expect:,}")
    return "\n".join(out) + "\n", got


def kunta_codes():
    feats = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    return sorted({str(f["properties"]["kunta"]) for f in feats})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="kunta codes to pull")
    ap.add_argument("--force", action="store_true", help="re-pull even when the file matches")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)

    codes = args.only or kunta_codes()
    total, skipped, failed = 0, 0, []
    for n, code in enumerate(codes, 1):
        dest = RAW / f"{code}.csv"
        meta = RAW / f"{code}.csv.meta.json"
        try:
            want = hits(code)
        except Exception as e:  # noqa: BLE001
            print(f"[{n}/{len(codes)}] {code}  hits failed: {e}")
            failed.append((code, f"hits: {e}"))
            continue
        if dest.exists() and not args.force:
            have = sum(1 for _ in dest.open(encoding="utf-8")) - 1
            if have == want:
                print(f"[{n}/{len(codes)}] {code}  cached {have:,}")
                skipped += 1
                total += have
                continue
            print(f"[{n}/{len(codes)}] {code}  cached {have:,} but server says {want:,} — re-pulling")
        print(f"[{n}/{len(codes)}] {code}  {want:,} addresses")
        if want == 0:
            # A kunta with no addresses is a real answer (it happens on Åland's smallest),
            # and it is written down so the next run does not ask again.
            dest.write_text("", encoding="utf-8")
        else:
            try:
                txt, got = pull(code, want)
            except Exception as e:  # noqa: BLE001
                print(f"    ! {e}")
                failed.append((code, str(e)))
                continue
            if got != want:
                # Never write a short file silently: a half-pulled kunta would look complete
                # to the builder and quietly lose streets.
                print(f"    ! got {got:,}, server said {want:,} — not written")
                failed.append((code, f"short pull {got} != {want}"))
                continue
            dest.write_text(txt, encoding="utf-8")
        meta.write_text(json.dumps({
            "source": "Ryhti-rakennustietojärjestelmä — open_address",
            "publisher": "Suomen ympäristökeskus (Syke) / Ryhti",
            "layer": LAYER, "wfs": WFS, "verify_at_source": VERIFY,
            "licence": LICENCE, "kunta": code, "rows": want,
            "columns": COLS.split(","), "crs": "EPSG:4326",
            "fetched": dt.date.today().isoformat(),
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        total += want
    print(f"\n{total:,} addresses in {len(codes) - len(failed)} kunnat ({skipped} already cached)")
    if failed:
        print(f"{len(failed)} kunnat failed:")
        for code, why in failed:
            print(f"  {code}  {why[:110]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
