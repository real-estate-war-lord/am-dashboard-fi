#!/usr/bin/env python3
"""tests/ui_v2.spec.py — the v2.0 UI acceptance suite (Playwright, headless Chromium).

    make ui                 every check of every phase shipped so far
    make ui PHASE=P3        only the checks registered up to and including P3
    make ui SHOTS=1         also write docs/ui_v2/*.png at 1440 and 390

One check is one `@check("id", phase=..., viewport=...)` function taking `(page, url)`. A phase
registers its own checks and never weakens an earlier phase's. The runner serves `dist/` itself on
an ephemeral loopback port and stops the server in a `finally:` — never port 8080, which a sibling
dashboard on this machine sometimes holds.

`ERRORS` is the live list of pageerror / console.error strings for the page being driven; a check
may assert on it, and every route is asserted clean by the `zero_js_errors` check.
"""
from __future__ import annotations

import functools
import http.server
import os
import pathlib
import socketserver
import sys
import threading
import traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SHOTDIR = ROOT / "docs" / "ui_v2"

PHASES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]

# the routes every width is swept over (P9/P10); `name` is the screenshot stem
ROUTES = [
    ("map", "#map"),
    ("map_kunta", "#map/091"),
    ("area_kunta", "#area/kunta/091"),
    ("area_postinumero", "#area/postinumero/00100"),
    ("area_osa_alue", "#area/osa_alue/091010"),
    ("data_areas", "#data/areas/kunta"),
    ("data_projects", "#data/projects"),
    ("data_sources", "#data/sources"),
    ("charts", "#charts?ind=growth&a=kunta:091"),
    ("property", "#property?p=60.2448,24.8665"),
]
WIDTHS = [(1366, 768), (1440, 900), (1536, 864), (390, 844)]

CHECKS: list[dict] = []
ERRORS: list[str] = []


def check(cid, phase="P1", viewport="1440x900", route=None):
    def deco(fn):
        CHECKS.append({"id": cid, "phase": phase, "viewport": viewport, "fn": fn,
                       "doc": (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else ""})
        return fn
    return deco


# --------------------------------------------------------------------------- server


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


def serve_dist():
    """Serve dist/ on a free ephemeral port. Returns (url, shutdown)."""
    handler = functools.partial(_Quiet, directory=str(DIST))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    def stop():
        httpd.shutdown()
        httpd.server_close()

    return f"http://127.0.0.1:{port}/", stop


# --------------------------------------------------------------------------- helpers


_NAV = [0]


def goto(page, base, hash_, wait="#body"):
    """Load a route into a page nobody has poked at, and wait for #body to be filled.

    The cache-busting `?n=` is not decoration: a `page.goto` that differs from the current URL
    only in its fragment is a *same-document* navigation, and Chromium then never fires a load —
    Playwright waits for one until it times out. A distinct search string makes every route a real
    document load, which is also what makes each check independent of the one before it. The app
    reads `location.hash` only, so the query is invisible to it."""
    ERRORS.clear()
    _NAV[0] += 1
    page.goto(f"{base}?n={_NAV[0]}{hash_}", wait_until="domcontentloaded")
    page.wait_for_selector(wait, state="attached", timeout=15000)
    page.wait_for_function("document.getElementById('body').children.length > 0", timeout=15000)
    page.wait_for_timeout(400)
    return page


def texts(page, sel):
    return [t.strip() for t in page.eval_on_selector_all(sel, "els => els.map(e => e.textContent)")]


def body_text(page):
    return page.evaluate("document.body.innerText")


def hash_of(page):
    return page.evaluate("location.hash")


def no_overflow(page):
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")


def boxes(page, sel):
    return page.eval_on_selector_all(sel, """els => els.map(e => {
        const r = e.getBoundingClientRect();
        return {x: r.x, y: r.y, w: r.width, h: r.height, right: r.right, bottom: r.bottom};
    })""")


def overlap(a, b):
    """do two DOMRect-shaped dicts overlap by more than a rounding error?"""
    return (a["x"] < b["right"] - 1 and b["x"] < a["right"] - 1
            and a["y"] < b["bottom"] - 1 and b["y"] < a["bottom"] - 1)


# a 1x1 transparent PNG — what every off-machine request is answered with
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6360000002000100ffff0300000600055773d5c0000000"
    "0049454e44ae426082")


def block_external(route):
    """Answer everything that is not this test server, instead of aborting it.

    Aborting looked cleaner and was wrong twice over: Leaflet re-requests an aborted tile for
    ever (44 retries of one tile in four seconds was enough to starve Playwright's own selector
    polling and time a check out), and every abort also raises a `console.error` that would
    otherwise count as a page error. A 200 with an empty tile ends both."""
    url = route.request.url
    if "127.0.0.1" in url or url.startswith("data:") or url.startswith("blob:"):
        return route.continue_()
    if route.request.resource_type == "image":
        return route.fulfill(status=200, content_type="image/png", body=PNG_1X1)
    return route.fulfill(status=200, content_type="text/plain", body="")


def download_text(page, trigger):
    """click `trigger` and return the downloaded file as text (BOM stripped)."""
    with page.expect_download(timeout=15000) as dl:
        trigger()
    path = dl.value.path()
    return pathlib.Path(path).read_text(encoding="utf-8-sig")


# ===========================================================================
# P1 — navigation, routes, the Leaflet teardown registry
# ===========================================================================


@check("P1-nav-4", phase="P1")
def _nav_four(page, base):
    """the sidebar has exactly 4 items: Map · Data · Charts · Test property"""
    goto(page, base, "#map")
    items = texts(page, "[data-testid=nav-item]")
    assert items == ["Map", "Data", "Charts", "Test property"], items


@check("P1-redirects", phase="P1")
def _redirects(page, base):
    """every v1.1 hash lands on its v2.0 spelling"""
    table = [
        ("#table/kunta", "data/areas/kunta"),
        ("#table/postinumero", "data/areas/postinumero"),
        ("#pipeline", "data/projects"),
        ("#sources", "data/sources"),
        ("#analysis?a=60.24480,24.86650&la=Koti", "property"),
        ("#compare?a=kunta:091&b=kunta:837", "area/kunta/091"),
    ]
    for old, want in table:
        goto(page, base, old)
        got = hash_of(page)
        assert got.startswith("#" + want), f"{old} → {got}, wanted #{want}…"
    # the property redirect keeps the pin and the label
    goto(page, base, "#analysis?a=60.24480,24.86650&la=Koti")
    assert "p=60.2448,24.8665:Koti" in hash_of(page), hash_of(page)


@check("P1-no-compare", phase="P1")
def _no_compare(page, base):
    """no Compare control on any route, and the old #compare route redirects

    The test is on controls, not on prose: `unemp_m`'s published caveat reads "Compare month to
    month, not to Paavo", which is the English verb and has nothing to do with the deleted view."""
    for _, h in ROUTES:
        goto(page, base, h)
        ctrl = texts(page, "button, a, [role=tab], [role=menuitem], summary, h1, h2, h3")
        hits = [t for t in ctrl if "compare" in t.lower()]
        assert not hits, f"{h}: {hits[:3]}"
        assert "Compare with" not in body_text(page), f"'Compare with…' on {h}"
    goto(page, base, "#compare?a=kunta:091&b=kunta:837")
    assert hash_of(page).startswith("#area/kunta/091"), hash_of(page)


@check("P1-data-tabs", phase="P1")
def _data_tabs(page, base):
    """Data has three tabs and #data lands on Areas"""
    goto(page, base, "#data")
    assert hash_of(page).startswith("#data/areas/kunta"), hash_of(page)
    tabs = texts(page, "[data-testid=data-tab]")
    assert [t.rstrip("0123456789") for t in tabs] == ["Areas", "Projects", "Sources"], tabs
    for h, table in [("#data/areas/kunta", "areas-table"), ("#data/projects", "projects-table"),
                     ("#data/sources", "sources-table")]:
        goto(page, base, h)
        assert page.query_selector(f"[data-testid={table}]"), f"{table} missing on {h}"


@check("P1-sources-fetched", phase="P1")
def _sources_fetched(page, base):
    """no empty cell in the Sources table's Fetched column"""
    goto(page, base, "#data/sources")
    cells = page.eval_on_selector_all(
        "[data-testid=sources-table] tbody tr",
        "rows => rows.map(r => (r.children[3] || {}).textContent || '')")
    assert cells, "no source rows"
    assert all(c.strip() for c in cells), cells


@check("P1-export-menu", phase="P1")
def _export_menu(page, base):
    """Export ▾ in the sidebar footer opens a menu, and the old 4-line caption is gone"""
    goto(page, base, "#map")
    assert "Everything in one CSV" not in body_text(page)
    btn = page.query_selector("[data-testid=export-btn]")
    assert btn, "no export button"
    btn.click()
    page.wait_for_timeout(120)
    items = page.eval_on_selector_all("[data-testid=export-menu] [data-export]",
                                      "els => els.map(e => e.dataset.export)")
    assert "areas" in items and "view" in items, items
    # Esc closes it
    page.keyboard.press("Escape")
    page.wait_for_timeout(120)
    assert page.eval_on_selector("[data-testid=export-menu]", "e => e.hidden") is True


@check("P1-maps-registry", phase="P1")
def _maps_registry(page, base):
    """window.__maps holds exactly the live maps, and a view change tears the old one down"""
    goto(page, base, "#map")
    assert page.evaluate("window.__maps.length") == 1, page.evaluate("window.__maps.length")
    for h in ["#area/kunta/091", "#property?p=60.2448,24.8665", "#map", "#data/areas/kunta"]:
        page.evaluate(f"location.hash = {h!r}")
        page.wait_for_timeout(700)
    page.wait_for_timeout(500)
    n = page.evaluate("window.__maps.length")
    assert n == 0, f"{n} maps left alive on a table view"
    assert not ERRORS, ERRORS[:4]


@check("P1-maps-no-errors", phase="P1")
def _maps_no_errors(page, base):
    """walking map → area → property → map produces zero JS errors"""
    goto(page, base, "#map")
    for h in ["#area/kunta/091", "#property?p=60.2448,24.8665", "#map/091", "#map"]:
        page.evaluate(f"location.hash = {h!r}")
        page.wait_for_timeout(800)
    assert not ERRORS, ERRORS[:6]


@check("P1-hash-roundtrip", phase="P1")
def _hash_roundtrip(page, base):
    """every route serialises to itself — the address bar is rewritten once, not every frame"""
    for _, h in ROUTES:
        goto(page, base, h)
        once = hash_of(page)
        page.wait_for_timeout(250)
        assert hash_of(page) == once, f"{h}: {once} → {hash_of(page)}"


@check("P1-zero-js-errors", phase="P1")
def _zero_js_errors(page, base):
    """no route throws"""
    bad = []
    for name, h in ROUTES:
        goto(page, base, h)
        if ERRORS:
            bad.append((name, ERRORS[0]))
    assert not bad, bad


# ===========================================================================
# runner
# ===========================================================================


def run(phase_upto="P10", shots=False, only=None):
    from playwright.sync_api import sync_playwright

    if not (DIST / "index.html").exists():
        print("✗ dist/index.html is missing — run `make build` first")
        return 1

    limit = PHASES.index(phase_upto) if phase_upto in PHASES else len(PHASES) - 1
    todo = [c for c in CHECKS if PHASES.index(c["phase"]) <= limit
            and (not only or only in c["id"])]
    if not todo:
        print(f"no checks registered up to {phase_upto}")
        return 0

    base, stop = serve_dist()
    passed, failed = [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            pages = {}

            def page_for(vp):
                if vp not in pages:
                    w, h = (int(x) for x in vp.split("x"))
                    ctx = browser.new_context(viewport={"width": w, "height": h},
                                              accept_downloads=True)
                    # nothing outside this machine: a tile request must never decide a test
                    ctx.route("**://*/**", block_external)
                    pg = ctx.new_page()
                    pg.on("pageerror", lambda e: ERRORS.append(f"pageerror: {e}"))
                    pg.on("console", lambda m: ERRORS.append(f"console.error: {m.text}")
                          if m.type == "error" else None)
                    pages[vp] = pg
                return pages[vp]

            for c in todo:
                pg = page_for(c["viewport"])
                try:
                    c["fn"](pg, base)
                    passed.append(c["id"])
                    print(f"  ✓ {c['id']:<22} {c['doc']}")
                except Exception as exc:  # noqa: BLE001 — a failing check is a result, not a crash
                    failed.append((c["id"], exc))
                    print(f"  ✗ {c['id']:<22} {c['doc']}")
                    print("      " + str(exc).strip().replace("\n", "\n      ")[:800])
                    if os.environ.get("UI_TRACE"):
                        traceback.print_exc()

            if shots:
                SHOTDIR.mkdir(parents=True, exist_ok=True)
                for w, h in [(1440, 900), (390, 844)]:
                    ctx = browser.new_context(viewport={"width": w, "height": h})
                    ctx.route("**://*/**", block_external)
                    pg = ctx.new_page()
                    for name, route in ROUTES:
                        goto(pg, base, route)
                        pg.wait_for_timeout(900)
                        pg.screenshot(path=str(SHOTDIR / f"{name}_{w}.png"), full_page=(w == 390))
                    ctx.close()
                    print(f"  · screenshots at {w} px → docs/ui_v2/")
            browser.close()
    finally:
        stop()

    print(f"\n{len(passed)}/{len(todo)} checks pass (up to {phase_upto})")
    if failed:
        print("failed: " + ", ".join(i for i, _ in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    ph = os.environ.get("PHASE", "P10")
    sys.exit(run(ph, shots=bool(os.environ.get("SHOTS")), only=os.environ.get("ONLY")))
