#!/usr/bin/env python3
"""data/raw/ryhti_addr/*.csv → data/processed/addr/ — the lazy address lookup (phase 10).

The Test-property box accepts an address as well as a link or a coordinate pair. Resolving
one needs 3.9 million addresses, which is far too much to ship in the page, so the lookup is
split the same way the area data is: **one small file per kunta, fetched when it is needed**.

    data/processed/addr/<kunta>.json   every street in that kunta, with its house numbers
    data/processed/addr/ix/<c>.json    which kunnat have a street starting with <c>

`ix/` is what answers "Mannerheimintie 10" with no town after it: the page loads one shard,
learns which kunnat have that street, and then fetches only those. A search that names a
kunta or a postal code skips the shard entirely.

**Encoding.** A street is one row `[fin, swe, houses]` and `houses` is a string:

    "10,6016986,2493825;10a,5,5;12,13,11"

— house number (with its entrance letter folded on, lower case), then latitude and longitude
as integers scaled by 1e5 (~1 m, far finer than the question being asked). **The first house
carries absolute coordinates and every later one a delta from the house before it**, which is
what keeps a national address set to tens of megabytes rather than a hundred: neighbouring
houses are metres apart, so a delta is two or three digits where an absolute is seven.

Both language forms of a street name point at the **same row**, so a bilingual street costs
its houses once. There is deliberately **no name index in the file** — the page builds one by
normalising the two names as it loads the kunta, which costs microseconds and would otherwise
be a third of the bytes. The normalisation is `normAddr()` from `src/testprop.js`,
reimplemented here; the two must agree or every lookup misses, which `make test` checks.

Stdlib only.
"""
import argparse
import collections
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ryhti_addr"
OUT = ROOT / "data" / "processed" / "addr"
GEO = ROOT / "data" / "geo" / "kunnat.geojson"
MAX_BYTES = 3_000_000          # the repo's hard ceiling for a processed/dist file

FOLD = str.maketrans({"ä": "a", "å": "a", "ö": "o", "é": "e", "ü": "u"})
DROP = str.maketrans({c: " " for c in ".,:;'`´\"()"})


def norm(s):
    """The one normalisation. Must stay identical to normAddr() in src/testprop.js."""
    return " ".join((s or "").lower().translate(FOLD).translate(DROP).split())


def kunta_names():
    feats = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    return {str(f["properties"]["kunta"]): f["properties"] for f in feats}


def read_csv(path):
    """The WFS CSV, parsed without the csv module's quoting surprises on a POINT field.

    Street names can contain a comma in principle, so the quoted-field rules do matter —
    csv.reader handles them; the POINT column is the last one and is never quoted.
    """
    import csv
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            yield row


def point(s):
    """'POINT (24.93825 60.16986)' -> (lat, lon) scaled to 1e-5 integers."""
    if not s or not s.startswith("POINT"):
        return None
    try:
        lon, lat = s[s.index("(") + 1:s.index(")")].split()
        return round(float(lat) * 1e5), round(float(lon) * 1e5)
    except (ValueError, IndexError):
        return None


def build_one(code, props):
    """One kunta -> (payload, {normalised street -> None}) or (None, {}) when it has no addresses."""
    src = RAW / f"{code}.csv"
    if not src.exists():
        return None, {}
    # street identity is the pair of published names; the Finnish one leads where it exists
    streets = collections.OrderedDict()          # (fin, swe) -> {house -> (lat, lon)}
    rows = 0
    skipped = collections.Counter()
    for r in read_csv(src):
        fin = (r.get("address_name_fin") or "").strip()
        swe = (r.get("address_name_swe") or "").strip()
        if not fin and not swe:
            # The register publishes some addresses with a point but no street name in either
            # language. They are real rows; they simply cannot be reached by typing a street,
            # so they are counted and reported rather than quietly dropped.
            skipped["no_street_name"] += 1
            continue
        pt = point(r.get("location_geometry_data"))
        if pt is None:
            skipped["no_point"] += 1
            continue
        num = (r.get("number_part_of_address_number") or "").strip()
        let = (r.get("subdivision_letter_of_address_number") or "").strip().lower()
        key = (fin, swe if swe != fin else "")
        house = f"{num}{let}" if num else let
        streets.setdefault(key, {})
        # A street can carry the same house twice (two buildings on one plot). The first
        # published point is kept; they are metres apart and the question is which area it is in.
        streets[key].setdefault(house, pt)
        rows += 1
    if not streets:
        return None, {}
    nonum = sum(1 for houses in streets.values() for h in houses if not any(c.isdigit() for c in h))

    rowsout, index = [], {}
    for (fin, swe), houses in streets.items():
        def sortkey(h):
            digits = "".join(c for c in h if c.isdigit())
            return (int(digits) if digits else 0, h)
        parts, plat, plon = [], None, None
        for h, (lat, lon) in sorted(houses.items(), key=lambda kv: sortkey(kv[0])):
            if plat is None:
                parts.append(f"{h},{lat},{lon}")
            else:
                parts.append(f"{h},{lat - plat},{lon - plon}")
            plat, plon = lat, lon
        i = len(rowsout)
        rowsout.append([fin, swe, ";".join(parts)])
        for name in (fin, swe):
            n = norm(name)
            if n:
                index.setdefault(n, i)            # only for the national shards, not shipped per kunta
    payload = {
        "k": code, "name": props.get("name", ""), "name_sv": props.get("name_sv", ""),
        "n": rows, "streets": len(rowsout),
        "skipped": dict(skipped), "no_house_number": nonum,
        "built": dt.date.today().isoformat(),
        "source": "Ryhti-rakennustietojärjestelmä — open_address",
        "licence": "CC BY 4.0 — Lähde: Ryhti-rakennustietojärjestelmä (Suomen ympäristökeskus)",
        "s": rowsout,
    }
    return payload, index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    if not RAW.exists():
        print(f"no {RAW} — run scripts/fetch_addresses.py first", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ix").mkdir(parents=True, exist_ok=True)

    names = kunta_names()
    codes = args.only or sorted(names)
    shards = collections.defaultdict(lambda: collections.defaultdict(list))
    total, biggest, missing, written = 0, (0, ""), [], 0
    skipped = collections.Counter()
    for code in codes:
        payload, index = build_one(code, names.get(code, {}))
        if payload is None:
            missing.append(code)
            continue
        dest = OUT / f"{code}.json"
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        dest.write_text(text, encoding="utf-8")
        n = len(text.encode())
        written += 1
        total += payload["n"]
        if n > biggest[0]:
            biggest = (n, code)
        if n > MAX_BYTES:
            # Never ship a file over the ceiling silently — the repo rule is a rule.
            print(f"  ! {code} is {n:,} B, over the {MAX_BYTES:,} B ceiling", file=sys.stderr)
        skipped.update(payload["skipped"])
        for street in index:
            shards[street[0]][street].append(code)
        print(f"  · {code} {names.get(code, {}).get('name', ''):<22} "
              f"{payload['n']:>7,} addresses · {payload['streets']:>6,} streets · {n:>9,} B")

    # the shards: one file per first character of a normalised street name
    for ch, m in sorted(shards.items()):
        safe = f"_{ord(ch):x}" if not (ch.isalnum() and ch.isascii()) else ch
        text = json.dumps({k: ",".join(v) for k, v in sorted(m.items())},
                          ensure_ascii=False, separators=(",", ":"))
        (OUT / "ix" / f"{safe}.json").write_text(text, encoding="utf-8")
        if len(text.encode()) > MAX_BYTES:
            print(f"  ! shard {safe} is {len(text.encode()):,} B, over the ceiling", file=sys.stderr)
    manifest = {
        "built": dt.date.today().isoformat(),
        "addresses": total, "kunnat": written,
        "skipped": dict(skipped),
        "shards": sorted(f"_{ord(c):x}" if not (c.isalnum() and c.isascii()) else c for c in shards),
        "source": "Ryhti-rakennustietojärjestelmä — open_address",
        "verify_at_source": ("https://paikkatiedot.ymparisto.fi/geoserver/ryhti_building/ogc/features/v1"
                             "/collections/open_address/items?limit=10&f=application/json"),
        "licence": "CC BY 4.0 — Lähde: Ryhti-rakennustietojärjestelmä (Suomen ympäristökeskus)",
        "note": ("Coordinates are the register's own, rounded to 1e-5 degrees (~1 m). A house "
                 "published twice keeps its first point. Kunnat with no published address are "
                 "listed in `without`. `skipped.no_street_name` counts addresses the register "
                 "publishes with a point but no street name in either language: they are real "
                 "rows that simply cannot be reached by typing a street, so they are counted "
                 "here rather than quietly dropped. `skipped.no_point` counts rows with no "
                 "usable geometry."),
        "without": missing,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8")
    print(f"\n{total:,} addresses · {written} kunnat · {len(shards)} shards "
          f"· largest kunta file {biggest[0]:,} B ({biggest[1]})")
    if skipped:
        print("not searchable, and counted rather than dropped silently:")
        for k, v in sorted(skipped.items()):
            print(f"  {v:,}  {'no street name in either language' if k == 'no_street_name' else 'no usable point geometry'}")
    if missing:
        print(f"no address file for {len(missing)} kunnat: {', '.join(missing[:12])}"
              + (" …" if len(missing) > 12 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
