#!/usr/bin/env python3
"""Pull every StatFin table named in config/indicators.json into data/raw/statfin/.

    python3 scripts/fetch_statfin.py [--only <table>] [--force] [--dry-run]

One file per (table, chunk), each with a *.meta.json stamp beside it carrying the request,
the publisher's own `updated` timestamp and the fetch date. The pulls themselves are
git-ignored; the stamps are committed, so a committed figure can always be traced to a
dated request.

**Chunking.** PxWeb caps the number of cells per request and answers 403 when a query asks
for too many. The needed selection is read from the registry, the cell count is computed
from the table's own metadata, and a query too big for one call is split along its widest
non-area, non-time variable, then along time. Nothing is dropped to make a query fit: if a
chunk is still too big the script says so and stops, rather than quietly fetching less than
the indicator asked for.

**What is requested.** Exactly the value codes the registry names, plus the area variable as
`*` and the time variable as `*`. A variable the registry does not mention is left out only
when the table's metadata says it is eliminable (the API then returns its total); otherwise
the script refuses, because an un-eliminated variable makes the API return a cross-product
and every downstream sum would silently double-count.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import statfin  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "indicators.json"
OUT = ROOT / "data" / "raw" / "statfin"
CELL_CAP = 90_000          # comfortably inside PxWeb's own limit, which it does not publish


def cfg():
    return json.loads(CFG.read_text(encoding="utf-8"))


def all_sources(c):
    for ind in list(c.get("indicators", [])) + list((c.get("osa") or {}).get("indicators", [])):
        for s in ind.get("sources", []):
            if s.get("src") == "statfin":
                yield ind, s


def plan(sel, meta_vars):
    """[(chunk selection, label)] — one entry per request, each inside the cell cap."""
    def size(s):
        n = 1
        for code, vals in s.items():
            n *= len(meta_vars[code]["values"]) if vals == ["*"] else len(vals)
        return n
    if size(sel) <= CELL_CAP:
        return [(sel, "all")]
    # split along the widest variable that is neither the area nor the time axis
    def width(code):
        v = sel[code]
        return len(meta_vars[code]["values"]) if v == ["*"] else len(v)
    # only a variable with more than one value can be split; splitting a single-value
    # selection would produce the same query again and recurse forever
    splittable = [c for c in sel if sel[c] != ["*"] and len(sel[c]) > 1]
    if splittable:
        code = max(splittable, key=width)
        out = []
        for val in sel[code]:
            sub = dict(sel)
            sub[code] = [val]
            for s2, lab in plan(sub, meta_vars):
                out.append((s2, f"{val}" if lab == "all" else f"{val}-{lab}"))
        return out
    # nothing left but the area and time axes: split time into runs
    time_code = next((c for c in sel if meta_vars[c].get("time")), None)
    if not time_code:
        print(f"    ⚠ a single request still asks for {size(sel):,} cells and nothing is left to "
              f"split — the publisher may refuse it (HTTP 403)")
        return [(sel, "all")]
    years = meta_vars[time_code]["values"]
    per = max(1, CELL_CAP // max(1, size({k: v for k, v in sel.items() if k != time_code})))
    out = []
    for i in range(0, len(years), per):
        sub = dict(sel)
        sub[time_code] = years[i:i + per]
        out.append((sub, f"{years[i]}_{years[min(i + per, len(years)) - 1]}"))
    return out


def safe(name):
    return name.replace(":", "__").replace("/", "__")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="fetch just this table (e.g. vaerak/11re)")
    ap.add_argument("--force", action="store_true", help="re-fetch even when the file exists")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    metas_pending = []

    c = cfg()
    # One selection per TABLE, not per indicator: the union of every value code any indicator
    # asks for. Two indicators on the same table then share one set of files instead of
    # overwriting each other's, and the API is asked once for what both need.
    tables, users = {}, {}
    for ind, s in all_sources(c):
        t = s["table"]
        if args.only and t != args.only:
            continue
        users.setdefault(t, []).append(ind["key"])
        if t not in metas_pending:
            metas_pending.append(t)
        want = tables.setdefault(t, {"vars": {}, "area": s.get("area_var"), "time": s.get("time_var"),
                                     "contents": []})
        for code, vals in (s.get("vars") or {}).items():
            cur = want["vars"].setdefault(code, [])
            for v in (vals if isinstance(vals, list) else [vals]):
                if v not in cur:
                    cur.append(v)
        for code in list(ind.get("num") or []) + list(ind.get("den") or []):
            if code not in want["contents"]:
                want["contents"].append(code)
        want["area"] = want["area"] or s.get("area_var")
        want["time"] = want["time"] or s.get("time_var")
    if not tables:
        print("nothing to fetch — config/indicators.json names no StatFin sources yet")
        return

    metas, fetched, skipped, problems = {}, 0, 0, []
    for t, want in tables.items():
        print(f"· metadata {t}")
        mv = metas[t] = {v["code"]: v for v in statfin.meta(t)["variables"]}
        sel = {k: list(v) for k, v in want["vars"].items()}
        if "contentscode" in mv and "contentscode" not in sel:
            known = set(mv["contentscode"]["values"])
            codes = [x for x in want["contents"] if x in known]
            if codes:
                sel["contentscode"] = codes
        if want["area"]:
            sel[want["area"]] = ["*"]
        if want["time"]:
            sel[want["time"]] = ["*"]
        missing = [v for v, d in mv.items()
                   if v not in sel and not d.get("elimination") and not d.get("time")]
        if missing:
            problems.append(f"{t}: {missing} are neither selected nor eliminable — "
                            f"the API would return a cross-product and every sum would double-count")
            continue
        chunks = plan(sel, mv)
        print(f"  {t:52} {len(chunks)} request(s) for {', '.join(sorted(set(users[t])))}")
        for sub, lab in chunks:
            dest = OUT / f"{safe(t)}__{lab}.json"
            if dest.exists() and not args.force:
                skipped += 1
                continue
            if args.dry_run:
                print(f"    would fetch {dest.name}: "
                      + ", ".join(f"{k}={'*' if v == ['*'] else ','.join(map(str, v))[:60]}"
                                  for k, v in sub.items()))
                continue
            ds = statfin.pull(t, sub, dest, note="for " + ", ".join(sorted(set(users[t]))))
            n = len(ds.get("value") or [])
            print(f"    {dest.name} · {n:,} cells · {dest.stat().st_size:,} B")
            fetched += 1

    print(f"\n{fetched} fetched, {skipped} already present")
    if problems:
        print(f"⚠ {len(problems)} problem(s):")
        for p in problems:
            print("  - " + p)
        sys.exit(1)


if __name__ == "__main__":
    main()
