#!/usr/bin/env python3
"""Aluesarjat PxWeb client — the Helsinki-region statistics database. Stdlib only.

    https://stat.hel.fi/api/v1/fi/Aluesarjat/<folder>/<table>.px

Same PxWeb v1 shape as StatFin, different host, and **a different licence**: Aluesarjat's
terms say the data may be used for **non-commercial purposes** ("Tietoaineistoa voi käyttää
ei-kaupallisiin tarkoituksiin"). That is not CC BY 4.0, and it is the reason the osa-alue
layer carries its own licence line in the UI and in docs/SOURCES.md. Commercial use needs
permission from the publisher.

Walk the **Finnish** tree: `/api/v1/fi/Aluesarjat/` has seven folders, the English one two.

Two traps, both handled by callers here:
  · a variable left out of the query is ELIMINATED to its total, so every dimension is
    always named explicitly;
  · the area variable is spelled `Alue` in some tables and `Osa-alue` in others, and the
    wrong one is an HTTP 400.

Area codes are ten digits: kunta(3) + suurpiiri(1) + peruspiiri(3) + osa-alue(3). They are
exactly Helsingin kaupunki's own `kokotunnus`, which is what `data/geo/osa_alueet.geojson`
stores, so the join needs no crosswalk.
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
HOST = "https://stat.hel.fi/api/v1/fi/Aluesarjat"
UI = "https://stat.hel.fi/pxweb/fi/Aluesarjat"
UA = "am-dashboard-fi/1.0 (open-data dashboard; contact via repository)"
THROTTLE = 1.0
RETRIES = 4
TIMEOUT = 180
LICENCE = ("Aluesarjat — non-commercial use only (\"Tietoaineistoa voi käyttää "
           "ei-kaupallisiin tarkoituksiin\"). Not CC BY 4.0. Lähde: Aluesarjat / "
           "Helsingin kaupunki ja Uudenmaan liitto.")
_last = [0.0]


def _wait():
    d = THROTTLE - (time.time() - _last[0])
    if d > 0:
        time.sleep(d)
    _last[0] = time.time()


def table_url(path):
    """"vrm/vaerak/alu_vaerak_004r" -> the API URL."""
    return f"{HOST}/{path}.px"


def ui_url(path):
    """The published table page a reader can open.

    PxWeb's UI folders are the API path joined with double underscores and prefixed by the
    database name: vrm/vaenn/alu_vaenn_006c -> Aluesarjat__vrm__vaenn/alu_vaenn_006c.px/
    (probed 2026-09-24; the plain slash form answers 404).
    """
    parts = path.split("/")
    folder = "__".join(["Aluesarjat"] + parts[:-1])
    return f"{UI}/{folder}/{parts[-1]}.px/"


def _open(req):
    last = None
    for attempt in range(RETRIES):
        _wait()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504) and attempt < RETRIES - 1:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"giving up after {RETRIES} attempts: {last}")


def meta(path):
    return json.loads(_open(urllib.request.Request(
        table_url(path), headers={"User-Agent": UA, "Accept-Encoding": "gzip"})))


def area_var(m):
    """`Alue` in some tables, `Osa-alue` in others — read it, never assume it."""
    for v in m["variables"]:
        if v["code"] in ("Alue", "Osa-alue"):
            return v["code"]
    raise KeyError("no area variable: " + ", ".join(v["code"] for v in m["variables"]))


def time_var(m):
    for v in m["variables"]:
        if v.get("time") or v["code"] == "Vuosi":
            return v["code"]
    raise KeyError("no time variable")


def query(path, sel):
    q = []
    for code, values in sel.items():
        vs = values if isinstance(values, (list, tuple)) else [values]
        if list(vs) == ["*"]:
            q.append({"code": code, "selection": {"filter": "all", "values": ["*"]}})
        else:
            q.append({"code": code, "selection": {"filter": "item", "values": [str(v) for v in vs]}})
    payload = json.dumps({"query": q, "response": {"format": "json-stat2"}}).encode("utf-8")
    return json.loads(_open(urllib.request.Request(
        table_url(path), data=payload,
        headers={"User-Agent": UA, "Content-Type": "application/json", "Accept-Encoding": "gzip"})))


def pull(path, sel, out, note=""):
    ds = query(path, sel)
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ds, ensure_ascii=False), encoding="utf-8")
    out.with_suffix(out.suffix + ".meta.json").write_text(json.dumps({
        "table": path, "url": table_url(path), "verify_at_source": ui_url(path),
        "query": sel, "updated": ds.get("updated", ""), "label": ds.get("label", ""),
        "fetched": dt.date.today().isoformat(),
        "publisher": "Aluesarjat (Helsingin kaupunki / Uudenmaan liitto)",
        "licence": LICENCE, "note": note,
        "cells": len(ds.get("value") or []),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return ds


def rows(ds):
    import statfin
    return statfin.rows(ds)


def stamp(out):
    p = pathlib.Path(str(out) + ".meta.json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
