#!/usr/bin/env python3
"""StatFin PxWeb client — stdlib only.

Statistics Finland's open PxWeb API, keyless, CC BY 4.0 ("Lähde: Tilastokeskus").
There is **no PxWebApi v2**: /api/v2/, /api/v2-beta/ and statfin.stat.fi/api/v2/ all
answer 404 (probed 2026-09-24, docs/PROBE_FI.md). v1 it is.

    GET  {BASE}/{db}/                 list the tables in a sub-database
    GET  {BASE}/{db}/{id}.px          the table's metadata (variables, value codes, texts)
    POST {BASE}/{db}/{id}.px          the data, body = {"query":[…],"response":{"format":"json-stat2"}}

A table is named "<db>/<id>" everywhere in this repo (config/indicators.json, the fetch
stamps, the verify-at-source links), because the id alone is not unique across databases.

House rules, all of them the publisher's:
  · ~10 calls / 10 s — THROTTLE is honoured between every call, and a 429 or 503 backs off.
  · a cell cap per call — a query that asks for too much comes back 403; split it.
  · every pull writes <file>.meta.json beside it with the URL, the query, the response's
    `updated` stamp and the fetch date, so a figure can always be traced to its pull.

Some tables live in the frozen archive database StatFin_Passiivi (asvu/13eb, asas, ras …):
pass db="StatFin_Passiivi" via a "<database>:<db>/<id>" table name.
"""
import datetime as dt
import gzip
import io
import json
import pathlib
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
HOST = "https://pxdata.stat.fi/PxWeb/api/v1"
LANG = "en"
UA = "am-dashboard-fi/1.0 (open-data dashboard; contact via repository)"
THROTTLE = 1.2          # seconds between calls — comfortably inside ~10 calls / 10 s
RETRIES = 4
TIMEOUT = 180

_last = [0.0]


def _wait():
    d = THROTTLE - (time.time() - _last[0])
    if d > 0:
        time.sleep(d)
    _last[0] = time.time()


def split_table(name):
    """"ashi/13mt" -> ("StatFin", "ashi", "13mt"); "StatFin_Passiivi:asvu/13eb_2025q4" likewise."""
    database = "StatFin"
    if ":" in name:
        database, name = name.split(":", 1)
    db, _, tid = name.partition("/")
    if not db or not tid:
        raise ValueError(f"table name must be '<db>/<id>', got {name!r}")
    return database, db, tid


def api_id(database, db, tid):
    """The id the API path wants.

    Live StatFin serves short ids ("13mt.px"). The frozen StatFin_Passiivi serves the long
    form ("statfinpas_asvu_pxt_13eb_2025q4.px") — the same spelling its table page uses. The
    config always names a table the short way and this fills in the rest.
    """
    if database.endswith("Passiivi") and not tid.startswith("statfinpas_"):
        return f"statfinpas_{db}_pxt_{tid}"
    return tid


def table_url(name):
    database, db, tid = split_table(name)
    return f"{HOST}/{LANG}/{database}/{db}/{api_id(database, db, tid)}.px"


def ui_url(name):
    """The published table page a reader can open — the 'Verify at source' destination.

    Same id as the API path, in the PxWeb UI's own folder spelling:
    .../PxWeb/pxweb/en/<database>/<database>__<db>/<id>.px/  (probed 2026-09-24; the
    statfin_<db>_pxt_<id> spelling that appears in older links answers HTTP 500).
    """
    database, db, tid = split_table(name)
    return (f"https://pxdata.stat.fi/PxWeb/pxweb/{LANG}/{database}/{database}__{db}/"
            f"{api_id(database, db, tid)}.px/")


def _open(req):
    last = None
    for attempt in range(RETRIES):
        _wait()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                return body, r.status
        except urllib.error.HTTPError as e:
            last = e
            # 429 too many requests, 403 too many cells (do not retry), 5xx transient
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(4 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"giving up after {RETRIES} attempts: {last}")


def meta(name):
    """The table's metadata: {"title": …, "variables": [{code, text, values, valueTexts, …}]}."""
    req = urllib.request.Request(table_url(name), headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    body, _ = _open(req)
    return json.loads(body)


def tables(db, database="StatFin"):
    """Every table in a sub-database: [{"id": "13mt.px", "text": "13mt -- …", "updated": …}]."""
    req = urllib.request.Request(f"{HOST}/{LANG}/{database}/{db}/",
                                 headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    body, _ = _open(req)
    return json.loads(body)


def query(name, sel):
    """POST a selection and return the json-stat2 dataset.

    `sel` is {variable code: value codes}. A value list of ["*"] becomes filter "all" with
    the wildcard; anything else is an explicit item list, so a typo is a 400 from the
    publisher rather than a silently different number. A variable left out is returned as
    its total ONLY when the metadata says elimination — check before you leave one out.
    """
    q = []
    for code, values in sel.items():
        vs = values if isinstance(values, (list, tuple)) else [values]
        if list(vs) == ["*"]:
            q.append({"code": code, "selection": {"filter": "all", "values": ["*"]}})
        else:
            q.append({"code": code, "selection": {"filter": "item", "values": [str(v) for v in vs]}})
    payload = json.dumps({"query": q, "response": {"format": "json-stat2"}}).encode("utf-8")
    req = urllib.request.Request(table_url(name), data=payload,
                                 headers={"User-Agent": UA, "Content-Type": "application/json",
                                          "Accept-Encoding": "gzip"})
    body, _ = _open(req)
    return json.loads(body)


def rows(ds):
    """json-stat2 dataset -> [{dimension id: value code, …, "value": float|None}].

    Row order follows the dataset's own `id`/`size`, so it does not depend on the order the
    variables were asked for. A null cell stays None: a suppressed figure is not a zero.
    """
    ids, sizes = ds["id"], ds["size"]
    cats = []
    for d in ids:
        idx = ds["dimension"][d]["category"]["index"]
        cats.append(list(idx) if isinstance(idx, list)
                    else [c for c, _ in sorted(idx.items(), key=lambda kv: kv[1])])
    values = ds["value"]
    n = 1
    for s in sizes:
        n *= s
    out = []
    for flat in range(n):
        rem, row = flat, {}
        for k in range(len(ids) - 1, -1, -1):      # json-stat2 is row-major: the last dimension varies fastest
            rem, idx = divmod(rem, sizes[k])
            row[ids[k]] = cats[k][idx]
        row["value"] = values[flat] if isinstance(values, list) else values.get(str(flat))
        out.append(row)
    return out


def labels(ds, dim):
    """{value code: published label} for one dimension — used for kunta and area names."""
    return dict(ds["dimension"][dim]["category"]["label"])


def pull(name, sel, out, note=""):
    """Fetch, write <out> and the <out>.meta.json stamp beside it. Returns the dataset."""
    ds = query(name, sel)
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ds, ensure_ascii=False), encoding="utf-8")
    stamp = {
        "table": name,
        "url": table_url(name),
        "verify_at_source": ui_url(name),
        "query": sel,
        "updated": (ds.get("updated") or ""),
        "label": ds.get("label", ""),
        "fetched": dt.date.today().isoformat(),
        "publisher": "Tilastokeskus",
        "licence": "CC BY 4.0 — Lähde: Tilastokeskus",
        "note": note,
        "cells": len(ds.get("value", [])) if isinstance(ds.get("value"), list) else None,
    }
    out.with_suffix(out.suffix + ".meta.json").write_text(
        json.dumps(stamp, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return ds


def load(out):
    """Read a previous pull back, or None when it has not been fetched yet."""
    p = pathlib.Path(out)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def stamp(out):
    p = pathlib.Path(str(out) + ".meta.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
