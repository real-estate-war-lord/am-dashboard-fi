#!/usr/bin/env python3
"""Check every table, variable and value code in config/indicators.json against the live
StatFin metadata. Run this FIRST — it says which codes to fix before pulling any data.

Needs network access to pxdata.stat.fi (no key). Non-StatFin sources (Paavo, Aluesarjat,
Kela, Verohallinto) are listed but not code-checked here; scripts/check_source_links.py
fetches their URLs instead.

Usage: python scripts/validate_config.py [--show 20] [--quiet]
Exit code 1 if anything is wrong, so `make validate` fails loudly.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import statfin  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "indicators.json"
PROBLEMS = []


def cfg():
    return json.loads(CFG.read_text(encoding="utf-8"))


def all_indicators(c):
    return list(c.get("indicators", [])) + list((c.get("osa") or {}).get("indicators", []))


def bad(msg):
    PROBLEMS.append(msg)
    print("    ✗ " + msg)


def check_source(ind, s, show, cache):
    if s.get("src") != "statfin":
        print(f"  · {ind['key']}: {s.get('src')} source — not code-checked here "
              f"({s.get('url') or s.get('table') or ''})")
        return
    name = s.get("table")
    if not name:
        bad(f"{ind['key']}: a statfin source with no `table`")
        return
    if name not in cache:
        try:
            cache[name] = statfin.meta(name)
        except Exception as e:  # noqa: BLE001
            cache[name] = None
            bad(f"{ind['key']}: metadata for {name} failed: {e}")
    m = cache[name]
    if not m:
        return
    vars_ = {v["code"]: v for v in m.get("variables", [])}
    elim = [k for k, v in vars_.items() if v.get("elimination")]
    print(f"  • {ind['key']} → {name} · {m.get('title', '')[:70]}")
    print(f"      vars: {', '.join(vars_)} · eliminable: {elim or 'none'}")
    # every variable must be either asked for or eliminable, or the API returns a cross-product
    for code, v in vars_.items():
        if code not in (s.get("vars") or {}) and not v.get("elimination") and not v.get("time"):
            bad(f"{ind['key']}/{name}: variable {code!r} is neither selected nor eliminable — "
                f"add it to `vars` or the pull will silently mix its categories")
    area_var = s.get("area_var")
    if area_var and area_var not in vars_:
        bad(f"{ind['key']}/{name}: area_var {area_var!r} not in table; available: {list(vars_)}")
    for code, values in (s.get("vars") or {}).items():
        if code not in vars_:
            bad(f"{ind['key']}/{name}: variable {code!r} not in table; available: {list(vars_)}")
            continue
        codes = dict(zip(vars_[code]["values"], vars_[code]["valueTexts"]))
        vs = values if isinstance(values, list) else [values]
        for val in vs:
            if val == "*":
                sample = "; ".join(f"{c}={t}" for c, t in list(codes.items())[:3])
                print(f"      · {code}=* ({len(codes)} codes) e.g. {sample}")
                continue
            if str(val) not in codes:
                bad(f"{ind['key']}/{name}: {code}={val!r} not found. First {show} codes:")
                for cid, txt in list(codes.items())[:show]:
                    print(f"          {cid!r:28} {txt}")
            else:
                print(f"      ✓ {code}={val!r} → {codes[str(val)]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=20)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    c = cfg()
    inds = all_indicators(c)
    if not inds:
        print("config/indicators.json has no indicators registered yet — nothing to check.")
        print("(That is the expected state until docs/PLAN.md phase 3; nothing is registered before it is probed.)")
        return
    keys = [i["key"] for i in inds]
    dupes = {k for k in keys if keys.count(k) > 1}
    if dupes:
        bad(f"duplicate indicator keys: {sorted(dupes)}")
    cache = {}
    for ind in inds:
        for s in ind.get("sources", []):
            check_source(ind, s, args.show, cache)
        for s in ind.get("src_verify", []):
            if not s.get("url") and not s.get("table"):
                bad(f"{ind['key']}: a src_verify entry with neither `url` nor `table`")
            if not s.get("geo"):
                bad(f"{ind['key']}: a src_verify entry with no `geo` — pickSrc() cannot place it")
    print()
    if PROBLEMS:
        print(f"✗ {len(PROBLEMS)} problem(s):")
        for p in PROBLEMS:
            print("  - " + p)
        sys.exit(1)
    print(f"✓ {len(inds)} indicators, {len(cache)} StatFin tables — every code checks out")


if __name__ == "__main__":
    main()
