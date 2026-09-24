#!/usr/bin/env python3
"""Fetch every 'Verify at source' URL the dashboard offers and report the ones that break.

The promise the UI makes is that a reader can click through to the publisher's own table.
This checks that the promise holds: every `src_verify` entry in config/indicators.json,
every URL in data/processed/makro.json's source list, and the documented landing pages.

Usage:
  python scripts/check_source_links.py --quick --sample 2   # a couple per source (make validate)
  python scripts/check_source_links.py                      # every link (make links)
Exit code 1 when a link is dead, so `make validate` and `make links` fail loudly.
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "indicators.json"
PROC = ROOT / "data" / "processed"
UA = "am-dashboard-fi/1.0 (link check; open-data dashboard)"
TIMEOUT = 60
THROTTLE = 1.0


def head(url):
    """GET with a tiny range — a HEAD is refused by several of these hosts."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-2047"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, len(r.read()), time.time() - t0, ""
    except urllib.error.HTTPError as e:
        return e.code, 0, time.time() - t0, e.reason
    except Exception as e:  # noqa: BLE001
        return 0, 0, time.time() - t0, str(e)


def collect():
    """[(label, url)] — deduplicated, in a stable order."""
    seen, out = set(), []
    def add(label, url):
        if url and url not in seen:
            seen.add(url)
            out.append((label, url))
    if CFG.exists():
        c = json.loads(CFG.read_text(encoding="utf-8"))
        inds = list(c.get("indicators", [])) + list((c.get("osa") or {}).get("indicators", []))
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import statfin  # noqa: E402
        for i in inds:
            for s in i.get("src_verify", []):
                add(f"{i['key']} ({s.get('geo', '?')})",
                    s.get("url") or (statfin.ui_url(s["table"]) if s.get("table") else ""))
    for f in ("makro.json", "osa_alue.json"):
        p = PROC / f
        if p.exists():
            for s in (json.loads(p.read_text(encoding="utf-8")).get("meta") or {}).get("sources", []):
                add(f"meta:{s.get('key', s.get('label', '?'))}", s.get("url"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="check only a sample")
    ap.add_argument("--sample", type=int, default=2)
    args = ap.parse_args()
    links = collect()
    if not links:
        print("no verify-at-source links registered yet — nothing to check.")
        print("(That is the expected state until docs/PLAN.md phase 3.)")
        return
    if args.quick:
        links = links[: max(1, args.sample)] + links[-max(1, args.sample):]
        links = list(dict.fromkeys(links))
    bad = []
    print(f"{'source':38} {'HTTP':>5} {'s':>6}  url")
    for label, url in links:
        code, n, sec, err = head(url)
        ok = 200 <= code < 400
        print(f"{label[:38]:38} {code:>5} {sec:6.2f}  {url[:96]}{'' if ok else '   ✗ ' + str(err)[:60]}")
        if not ok:
            bad.append((label, url, code, err))
        time.sleep(THROTTLE)
    print()
    if bad:
        print(f"✗ {len(bad)} dead link(s):")
        for label, url, code, err in bad:
            print(f"  - {label}: HTTP {code} {err} — {url}")
        sys.exit(1)
    print(f"✓ {len(links)} link(s) reachable")


if __name__ == "__main__":
    main()
