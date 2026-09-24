#!/usr/bin/env python3
"""Schools → data/processed/schools.json (phase 14).

Two publishers, and a hard limit that has to be said out loud:

  **Tilastokeskus `oppilaitokset`** — the official school register, 2 501 schools **with
  coordinates**, so nothing here is geocoded:
  `https://geo.stat.fi/geoserver/oppilaitokset/wfs`, CC BY 4.0. It carries no municipality
  code, so each school is placed in its kunta, postal area and osa-alue by point-in-polygon on
  this dashboard's own rings — the same lookup the test-property pin uses.

  **Ylioppilastutkintolautakunta (YTL)** — matriculation results. YTL's own statistics pages
  publish national aggregates as PDFs, but it also publishes an open, unauthenticated
  **candidate-level** file per exam session at
  `https://tiedostot.ylioppilastutkinto.fi/ext/data/FT<year><K|S>D4001.csv`, carrying the
  school number, the school name and each candidate's grade in each subject on YTL's 0–7 scale.
  School-level figures are therefore plain arithmetic on published rows.

**Finland publishes no comprehensive-school results.** There is no Finnish equivalent of a
national test result per peruskoulu — not suppressed, not behind a licence: it does not exist,
because Finland does not run national comprehensive-school exams for publication. 2 167 of the
2 501 schools here are therefore points on a map with a name and a type and nothing else, and
the UI says so rather than leaving an empty column to be read as a bad result.

**Disclosure.** The YTL file is candidate-level. Aggregating it to a school is arithmetic on
published rows, but a mean over three candidates describes three people. A school session with
fewer than MIN_CANDIDATES candidates is **suppressed**, and a suppressed figure is null — never
a zero. YTL's own `**` marker is read the same way.

Needs shapely. Output committed, so `make build` needs neither it nor a network.

    python3 scripts/build_schools.py
    python3 scripts/build_schools.py --years 2025 2026
"""
import argparse
import collections
import csv
import datetime as dt
import gzip
import io
import json
import pathlib
import statistics
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "schools"
GEO = ROOT / "data" / "geo"
OUT = ROOT / "data" / "processed" / "schools.json"

REG_WFS = "https://geo.stat.fi/geoserver/oppilaitokset/wfs"
REG_LAYER = "oppilaitokset:oppilaitokset"
REG_LICENCE = "CC BY 4.0 — Lähde: Tilastokeskus"
REG_VERIFY = "https://www.avoindata.fi/data/fi/dataset/oppilaitokset"
YTL_URL = "https://tiedostot.ylioppilastutkinto.fi/ext/data/FT{year}{term}D4001.csv"
YTL_LICENCE = "Ylioppilastutkintolautakunta (YTL) — open statistics file; no licence statement published"
YTL_VERIFY = "https://www.ylioppilastutkinto.fi/tietopalvelut/tilastot"
UA = "am-dashboard-fi/1.1 (open-data dashboard; schools layer)"

MIN_CANDIDATES = 10        # below this a school session is suppressed; see the docstring

# ---------------------------------------------------------------- the join
#
# There is no shared key. Tilastokeskus numbers a school with a five-digit `tunn` (08888) and
# YTL with its own four-digit `koulun_nro` (1488); the two numbering systems are unrelated and
# zero-padding one into the other matches nothing at all. What they do share is the school's
# name, and **336 of YTL's 387 names are exactly equal** to a register name once case,
# punctuation and doubled spaces are normalised.
#
# So the join is exact normalised-name equality **against upper-secondary schools only**, and
# nothing fuzzier. A near match would attach one school's results to another school, and that
# is precisely the kind of error nothing downstream would ever reveal. The names that do not
# match are counted, listed in the payload and shown in the UI, rather than forced.
def norm_name(s):
    out = []
    for ch in (s or "").lower():
        out.append(ch if ch.isalnum() or ch.isspace() else " ")
    return " ".join("".join(out).split())
SESSIONS = [(y, t) for y in (2022, 2023, 2024, 2025, 2026) for t in ("K", "S")]

# The register's own type codes, kept as published and translated only for display.
TYPE_OF = {
    "Peruskoulut": "comprehensive",
    "Peruskouluasteen erityiskoulut": "special",
    "Perus- ja lukioasteen koulut": "comprehensive_upper",
    "Lukiot": "upper_secondary",
}
# YTL's subject columns worth carrying: the ones nearly every candidate sits.
SUBJECTS = {"A": "Mother tongue", "M": "Mathematics, advanced", "N": "Mathematics, basic",
            "EA": "English, advanced", "BI": "Biology", "FY": "Physics", "KE": "Chemistry",
            "YH": "Social studies", "HI": "History", "PS": "Psychology", "GE": "Geography"}


def get(url, timeout=300, tries=4):
    for attempt in range(tries):
        time.sleep(1.0 if attempt == 0 else 12 * attempt)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                return body
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < tries - 1:
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries - 1:
                continue
            raise
    raise RuntimeError("unreachable")


def cached(name, url, force=False):
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / name
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"  · cached {name} ({dest.stat().st_size:,} B)")
        return dest.read_bytes()
    body = get(url)
    dest.write_bytes(body)
    print(f"  · {name} {len(body):,} B")
    return body


def num(v):
    """YTL writes `**` for a figure it has suppressed. It stays null; it never becomes a zero."""
    s = (v or "").strip()
    if not s or s == "**":
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def load_areas():
    from shapely.geometry import shape
    from shapely.strtree import STRtree
    out = []
    for level, key, fname in (("kunta", "kunta", "kunnat.geojson"),
                              ("postinumero", "nr", "postinumerot.geojson"),
                              ("osa_alue", "code", "osa_alueet.geojson")):
        p = GEO / fname
        if not p.exists():
            continue
        for f in json.loads(p.read_text(encoding="utf-8"))["features"]:
            out.append((level, str(f["properties"][key]), shape(f["geometry"]).buffer(0),
                        f["properties"].get("name", "")))
    return out, STRtree([g for _, _, g, _ in out])


def ytl_by_school(force=False, years=None):
    """-> {school number: {session: {n, mean_total, subjects{…}}}}, plus the national means."""
    per = collections.defaultdict(dict)
    national = {}
    sessions = [(y, t) for (y, t) in SESSIONS if not years or str(y) in years]
    for year, term in sessions:
        name = f"FT{year}{term}D4001.csv"
        try:
            body = cached(name, YTL_URL.format(year=year, term=term), force)
        except urllib.error.HTTPError as e:
            # A session that has not been published yet is a fact, not a failure.
            print(f"  · {name}: HTTP {e.code} — not published yet, skipped")
            continue
        rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig")), delimiter=";"))
        by_school = collections.defaultdict(list)
        for r in rows:
            n = (r.get("koulun_nro") or "").strip()
            if n:
                by_school[n].append(r)
        session = f"{year}{term}"
        tot_all = [num(r.get("yht")) for r in rows]
        tot_all = [x for x in tot_all if x is not None]
        national[session] = {
            "n": len(rows),
            "schools": len(by_school),
            "mean_total": round(statistics.mean(tot_all), 2) if tot_all else None,
            "subjects": {},
        }
        for code in SUBJECTS:
            vals = [num(r.get(code)) for r in rows]
            vals = [x for x in vals if x is not None]
            if vals:
                national[session]["subjects"][code] = {
                    "mean": round(statistics.mean(vals), 2), "n": len(vals)}
        kept, suppressed = 0, 0
        for nr, rs in by_school.items():
            if len(rs) < MIN_CANDIDATES:
                suppressed += 1
                continue
            tot = [num(r.get("yht")) for r in rs]
            tot = [x for x in tot if x is not None]
            entry = {"n": len(rs),
                     "mean_total": round(statistics.mean(tot), 2) if tot else None,
                     "name": (rs[0].get("koulun_nimi") or "").strip(),
                     "subjects": {}}
            for code in SUBJECTS:
                vals = [num(r.get(code)) for r in rs]
                vals = [x for x in vals if x is not None]
                # a subject only a handful of this school's candidates sat is suppressed too
                if len(vals) >= MIN_CANDIDATES:
                    entry["subjects"][code] = {"mean": round(statistics.mean(vals), 2), "n": len(vals)}
            per[nr][session] = entry
            kept += 1
        print(f"    {session}: {len(rows):,} candidates · {kept} schools kept · "
              f"{suppressed} suppressed (< {MIN_CANDIDATES} candidates)")
    return per, national


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--years", nargs="*")
    args = ap.parse_args()
    try:
        from shapely.geometry import Point
    except ImportError:
        print("shapely is needed here: python3 -m pip install -r requirements-services.txt",
              file=sys.stderr)
        return 1

    print("register:")
    reg = json.loads(cached("oppilaitokset.geojson",
                            f"{REG_WFS}?service=WFS&version=2.0.0&request=GetFeature"
                            f"&typeNames={REG_LAYER}&srsName=EPSG:4326"
                            f"&outputFormat=application/json", args.force).decode("utf-8"))
    feats = reg["features"]
    reg_year = max((f["properties"].get("til_vuosi") or 0) for f in feats)
    print(f"  · {len(feats):,} schools, register year {reg_year}")

    print("YTL matriculation results:")
    ytl, national = ytl_by_school(args.force, args.years)
    print(f"  · {len(ytl)} lukios have at least one unsuppressed session")

    # YTL's rows re-keyed by normalised school name, the only key the two registers share
    ytl_by_norm_name, dup = {}, []
    for nr, sessions in ytl.items():
        latest = sorted(sessions)[-1]
        n = norm_name(sessions[latest].get("name") or "")
        if not n:
            continue
        if n in ytl_by_norm_name:
            dup.append(n)
            continue
        ytl_by_norm_name[n] = sessions
    if dup:
        print(f"  ⚠ {len(dup)} YTL names appear twice and are left unjoined: {', '.join(dup[:5])}")
    used_names = set()

    areas, tree = load_areas()
    schools, placed, unplaced = [], 0, 0
    by_type = collections.Counter()
    for f in feats:
        p = f["properties"]
        g = f.get("geometry") or {}
        if g.get("type") != "Point":
            unplaced += 1
            continue
        lon, lat = g["coordinates"][0], g["coordinates"][1]
        pt = Point(lon, lat)
        where = {}
        for i in tree.query(pt):
            level, code, poly, name = areas[i]
            if level in where or not poly.contains(pt):
                continue
            where[level] = code
            if level == "kunta":
                where["kunta_name"] = name
        if "kunta" not in where:
            unplaced += 1
        else:
            placed += 1
        nr = str(p.get("tunn") or "").strip()
        t = TYPE_OF.get(p.get("oltyp_nimi") or "", "other")
        by_type[t] += 1
        row = {"nr": nr, "name": (p.get("onimi") or "").strip(), "type": t,
               "type_fi": p.get("oltyp_nimi") or "",
               "kom": where.get("kunta", ""), "kunta": where.get("kunta_name", ""),
               "postinumero": where.get("postinumero", ""), "osa_alue": where.get("osa_alue", ""),
               "lat": round(lat, 6), "lon": round(lon, 6), "address": "",
               "register_year": p.get("til_vuosi")}
        # The page reads a school through `years` / `latest` / `latest_year`, so the results are
        # shaped that way here rather than the page learning a second shape.
        row["years"], row["latest"], row["latest_year"] = {}, {}, {}
        res = ytl_by_norm_name.get(norm_name(row["name"])) if t in ("upper_secondary", "comprehensive_upper") else None
        if res:
            used_names.add(norm_name(row["name"]))
            for session in sorted(res):
                e = res[session]
                cell = {"grade_avg": e.get("mean_total"), "candidates": e.get("n")}
                for code, sub in (e.get("subjects") or {}).items():
                    cell["subj_" + code] = sub["mean"]
                row["years"][session] = cell
            latest = sorted(res)[-1]
            row["latest"] = row["years"][latest]
            row["latest_year"] = {k: latest for k in row["years"][latest]}
            row["ytl_name"] = res[latest].get("name") or ""
        schools.append(row)

    matched = sum(1 for s in schools if s.get("years"))
    lukios = by_type["upper_secondary"] + by_type["comprehensive_upper"]
    unjoined = sorted((ytl[nr][sorted(ytl[nr])[-1]].get("name") or "")
                      for nr in ytl if norm_name(ytl[nr][sorted(ytl[nr])[-1]].get("name") or "")
                      not in used_names)
    print(f"  · {placed:,} schools placed in a kunta, {unplaced} not "
          f"· {matched} of {lukios} lukios joined to a YTL result")
    print(f"  · {len(unjoined)} YTL schools have no exact name match in the register "
          f"(adult lines, schools abroad, renamed schools): {', '.join(unjoined[:4])}…")

    # kunta and national benchmarks, so a popup can say "this school vs its kunta vs Finland"
    # benchmarks the page reads as benchmarks.kunta[kom][session] and benchmarks.finland[session]
    per_kunta = collections.defaultdict(lambda: collections.defaultdict(list))
    for s in schools:
        for session, cell in (s.get("years") or {}).items():
            if cell.get("grade_avg") is not None and s["kom"]:
                per_kunta[s["kom"]][session].append(cell["grade_avg"])
    benchmarks = {
        "kunta": {k: {y: round(statistics.mean(v), 2) for y, v in per.items()}
                  for k, per in per_kunta.items()},
        "finland": {y: (m.get("mean_total")) for y, m in national.items()},
        "finland_detail": national,
    }
    latest_session = sorted(national)[-1] if national else ""
    payload = {
        "built": dt.date.today().isoformat(),
        "retrieved": dt.date.today().isoformat(),
        "n": len(schools),
        "by_type": dict(by_type),
        "sessions": sorted(national),
        "years": sorted(national),
        "latest_session": latest_session,
        "min_candidates": MIN_CANDIDATES,
        "benchmarks": benchmarks,
        "sources": [
            {"label": "Tilastokeskus — oppilaitokset", "licence": REG_LICENCE,
             "url": REG_VERIFY, "used_for": "every school point, with the register's own coordinates"},
            {"label": "Ylioppilastutkintolautakunta — matriculation exam statistics",
             "licence": YTL_LICENCE, "url": YTL_VERIFY,
             "used_for": "upper-secondary results, aggregated from the published candidate file"},
        ],
        "no_comprehensive_results": (
            "Finland publishes no comprehensive-school results. There is no national test result "
            "per peruskoulu to publish — it is not suppressed and it is not behind a licence, it "
            "does not exist. A comprehensive school here is a point with a name and a type."),
        "method": (
            f"Upper-secondary figures are the mean over YTL's own published candidate rows for "
            f"that school and exam session, on YTL's 0–7 grade-point scale. A school session with "
            f"fewer than {MIN_CANDIDATES} candidates is suppressed, and so is a subject fewer than "
            f"{MIN_CANDIDATES} of its candidates sat: a mean over three people describes three "
            f"people. YTL's own `**` is read as suppressed, never as zero. Schools are placed in "
            f"their kunta, postal area and osa-alue by point-in-polygon on this dashboard's own "
            f"rings, because the register publishes coordinates but no area codes."),
        "subjects": SUBJECTS,
        "join": {
            "on": "exact normalised school name, upper-secondary schools only",
            "why": ("Tilastokeskus numbers a school 08888 and YTL numbers it 1488; the two "
                    "systems are unrelated and share no key. The name is the only thing they "
                    "share, and only exact equality is accepted — a near match would attach one "
                    "school's results to another and nothing downstream would reveal it."),
            "matched": matched, "lukios": lukios,
            "unjoined_ytl_schools": unjoined,
        },
        "schools": schools,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    OUT.write_text(text, encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)} ({len(text.encode()):,} B · {len(schools)} schools)")
    print("  types: " + " · ".join(f"{k} {v:,}" for k, v in sorted(by_type.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
