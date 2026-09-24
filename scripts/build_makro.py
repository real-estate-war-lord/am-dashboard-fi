#!/usr/bin/env python3
"""raw + geo + external -> data/processed/makro.json (+ the per-kunta lazy files).

    python3 scripts/build_makro.py [--quiet]

**The hard-data rule.** Every number written here is a published cell or plain arithmetic on
published cells — a difference, a share, a sum, a ratio. There is no fitted trend, no
assumption, no imputation and no cap. A cell the publisher suppressed stays `None` all the
way to the page, where it renders as `–`; it is never read as zero, and an area with no
coverage is not the same as an area whose value is zero.

**Two levels of detail.** 3 018 postal polygons cannot fit inline in one HTML file next to
their values and fifteen years of history. So:

  data/processed/makro.json         inlined in the page: kunnat with coarse rings, full
                                    values and full history; postal areas with their latest
                                    values and a bounding box, but no rings and no history
  data/processed/area/<kunta>.json  fetched when a kunta is opened: the detailed rings and
                                    the full history of that kunta's postal areas

Both come from the same build, so the two can never disagree about which areas exist.

**Codes.** Every area code is a string and keeps its leading zeros. StatFin writes a kunta
as `KU091` in some databases and `091` in others; both normalise to `091` here, once.
`int("091")` is 91, and 91 is Jokioinen.
"""
import argparse
import csv
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import geo_common as G  # noqa: E402
import statfin  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "indicators.json"
RAW = ROOT / "data" / "raw" / "statfin"
EXT = ROOT / "data" / "external"
GEO = ROOT / "data" / "geo"
PROC = ROOT / "data" / "processed"
TOTALS = {"SSS", "SSS_", "TOTAL", "IALT"}      # whole-country / whole-total codes we never map to an area
ANNUAL_YEARS = 12        # years of annual history carried inline (config/indicators.json history_years)
MONTHLY_MONTHS = 60      # months of monthly history — carried in the lazy monthly file, not inline
QUARTERS = 48            # quarters of quarterly history (12 years)
QUIET = False


def say(*a):
    if not QUIET:
        print(*a)


# ---------------------------------------------------------------- reading the pulls

def norm_area(code):
    """'KU091' -> '091'; '091' -> '091'; '00100' -> '00100'. Always a string."""
    c = str(code)
    if c.startswith("KU") and c[2:].isdigit():
        c = c[2:]
    if c.isdigit() and len(c) < 3:
        c = c.zfill(3)
    return c


_files = None


def raw_files():
    global _files
    if _files is None:
        _files = sorted(p for p in RAW.glob("*.json") if not p.name.endswith(".meta.json"))
    return _files


def safe(name):
    return name.replace(":", "__").replace("/", "__")


_cache = {}


def cells(table, key_vars=None, area_v=None, time_v=None, keep_totals=False):
    """Every pull of one table, merged: {area: {period: {code: value}}} plus the stamps.

    `code` is the **cell key**: the values of the dimensions named in the source's
    `key_vars`, joined with "|" in that order. A table split by two things needs both in the
    key — `ashi/13mt` is priced by building type *and* by contentscode, and collapsing it to
    the contentscode alone would silently keep whichever building type was read last.
    `key_vars` comes from the config, not from the chunk that happens to be on disk, so a
    query split across several files still produces the same keys.

    With no `key_vars` the key is the contentscode, or the one other multi-valued dimension
    when the table has no contentscode.
    """
    ck = (table, tuple(key_vars or ()), area_v, time_v, keep_totals)
    if ck in _cache:
        return _cache[ck]
    prefix = safe(table) + "__"
    out, stamps, labels = {}, [], {}
    for p in raw_files():
        if not p.name.startswith(prefix):
            continue
        ds = json.loads(p.read_text(encoding="utf-8"))
        st = statfin.stamp(p)
        if st:
            stamps.append(st)
        ids = ds["id"]
        area_var = area_v if area_v in ids else None
        time_var = time_v if time_v in ids else None
        if not area_var:
            area_var = next((v for v in ids if v.startswith(("alue", "postinumeroalue", "kunta"))
                             or v == "Alue"), None)
        if not time_var:
            time_var = next((v for v in ids if v.startswith("timeperiod")), None)
        if not area_var or not time_var:
            say(f"  ⚠ {p.name}: no area or time dimension ({ids}) — skipped")
            continue
        if area_var in ds["dimension"]:
            labels.update({norm_area(k): v for k, v in statfin.labels(ds, area_var).items()})
        # which dimension carries the "what is this number" code
        if key_vars:
            kv = [v for v in key_vars if v in ids]
        else:
            kv = ["contentscode"] if "contentscode" in ids else []
            if not kv:
                others = [v for v in ids if v not in (area_var, time_var)]
                multi = [v for v in others if len(ds["dimension"][v]["category"]["index"]) > 1]
                kv = multi[:1]
        for r in statfin.rows(ds):
            a = norm_area(r[area_var])
            if a in TOTALS and not keep_totals:
                continue
            t = str(r[time_var])
            code = "|".join(str(r[v]) for v in kv) if kv else "value"
            out.setdefault(a, {}).setdefault(t, {})[code] = r["value"]
    _cache[ck] = (out, stamps, labels)
    return _cache[ck]


def source_cells(src, ind):
    """{area: {period: {code: value}}} for one source entry, with its name mapping applied."""
    if src.get("src") == "statfin":
        data, stamps, labels = cells(src["table"], src.get("key_vars"),
                                    src.get("area_var"), src.get("time_var"))
        alias = src.get("as")
        if alias:
            data = {a: {t: {alias: next(iter(v.values()))} for t, v in per.items()}
                    for a, per in data.items()}
        return data, stamps, labels
    if src.get("src") == "kela":
        return kela_cells(src), [kela_stamp()], {}
    if src.get("src") == "csv":
        return csv_cells(src), [csv_stamp(src)], {}
    if src.get("src") == "climate":
        return climate_cells(src), [climate_stamp(src)], {}
    if src.get("src") == "infra":
        return infra_cells(src), [infra_stamp()], {}
    say(f"  ⚠ {ind['key']}: unknown source type {src.get('src')!r} — skipped")
    return {}, [], {}


def csv_cells(src):
    """A committed CSV written by one of the scripts/import_*.py files.

    The source names its own columns, so a new file source needs no new code here:
        area_col   the kunta code, read as a string
        period_col the year or month
        code_col   which cell this row is (optional; one-measure files leave it out)
        value_col  the number
    """
    p = ROOT / src["file"]
    if not p.exists():
        say(f"  ⚠ {src['file']} missing — run its scripts/import_*.py")
        return {}
    out = {}
    with p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=src.get("delimiter", ";")):
            area = norm_area(row[src["area_col"]])
            t = str(row[src["period_col"]])
            code = row[src["code_col"]] if src.get("code_col") else src.get("as", "value")
            raw = row[src["value_col"]]
            if raw in ("", None):
                continue                       # an empty cell is missing, not zero
            try:
                out.setdefault(area, {}).setdefault(t, {})[code] = float(raw)
            except ValueError:
                continue
    return out


_climate = None


def climate_load():
    """data/processed/climate.json, built by scripts/build_climate.py.

    It is read here rather than computed here because computing it needs numpy and pillow
    (requirements-geo.txt) and `make build` must keep working on a plain Python — the same
    arrangement the services layer uses. The file is committed; `make climate` rebuilds it.
    """
    global _climate
    if _climate is None:
        p = ROOT / "data" / "processed" / "climate.json"
        _climate = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        if not _climate:
            say("  ⚠ data/processed/climate.json missing — run `make climate`")
    return _climate


def climate_cells(src):
    """{area: {period: {code: value}}} out of climate.json.

    Climate figures have no time series: a flood zone is a published map with an edition, not
    an annual observation. They are stamped with the edition year so the page can say when the
    map was drawn, and every year of the dashboard's history shows the same figure — which is
    the truth about a hazard map, not a gap.
    """
    d = climate_load()
    block = (d.get(src["block"]) or {}).get(src["geo"]) or {}
    # the publisher's own edition year, not the day we built the file: a hazard map has an
    # edition, and labelling it with today's date would claim a freshness it does not have
    meta = ((d.get("meta") or {}).get(src["block"]) or {})
    year = str(src.get("period") or meta.get("year") or (d.get("built") or "")[:4])
    out = {}
    for area, vals in block.items():
        for code, v in vals.items():
            if v is None:
                continue
            out.setdefault(norm_area(area), {}).setdefault(year, {})[code] = float(v)
    return out


def climate_stamp(src):
    d = climate_load()
    m = ((d.get("meta") or {}).get(src["block"]) or {})
    return {"table": f"climate/{src['block']}", "label": m.get("source", ""),
            "verify_at_source": m.get("verify_at_source", ""), "licence": m.get("licence", ""),
            "updated": m.get("year") or (d.get("built") or ""), "fetched": d.get("built", ""),
            "publisher": m.get("source", "")}


_infra = None


def infra_load():
    global _infra
    if _infra is None:
        p = ROOT / "data" / "processed" / "infra_index.json"
        _infra = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        if not _infra:
            say("  ⚠ data/processed/infra_index.json missing — run `make infra`")
    return _infra


def infra_cells(src):
    """Counts out of the infra index: projects in the area, and projects within 1 200 m.

    **Only `major` projects are counted.** Väylävirasto's own list runs from a multi-year rail
    programme down to repainting one bridge, and a repaint is not a growth signal. `major` is
    the agency's own behaviour, not our judgement: it wrote a project page for the project.
    Counted over projects that have not opened, because a finished road is not a signal either.
    """
    d = infra_load()
    if not d:
        return {}
    major = set(d.get("major") or [])
    opened = set(d.get("opened") or [])
    year = str((d.get("built") or "")[:4])
    out = {}
    for key, m in (d.get("areas") or {}).items():
        level, _, code = key.partition(":")
        if level != src["geo"]:
            continue
        inside = [i for i in m.get("in", []) if i in major and i not in opened]
        near = [i for i in m.get("near", []) if i in major and i not in opened]
        out.setdefault(norm_area(code), {}).setdefault(year, {})[src["as"]] = float(
            len(inside) if src["as"] == "projects_upcoming" else len(set(inside) | set(near)))
    return out


def infra_stamp():
    d = infra_load()
    return {"table": "infra/index", "label": "Väylävirasto — hanketiedot",
            "verify_at_source": "https://vayla.fi/kaikki-hankkeet",
            "licence": "CC BY 4.0 — Lähde: Väylävirasto",
            "updated": d.get("built", ""), "fetched": d.get("built", ""),
            "publisher": "Väylävirasto"}


def csv_stamp(src):
    p = ROOT / (src["file"] + ".meta.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


_kela = None


def kela_cells(src):
    """Kela's December stock per kunta, plus the newest published month, keyed by year."""
    global _kela
    if _kela is not None:
        return _kela
    p = ROOT / src.get("file", "data/external/kela_asumistuki.csv")
    if not p.exists():
        say(f"  ⚠ {p} missing — run scripts/import_kela.py")
        _kela = {}
        return _kela
    out = {}
    with p.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            # the December figure is that year's value; a newer month replaces it under its own year
            year = row["period"][:4]
            cur = out.setdefault(norm_area(row["kunta"]), {})
            prev = cur.get(year, {})
            if not prev or row["period"] >= prev.get("_period", ""):
                cur[year] = {"kela_saajat": float(row["households"]), "_period": row["period"]}
    for a in out:
        for y in out[a]:
            out[a][y].pop("_period", None)
    _kela = out
    return out


def kela_stamp():
    p = EXT / "kela_asumistuki.csv.meta.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ---------------------------------------------------------------- the projection

PROJ_CALCS = {"proj_growth", "proj_abs", "proj_growth_5y", "proj_rate_5y", "proj_group",
              "proj_share_rel"}
_proj_cache = {}


def projection(src):
    """{area: {year: {"pop": n, "groups": {band: n}}}} plus the national row.

    Väestöennuste 2024 is one vintage, not a series of releases: every figure in the Outlook
    group comes from this single published projection, and nothing is fitted, extrapolated or
    blended with anything else. The age bands are sums of the projection's own single-year
    cells — a sum of published cells, which is all the hard-data rule allows and all that is
    needed.
    """
    key = (src["table"], json.dumps(src.get("ages") or {}, sort_keys=True))
    if key in _proj_cache:
        return _proj_cache[key]
    # the whole-country row is kept here on purpose: "the area's 20–34 share versus Finland's"
    # needs Finland's own projected share, from the same projection, not from anywhere else
    raw, stamps, _ = cells(src["table"], src.get("key_vars"), src.get("area_var"),
                           src.get("time_var"), keep_totals=True)
    bands = src.get("ages") or {}
    out = {}
    for area, per_year in raw.items():
        rows = {}
        for year, codes in per_year.items():
            pop = codes.get("SSS")
            groups = {}
            for band, ages in bands.items():
                got = [codes.get(a) for a in ages]
                groups[band] = sum(v for v in got if v is not None) if any(
                    v is not None for v in got) else None
            rows[year] = {"pop": pop, "groups": groups}
        out[area] = rows
    _proj_cache[key] = (out, stamps)
    return out, stamps


def proj_value(ind, rows, nat, proj):
    """One number for one area — a vintage, not a series, so there is no history to return."""
    calc = ind["calc"]
    a, b = str(proj.get("from")), str(proj.get("to"))
    five = str(int(a) + 5)
    p0 = (rows.get(a) or {}).get("pop")
    p1 = (rows.get(b) or {}).get("pop")
    p5 = (rows.get(five) or {}).get("pop")
    if calc == "proj_growth":
        return None if not p0 or p1 is None else (p1 / p0 - 1) * 100.0
    if calc == "proj_abs":
        return None if p0 is None or p1 is None else p1 - p0
    if calc == "proj_growth_5y":
        return None if not p0 or p5 is None else (p5 / p0 - 1) * 100.0
    if calc == "proj_rate_5y":
        return None if not p0 or p5 is None else (p5 - p0) / 5.0 / p0 * 1000.0
    gk = ind.get("group_key")
    g0 = ((rows.get(a) or {}).get("groups") or {}).get(gk)
    g1 = ((rows.get(b) or {}).get("groups") or {}).get(gk)
    if calc == "proj_group":
        return None if not g0 or g1 is None else (g1 / g0 - 1) * 100.0
    if calc == "proj_share_rel":
        nb = (nat.get(b) or {})
        np_, ng = nb.get("pop"), (nb.get("groups") or {}).get(gk)
        if not p1 or g1 is None or not np_ or ng is None:
            return None
        return g1 / p1 * 100.0 - ng / np_ * 100.0
    return None


# ---------------------------------------------------------------- the calcs

def ssum(vals):
    """Sum, but None if every input is missing — a suppressed cell is not a zero."""
    got = [v for v in vals if v is not None]
    return sum(got) if got else None


DWELLINGS = {}       # {area code: dwelling stock} — kunta codes and MK<nn> maakunta codes


def calc_series(ind, per_period, area=None):
    """{period: value} for one area, from {period: {code: value}}."""
    calc = ind.get("calc", "passthrough")
    num, den = ind.get("num") or [], ind.get("den") or []
    out = {}
    periods = sorted(per_period)
    if calc == "passthrough":
        for t in periods:
            out[t] = per_period[t].get(num[0]) if num else None
    elif calc in ("share_pct", "ratio_pct"):
        for t in periods:
            c = per_period[t]
            n = ssum(c.get(k) for k in num)
            d = ssum(c.get(k) for k in den)
            # every numerator cell must be present, or the share is of an unknown part
            if n is None or d is None or d == 0 or any(c.get(k) is None for k in num):
                out[t] = None
            else:
                out[t] = n / d * 100.0
    elif calc == "weighted_mean":
        # Σ(value × weight) ÷ Σ(weight) over the codes listed — the exact arithmetic mean over
        # the underlying transactions when `num` is itself an arithmetic mean per transaction
        # and `weight` is that mean's own count. ashi publishes both cells for every building
        # type, so aggregating room-count classes needs no assumption.
        wt = ind.get("weight") or []
        for t in periods:
            c = per_period[t]
            tot_w = 0.0
            tot_v = 0.0
            for k, w in zip(num, wt):
                v, n_ = c.get(k), c.get(w)
                if v is None or n_ in (None, 0):
                    continue
                tot_v += v * n_
                tot_w += n_
            out[t] = tot_v / tot_w if tot_w else None
    elif calc == "sum":
        for t in periods:
            out[t] = ssum(per_period[t].get(k) for k in num)
    elif calc == "per_1000":
        for t in periods:
            c = per_period[t]
            n = ssum(c.get(k) for k in num)
            d = ssum(c.get(k) for k in den)
            out[t] = None if n is None or not d else n / d * 1000.0
    elif calc == "per_1000_dwellings":
        # the denominator is the area's own dwelling stock, the same stock for every period,
        # so a rate computed for a maakunta stays a maakunta rate when it is inherited
        d = DWELLINGS.get(area)
        for t in periods:
            n = ssum(per_period[t].get(k) for k in num)
            out[t] = None if n is None or not d else n / d * 1000.0
    elif calc == "yoy_pct":
        key = num[0]
        for i, t in enumerate(periods):
            if i == 0:
                continue
            a = per_period[periods[i - 1]].get(key)
            b = per_period[t].get(key)
            out[t] = None if a in (None, 0) or b is None else (b / a - 1.0) * 100.0
    else:
        say(f"  ⚠ {ind['key']}: unknown calc {calc!r}")
        return {}
    return {t: v for t, v in out.items() if v is not None}


DP = {"pct0": 1, "pct1": 2, "signpct1": 2, "eur0": 0, "eur1": 2, "m2": 1, "int": 0, "per1000": 2}


def cadence(period):
    """'2024' -> 'y', '2026Q1' -> 'q', '2026M08' -> 'm'."""
    return "m" if "M" in period else "q" if "Q" in period else "y"


def split_cadence(ind, per_period, area=None):
    """(annual-or-monthly series, quarterly series) — computed separately.

    Cells of different cadence never combine: a yearly figure and a quarterly one are two
    series, not one. The annual series is what the map and the year selector use; the
    quarterly one backs the Yearly | Quarterly toggle and the trend chart.
    """
    groups = {}
    for t, codes in per_period.items():
        groups.setdefault(cadence(t), {})[t] = codes
    ya = {}
    for c in ("y", "m"):
        if groups.get(c):
            ya.update(trim(round_series(calc_series(ind, groups[c], area), ind.get("fmt", "")),
                           ANNUAL_YEARS, MONTHLY_MONTHS))
    q = (trim(round_series(calc_series(ind, groups["q"], area), ind.get("fmt", "")),
              ANNUAL_YEARS, MONTHLY_MONTHS) if groups.get("q") else {})
    return ya, q


def round_series(s, fmt=""):
    """Round to what the format actually shows, plus one digit. Bytes matter: this file is
    inlined in the page, and a trailing 0.0000001 on 45 000 cells is a hundred kilobytes."""
    dp = DP.get(fmt, 3)
    return {t: (round(v, dp) if isinstance(v, float) else v) for t, v in s.items()}


def trim(series, annual_years, monthly_months, quarters=QUARTERS):
    """Keep a window of history, newest first. Everything published stays available at source;
    this is only what the page carries inline."""
    if not series:
        return series
    keys = sorted(series)
    if any("M" in k for k in keys):
        keep = keys[-monthly_months:]
    elif any("Q" in k for k in keys):
        keep = keys[-quarters:]
    else:
        keep = keys[-annual_years:]
    return {k: series[k] for k in keep}


# ---------------------------------------------------------------- geometry

def load_geo(name):
    p = GEO / f"{name}.geojson"
    if not p.exists():
        sys.exit(f"✗ {p} missing — run `make geo` first")
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    global QUIET
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    QUIET = args.quiet

    global ANNUAL_YEARS
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    ANNUAL_YEARS = int(cfg.get("history_years") or ANNUAL_YEARS)
    inds = cfg.get("indicators", [])
    if not inds:
        say("config/indicators.json has no indicators — writing an empty makro.json")

    kunnat_coarse = load_geo("kunnat_coarse")
    kunnat_detail = load_geo("kunnat")
    postal_coarse = load_geo("postinumerot_coarse")
    postal_detail = load_geo("postinumerot")

    kmeta = {f["properties"]["kunta"]: f["properties"] for f in kunnat_detail["features"]}
    krings = {f["properties"]["kunta"]: G.rings_of(f["geometry"]) for f in kunnat_coarse["features"]}
    pmeta = {f["properties"]["nr"]: f["properties"] for f in postal_detail["features"]}
    prings = {f["properties"]["nr"]: G.rings_of(f["geometry"]) for f in postal_detail["features"]}

    # name_sv rides along because Finland is bilingual and the address search must accept
    # "Helsingfors" as readily as "Helsinki"; it is dropped again when it equals the Finnish name
    KUNTA = {c: {"code": c, "name": p["name"], "region": p.get("region", ""),
                 "maakunta": p.get("maakunta", ""), "rings": krings.get(c, []),
                 **({"name_sv": p["name_sv"]} if p.get("name_sv") and p["name_sv"] != p["name"] else {}),
                 "hist": {}, "histq": {}, "inh": []}
             for c, p in kmeta.items()}
    AREA = {n: {"nr": n, "name": p["name"], "muni": p["kunta"], "bb": p["bb"], "c": p.get("c"),
                "hist": {}, "histq": {}, "inh": []}
            for n, p in pmeta.items()}

    say(f"· {len(KUNTA)} kunnat · {len(AREA)} postinumeroalueet")

    # Dwelling stock per kunta and per maakunta, from Paavo's latest year. It is the
    # denominator of every per-1 000-dwellings rate, and a maakunta's stock is the sum of its
    # kunnat's published stocks — a sum of published cells, nothing more.
    pa_k, _, _ = cells("Postinumeroalueittainen_avoin_tieto:uusin/12f8")
    dw_year = ""
    for code, per in pa_k.items():
        yrs = [t for t in per if per[t].get("ra_asunn") is not None]
        if not yrs:
            continue
        t = max(yrs)
        dw_year = max(dw_year, t)
        DWELLINGS[code] = per[t]["ra_asunn"]
    # Paavo publishes the maakunta totals itself; only where it does not is the total built
    # by summing the kunnat's own published stocks
    missing_mk = {}
    for code, o in KUNTA.items():
        mk = "MK" + str(o.get("maakunta") or "")
        if mk not in DWELLINGS and code in DWELLINGS:
            missing_mk[mk] = missing_mk.get(mk, 0) + DWELLINGS[code]
    DWELLINGS.update(missing_mk)
    say(f"· dwelling stock {dw_year}: {len([k for k in DWELLINGS if k.isdigit()])} kunnat, "
        f"{len([k for k in DWELLINGS if k.startswith('MK')])} maakunnat "
        f"(Finland {sum(v for k, v in DWELLINGS.items() if k.isdigit()):,})")

    # ---- compute every indicator at every level it has a source for -----------------------
    sources_meta, out_inds, dropped = {}, [], {}
    periods_seen = set()
    for ind in inds:
        entry = {k: ind[k] for k in ("key", "label", "short", "unit", "fmt", "group", "direction",
                                     "level", "hue", "desc", "source") if k in ind}
        for k in ("note", "warn", "chip", "src_verify", "tables", "proj", "group_key"):
            if ind.get(k):
                entry[k] = ind[k]
        entry["asof"] = {}
        entry["coverage"] = {}
        entry["years"] = []
        entry["quarters"] = []
        # merge every source that serves the same level before computing: an indicator whose
        # numerator and denominator come from two publishers (Kela ÷ Paavo) needs both cells
        # in the same {area: {period: {code: value}}} before the division can happen.
        # An Outlook indicator is one vintage of one published projection. It has no history,
        # so it never goes through the per-period machinery.
        if ind.get("calc") in PROJ_CALCS:
            src = next((x for x in ind.get("sources", []) if x.get("projection")), None)
            if src:
                rows_by_area, stamps = projection(src)
                for st in stamps:
                    if st:
                        sources_meta[st.get("table") or str(len(sources_meta))] = st
                nat = rows_by_area.get("SSS") or {}
                proj = ind.get("proj") or {}
                hit = 0
                for code, o in KUNTA.items():
                    rows = rows_by_area.get(code)
                    if not rows:
                        continue
                    v = proj_value(ind, rows, nat, proj)
                    if v is None:
                        continue
                    o[ind["key"]] = round(v, DP.get(ind.get("fmt", ""), 3))
                    hit += 1
                    if "fc_pop" not in o:
                        o["fc_pop"] = {y: r["pop"] for y, r in sorted(rows.items())
                                       if r["pop"] is not None}
                        o["fc_groups"] = {y: {k: g for k, g in (rows.get(y) or {}).get("groups", {}).items()
                                              if g is not None}
                                          for y in (str(proj.get("from")), str(proj.get("to")))
                                          if rows.get(y)}
                entry["coverage"]["kunta"] = hit
                entry["asof"]["kunta"] = str(proj.get("to") or "")
                say(f"  {ind['key']:12} {'kunta':12} {hit:>5} own · projection "
                    f"{proj.get('from')}→{proj.get('to')} · {proj.get('vintage')}")
            entry["years"].sort()
            entry["quarters"].sort()
            if not entry["quarters"]:
                entry.pop("quarters")
            out_inds.append(entry)
            continue
        by_geo, inherit_from = {}, None
        for src in ind.get("sources", []):
            inherit_from = inherit_from or src.get("inherit")
            geo = src.get("geo")
            if geo not in ("kunta", "postinumero"):
                say(f"  ⚠ {ind['key']}: source with geo {geo!r} — skipped")
                continue
            data, stamps, _labels = source_cells(src, ind)
            for st in stamps:
                if st:
                    sources_meta[st.get("table") or st.get("source") or str(len(sources_meta))] = st
            # ashi spells the same building type differently in 13mt (room-count classes of
            # blocks of flats) and 13mx (0 total / 1 terraced / 3 blocks of flats). A source may
            # therefore rename its own cells onto the indicator's names, rather than the
            # indicator pretending one code list fits every table.
            rename = src.get("cells") or {}
            dest = by_geo.setdefault(geo, {})
            for area, per_period in data.items():
                d = dest.setdefault(area, {})
                for t, codes in per_period.items():
                    row = d.setdefault(t, {})
                    for k, v in codes.items():
                        row[rename.get(k, k)] = v
        for geo, data in by_geo.items():
            pool = KUNTA if geo == "kunta" else AREA
            miss, hit, latest_period, qhit = 0, 0, "", 0
            spare = {}                       # values published for a coarser area (MK01 …)
            for area, per_period in data.items():
                o = pool.get(area)
                if o is None:
                    if inherit_from and area.startswith("MK"):
                        spare[area] = per_period
                    else:
                        miss += 1
                        dropped.setdefault(ind["key"], set()).add(area)
                    continue
                y, q = split_cadence(ind, per_period, area)
                if y:
                    o["hist"][ind["key"]] = y
                    latest_period = max(latest_period, max(y))
                    hit += 1
                if q:
                    o["histq"][ind["key"]] = q
                    qhit += 1
                    if not y:
                        latest_period = max(latest_period, max(q))
                        hit += 1
            # a figure the publisher only gives for the whole maakunta is shown on its kunnat,
            # marked ^ so nobody reads it as that kunta's own measurement
            inherited = 0
            if inherit_from and spare:
                for code, o in pool.items():
                    if ind["key"] in o["hist"] or ind["key"] in o["histq"]:
                        continue
                    mk = "MK" + str(o.get("maakunta") or "")
                    per_period = spare.get(mk)
                    if not per_period:
                        continue
                    # computed for the maakunta, on the maakunta's own denominator: a rate
                    # inherited by a kunta must still be the maakunta's rate, not the
                    # maakunta's numerator over that kunta's denominator
                    y, q = split_cadence(ind, per_period, mk)
                    if y:
                        o["hist"][ind["key"]] = y
                        latest_period = max(latest_period, max(y))
                    if q:
                        o["histq"][ind["key"]] = q
                        if not y:
                            latest_period = max(latest_period, max(q))
                    if y or q:
                        o["inh"].append(ind["key"])
                        inherited += 1
                if inherited:
                    entry["inherited"] = {"level": inherit_from, "areas": inherited}
            if latest_period:
                entry["asof"][geo] = latest_period
            entry["coverage"][geo] = hit + inherited
            # the periods this indicator actually has, recorded in the registry so the year
            # selector and the charts know the axis without the history being in the page
            for o in pool.values():
                for t in (o["hist"].get(ind["key"]) or {}):
                    if cadence(t) == "y" and t not in entry["years"]:
                        entry["years"].append(t)
                for t in (o["histq"].get(ind["key"]) or {}):
                    if t not in entry["quarters"]:
                        entry["quarters"].append(t)
            if qhit:
                entry.setdefault("quarterly", {})[geo] = qhit
            periods_seen.update(
                t for o in pool.values() for t in (o["hist"].get(ind["key"]) or {}))
            say(f"  {ind['key']:12} {geo:12} {hit:>5} own"
                + (f" + {inherited} ^{inherit_from}" if inherit_from and inherited else "")
                + (f" · {qhit} quarterly" if qhit else "")
                + f" · latest {latest_period or '–'}"
                + (f" · {miss} codes outside this level" if miss else ""))
        entry["years"].sort()
        entry["quarters"].sort()
        if not entry["quarters"]:
            entry.pop("quarters")
        out_inds.append(entry)

    # the live value of each indicator is the newest period it actually has for that area
    for pool in (KUNTA, AREA):
        for o in pool.values():
            for key, s in o["hist"].items():
                o[key] = s[max(s)]
            for key, s in o["histq"].items():
                if key not in o["hist"]:       # quarterly-only indicator: its newest quarter
                    o[key] = s[max(s)]

    # population rides along as an attribute, not an indicator: every popup shows it
    pop_k, _, _ = cells("Postinumeroalueittainen_avoin_tieto:uusin/12f8")
    pop_p, _, _ = cells("Postinumeroalueittainen_avoin_tieto:uusin/12f7")
    vaerak, _, _ = cells("vaerak/11re")
    for code, o in KUNTA.items():
        per = vaerak.get(code) or pop_k.get(code) or {}
        years = [t for t in per if (per[t].get("he_vakiy") or per[t].get("vaerak-vaesto")) is not None]
        if years:
            t = max(years)
            o["pop"] = per[t].get("he_vakiy") or per[t].get("vaerak-vaesto")
            o["pop_year"] = t
            ph = {y: (per[y].get("he_vakiy") or per[y].get("vaerak-vaesto"))
                  for y in sorted(per) if (per[y].get("he_vakiy") or per[y].get("vaerak-vaesto")) is not None}
            o["pop_hist"] = trim(ph, ANNUAL_YEARS, MONTHLY_MONTHS)
    for nr, o in AREA.items():
        per = pop_p.get(nr) or {}
        years = [t for t in per if per[t].get("he_vakiy") is not None]
        if years:
            t = max(years)
            o["pop"] = per[t]["he_vakiy"]
            o["pop_year"] = t

    years = sorted({t for t in periods_seen if len(t) == 4 and t.isdigit()})
    latest_year = years[-1] if years else ""

    # ---- the inline payload ---------------------------------------------------------------
    # A monthly series is ten times the rows of an annual one and would take a third of the
    # inline budget on its own. It moves to dist/monthly.json, which the page fetches the
    # first time a monthly indicator is selected — the same trade as the per-kunta files.
    monthly_keys = sorted({k for o in KUNTA.values() for k, h in o["hist"].items()
                           if any("M" in t for t in h)})
    monthly = {"built": dt.date.today().isoformat(), "keys": monthly_keys, "kunta": {}}
    for code, o in KUNTA.items():
        rows = {k: o["hist"].pop(k) for k in monthly_keys if k in o["hist"]}
        if rows:
            monthly["kunta"][code] = rows
    # the observed-population series is only read by the Outlook chart on one area page at a
    # time, so it travels in that kunta's lazy file rather than in every page load
    pop_hist = {c: o.pop("pop_hist") for c, o in KUNTA.items() if o.get("pop_hist")}
    # the projected series and the age split are read by one area page at a time, like the
    # observed series they are drawn beside
    fc_pop = {c: o.pop("fc_pop") for c, o in KUNTA.items() if o.get("fc_pop")}
    fc_groups = {c: o.pop("fc_groups") for c, o in KUNTA.items() if o.get("fc_groups")}
    # Every kunta's full history in one file. The map and the table at the latest period need
    # none of it; a chart, an area page, the "Δ since" column or any earlier year needs all of
    # it at once, so it is one fetch rather than 308.
    kunta_hist = {}
    for c, o in KUNTA.items():
        row = {}
        if o.get("hist"):
            row["hist"] = o["hist"]
        if o.get("histq"):
            row["histq"] = o["histq"]
        if row:
            kunta_hist[c] = row
    for o in KUNTA.values():
        o.pop("hist", None)
        o.pop("histq", None)
    for o in KUNTA.values():
        if not o.get("inh"):
            o.pop("inh", None)
        if not o.get("histq"):
            o.pop("histq", None)
    munis = [KUNTA[c] for c in sorted(KUNTA)]
    areas = []
    for nr in sorted(AREA):
        o = dict(AREA[nr])
        o.pop("hist", None)                 # history rides in the per-kunta file
        o.pop("histq", None)
        if not o.get("inh"):
            o.pop("inh", None)
        o.pop("pop_year", None)             # the same year for every area — it is in meta
        o.pop("c", None)                    # the page takes a label point from the bounding box
        o["bb"] = [round(x, 4) for x in o["bb"]]
        areas.append(o)
    meta = {
        "built": dt.date.today().isoformat(),
        "years": years, "latest_year": latest_year,
        "levels": {"kunta": len(munis), "postinumero": len(areas)},
        "vintage": {"kuntajako": kunnat_detail["meta"].get("vintage"),
                    "paavo": postal_detail["meta"].get("layer"),
                    "paavo_statistics_year": postal_detail["meta"].get("statistics_year")},
        "attribution": ["Lähde: Tilastokeskus (CC BY 4.0)", "Lähde: Kela (CC BY 4.0)",
                        "Boundaries: Tilastokeskus, Helsingin kaupunki, HSY (CC BY 4.0)"],
        "note": ("Every figure is a published cell or plain arithmetic on published cells. "
                 "A suppressed figure is shown as – and is never read as zero."),
        "sources": [{"key": st.get("table") or "kela", "label": st.get("label") or st.get("source", ""),
                     "url": st.get("verify_at_source") or st.get("dataset", ""),
                     "tables": st.get("table", ""), "asof": st.get("updated", "")[:10],
                     "fetched": st.get("fetched", ""), "licence": st.get("licence", "")}
                    for st in sources_meta.values()],
        "lazy": {"hist": "hist.json — every kunta's full history, fetched for a chart, an area "
                         "page or any period other than the latest",
                 "area": "area/<kunta>.json — one kunta's detailed postal rings, its postal "
                         "areas' history and its own observed-population series",
                 "monthly": "monthly.json — every monthly series, fetched when one is selected"},
        "monthly_keys": monthly_keys,
        "paavo_year": postal_detail["meta"].get("statistics_year"),
    }
    PROC.mkdir(parents=True, exist_ok=True)
    doc = {"meta": meta, "indicators": out_inds, "municipalities": munis, "areas": areas}
    out = PROC / "makro.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n = out.stat().st_size
    say(f"wrote {out.relative_to(ROOT)} ({n:,} B)" + ("" if n <= G.MAX_BYTES else "   ⚠ OVER 3 MB"))

    hp = PROC / "hist.json"
    hp.write_text(json.dumps({"built": dt.date.today().isoformat(), "kunta": kunta_hist},
                             ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    say(f"wrote {hp.relative_to(ROOT)} ({hp.stat().st_size:,} B · {len(kunta_hist)} kunnat)")

    mp = PROC / "monthly.json"
    mp.write_text(json.dumps(monthly, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    say(f"wrote {mp.relative_to(ROOT)} ({mp.stat().st_size:,} B · {len(monthly_keys)} series · "
        f"{len(monthly['kunta'])} kunnat)")

    # ---- the per-kunta lazy payload --------------------------------------------------------
    adir = PROC / "area"
    for old in adir.glob("*.json"):
        old.unlink()
    adir.mkdir(parents=True, exist_ok=True)
    by_kunta, biggest = {}, 0
    for nr, o in AREA.items():
        by_kunta.setdefault(o["muni"], []).append(nr)
    for kunta, nrs in sorted(by_kunta.items()):
        rows = [{"nr": nr, "rings": prings.get(nr, []), "hist": AREA[nr]["hist"],
                 "histq": AREA[nr]["histq"]} for nr in sorted(nrs)]
        p = adir / f"{kunta}.json"
        p.write_text(json.dumps({"kunta": kunta, "built": meta["built"], "areas": rows,
                                 "pop_hist": pop_hist.get(kunta, {}),
                                 "fc_pop": fc_pop.get(kunta, {}),
                                 "fc_groups": fc_groups.get(kunta, {})},
                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        biggest = max(biggest, p.stat().st_size)
    say(f"wrote {len(by_kunta)} per-kunta files in {adir.relative_to(ROOT)} "
        f"(largest {biggest:,} B)")

    if dropped:
        # most of these are the publisher's own aggregates riding in the same table (MK01 =
        # a maakunta, ELY03 = an employment district). They are not kunnat and are meant to
        # be left out. The rest are codes from an older kuntajako and are reported by name.
        agg, gone = set(), set()
        for codes in dropped.values():
            for c in codes:
                (agg if not c.isdigit() else gone).add(c)
        say(f"\n· {len(agg)} publisher aggregates in the same tables, correctly not mapped to a kunta: "
            + ", ".join(sorted(agg)[:10]) + (" …" if len(agg) > 10 else ""))
        if gone:
            k5 = sorted(c for c in gone if len(c) == 5)
            k3 = sorted(c for c in gone if len(c) != 5)
            if k3:
                say(f"· {len(k3)} kunta codes not in {kunnat_detail['meta'].get('vintage')} "
                    f"— dropped, never guessed onto a neighbour: " + ", ".join(k3))
            if k5:
                say(f"· {len(k5)} postal codes not in the 2026 Paavo vintage (the price and rent "
                    f"tables are on older classifications) — dropped: " + ", ".join(k5[:12])
                    + (" …" if len(k5) > 12 else ""))
    if n > G.MAX_BYTES:
        sys.exit(f"✗ makro.json is {n:,} B, over the {G.MAX_BYTES:,} B ceiling")


if __name__ == "__main__":
    main()
