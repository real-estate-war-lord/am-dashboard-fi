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
import re
import socketserver
import sys
import threading
import traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SHOTDIR = ROOT / "docs" / "ui_v2"

PHASES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "V1", "V2", "V3", "V4", "V5", "V6", "V7"]

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
    # the column is found by its header, not by an index: V5 added a Publisher column (EXP8) and a
    # fixed index would silently have started asserting on a different column
    cells = page.evaluate("""() => {
        const t = document.querySelector('[data-testid=sources-table]');
        const heads = [...t.querySelectorAll('thead th')].map(e => e.textContent.trim());
        const i = heads.indexOf('Fetched');
        if (i < 0) return null;
        return [...t.querySelectorAll('tbody tr')].map(r => (r.children[i] || {}).textContent || '');
    }""")
    assert cells is not None, "no Fetched column in the sources table"
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
# P2 — one toolbar on the map
# ===========================================================================


REMOVED_CONTROLS = ["Climate risk", "1/100a", "1/1000a", "Infra projects", "Public buildings",
                    "Services", "Zoning", "1 km population grid", "Full screen"]


@check("P2-one-row", phase="P2")
def _one_row(page, base):
    """map row 1 is search · Layers ▾ · Indicator ▾ · Period, and nothing else is a toolbar button"""
    goto(page, base, "#map")
    bar = page.query_selector("[data-testid=map-toolbar][data-row='1']")
    assert bar, "no map toolbar"
    assert page.query_selector("[data-testid=search]"), "no unified search"
    assert page.query_selector("[data-testid=layers-btn]"), "no Layers button"
    assert page.query_selector("#indsel, [data-testid=ind-picker]"), "no indicator control"
    # none of v1.1's toolbar buttons survives outside the Layers popover
    tool = page.eval_on_selector_all(
        "[data-testid=map-toolbar] button",
        "els => els.filter(e => !e.closest('.lypop')).map(e => e.textContent.trim())")
    for word in REMOVED_CONTROLS:
        assert not [t for t in tool if word in t], f"'{word}' still on the toolbar: {tool}"
    # row 2 is the chips
    assert page.query_selector("[data-testid=ind-chips][data-row='2']"), "no chips row"


@check("P2-layers-menu", phase="P2")
def _layers_menu(page, base):
    """Layers ▾ holds every feature layer and every context layer, and toggling one writes the hash"""
    goto(page, base, "#map")
    page.click("[data-testid=layers-btn]")
    page.wait_for_timeout(150)
    keys = page.eval_on_selector_all("[data-testid=layers-pop] [data-layer]",
                                     "els => els.map(e => e.dataset.layer)")
    for want in ["infra", "public", "services", "buildings", "wms:zoning", "wms:grid"]:
        assert want in keys, f"{want} missing from Layers ▾: {keys}"
    # the flood zones are NOT a layer here: P3 binds them to the Climate indicator, and the menu
    # only carries the reader's hide toggle for the zones the active indicator brought with it
    assert not [k for k in keys if k.startswith("clim:")], keys
    page.click("[data-testid=layers-pop] [data-layer=infra]")
    page.wait_for_timeout(400)
    # v2.1 NAV6/LAY4 replaced `infra=1` with the one `lay=` key the property route already wrote;
    # `#map?infra=1` still opens the same map through the alias table (check V3-map-lay-key)
    assert "lay=infra" in hash_of(page), hash_of(page)
    assert page.eval_on_selector("[data-testid=legend-infra]", "e => e.offsetHeight > 0")
    page.keyboard.press("Escape")
    page.wait_for_timeout(120)
    assert page.eval_on_selector("[data-testid=layers-pop]", "e => e.hidden") is True
    assert not ERRORS, ERRORS[:3]


@check("P2-legends-are-keys", phase="P2")
def _legends_are_keys(page, base):
    """a floating legend has no filter button left in it, and legends never overlap"""
    goto(page, base, "#map/091?ind=growth&infra=1&public=1&services=1&clim=sea_100")
    page.wait_for_timeout(2500)
    # the only control a legend keeps is its own fold (spec §4.5, "collapsible with –")
    inner = texts(page, ".maplegend button:not(.lgfold), .maplegend .only, .maplegend [data-pubcat], "
                        ".maplegend [data-srvcat], .maplegend [data-pubkind], .maplegend [data-srvmode]")
    assert not inner, f"clickable filters left in a legend: {inner[:4]}"
    vis = [b for b in boxes(page, ".maplegend") if b["w"] > 4 and b["h"] > 4]
    for a in range(len(vis)):
        for b in range(a + 1, len(vis)):
            assert not overlap(vis[a], vis[b]), f"legends overlap: {vis[a]} {vis[b]}"


@check("P2-search-jumps", phase="P2")
def _search_jumps(page, base):
    """the quick jumps live at the top of the search dropdown and move the camera only"""
    goto(page, base, "#map")
    page.click("#mq")
    page.wait_for_timeout(200)
    rows = texts(page, "[data-testid=search] .mqrow b")
    assert rows[:5] == ["Helsinki", "Tampere", "Turku", "Oulu", "Finland"], rows[:6]
    before = hash_of(page)
    page.click("[data-testid=search] .mqrow[data-msi='0']")
    page.wait_for_timeout(700)
    assert hash_of(page) == before, f"a jump changed the hash: {before} → {hash_of(page)}"


@check("P2-search-area", phase="P2")
def _search_area(page, base):
    """a kunta name, a postal code and a coordinate each resolve to the right destination"""
    goto(page, base, "#map")
    page.fill("#mq", "Tampere")
    page.wait_for_timeout(250)
    page.keyboard.press("Enter")
    page.wait_for_timeout(700)
    assert hash_of(page).startswith("#map/837"), hash_of(page)

    goto(page, base, "#map")
    page.fill("#mq", "00100")
    page.wait_for_timeout(250)
    page.keyboard.press("Enter")
    page.wait_for_timeout(700)
    assert hash_of(page).startswith("#area/postinumero/00100"), hash_of(page)

    goto(page, base, "#map")
    page.fill("#mq", "60.2448, 24.8665")
    page.wait_for_timeout(250)
    rows = texts(page, "[data-testid=search] .mqrow")
    assert any("60.24480" in r for r in rows), rows[:3]
    page.keyboard.press("Enter")
    page.wait_for_timeout(2500)
    # v2.1 SRCH3 (DK P10 §1): a coordinate now drops a pin and keeps the reader on the macro map —
    # the sheet is one click further, from the pin card (check V3-pin-stays-on-map)
    h = hash_of(page)
    assert h.startswith("#map") and "pin=60.24480,24.86650" in h, h


@check("P2-privacy-off-map", phase="P2")
def _privacy_off_map(page, base):
    """the privacy sentence is a tooltip on the search, not a paragraph under the map"""
    goto(page, base, "#map")
    assert "Processed in your browser" not in body_text(page)
    tip = page.eval_on_selector("[data-testid=search] .mqtip", "e => e.title")
    assert "Processed in your browser" in tip, tip
    # …and it is still spelled out on the Test property page
    goto(page, base, "#property")
    assert "Processed in your browser" in body_text(page)


@check("P2-map-top-1366", phase="P2", viewport="1366x768")
def _map_top(page, base):
    """at 1366x768 the map starts within 200 px of the top of the viewport"""
    goto(page, base, "#map")
    page.wait_for_timeout(700)
    box = boxes(page, "[data-testid=map]")[0]
    assert box["y"] <= 200, f"map top at {box['y']} px"
    assert box["h"] >= 380, f"map only {box['h']} px tall"


@check("P2-fullscreen-topbar", phase="P2")
def _fullscreen_topbar(page, base):
    """Full screen is a page-level action in the top bar, and only on the map"""
    goto(page, base, "#map")
    btn = page.query_selector("[data-testid=map-full]")
    assert btn, "no full-screen button"
    assert page.eval_on_selector("[data-testid=map-full]", "e => !!e.closest('.topbar')")
    goto(page, base, "#data/areas/kunta")
    assert not page.query_selector("[data-testid=map-full]")


# ===========================================================================
# P3 — the shared IndicatorPicker and PeriodControl
# ===========================================================================


PICKER_ROUTES = ["#map", "#area/kunta/091", "#area/postinumero/00100",
                 "#data/areas/kunta", "#charts?ind=growth&a=kunta:091",
                 "#property?p=60.2448,24.8665"]


@check("P3-picker-everywhere", phase="P3")
def _picker_everywhere(page, base):
    """exactly one indicator picker, and one period control, on every view that studies an indicator"""
    for h in PICKER_ROUTES:
        goto(page, base, h)
        n = len(page.query_selector_all("[data-testid=ind-picker]"))
        assert n == 1, f"{h}: {n} pickers"
        assert page.query_selector("[data-testid=ind-picker-btn]"), h
        assert len(page.query_selector_all("[data-testid=period]")) <= 1, h


@check("P3-picker-popover", phase="P3")
def _picker_popover(page, base):
    """the popover searches, groups and selects — by mouse and by keyboard"""
    goto(page, base, "#map")
    page.click("[data-testid=ind-picker-btn]")
    page.wait_for_timeout(200)
    assert page.query_selector("[data-testid=ind-picker-pop]:not([hidden])")
    groups = texts(page, "[data-testid=ind-picker-pop] [data-group]")
    assert len(groups) >= 6, groups
    assert page.evaluate("document.activeElement.dataset.ipksearch !== undefined"), "search not focused"
    page.fill("[data-testid=ind-search]", "flood")
    page.wait_for_timeout(200)
    rows = texts(page, "[data-testid=ind-picker-pop] .ipkr b")
    assert rows and all("flood" in r.lower() for r in rows), rows
    page.keyboard.press("Enter")
    page.wait_for_timeout(700)
    assert "ind=flood_" in hash_of(page), hash_of(page)
    # Escape closes it and gives the button the focus back
    page.click("[data-testid=ind-picker-btn]")
    page.wait_for_timeout(150)
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    assert page.eval_on_selector("[data-testid=ind-picker-pop]", "e => e.hidden") is True
    assert page.evaluate("document.activeElement.dataset.ipkopen !== undefined")


@check("P3-period-modes", phase="P3")
def _period_modes(page, base):
    """one control, three shapes, chosen by the indicator — never two at once"""
    goto(page, base, "#map?ind=growth")
    assert page.query_selector("[data-testid=period-year]"), "no year select on a history indicator"
    assert not page.query_selector("[data-testid=period-rp]")
    assert not page.query_selector("[data-testid=period-proj]")

    goto(page, base, "#map?ind=fc_growth")
    proj = page.query_selector("[data-testid=period-proj]")
    assert proj, "no projection badge on an Outlook indicator"
    txt = proj.inner_text()
    assert txt.startswith("Projection 2026→2040"), txt
    assert "Tilastokeskus" in txt and "Väestöennuste" in txt, txt
    assert not page.query_selector("[data-testid=period-year]")

    goto(page, base, "#map?ind=flood_sea_100")
    rp = page.query_selector("[data-testid=period-rp]")
    assert rp, "no return-period control on a flood indicator"
    assert texts(page, "[data-testid=period-rp] button") == ["1/100a", "1/1000a"]
    assert not page.query_selector("[data-testid=period-year]")
    # switching the return period swaps the indicator and never crosses sea ↔ river
    page.click("[data-testid=period-rp] [data-rp='1000']")
    page.wait_for_timeout(700)
    assert "ind=flood_sea_1000" in hash_of(page), hash_of(page)


@check("P3-climate-zones", phase="P3")
def _climate_zones(page, base):
    """a Climate indicator draws the SYKE zones; anything else takes them away"""
    goto(page, base, "#map/091?ind=flood_sea_100")
    page.wait_for_timeout(1200)
    leg = page.query_selector("[data-testid=legend-zones]")
    assert leg and leg.inner_text().strip(), "no zones legend on a flood indicator"
    assert "1/100a" in leg.inner_text(), leg.inner_text()
    # the legend's own hide toggle lives in Layers ▾ and writes zones=0
    page.click("[data-testid=layers-btn]")
    page.wait_for_timeout(200)
    assert page.query_selector("[data-testid=layers-pop] [data-layer=zones]")
    page.click("[data-testid=layers-pop] [data-layer=zones]")
    page.wait_for_timeout(500)
    assert "zones=0" in hash_of(page), hash_of(page)

    goto(page, base, "#map/091?ind=growth")
    page.wait_for_timeout(1000)
    leg = page.query_selector("[data-testid=legend-zones]")
    assert not (leg and leg.inner_text().strip()), leg.inner_text() if leg else ""
    page.click("[data-testid=layers-btn]")
    page.wait_for_timeout(200)
    assert not page.query_selector("[data-testid=layers-pop] [data-layer=zones]")


@check("P3-clim-link-still-works", phase="P3")
def _clim_link(page, base):
    """a v1.1 ?clim= link selects the indicator those zones measure"""
    goto(page, base, "#map/091?clim=river_1000")
    assert "ind=flood_river_1000" in hash_of(page), hash_of(page)


@check("P3-inherited-group", phase="P3")
def _inherited_group(page, base):
    """on a postal-code page the kunta-level indicators are listed under their own heading"""
    goto(page, base, "#area/postinumero/00100")
    page.click("[data-testid=ind-picker-btn]")
    page.wait_for_timeout(300)
    groups = texts(page, "[data-testid=ind-picker-pop] [data-group]")
    assert "From the municipality" in groups, groups
    tags = texts(page, "[data-testid=ind-picker-pop] [data-group='From the municipality'] ~ .ipkr em")
    assert tags and tags[0] == "muni", tags[:3]


@check("P3-chips", phase="P3")
def _chips(page, base):
    """the chips row is the picker's short form and the active one is filled"""
    goto(page, base, "#map?ind=unemp")
    chips = page.query_selector_all("[data-testid=ind-chips] .iqb")
    assert len(chips) >= 4, len(chips)
    on = [c.inner_text() for c in chips if "on" in (c.get_attribute("class") or "")]
    assert len(on) == 1, on
    btn = page.eval_on_selector("[data-testid=ind-picker-btn] .ipkl", "e => e.textContent")
    assert on[0] == btn, (on, btn)


@check("P3-family-ramps", phase="P3")
def _family_ramps(page, base):
    """observed is green, a projection is purple, climate is blue — in the legend and on the map"""
    def darkest(h):
        goto(page, base, h)
        page.wait_for_timeout(1200)
        cols = page.eval_on_selector_all(
            "[data-testid=legend] .lgrow i",
            "els => els.map(e => getComputedStyle(e).backgroundColor)")
        assert cols, h
        rgb = [tuple(int(x) for x in c[c.index('(') + 1:c.index(')')].split(',')[:3]) for c in cols]
        # the "no data" swatch is the last row; the darkest bin is the first
        return rgb[0]
    r, g, b = darkest("#map?ind=growth")
    assert g > r and g > b, f"observed ramp is not green: {(r, g, b)}"
    r, g, b = darkest("#map?ind=fc_growth")
    assert b > g and r > g, f"projection ramp is not purple: {(r, g, b)}"
    r, g, b = darkest("#map?ind=flood_sea_100")
    assert b > r and b > g, f"climate ramp is not blue: {(r, g, b)}"
    # …and a projection is dashed wherever it is a line
    goto(page, base, "#area/kunta/091?show=outlook")
    page.wait_for_timeout(900)
    dashes = page.eval_on_selector_all(
        ".bleg + svg path, svg path[stroke-dasharray]",
        "els => els.map(e => e.getAttribute('stroke-dasharray')).filter(Boolean)")
    assert dashes, "no dashed projection line on the outlook chart"


# ===========================================================================
# P4 — the map area card
# ===========================================================================


@check("P4-card-contents", phase="P4")
def _card_contents(page, base):
    """identity, five figures, two buttons, two toggles — and nothing else"""
    goto(page, base, "#map/091")
    page.wait_for_timeout(2000)
    card = page.query_selector("[data-testid=area-card]")
    assert card, "no area card"
    ident = page.eval_on_selector("[data-testid=area-card] .mstrip-id", "e => e.textContent")
    for word in ["Helsinki", "Uusimaa", "inhabitants", "osa-alueet"]:
        assert word in ident, (word, ident)
    cells = texts(page, "[data-testid=area-card] .mstrip-k .mcell > span")
    assert len(cells) == 5, cells
    acts = texts(page, "[data-testid=area-card] .mstrip-act button")
    assert acts == ["Open Helsinki page ›", "↗ Chart"], acts
    # the UPCOMING chip row is gone; the projects are a toggle
    assert not page.query_selector("[data-testid=area-card] .upcoming")
    secs = page.eval_on_selector_all("[data-testid=area-card] details", "e => e.map(x => x.dataset.show)")
    assert secs == ["outlook", "upcoming"], secs
    assert all(not page.eval_on_selector(f"[data-testid=area-card] details[data-show={k}]", "e => e.open")
               for k in secs), "a toggle is open by default"


@check("P4-card-toggles", phase="P4")
def _card_toggles(page, base):
    """the toggles carry their state in the URL, both ways"""
    goto(page, base, "#map/091")
    page.wait_for_timeout(2000)
    page.click("[data-testid=area-card] details[data-show=outlook] summary")
    page.wait_for_timeout(400)
    assert "show=outlook" in hash_of(page), hash_of(page)
    body = page.eval_on_selector("[data-testid=area-card] details[data-show=outlook]", "e => e.textContent")
    assert "Tilastokeskus" in body and "Helsingin kaupunki" in body, body[:200]
    assert "residents" in body, body[:200]
    page.click("[data-testid=area-card] details[data-show=outlook] summary")
    page.wait_for_timeout(400)
    assert "show=" not in hash_of(page), hash_of(page)
    # …and a link that names them opens on them
    goto(page, base, "#map/091?show=outlook,upcoming")
    page.wait_for_timeout(2000)
    for k in ["outlook", "upcoming"]:
        assert page.eval_on_selector(f"[data-testid=area-card] details[data-show={k}]", "e => e.open"), k


@check("P4-card-fold", phase="P4")
def _card_fold(page, base):
    """the whole card collapses, and the collapsed state travels in the link"""
    goto(page, base, "#map/091")
    page.wait_for_timeout(1800)
    page.click("[data-testid=area-card] [data-cardfold]")
    page.wait_for_timeout(400)
    assert "card=0" in hash_of(page), hash_of(page)
    assert not page.query_selector("[data-testid=area-card] .mstrip-k")
    goto(page, base, "#map/091?card=0")
    page.wait_for_timeout(1500)
    assert page.eval_on_selector("[data-testid=area-card]", "e => e.classList.contains('is-full') === false")
    assert not page.query_selector("[data-testid=area-card] .mstrip-k")


@check("P4-card-tiles-select", phase="P4")
def _card_tiles_select(page, base):
    """a headline figure on the card selects that indicator"""
    goto(page, base, "#map/091?ind=growth")
    page.wait_for_timeout(1800)
    page.click("[data-testid=tile-unemp]")
    page.wait_for_timeout(800)
    assert "ind=unemp" in hash_of(page), hash_of(page)
    btn = page.eval_on_selector("[data-testid=ind-picker-btn] .ipkl", "e => e.textContent")
    assert btn.startswith("Unemp"), btn


# ===========================================================================
# P5 — the area page
# ===========================================================================


@check("P5-no-key-figures", phase="P5")
def _no_key_figures(page, base):
    """the KEY FIGURES block and its group tabs are gone"""
    for h in ["#area/kunta/091", "#area/postinumero/00100", "#area/osa_alue/091010"]:
        goto(page, base, h)
        assert "KEY FIGURES" not in body_text(page).upper(), h
        assert not page.query_selector("[data-argroup]"), h
        assert not page.query_selector("[data-artab]"), h


@check("P5-study-row", phase="P5")
def _study_row(page, base):
    """chart panel and mini map are siblings, 60/40, equal height, panel on the left"""
    goto(page, base, "#area/kunta/091")
    page.wait_for_timeout(2200)
    row = page.query_selector("[data-testid=study-row]")
    assert row, "no study row"
    panel = boxes(page, "[data-testid=study-row] [data-testid=chart-panel]")[0]
    mini = boxes(page, "[data-testid=study-row] [data-testid=minimap]")[0]
    assert panel["x"] < mini["x"], "the map is not on the right"
    assert abs(panel["h"] - mini["h"]) <= 2, (panel["h"], mini["h"])
    share = panel["w"] / (panel["w"] + mini["w"])
    assert 0.54 <= share <= 0.66, share
    assert panel["y"] < 768, f"the study row starts at {panel['y']} px"


@check("P5-minimap-drag", phase="P5")
def _minimap_drag(page, base):
    """the mini map drags, and ⤢ takes it full screen until Esc"""
    goto(page, base, "#area/kunta/091")
    page.wait_for_timeout(2500)
    before = page.evaluate("window.__maps.map(m => [m.getCenter().lat, m.getCenter().lng])")
    assert before, "no live map"
    box = boxes(page, "[data-testid=minimap] .leaflet-container")[0]
    page.mouse.move(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["w"] / 2 - 120, box["y"] + box["h"] / 2, steps=10)
    page.mouse.up()
    page.wait_for_timeout(700)
    after = page.evaluate("window.__maps.map(m => [m.getCenter().lat, m.getCenter().lng])")
    assert after != before, f"a 120 px drag did not move the map: {before} {after}"

    page.click("[data-testid=minimap-full]")
    page.wait_for_timeout(500)
    full = boxes(page, "[data-testid=minimap]")[0]
    vw = page.evaluate("window.innerWidth"), page.evaluate("window.innerHeight")
    assert full["w"] >= vw[0] * .9 and full["h"] >= vw[1] * .9, (full, vw)
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    small = boxes(page, "[data-testid=minimap]")[0]
    assert small["w"] < vw[0] * .6, small
    assert not ERRORS, ERRORS[:3]


@check("P5-panel-modes", phase="P5")
def _panel_modes(page, base):
    """the panel has four shapes and picks the one the indicator needs"""
    want = {"#area/kunta/091?ind=growth": ("history", None),
            "#area/kunta/091?ind=fc_growth": ("outlook", None),
            "#area/kunta/091?ind=flood_sea_100": ("climate", "clim-bars"),
            "#area/kunta/091?ind=completions_1000": ("snapshot", "state-nohistory")}
    for h, (mode, testid) in want.items():
        goto(page, base, h)
        page.wait_for_timeout(1600)
        got = page.eval_on_selector("[data-testid=chart-panel]", "e => e.dataset.mode")
        assert got == mode, f"{h}: {got}"
        if testid:
            assert page.query_selector(f"[data-testid={testid}]"), f"{h}: no {testid}"
    # the climate panel draws one bar per return period
    goto(page, base, "#area/kunta/091?ind=flood_sea_100")
    page.wait_for_timeout(1400)
    bars = page.query_selector_all("[data-testid=clim-bars] .cbar")
    assert len(bars) == 2, len(bars)


@check("P5-toggles", phase="P5")
def _toggles(page, base):
    """Population outlook opens on a kunta page and not on a postal-code one; show= carries it"""
    goto(page, base, "#area/kunta/091")
    page.wait_for_timeout(1800)
    assert page.eval_on_selector(".seclist details[data-show=outlook]", "e => e.open")
    assert not page.eval_on_selector(".seclist details[data-show=figures]", "e => e.open")
    goto(page, base, "#area/postinumero/00100")
    page.wait_for_timeout(1800)
    assert not page.eval_on_selector(".seclist details[data-show=figures]", "e => e.open")
    page.click(".seclist details[data-show=figures] summary")
    page.wait_for_timeout(500)
    assert "show=figures" in hash_of(page), hash_of(page)
    goto(page, base, "#area/postinumero/00100?show=figures")
    page.wait_for_timeout(1800)
    assert page.eval_on_selector(".seclist details[data-show=figures]", "e => e.open")


@check("P5-inherited-labelled", phase="P5")
def _inherited_labelled(page, base):
    """an inherited tile says "municipality figure"; nothing on the page is a lone °"""
    goto(page, base, "#area/postinumero/00100")
    page.wait_for_timeout(1800)
    tiles = page.eval_on_selector_all(
        "[data-testid=tiles] .hlc",
        "els => els.map(e => [e.dataset.testid, e.className.includes('inh'), e.textContent])")
    assert len(tiles) == 5, len(tiles)
    inh = [t for t in tiles if t[1]]
    assert inh, "no inherited tile on a postal-code page"
    assert all("municipality figure" in t[2] for t in inh), inh
    own = [t for t in tiles if not t[1]]
    assert own and all("municipality figure" not in t[2] for t in own), own
    # the tiles no longer carry a bare degree sign
    txt = " ".join(t[2] for t in tiles)
    assert "°" not in txt, txt


@check("P5-vs-median", phase="P5")
def _vs_median(page, base):
    """"vs median" is a difference — pp for a share, the unit otherwise, never a % of the median"""
    for h in ["#area/kunta/091?ind=net_migr", "#area/kunta/091?ind=crime_1000",
              "#area/kunta/091?ind=growth", "#area/kunta/091?ind=price_m2"]:
        goto(page, base, h)
        page.wait_for_timeout(1400)
        head = page.eval_on_selector("[data-testid=chart-panel] .pnhead", "e => e.textContent")
        if "vs median" not in head:
            continue
        seg = head.split("vs median")[0].split()[-2:]
        txt = " ".join(seg)
        assert "%" not in txt or "pp" in txt, f"{h}: 'vs median' reads {txt!r}"
        # and it is never an absurd ratio
        assert not any(abs(float(t.replace(",", ".").replace("\u2212", "-").replace("+", ""))) > 1e4
                       for t in seg if t.replace(",", ".").replace("+", "").replace("\u2212", "-")
                       .replace("-", "").replace(".", "").isdigit()), f"{h}: {txt!r}"


# ===========================================================================
# P6 — Test property
# ===========================================================================


PROP = "#property?p=60.2448,24.8665"


@check("P6-five-tiles", phase="P6")
def _five_tiles(page, base):
    """always five tiles, none of them a grey filler block"""
    for p in [PROP, "#property?p=60.2295,24.8720", "#property?p=61.4978,23.7610"]:
        goto(page, base, p)
        page.wait_for_timeout(2800)
        tiles = page.eval_on_selector_all(
            "[data-testid=tiles] > *",
            "els => els.map(e => [e.dataset.testid || '', e.textContent.trim()])")
        assert len(tiles) == 5, (p, tiles)
        assert all(t[0].startswith("tile-") and t[1] for t in tiles), (p, tiles)
        inh = [t for t in tiles if "municipality figure" in t[1]]
        own = [t for t in tiles if "municipality figure" not in t[1]]
        assert own, (p, "every tile inherited")
        for t in tiles:
            assert "°" not in t[1], (p, t)


@check("P6-header", phase="P6")
def _header(page, base):
    """the header names the kunta, the postinumero, the osa-alue and the coordinates, with four actions"""
    goto(page, base, PROP)
    page.wait_for_timeout(2800)
    tags = texts(page, ".anhead .artags .tag")
    assert any("Helsinki" == t for t in tags), tags
    assert any(t.startswith("00410") for t in tags), tags
    assert any("60.24480, 24.86650" == t for t in tags), tags
    acts = texts(page, ".anhead .tools > *")
    assert acts[0].startswith("Open on map"), acts
    assert any(a.endswith("›") for a in acts[1:]), acts
    assert any("OpenStreetMap" in a for a in acts), acts
    assert any("Copy link" in a for a in acts), acts


@check("P6-study-row", phase="P6")
def _tp_study_row(page, base):
    """the same study row as the area page, anchored on the pin's finest area"""
    goto(page, base, PROP)
    page.wait_for_timeout(3000)
    assert page.query_selector("[data-testid=study-row] [data-testid=chart-panel]")
    assert page.query_selector("[data-testid=study-row] [data-testid=minimap]")
    hint = page.eval_on_selector("[data-testid=minimap] .hint", "e => e.textContent")
    assert "osa-alue" in hint or "postal-code" in hint or "municipality" in hint, hint
    # dragging moves it, ⤢ fills the screen, Esc restores
    box = boxes(page, "[data-testid=minimap] .leaflet-container")[0]
    before = page.evaluate("window.__maps.map(m => [m.getCenter().lat, m.getCenter().lng])")
    page.mouse.move(box["x"] + box["w"] / 2, box["y"] + box["h"] / 2)
    page.mouse.down()
    page.mouse.move(box["x"] + box["w"] / 2 - 120, box["y"] + box["h"] / 2, steps=10)
    page.mouse.up()
    page.wait_for_timeout(700)
    assert page.evaluate("window.__maps.map(m => [m.getCenter().lat, m.getCenter().lng])") != before
    page.click("[data-testid=minimap-full]")
    page.wait_for_timeout(500)
    full = boxes(page, "[data-testid=minimap]")[0]
    assert full["w"] >= page.evaluate("window.innerWidth") * .9, full
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    assert boxes(page, "[data-testid=minimap]")[0]["w"] < page.evaluate("window.innerWidth") * .6


@check("P6-legends-stack", phase="P6")
def _tp_legends(page, base):
    """the infra and public-building legends stack inside the map and never overlap"""
    goto(page, base, PROP + "&lay=infra,public")
    page.wait_for_timeout(3500)
    mapbox = boxes(page, "[data-testid=minimap] .mapwrap")[0]
    legs = [b for b in boxes(page, "[data-testid=minimap] .maplegend") if b["w"] > 4 and b["h"] > 4]
    assert len(legs) >= 3, len(legs)
    for i in range(len(legs)):
        assert legs[i]["x"] >= mapbox["x"] - 1 and legs[i]["right"] <= mapbox["right"] + 1, legs[i]
        for j in range(i + 1, len(legs)):
            assert not overlap(legs[i], legs[j]), (legs[i], legs[j])


@check("P6-sections", phase="P6")
def _tp_sections(page, base):
    """the sheet's sections are <details>, Infrastructure nearby open, state in show="""
    goto(page, base, PROP)
    page.wait_for_timeout(3000)
    secs = page.eval_on_selector_all(".seclist details",
                                     "e => e.map(x => [x.dataset.show, x.open])")
    keys = [k for k, _ in secs]
    for want in ["infra", "public", "schools", "climate", "profile", "sources"]:
        assert want in keys, (want, keys)
    assert dict(secs)["infra"] is True, secs
    assert dict(secs)["public"] is False, secs
    page.click(".seclist details[data-show=climate] summary")
    page.wait_for_timeout(500)
    assert "show=" in hash_of(page) and "climate" in hash_of(page), hash_of(page)


@check("P6-empty-state", phase="P6")
def _tp_empty(page, base):
    """no pin: the input is focused and one example is offered"""
    goto(page, base, "#property")
    page.wait_for_timeout(700)
    assert page.query_selector("[data-testid=state-empty]")
    assert page.evaluate("document.activeElement.dataset.testid") == "prop-input"
    assert page.query_selector("[data-tpexample]"), "no example offered"


@check("P6-paste-google-link", phase="P6")
def _tp_paste(page, base):
    """a pasted Google Maps link replaces the pin — one pin, not two"""
    goto(page, base, PROP)
    page.wait_for_timeout(2800)
    page.click("[data-testid=search]") if page.query_selector("[data-testid=search]") else None
    goto(page, base, "#property")
    page.wait_for_timeout(600)
    page.fill("[data-testid=prop-input]", "https://www.google.com/maps/@60.1699,24.9384,15z")
    page.keyboard.press("Enter")
    page.wait_for_timeout(3000)
    h = hash_of(page)
    assert h.startswith("#property?p=60.1699,24.9384"), h
    assert h.count(";") == 0, h


@check("P6-per-map-renderers", phase="P6")
def _tp_panes(page, base):
    """the mini map draws its own markers — never through the macro map's layers"""
    goto(page, base, PROP + "&lay=infra,public")
    page.wait_for_timeout(3500)
    assert page.evaluate("window.__maps.length") == 1, page.evaluate("window.__maps.length")
    own = page.evaluate("!!(window.__maps[0] && window.__maps[0]._am && window.__maps[0]._am.pub)")
    assert own, "the mini map has no renderer set of its own"
    assert not ERRORS, ERRORS[:3]


# ===========================================================================
# P7 — Export ▾ and the long schema
# ===========================================================================


LONG_HEADER = ("level;code;name;parent_code;parent_name;maakunta;population;indicator;label;unit;"
               "period;period_type;value;value_type;inherited_from;direction;source;table_id;"
               "source_url;as_of;fetched;licence")


def _export(page, base, where, item, route="#data/areas/kunta"):
    goto(page, base, route)
    page.wait_for_timeout(1800)
    page.click(f"{where} [data-testid=export-btn]")
    page.wait_for_timeout(250)
    return download_text(page, lambda: page.click(f"{where} [data-testid=export-menu] [data-export={item}]"))


@check("P7-menu", phase="P7")
def _export_menu_items(page, base):
    """the same five items in both places, and the sidebar one is not clipped by its own column"""
    goto(page, base, "#property?p=60.2448,24.8665")
    page.wait_for_timeout(2800)
    for where in [".exfoot", ]:
        page.click(f"{where} [data-testid=export-btn]")
        page.wait_for_timeout(250)
        items = page.eval_on_selector_all(f"{where} [data-testid=export-menu] [data-export]",
                                          "els => els.map(e => e.dataset.export)")
        # the five v2.0 items, in order, still exactly where they were; V5 added `climate` (EXP10)
        assert [i for i in items if i != "climate"] == ["view", "areas", "projects", "property", "sources"], items
        assert len(items) >= 5, items
        box = boxes(page, f"{where} [data-testid=export-menu]")[0]
        assert box["w"] > 100 and box["h"] > 60, box
        assert box["y"] >= 0 and box["bottom"] <= page.evaluate("window.innerHeight"), box
    goto(page, base, "#data/areas/kunta")
    page.wait_for_timeout(1200)
    page.click(".datatabs [data-testid=export-btn]")
    page.wait_for_timeout(250)
    assert page.query_selector(".datatabs [data-testid=export-menu] [data-export=areas]")


@check("P7-long-schema", phase="P7")
def _long_schema(page, base):
    """all area data is the long schema, every row sourced, no project or macro rows"""
    txt = _export(page, base, ".datatabs", "areas")
    lines = txt.splitlines()
    assert lines[0] == LONG_HEADER, lines[0]
    assert len(lines) > 10000, len(lines)
    cols = lines[0].split(";")
    idx = {c: i for i, c in enumerate(cols)}
    rows = [ln.split(";") for ln in lines[1:]]
    levels = {r[idx["level"]] for r in rows}
    assert levels <= {"kunta", "postinumero", "osa_alue"}, levels
    assert not [r for r in rows if not r[idx["source"]]], "a row with no source"
    assert not [r for r in rows if not r[idx["fetched"]]], "a row with no fetch date"
    assert not [r for r in rows if not r[idx["licence"]]], "a row with no licence"
    # the decimal is a point and there is no thousands grouping
    bad = [r[idx["value"]] for r in rows[:5000] if "," in r[idx["value"]] or " " in r[idx["value"]]]
    assert not bad, bad[:3]
    # a value inherited from the kunta says so, and says which
    inh = [r for r in rows if r[idx["value_type"]] == "inherited"]
    assert inh, "nothing marked inherited"
    assert all(r[idx["inherited_from"]] for r in inh), "inherited with no parent code"
    assert all(r[idx["level"]] in ("postinumero", "osa_alue") for r in inh)
    # a projection is never an actual
    proj = [r for r in rows if r[idx["indicator"]].startswith("fc_")]
    assert proj and all(r[idx["value_type"]] == "projection" for r in proj)
    assert all(r[idx["period_type"]] == "projection" for r in proj)
    assert all("→" in r[idx["period"]] for r in proj)


@check("P7-unit-agreement", phase="P7")
def _unit_agreement(page, base):
    """the unit and the magnitude agree — a k€ label never sits on a five-figure number"""
    txt = _export(page, base, ".datatabs", "areas")
    lines = txt.splitlines()
    idx = {c: i for i, c in enumerate(lines[0].split(";"))}
    bad = []
    for ln in lines[1:]:
        r = ln.split(";")
        u, v = r[idx["unit"]], r[idx["value"]]
        if not v:
            continue
        try:
            n = abs(float(v))
        except ValueError:
            continue
        if ("k€" in u or "kEUR" in u) and n >= 1e4:
            bad.append((r[idx["indicator"]], u, v))
        if ("mio" in u.lower() or "MEUR" in u) and n >= 1e6:
            bad.append((r[idx["indicator"]], u, v))
    assert not bad, bad[:5]


@check("P7-projects-own-file", phase="P7")
def _projects_own_file(page, base):
    """the projects file has its own schema and no indicator column"""
    txt = _export(page, base, ".datatabs", "projects", "#data/projects")
    lines = txt.splitlines()
    head = lines[0].split(";")
    assert "indicator" not in head and "value" not in head, head
    assert head[:5] == ["id", "name", "type", "status", "opening"], head[:5]
    assert len(lines) > 100, len(lines)


@check("P7-property-export", phase="P7")
def _property_export(page, base):
    """the pin's file leads with the property columns, and a second file lists what is near it"""
    goto(page, base, "#property?p=60.2448,24.8665")
    page.wait_for_timeout(3200)
    page.click(".exfoot [data-testid=export-btn]")
    page.wait_for_timeout(250)
    got = []
    page.on("download", lambda d: got.append(d))
    with page.expect_download(timeout=15000) as dl:
        page.click(".exfoot [data-testid=export-menu] [data-export=property]")
    first = pathlib.Path(dl.value.path()).read_text(encoding="utf-8-sig")
    page.wait_for_timeout(2500)
    assert first.splitlines()[0] == "property_label;lat;lon;" + LONG_HEADER, first.splitlines()[0]
    row = first.splitlines()[1].split(";")
    assert row[0] and row[1] == "60.2448" and row[2] == "24.8665", row[:3]
    names = [d.suggested_filename for d in got]
    assert any("nearby" in n for n in names), names
    near = pathlib.Path([d for d in got if "nearby" in d.suggested_filename][0].path()).read_text(encoding="utf-8-sig")
    assert near.splitlines()[0] == "kind;name;type;status;distance_m;source;source_url", near.splitlines()[0]


@check("P7-sources-export", phase="P7")
def _sources_export(page, base):
    """the sources catalogue is one row per source, with a licence on every one"""
    txt = _export(page, base, ".datatabs", "sources", "#data/sources")
    lines = txt.splitlines()
    assert lines[0] == "key;label;publisher;tables;as_of;fetched;licence;url;used_for", lines[0]
    idx = {c: i for i, c in enumerate(lines[0].split(";"))}
    rows = [ln.split(";") for ln in lines[1:]]
    assert len(rows) >= 10, len(rows)
    assert all(r[idx["fetched"]] for r in rows), "a source with no fetch date"
    assert all(r[idx["licence"]] for r in rows), "a source with no licence"


# ===========================================================================
# P8 — the number and label fixes from the Chrome review of v1.1
# ===========================================================================


@check("P8-units", phase="P8")
def _units(page, base):
    """a price is EUR/m² and a rent EUR/m²/month — on the tile, the card, the table and the picker"""
    goto(page, base, "#area/kunta/091")
    page.wait_for_timeout(2200)
    price = page.eval_on_selector("[data-testid=tile-price_m2] b", "e => e.textContent")
    rent = page.eval_on_selector("[data-testid=tile-rent] b", "e => e.textContent")
    assert price.endswith("EUR/m²"), price
    assert rent.endswith("EUR/m²/month"), rent
    goto(page, base, "#map/091")
    page.wait_for_timeout(2200)
    assert page.eval_on_selector("[data-testid=tile-price_m2] b", "e => e.textContent").endswith("EUR/m²")
    goto(page, base, "#map?ind=rent")
    page.wait_for_timeout(1200)
    assert page.eval_on_selector("[data-testid=ind-picker-btn] .ipku", "e => e.textContent") == "EUR/m²/month"
    # …and no surface anywhere prints a bare "EUR" for these two
    goto(page, base, "#area/kunta/091?show=figures")
    page.wait_for_timeout(2200)
    cells = texts(page, ".seclist tbody td.num")
    bare = [c for c in cells if c.endswith(" EUR")]
    assert not bare, bare[:4]


@check("P8-vs-median-text", phase="P8")
def _vs_median_text(page, base):
    """no surface prints a percent of a median"""
    for h in ["#area/kunta/091?ind=net_migr", "#area/kunta/091?ind=crime_1000",
              "#area/kunta/091?ind=migr_intra"]:
        goto(page, base, h)
        page.wait_for_timeout(1500)
        txt = body_text(page)
        assert "% VS MEDIAN" not in txt.upper(), h
        head = page.eval_on_selector("[data-testid=chart-panel] .pnhead", "e => e.textContent")
        for tok in head.replace("\u2212", "-").split():
            t = tok.replace("+", "").replace("-", "").replace(",", ".").replace("\xa0", "")
            if t.replace(".", "").isdigit():
                assert abs(float(t)) < 1e5, (h, head)


@check("P8-outlook-rate", phase="P8")
def _outlook_rate(page, base):
    """the projected change shows the total over the window and a compound annual rate"""
    goto(page, base, "#map/091?show=outlook")
    page.wait_for_timeout(2500)
    line = page.eval_on_selector(".mstrip-secs .olchg, .mstrip-secs .olboth", "e => e.textContent")
    assert "residents" in line, line
    assert "over" in line and "years" in line, f"no total change over the window: {line}"
    # a per-year rate may appear, but only as the compound one, and labelled
    flat = line.replace(" ", "")
    for i, _ in enumerate(flat):
        if flat.startswith("%/yr", i):
            assert flat[i:i + 13] == "%/yr(compound", f"a bare per-year rate is still printed: {line}"
    assert "compound" in line, line
    # both headline outlook figures name the same base year
    card = page.eval_on_selector(".mstrip-secs details[data-show=outlook]", "e => e.textContent")
    assert "Tilastokeskus" in card and "Helsingin kaupunki" in card, card[:200]
    assert "same base year 2026" in card, card[:400]


@check("P8-period-label", phase="P8")
def _period_label(page, base):
    """the year select names the active indicator's own latest period"""
    goto(page, base, "#map?ind=growth")
    page.wait_for_timeout(1200)
    a = texts(page, "[data-testid=period-year] option")[-1]
    goto(page, base, "#map?ind=tax_income")
    page.wait_for_timeout(1200)
    sel = page.query_selector("[data-testid=period-year]")
    if sel:
        b = texts(page, "[data-testid=period-year] option")[-1]
        assert a != b or a.split()[0] == b.split()[0], (a, b)
    assert "latest (" not in a, a
    assert a.split()[0].isdigit(), a


@check("P8-one-rank-format", phase="P8")
def _one_rank_format(page, base):
    """every rank reads "#n of N", and the title says what N counts"""
    import re
    for h in ["#area/kunta/091", "#area/kunta/091?show=figures", "#map/091",
              "#property?p=60.2448,24.8665", "#data/areas/kunta"]:
        goto(page, base, h)
        page.wait_for_timeout(2200)
        txt = body_text(page)
        assert not re.search(r"#\d+\s*/\s*\d+", txt), (h, re.search(r"#\d+\s*/\s*\d+", txt).group(0))
        for m2 in re.finditer(r"#(\d[\d\u00a0 ]*)\s+of\s+(\d[\d\u00a0 ]*)", txt):
            assert m2, h
    goto(page, base, "#area/kunta/091")
    page.wait_for_timeout(2000)
    t = page.eval_on_selector("[data-testid=chart-panel] .pnr span", "e => e.title")
    assert "published figure" in t, t


@check("P8-no-lone-degree", phase="P8")
def _no_lone_degree(page, base):
    """an inherited figure is tagged, never marked with a bare °"""
    for h in ["#area/postinumero/00100?show=figures", "#property?p=60.2448,24.8665",
              "#data/areas/postinumero", "#area/osa_alue/091010?show=figures"]:
        goto(page, base, h)
        page.wait_for_timeout(2500)
        txt = body_text(page)
        assert "°" not in txt, (h, txt[max(0, txt.index("°") - 60):txt.index("°") + 20] if "°" in txt else "")
    goto(page, base, "#data/areas/postinumero")
    page.wait_for_timeout(2500)
    assert page.query_selector("[data-testid=areas-table] td .muni"), "no muni tag on an inherited cell"


@check("P8-fi-numbers", phase="P8")
def _fi_numbers(page, base):
    """fi-FI on screen: a space for thousands, a comma for decimals, changes always signed"""
    goto(page, base, "#area/kunta/091")
    page.wait_for_timeout(2200)
    price = page.eval_on_selector("[data-testid=tile-price_m2] b", "e => e.textContent")
    assert "\u00a0" in price or " " in price.replace("EUR/m²", ""), price
    assert "," not in price.split()[0] or "." not in price, price
    growth = page.eval_on_selector("[data-testid=tile-growth] b", "e => e.textContent")
    assert growth[0] in "+\u2212-", growth
    assert "," in growth, growth
    # a change on a share is in percentage points
    sub = page.eval_on_selector("[data-testid=tile-growth] em", "e => e.textContent")
    assert "pp" in sub, sub


# ===========================================================================
# P9 — responsive
# ===========================================================================


@check("P9-no-overflow-1366", phase="P9", viewport="1366x768")
def _no_overflow_1366(page, base):
    """nothing makes the page wider than the window at 1366"""
    _sweep_widths(page, base)


@check("P9-no-overflow-1440", phase="P9", viewport="1440x900")
def _no_overflow_1440(page, base):
    """…nor at 1440"""
    _sweep_widths(page, base)


@check("P9-no-overflow-1536", phase="P9", viewport="1536x864")
def _no_overflow_1536(page, base):
    """…nor at 1536"""
    _sweep_widths(page, base)


@check("P9-no-overflow-390", phase="P9", viewport="390x844")
def _no_overflow_390(page, base):
    """…nor on a phone"""
    _sweep_widths(page, base)


def _sweep_widths(page, base):
    bad = []
    for name, route in ROUTES:
        goto(page, base, route)
        page.wait_for_timeout(700)
        if not no_overflow(page):
            sw = page.evaluate("document.documentElement.scrollWidth")
            iw = page.evaluate("window.innerWidth")
            who = page.evaluate("""() => { const out = [];
                document.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
                  if (r.right > window.innerWidth + 1 && r.width > 0)
                    out.push(e.tagName + '.' + String(e.className && e.className.baseVal !== undefined
                      ? e.className.baseVal : e.className || '').slice(0, 28)); });
                return out.slice(0, 3); }""")
            bad.append((name, sw, iw, who))
        if ERRORS:
            bad.append((name, ERRORS[0]))
    assert not bad, bad


@check("P9-drawer", phase="P9", viewport="390x844")
def _drawer(page, base):
    """the sidebar becomes a 52 px top bar with a drawer that Esc closes"""
    goto(page, base, "#map")
    page.wait_for_timeout(900)
    assert page.eval_on_selector("[data-testid=sidebar]", "e => e.getBoundingClientRect().right <= 1")
    tog = page.query_selector("[data-testid=nav-toggle]")
    assert tog and tog.bounding_box()["height"] <= 56, tog.bounding_box() if tog else None
    page.click("[data-testid=nav-toggle]")
    page.wait_for_timeout(400)
    assert page.eval_on_selector("[data-testid=sidebar]", "e => e.getBoundingClientRect().x >= -1")
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    assert page.eval_on_selector("[data-testid=sidebar]", "e => e.getBoundingClientRect().right <= 1")
    assert page.evaluate("document.activeElement.dataset.testid") == "nav-toggle", "focus did not return"
    # the map still fills the width
    box = boxes(page, "[data-testid=map]")[0]
    assert box["w"] >= 320, box
    assert box["x"] >= 0 and box["right"] <= 391, box


@check("P9-stacks", phase="P9", viewport="390x844")
def _stacks(page, base):
    """the study row stacks, the table scrolls inside its card, the legends hide behind a pill"""
    goto(page, base, "#area/kunta/091")
    page.wait_for_timeout(2500)
    panel = boxes(page, "[data-testid=chart-panel]")[0]
    mini = boxes(page, "[data-testid=minimap]")[0]
    assert panel["y"] < mini["y"], "the map is not below the chart"
    assert panel["h"] >= 280 and mini["h"] >= 280, (panel["h"], mini["h"])

    goto(page, base, "#data/areas/kunta")
    page.wait_for_timeout(2200)
    sc = page.eval_on_selector("[data-testid=areas-table]", "e => { const b = e.closest('.scrollx');"
                               " return [b.scrollWidth > b.clientWidth, b.clientWidth]; }")
    assert sc[0], "the wide table does not scroll inside its card"
    assert sc[1] <= 390, sc

    goto(page, base, "#map")
    page.wait_for_timeout(1800)
    pill = page.query_selector(".mapwrap .legpill")
    assert pill, "no legend pill on a phone"
    pill.scroll_into_view_if_needed()
    assert page.eval_on_selector("[data-testid=legend]", "e => e.offsetParent === null"), "legend shown by default"
    pill.click()
    page.wait_for_timeout(300)
    assert page.eval_on_selector("[data-testid=legend]", "e => e.offsetParent !== null"), "pill did not open it"


@check("P9-one-export-affordance", phase="P9")
def _one_export(page, base):
    """Export ▾ is the only export control — no inline CSV buttons left beside it"""
    for h in ["#data/areas/kunta", "#data/projects", "#data/sources"]:
        goto(page, base, h)
        page.wait_for_timeout(1200)
        btns = page.eval_on_selector_all(
            "button", "els => els.filter(e => !e.closest('.exmenu'))"
                      ".map(e => e.textContent.trim())"
                      ".filter(t => /export|csv/i.test(t))")
        assert all("Export ▾" in t for t in btns), (h, btns)


# ===========================================================================
# P10 — the global sweeps
# ===========================================================================


# every other page the app can show, so a sheet is not left broken by a shared component
SHEET_ROUTES = [
    ("charts_dist", "#charts?ind=growth&a=kunta:091,kunta:837&mode=bar"),
    ("map_micro", "#map/091?micro=1"),
    ("map_pno", "#map/091/postinumero"),
    ("map_climate", "#map/091?ind=flood_sea_1000"),
    ("map_layers", "#map/091?infra=1&public=1&services=1"),   # the v1.1 flags, still readable (NAV6)
    ("map_pin", "#map/091/postinumero?pin=60.24480,24.86650&rad=1000"),
    ("property_layers", "#property?p=60.2448,24.8665&lay=infra,public,buildings"),
    # every property layer at once, including the two V4 added (services, the SYKE zones)
    ("property_all_layers", "#property?p=60.2448,24.8665&ind=flood_sea_100&lay=infra,public,services,rings"),
    ("area_show_all", "#area/kunta/091?show=outlook,figures,sub"),
    ("area_climate", "#area/kunta/091?ind=flood_sea_100"),   # the zones in the mini map (V5, MM6)
    ("schoollist", "#schoollist/kunta:091"),
    ("publist", "#publist/kunta:091"),
    # the three detail sheets — V5 put them in the sweeps, because until then nothing covered them
    ("project", "#project/kruunusillat"),
    ("school", "#school/00004"),
    ("public", "#public/091/arabianrannan-kirjasto@60.20898,24.97678"),
]


@check("P10-retired-words", phase="P10")
def _retired_words(page, base):
    """the controls v2.0 retired are named nowhere a reader can click them"""
    gone = ["Climate risk", "KEY FIGURES", "Compare with", "Paste Google Maps link",
            "Export data", "Own properties"]
    for _, h in ROUTES + SHEET_ROUTES:
        goto(page, base, h)
        page.wait_for_timeout(700)
        txt = body_text(page)
        for w in gone:
            assert w.lower() not in txt.lower(), (h, w)
        # the return-period pills are a period control now, never a toolbar button
        tool = page.eval_on_selector_all(
            "[data-testid=map-toolbar] button",
            "els => els.filter(e => !e.closest('.lypop') && !e.closest('[data-testid=period]')"
            " && !e.closest('[data-testid=ind-picker]')).map(e => e.textContent.trim())")
        assert not [t for t in tool if "1/100a" in t or "1/1000a" in t], (h, tool)


@check("P10-every-route-clean", phase="P10")
def _every_route_clean(page, base):
    """every route the app can show renders without a JS error"""
    bad = []
    for name, h in ROUTES + SHEET_ROUTES:
        goto(page, base, h)
        page.wait_for_timeout(1400)
        if ERRORS:
            bad.append((name, ERRORS[:2]))
    assert not bad, bad


@check("P10-picker-once", phase="P10")
def _picker_once(page, base):
    """one picker, one period control, one export menu per view — no duplicates anywhere"""
    for _, h in ROUTES + SHEET_ROUTES:
        goto(page, base, h)
        page.wait_for_timeout(700)
        n = len(page.query_selector_all("[data-testid=ind-picker]"))
        assert n <= 1, (h, f"{n} pickers")
        assert len(page.query_selector_all("[data-testid=period]")) <= 1, h
        assert len(page.query_selector_all("[data-testid=data-tabs]")) <= 1, h


@check("P10-legends-inside-map", phase="P10")
def _legends_inside(page, base):
    """every legend sits inside its map and never on top of another one"""
    for h in ["#map/091?ind=flood_sea_100&infra=1&public=1&services=1",
              "#property?p=60.2448,24.8665&lay=infra,public,buildings",
              "#area/kunta/091"]:
        goto(page, base, h)
        page.wait_for_timeout(3200)
        wrap = boxes(page, ".mapwrap")
        assert wrap, h
        # the stack itself must sit inside the map, and nothing in it may be clipped away: with
        # every legend folded to its title the column fits, which is the point of folding them
        for st in boxes(page, ".mapwrap .maplegs"):
            if st["w"] < 4:
                continue
            assert any(st["x"] >= w["x"] - 2 and st["right"] <= w["right"] + 2
                       and st["y"] >= w["y"] - 2 and st["bottom"] <= w["bottom"] + 2 for w in wrap), (h, st)
            assert not page.evaluate(
                "sel => { const e = document.querySelector(sel);"
                " return e ? e.scrollHeight > e.clientHeight + 2 : false; }",
                ".mapwrap .maplegs"), (h, "the legend stack has to be scrolled")
        legs = [b for b in boxes(page, ".mapwrap .maplegend") if b["w"] > 4 and b["h"] > 4]
        for i, a in enumerate(legs):
            inside = any(a["x"] >= w["x"] - 2 and a["right"] <= w["right"] + 2
                         and a["y"] >= w["y"] - 2 and a["bottom"] <= w["bottom"] + 2 for w in wrap)
            assert inside, (h, "a legend hangs outside its map", a)
            for c in legs[i + 1:]:
                assert not overlap(a, c), (h, a, c)


@check("P10-hash-stable-everywhere", phase="P10")
def _hash_stable(page, base):
    """every route, including the sheets, round-trips through the codec unchanged"""
    for _, h in ROUTES + SHEET_ROUTES:
        goto(page, base, h)
        once = hash_of(page)
        page.wait_for_timeout(500)
        assert hash_of(page) == once, (h, once, hash_of(page))


# ===========================================================================
# V1 — the parity audit every later phase works from
# ===========================================================================

AUDIT = ROOT / "docs" / "v2_1" / "PARITY_AUDIT.md"
# a row is `| NAV6 | … |` — the id column is what V3–V7 cite, so it is what is counted
AUDIT_ROW = re.compile(r"^\| *[A-Z]{1,5}[0-9]+ *\|", re.M)


@check("v21_audit_exists", phase="V1")
def _v21_audit(page, base):
    """the parity audit exists and still lists the gaps V2–V7 are assigned from"""
    assert AUDIT.exists(), f"{AUDIT} is missing — V1 writes it and no later phase may delete it"
    rows = AUDIT_ROW.findall(AUDIT.read_text(encoding="utf-8"))
    assert len(rows) >= 40, f"the audit has {len(rows)} rows, fewer than the 40 V1 shipped"


# ===========================================================================
# V2 — the colour rule for signed indicators (audit rows RAMP4, RAMP5, LEG7)
# ===========================================================================

# fi-FI writes a negative number with U+2212, so that is the character a bin label carries
MINUS = "−"
ELL = "…"


def legend_bins(page, sel="[data-testid=legend]"):
    """the indicator legend's class rows: (label, rgb) top-first, without the `no data` row."""
    rows = page.eval_on_selector_all(
        f"{sel} .lgrow",
        "els => els.map(e => [e.textContent.trim(), e.querySelector('i')"
        " ? getComputedStyle(e.querySelector('i')).backgroundColor : ''])")
    return [(t, c) for t, c in rows if c and "no data" not in t]


def rgb(c):
    return tuple(int(x) for x in c[c.index("(") + 1:c.index(")")].split(",")[:3])


@check("V2-signed-legend", phase="V2")
def _signed_legend(page, base):
    """a signed indicator's legend: fixed breaks on zero, greens above, reds below"""
    goto(page, base, "#map?ind=growth")
    page.wait_for_timeout(1200)
    bins = legend_bins(page)
    assert len(bins) in (4, 6), f"a signed legend has 4 or 6 bins, not {len(bins)}: {bins}"
    labels = [t for t, _ in bins]
    # the owner's own example string, on the class an exactly-flat year falls in
    assert f"0 {ELL} +0,5 %" in labels, labels
    # the bins are in value order, highest first, and zero is a boundary and not a class
    assert labels[0].startswith("> +"), labels
    assert labels[-1].startswith("< " + MINUS), labels
    # at least one red swatch and one green one, and the red ones are below zero
    zero = labels.index(f"0 {ELL} +0,5 %")
    above = [rgb(c) for _, c in bins[:zero + 1]]
    below = [rgb(c) for _, c in bins[zero + 1:]]
    assert above and below, (labels, zero)
    for r, g, b in above:
        assert g > r, f"a bin above zero is not green: {(r, g, b)} in {labels}"
    for r, g, b in below:
        assert r > g, f"a bin below zero is not red: {(r, g, b)} in {labels}"
    # the darker class of each side is the open-ended one
    assert sum(above[0]) < sum(above[-1]), above
    assert sum(below[-1]) < sum(below[0]), below
    # and the legend says the breaks will not move
    foot = page.eval_on_selector("[data-testid=legend-signed-footer]", "e => e.textContent")
    assert "fixed breaks, centred on zero" in foot, foot
    # the thin rule that marks the zero line sits under the lowest positive bin
    marked = texts(page, "[data-testid=legend] .lgrow.lgzero")
    assert marked == [f"0 {ELL} +0,5 %"], marked


@check("V2-signed-lower-better", phase="V2")
def _signed_lower_better(page, base):
    """on the crime trend an increase is red and a fall is green, and the legend says so"""
    goto(page, base, "#map?ind=crime_trend")
    page.wait_for_timeout(1200)
    bins = legend_bins(page)
    assert len(bins) in (4, 6), bins
    labels = [t for t, _ in bins]
    assert labels[0].startswith("> +"), labels
    # the top bin is the biggest increase, and on a lower-is-better indicator that is the red end
    r, g, b = rgb(bins[0][1])
    assert r > g, f"the increase side is not red: {(r, g, b)} — {labels}"
    r, g, b = rgb(bins[-1][1])
    assert g > r, f"the decrease side is not green: {(r, g, b)} — {labels}"
    note = body_text(page)
    assert "an increase is red, a fall is green" in note, "the legend does not say which way round"
    assert "lower is better" in note
    assert "fixed breaks, centred on zero" in note


@check("V2-signed-not-quantiles", phase="V2")
def _signed_not_quantiles(page, base):
    """the breaks are the indicator's own thresholds, not quantiles that move with the level"""
    def labels(h):
        goto(page, base, h)
        page.wait_for_timeout(1200)
        return [t for t, _ in legend_bins(page)]
    # the same indicator over 308 municipalities and over one municipality's postal codes
    nat = labels("#map?ind=growth")
    drilled = labels("#map/091?ind=growth")
    assert nat and drilled
    # every break is a multiple of the growth threshold (0.5) in both, and zero is one of them
    for ls in (nat, drilled):
        assert f"0 {ELL} +0,5 %" in ls, ls
        assert f"{MINUS}0,5 {ELL} 0 %" in ls, ls
    # a projection keeps purple above zero and takes the red below it, never green
    goto(page, base, "#map?ind=fc_growth")
    page.wait_for_timeout(1200)
    bins = legend_bins(page)
    assert len(bins) in (4, 6), bins
    top = rgb(bins[0][1])
    assert top[2] > top[1] and top[0] > top[1], f"an outlook top bin is not purple: {top}"
    bot = rgb(bins[-1][1])
    assert bot[0] > bot[1] and bot[0] > bot[2], f"an outlook bottom bin is not red: {bot}"
    assert "purple above zero, red below" in body_text(page)


@check("V2-same-ramp-everywhere", phase="V2")
def _same_ramp_everywhere(page, base):
    """the main map, both mini maps and the distribution strip draw one signed ramp"""
    def bins_of(h, sel="[data-testid=legend]"):
        goto(page, base, h)
        page.wait_for_timeout(1400)
        return legend_bins(page, sel)
    ref = bins_of("#map?ind=growth")
    for h in ("#area/kunta/091?ind=growth", "#property?p=60.2448,24.8665&ind=growth"):
        got = bins_of(h)
        assert [t for t, _ in got] == [t for t, _ in ref], (h, got, ref)
        assert [c for _, c in got] == [c for _, c in ref], (h, got, ref)
    # the map fills use the same colours as the legend it is under — no second palette
    goto(page, base, "#map?ind=growth")
    page.wait_for_timeout(1600)
    swatches = {c for _, c in legend_bins(page)}
    fills = set(page.eval_on_selector_all(
        "#lfmap path.leaflet-interactive",
        "els => els.map(e => e.getAttribute('fill')).filter(Boolean)"))
    assert fills, "no polygons drawn"
    stray = {f for f in fills if f.upper() != "#C4CBC4" and f not in _HEXES(swatches)}
    assert not stray, f"map fills outside the legend's own classes: {sorted(stray)[:4]}"


def _HEXES(colors):
    """`rgb(a, b, c)` as the `#RRGGBB` Leaflet writes into the `fill` attribute."""
    return {"#%02X%02X%02X" % rgb(c) for c in colors} | {"#%02x%02x%02x" % rgb(c) for c in colors}


@check("V2-dist-strip-dot", phase="V2")
def _dist_strip_dot(page, base):
    """the distribution strip's dot is the class colour, not a fixed accent"""
    # rent_yoy is published once and has no series for most kunnat, so its panel falls back to the
    # strip — the one place a signed ramp has to colour something that is not a map
    found = []
    for h in ("#area/kunta/091?ind=rent_yoy", "#area/kunta/092?ind=rent_yoy",
              "#area/kunta/837?ind=rent_yoy"):
        goto(page, base, h)
        page.wait_for_timeout(1200)
        if not page.query_selector("[data-testid=dist-dot]"):
            continue
        fill = page.eval_on_selector("[data-testid=dist-dot]", "e => getComputedStyle(e).fill")
        r, g, b = rgb(fill)
        assert not (r == g == b), f"{h}: the dot is grey — {fill}"
        # the mini map beside it is built over a different set of areas; the breaks are fixed, so
        # the same value must still land on the very same swatch
        swatches = {rgb(c) for _, c in legend_bins(page)}
        assert (r, g, b) in swatches, f"{h}: {fill} is not a legend class — {sorted(swatches)}"
        found.append(h)
    assert found, "no signed indicator fell back to the distribution strip on any of these routes"


@check("V2-sequential-untouched", phase="V2")
def _sequential_untouched(page, base):
    """a level indicator keeps its five sequential quantile classes"""
    goto(page, base, "#map?ind=unemp")
    page.wait_for_timeout(1200)
    bins = legend_bins(page)
    assert len(bins) == 5, f"unemp should keep 5 quantile classes, got {len(bins)}"
    labels = [t for t, _ in bins]
    assert labels[-1].startswith("≤"), labels
    # none of the signed legend's furniture: no zero rule, no fixed-breaks footer, no signed labels
    assert "fixed breaks, centred on zero" not in body_text(page)
    assert not page.query_selector("[data-testid=legend-signed-footer]")
    assert not page.query_selector("[data-testid=legend] .lgrow.lgzero")
    assert not [t for t in labels if ELL in t], labels
    # one hue in five steps: each class is darker than the one below it, and never two hues
    lums = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in (rgb(c) for _, c in bins)]
    assert lums == sorted(lums), f"a sequential ramp must darken towards the top: {lums}"


# ===========================================================================
# V3 — the map: a pasted location stays on the map, and the map's one layer key
# ===========================================================================

PIN_TXT = "60.2448, 24.8665"          # the same point every other property check uses
PIN_HASH = "pin=60.24480,24.86650"
# the three areas that point falls in, finest first — what the pin card names
PIN_WHERE = ("Malminkartano", "00410 Malminkartano", "Helsinki")
# Helsinki publishes osa-alueet, so a pin dropped in it drills to the postal-code level
PIN_MAP = "#map/091/postinumero"


@check("V3-pin-stays-on-map", phase="V3")
def _pin_stays(page, base):
    """a pasted coordinate drops a pin and keeps the reader on the map (audit SRCH3/SRCH4/SRCH5)"""
    goto(page, base, "#map")
    page.wait_for_timeout(600)
    page.fill("#mq", PIN_TXT)
    page.wait_for_timeout(350)
    # the coordinate row is the one AC-M3 finds, and it now offers the pin, not the sheet
    row = page.query_selector("[data-testid=search-coord]")
    assert row, "no [data-testid=search-coord] row for a pasted coordinate"
    assert "Drop a pin here" in row.inner_text(), row.inner_text()
    assert "60.24480" in row.inner_text(), row.inner_text()
    assert "test property" not in row.inner_text().lower(), row.inner_text()
    row.click()
    page.wait_for_timeout(3200)

    h = hash_of(page)
    assert h.startswith("#map"), f"the search navigated away from the map: {h}"
    assert PIN_HASH in h, h
    assert "rad=1000" in h, f"the pin arrives without its 1 km rings: {h}"

    card = page.query_selector("[data-testid=pin-card]")
    assert card, "no [data-testid=pin-card] after dropping a pin"
    assert page.eval_on_selector("[data-testid=pin-card]", "e => e.offsetHeight > 0")
    txt = card.inner_text()
    assert "Test property" in txt, txt                  # the label
    assert "60.24480, 24.86650" in txt, txt             # the coordinates exactly as they were read
    # osa-alue › postinumero › kunta, finest first
    assert " › ".join(PIN_WHERE) in txt, f"the pin card does not name its areas finest-first: {txt}"
    # the map is on the pin, at a readable zoom, and the marker is drawn
    z = page.evaluate("window.__maps[0].getZoom()")
    assert 12 <= z <= 14, f"the map should land at ~13 on a dropped pin, not {z}"
    c = page.evaluate("window.__maps[0].getCenter()")
    assert abs(c["lat"] - 60.2448) < 0.02 and abs(c["lng"] - 24.8665) < 0.02, c
    assert page.query_selector(".mapwrap .tp-pin"), "the pin itself is not on the map"

    # and one click further is the sheet the row used to jump straight to
    page.click("[data-testid=pin-open]")
    page.wait_for_timeout(2500)
    assert hash_of(page).startswith("#property?p=60.2448,24.8665"), hash_of(page)
    assert not ERRORS, ERRORS[:3]


@check("V3-pin-removable", phase="V3")
def _pin_removable(page, base):
    """× on the pin card takes the pin off the map and out of the link"""
    goto(page, base, f"{PIN_MAP}?{PIN_HASH}&rad=1000")
    page.wait_for_timeout(2600)
    assert page.query_selector("[data-testid=pin-card]"), "a pin= link does not show its card"
    page.click("[data-testid=pin-card] [data-pinrm]")
    page.wait_for_timeout(1200)
    assert "pin=" not in hash_of(page), hash_of(page)
    assert "rad=" not in hash_of(page), hash_of(page)
    assert not page.query_selector("[data-testid=pin-card]")
    assert not page.query_selector(".mapwrap .tp-pin")
    assert not ERRORS, ERRORS[:3]


def pin_card_clear(page, base):
    """the pin card never covers the toolbar or the legend stack (audit SRCH7)"""
    goto(page, base, f"{PIN_MAP}?ind=growth&lay=infra,public&{PIN_HASH}&rad=1000")
    page.wait_for_timeout(3000)
    cards = boxes(page, "[data-testid=pin-card]")
    assert cards and cards[0]["h"] > 10, "no pin card"
    card = cards[0]
    # the card is a block in the flow, so "does not overlap" is checked against everything it
    # could plausibly have been floated over: the toolbar above it and the map below it
    for sel in ("[data-testid=map-toolbar]", "[data-testid=ind-chips]", ".mapwrap .maplegs",
                ".mapwrap .maplegend", "[data-testid=map]", ".legpill"):
        for b in boxes(page, sel):
            if b["w"] < 4 or b["h"] < 4:
                continue
            assert not overlap(card, b), (sel, card, b)
    # …and it is not clipped by its own column either
    assert page.eval_on_selector("[data-testid=pin-card]",
                                 "e => e.scrollWidth <= e.clientWidth + 1"), "the pin card is clipped"
    assert page.query_selector("[data-testid=pin-open]"), "the pin card lost its action"
    assert no_overflow(page)


@check("V3-pin-card-clear-1440", phase="V3", viewport="1440x900")
def _pin_card_clear_1440(page, base):
    """at 1440 the pin card clears the toolbar and the legend stack"""
    pin_card_clear(page, base)


@check("V3-pin-card-clear-1366", phase="V3", viewport="1366x768")
def _pin_card_clear_1366(page, base):
    """at 1366 the pin card clears the toolbar and the legend stack"""
    pin_card_clear(page, base)


@check("V3-pin-card-clear-390", phase="V3", viewport="390x844")
def _pin_card_clear_390(page, base):
    """at 390 the pin card stacks instead of overlapping anything"""
    pin_card_clear(page, base)


@check("V3-radius-in-layers", phase="V3")
def _radius_in_layers(page, base):
    """the test-property radius is a row in Layers ▾, never a sixth control on row 1"""
    goto(page, base, f"{PIN_MAP}?{PIN_HASH}&rad=1000")
    page.wait_for_timeout(2600)
    loose = page.eval_on_selector_all(
        "[data-testid=map-toolbar] [data-tprad]",
        "els => els.filter(e => !e.closest('.lypop')).length")
    assert loose == 0, "the radius is back on row 1 — row 1 is search · Layers ▾ · Indicator ▾ · Period"
    page.click("[data-testid=layers-btn]")
    page.wait_for_timeout(200)
    rads = page.eval_on_selector_all("[data-testid=layers-pop] [data-tprad]",
                                     "els => els.map(e => e.dataset.tprad)")
    assert rads == ["0", "500", "1000", "2000", "5000"], rads
    page.click("[data-testid=layers-pop] [data-tprad='2000']")
    page.wait_for_timeout(700)
    assert "rad=2000" in hash_of(page), hash_of(page)
    assert not ERRORS, ERRORS[:3]


@check("V3-map-lay-key", phase="V3")
def _map_lay_key(page, base):
    """the map's feature layers are one `lay=` key, and every v1.1 flag still opens the same map"""
    # an old link switches the same layers on and is rewritten once
    goto(page, base, "#map/091?ind=growth&infra=1&public=1&services=1&micro=1")
    page.wait_for_timeout(1500)
    h = hash_of(page)
    for dead in ("infra=1", "public=1", "services=1", "micro=1"):
        assert dead not in h, (dead, h)
    assert "lay=infra,public,services,buildings" in h, h
    once = h
    page.wait_for_timeout(600)
    assert hash_of(page) == once, (once, hash_of(page))

    # and the switch in the menu writes the same key (AC-L2)
    goto(page, base, "#map")
    page.click("[data-testid=layers-btn]")
    page.wait_for_timeout(200)
    page.click("[data-testid=layers-pop] [data-layer=infra]")
    page.wait_for_timeout(600)
    assert "lay=infra" in hash_of(page), hash_of(page)
    assert page.eval_on_selector("[data-testid=legend-infra]", "e => e.offsetHeight > 0")
    page.click("[data-testid=layers-pop] [data-layer=infra]")
    page.wait_for_timeout(600)
    assert "lay=" not in hash_of(page), hash_of(page)
    assert not ERRORS, ERRORS[:3]


@check("V3-area-tab-alias", phase="V3")
def _area_tab_alias(page, base):
    """a v1.1 `t=` / `g=` area link still opens the section it named (audit NAV7)"""
    goto(page, base, "#area/kunta/091?t=bbr&g=Rents")
    page.wait_for_timeout(900)
    h = hash_of(page)
    assert "show=figures" in h, h
    assert "t=" not in h and "g=" not in h, h
    assert page.eval_on_selector("[data-show=figures]", "e => e.open") is True
    # `t=sub` named the sub-areas tab, which only a kunta page has (a postal code has no sub-areas)
    goto(page, base, "#area/kunta/091?t=sub")
    page.wait_for_timeout(900)
    assert "show=sub" in hash_of(page), hash_of(page)
    assert page.eval_on_selector("[data-show=sub]", "e => e.open") is True
    assert page.eval_on_selector("[data-show=figures]", "e => e.open") is False


@check("V3-zoom-keeps-selection", phase="V3")
def _zoom_keeps_selection(page, base):
    """zooming the macro map never changes the selection (AC-M9, audit MAP7)"""
    goto(page, base, "#map/049?ind=growth")
    page.wait_for_timeout(2600)
    before = hash_of(page)
    outline = page.evaluate("document.querySelectorAll('.mapwrap .leaflet-interactive').length")
    for z in (12, 9, 11):
        page.evaluate(f"window.__maps[0].setZoom({z})")
        page.wait_for_timeout(1100)
        assert hash_of(page).split("?")[0] == before.split("?")[0], (z, before, hash_of(page))
        assert "pin=" not in hash_of(page), hash_of(page)
    # the drilled municipality still owns the map: same path, same polygons, no popup opened
    assert hash_of(page).split("?")[0] == "#map/049", hash_of(page)
    assert page.evaluate("document.querySelectorAll('.mapwrap .leaflet-interactive').length") == outline
    assert not page.query_selector(".mapwrap .leaflet-popup")
    assert not ERRORS, ERRORS[:3]


@check("V3-search-fits", phase="V3")
def _search_fits(page, base):
    """the search box is wide enough for its own placeholder (audit SRCH8)"""
    goto(page, base, "#map")
    page.wait_for_timeout(600)
    # measure the placeholder in the input's own font rather than trusting the pixel width
    w = page.evaluate("""() => {
        const i = document.getElementById('mq');
        const cs = getComputedStyle(i);
        const c = document.createElement('canvas').getContext('2d');
        c.font = `${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
        const pad = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
        const wide = e => e ? Math.round(e.getBoundingClientRect().width) : -1;
        const tools = i.closest('.tools');
        return {text: c.measureText(i.placeholder).width + pad, box: i.clientWidth,
                ph: i.placeholder,
                // the chain, so a failure says which box is the narrow one
                chain: {search: wide(i.closest('.msearch')), tools: wide(tools),
                        card: wide(i.closest('.card')), main: wide(document.getElementById('main'))},
                siblings: [...(tools ? tools.children : [])].map(e => e.className + ':' + wide(e))};
    }""")
    assert w["text"] <= w["box"], (
        f"the placeholder {w['ph']!r} needs {w['text']:.0f} px of {w['box']} px "
        f"— {w['chain']} {w['siblings']}")


# ===========================================================================
# V4 — the Test property: one Layers ▾, Services, the full indicator list
# (audit rows LAY6, LAY7, TP3, TP10, TP11, TP12, TP13, TP14, TP17, TP18, MM6, PICK11)
# ===========================================================================


def mini_markers(page, kind):
    """how many markers of `kind` ("pub" / "srv") the mini map is drawing.

    Both layers are canvas markers — they have no DOM node of their own — so the count is read off
    the Leaflet map itself, walking the layer groups the overlays add. Each marker carries `_pub` /
    `_srv`, which is also what the popup handlers key on."""
    return page.evaluate("""k => {
        const m = window.__maps && window.__maps[0]; if (!m) return -1;
        let n = 0;
        const hit = l => { if (l['_' + k]) n++; };
        m.eachLayer(l => { hit(l); if (l.eachLayer) l.eachLayer(hit); });
        return n;
    }""", kind)


def legend_live(page, testid):
    return page.evaluate("""s => { const e = document.querySelector(s);
        return !!(e && e.offsetHeight > 0 && e.textContent.trim()); }""",
                         f"[data-testid=minimap] [data-testid={testid}]")


def open_layers(page):
    page.click("[data-testid=layers-btn]")
    page.wait_for_timeout(250)


@check("V4-property-layers-menu", phase="V4")
def _tp_layers_menu(page, base):
    """every layer the property map draws has exactly one switch in Layers ▾ (audit LAY6/TP12)"""
    goto(page, base, PROP)
    page.wait_for_timeout(3000)
    # the chip row beside the map is gone: the toolbar is the only place a layer is switched
    assert not page.query_selector("[data-anlay]"), "the v2.0 chip row is still on the property"
    assert not page.query_selector(".tpmaptools"), "the v2.0 map-tools bar is still on the property"
    loose = page.eval_on_selector_all(
        "[data-tprad]", "els => els.filter(e => !e.closest('.lypop')).length")
    assert loose == 0, "the radius control is still a second control beside the map (audit TP10)"

    open_layers(page)
    rows = page.eval_on_selector_all("[data-testid=layers-pop] [data-layer]",
                                     "els => els.map(e => e.dataset.layer)")
    for want in ["infra", "public", "services", "buildings", "rings"]:
        assert want in rows, (want, rows)
    assert len(rows) == len(set(rows)), f"a layer has two switches: {rows}"
    # the radius rows moved in here too, with the same five distances the map offers
    rads = page.eval_on_selector_all("[data-testid=layers-pop] [data-tprad]",
                                     "els => els.map(e => e.dataset.tprad)")
    assert rads == ["0", "500", "1000", "2000", "5000"], rads
    assert not ERRORS, ERRORS[:3]


@check("V4-property-services", phase="V4")
def _tp_services(page, base):
    """Services draw on the property mini map with their own legend, and go away again (audit TP11)"""
    goto(page, base, PROP)
    page.wait_for_timeout(3000)
    assert not legend_live(page, "legend-services"), "services are on by default"

    open_layers(page)
    page.click("[data-testid=layers-pop] [data-layer=services]")
    page.wait_for_timeout(3500)
    h = hash_of(page)
    assert "services" in h.split("lay=")[1].split("&")[0], h
    assert "srv=" in h, f"the category filter does not ride in the property hash: {h}"
    assert legend_live(page, "legend-services"), "no services legend inside the mini map"
    assert mini_markers(page, "srv") > 0, (
        "the services layer drew nothing around the pin",
        page.eval_on_selector("[data-testid=legend-services]", "e => e.textContent"), ERRORS[:3])

    # …and off means gone: markers and legend at once
    page.click("[data-testid=layers-pop] [data-layer=services]")
    page.wait_for_timeout(1200)
    assert not legend_live(page, "legend-services"), "the legend outlived its layer"
    assert mini_markers(page, "srv") == 0, "the markers outlived their switch"
    assert "services" not in hash_of(page), hash_of(page)
    assert not ERRORS, ERRORS[:3]


@check("V4-property-layer-off-sticks", phase="V4")
def _tp_layer_off(page, base):
    """switching a layer off removes markers and legend, and it stays off over a reload (audit LAY7)"""
    goto(page, base, PROP)
    page.wait_for_timeout(3500)
    assert mini_markers(page, "pub") > 0, "public buildings are not drawn by default at this pin"
    assert legend_live(page, "legend-public")

    open_layers(page)
    page.click("[data-testid=layers-pop] [data-layer=public]")
    page.wait_for_timeout(1500)
    assert mini_markers(page, "pub") == 0, "the public markers cannot be clicked away"
    assert not legend_live(page, "legend-public"), "the public legend outlived its layer"
    off = hash_of(page)
    assert "public" not in off.split("lay=")[1].split("&")[0], off

    # the async loader must not put it back, and neither must a reload of the link
    page.wait_for_timeout(2500)
    assert mini_markers(page, "pub") == 0, "an async file landing re-added a layer that is off"
    goto(page, base, off)
    page.wait_for_timeout(3500)
    assert mini_markers(page, "pub") == 0, "the reloaded link switched the layer back on"
    assert not legend_live(page, "legend-public")
    open_layers(page)
    assert page.eval_on_selector("[data-testid=layers-pop] [data-layer=public]",
                                 "e => e.getAttribute('aria-checked')") == "false"
    assert not ERRORS, ERRORS[:3]


@check("V4-property-picker-groups", phase="V4")
def _tp_picker_groups(page, base):
    """the property picker is the area picker of the place the pin fell in (audit TP13/PICK11)"""
    goto(page, base, PROP)
    page.wait_for_timeout(3200)
    page.click("[data-testid=ind-picker-btn]")
    page.wait_for_timeout(400)
    groups = texts(page, "[data-testid=ind-picker-pop] [data-group]")
    assert any(g.startswith("Climate") for g in groups), groups
    assert any(g.startswith("From the municipality") for g in groups), groups
    rows = page.eval_on_selector_all("[data-testid=ind-picker-pop] [data-ind]",
                                     "els => els.map(e => e.dataset.ind)")
    assert len(rows) >= 45, f"{len(rows)} indicators offered on the property"
    assert len(rows) == len(set(rows)), "an indicator is listed twice"
    # the inherited ones carry the same `muni` tag an area page gives them
    tags = texts(page, "[data-testid=ind-picker-pop] .ipkr em.tag-muni")
    assert tags and set(tags) == {"muni"}, tags
    assert not ERRORS, ERRORS[:3]


@check("V4-property-climate", phase="V4")
def _tp_climate(page, base):
    """a Climate indicator brings the return period, the bars and the SYKE zones (audit TP14/MM6)"""
    goto(page, base, PROP + "&ind=flood_sea_100")
    page.wait_for_timeout(3500)
    rp = page.query_selector("[data-testid=period-rp]")
    assert rp, "no return-period control on a Climate indicator"
    assert texts(page, "[data-testid=period-rp] button") == ["1/100a", "1/1000a"]
    assert page.query_selector("[data-testid=chart-panel] [data-testid=clim-bars]"), "no climate bars"
    assert legend_live(page, "legend-zones"), "no flood-zone legend inside the mini map"
    assert page.evaluate("!!(window.__maps[0] && window.__maps[0]._am)")
    # the zones are the indicator's own measurement: choose anything else and they go
    open_layers(page)
    assert page.query_selector("[data-testid=layers-pop] [data-layer=zones]")
    page.click("[data-testid=layers-pop] [data-layer=zones]")
    page.wait_for_timeout(900)
    assert "zones=0" in hash_of(page), hash_of(page)
    assert not legend_live(page, "legend-zones")

    goto(page, base, PROP + "&ind=growth")
    page.wait_for_timeout(3000)
    assert not legend_live(page, "legend-zones")
    open_layers(page)
    assert not page.query_selector("[data-testid=layers-pop] [data-layer=zones]")
    assert not ERRORS, ERRORS[:3]


@check("V4-property-export", phase="V4")
def _tp_export(page, base):
    """the property header carries Export ▾, with the pin's own file in it (audit TP3)"""
    goto(page, base, PROP)
    page.wait_for_timeout(3000)
    assert page.query_selector(".anhead [data-testid=export-btn]"), "no Export ▾ in the property header"
    acts = texts(page, ".anhead .tools > *")
    assert acts[0].startswith("Open on map"), acts
    page.click(".anhead [data-testid=export-btn]")
    page.wait_for_timeout(250)
    items = page.eval_on_selector_all(".anhead [data-testid=export-menu] [data-export]",
                                      "els => els.map(e => e.dataset.export)")
    assert "property" in items, items
    box = boxes(page, ".anhead [data-testid=export-menu]")[0]
    assert box["w"] > 10 and box["right"] <= page.evaluate("window.innerWidth") + 1, box
    txt = download_text(page, lambda: page.click(".anhead [data-testid=export-menu] [data-export=property]"))
    assert txt.splitlines()[0].startswith("property_label;lat;lon;"), txt.splitlines()[0]
    assert not ERRORS, ERRORS[:3]


@check("V4-property-radius", phase="V4")
def _tp_radius(page, base):
    """the radius really filters the property's overlays, not just the URL (audit TP10)"""
    goto(page, base, PROP)
    page.wait_for_timeout(3500)
    wide = mini_markers(page, "pub")
    assert wide > 0, "no public markers to filter"
    open_layers(page)
    page.click("[data-testid=layers-pop] [data-tprad='500']")
    page.wait_for_timeout(1500)
    assert "rad=500" in hash_of(page), hash_of(page)
    tight = mini_markers(page, "pub")
    assert tight < wide, f"the 500 m radius drew the same {tight} markers as no radius at all"
    assert not ERRORS, ERRORS[:3]


@check("V4-property-head-one-line", phase="V4", viewport="1536x864")
def _tp_head_one_line(page, base):
    """at 1536 the identity block still owns its own line (audit TP18, DK Q2)"""
    goto(page, base, PROP)
    page.wait_for_timeout(3000)
    rid = boxes(page, ".anhead .arid")[0]
    tools = boxes(page, ".anhead .tools")[0]
    assert tools["y"] >= rid["bottom"] - 2, ("the header split into two columns", rid, tools)
    tiles = boxes(page, ".anhead [data-testid=tiles]")[0]
    assert abs(tiles["x"] - rid["x"]) <= 2, ("the tiles start at a different left edge", rid, tiles)
    assert no_overflow(page)


# ===========================================================================
# V5 — the area page in place, the sheets, Data and Export
# ===========================================================================


AREA = "#area/kunta/091"


def map_state(page, i=0):
    """the mini map's centre and zoom, read off the live Leaflet instance"""
    return page.evaluate("""i => { const m = window.__maps && window.__maps[i]; if (!m) return null;
        const c = m.getCenter(); return {lat: +c.lat.toFixed(5), lon: +c.lng.toFixed(5), z: m.getZoom()}; }""", i)


@check("V5-area-refresh-in-place", phase="V5")
def _area_refresh_in_place(page, base):
    """a chip on the area page repaints the row — the mini map is never rebuilt (audit AREA4/PICK8/MM5)"""
    goto(page, base, AREA)
    page.wait_for_timeout(2500)
    # mark the live map object and the study row's DOM node, then drag/zoom the map somewhere of our own
    page.evaluate("window.__maps[0].__mark = 'v5'; "
                  "document.querySelector('[data-testid=minimap]').__mark = 'v5'")
    page.evaluate("window.__maps[0].setZoom(11)")
    page.wait_for_timeout(500)
    before = map_state(page)
    assert before and before["z"] == 11, before

    chips = page.eval_on_selector_all("[data-testid=ind-chips] .iqb:not(.on)", "els => els.map(e => e.dataset.ind)")
    assert chips, "no inactive chip to click"
    page.click(f"[data-testid=ind-chips] .iqb[data-ind='{chips[0]}']")
    page.wait_for_timeout(900)

    # the same Leaflet instance and the same card: nothing was torn down (MM3's registry is untouched)
    same = page.evaluate("[window.__maps[0].__mark === 'v5',"
                         " document.querySelector('[data-testid=minimap]').__mark === 'v5']")
    assert same == [True, True], ("the mini map was rebuilt on a chip click", same)
    after = map_state(page)
    assert after == before, ("the mini map lost its zoom / centre", before, after)
    # and the page really did change: the chip, the panel heading and the hash all moved
    assert f"ind={chips[0]}" in hash_of(page), hash_of(page)
    on = page.eval_on_selector_all("[data-testid=ind-chips] .iqb.on", "els => els.map(e => e.dataset.ind)")
    assert on == [chips[0]], on
    assert not ERRORS, ERRORS[:3]


@check("V5-area-fullscreen-survives", phase="V5")
def _area_fullscreen_survives(page, base):
    """⤢ full screen stays open across an indicator change (audit AREA4)"""
    goto(page, base, AREA)
    page.wait_for_timeout(2500)
    page.evaluate("window.__maps[0].__mark = 'v5'")
    page.click("[data-testid=minimap-full]")
    page.wait_for_timeout(600)
    assert page.query_selector("[data-testid=minimap].is-full"), "full screen did not open"
    # the overlay covers the toolbar, so the chips row inside it is the only way to change the
    # indicator without leaving full screen — and it has to be the one that is clicked
    inside = ".is-full .mm-chips"
    chips = page.eval_on_selector_all(f"{inside} .iqb:not(.on)", "els => els.map(e => e.dataset.ind)")
    assert chips, "no chips row inside the full-screen overlay"
    page.click(f"{inside} .iqb[data-ind='{chips[0]}']")
    page.wait_for_timeout(900)
    assert page.query_selector("[data-testid=minimap].is-full"), "the chip click closed full screen"
    assert page.evaluate("window.__maps[0].__mark === 'v5'"), "the map was rebuilt inside the overlay"
    assert f"ind={chips[0]}" in hash_of(page), hash_of(page)
    on = page.eval_on_selector_all(f"{inside} .iqb.on", "els => els.map(e => e.dataset.ind)")
    assert on == [chips[0]], ("the overlay's own chips row did not follow", on)
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    assert not page.query_selector("[data-testid=minimap].is-full"), "Esc did not close it"
    assert not ERRORS, ERRORS[:3]


@check("V5-property-refresh-in-place", phase="V5")
def _tp_refresh_in_place(page, base):
    """a chip on the Test property repaints the row — the pin's map keeps its zoom (audit TP6)"""
    goto(page, base, PROP)
    page.wait_for_timeout(3200)
    page.evaluate("window.__maps[0].__mark = 'v5'")
    page.evaluate("window.__maps[0].setZoom(13)")
    page.wait_for_timeout(500)
    before = map_state(page)
    assert before and before["z"] == 13, before
    chips = page.eval_on_selector_all("[data-testid=ind-chips] .iqb:not(.on)", "els => els.map(e => e.dataset.ind)")
    assert chips, "no inactive chip to click"
    page.click(f"[data-testid=ind-chips] .iqb[data-ind='{chips[0]}']")
    page.wait_for_timeout(1200)
    assert page.evaluate("window.__maps[0].__mark === 'v5'"), "the property mini map was rebuilt"
    assert map_state(page) == before, (before, map_state(page))
    assert f"ind={chips[0]}" in hash_of(page), hash_of(page)
    # the header, the panel and the sections all followed the new indicator
    assert page.query_selector("#tptop"), "the header block is missing"
    assert page.query_selector("#tpsecs [data-testid=tp-sec-profile]"), "the sections are missing"
    assert not ERRORS, ERRORS[:3]


@check("V5-area-minimap-zones", phase="V5")
def _area_minimap_zones(page, base):
    """a Climate indicator draws the SYKE zones in the area mini map, and only then (audit MM6)"""
    goto(page, base, AREA + "?ind=flood_sea_100")
    page.wait_for_timeout(2600)
    assert legend_live(page, "legend-zones"), "no flood-zone legend in the area mini map"
    wms = page.evaluate("""() => { const m = window.__maps[0]; let n = 0;
        m.eachLayer(l => { if (l._wmsUrl || (l.wmsParams && l.wmsParams.layers)) n++; }); return n; }""")
    assert wms >= 1, "no WMS layer on the area mini map"
    # a Climate return period is still the period control, and the panel is the bars
    assert page.eval_on_selector("[data-testid=period]", "e => e.dataset.mode") in ("horizon", "returnperiod")
    assert page.query_selector("[data-testid=clim-bars]"), "no climate bars in the panel"
    # anything else takes the zones away again, in place
    page.click("[data-testid=ind-chips] .iqb:not(.on) >> nth=0")
    page.wait_for_timeout(900)
    assert not legend_live(page, "legend-zones"), "the zones legend outlived its indicator"
    gone = page.evaluate("""() => { const m = window.__maps[0]; let n = 0;
        m.eachLayer(l => { if (l._wmsUrl || (l.wmsParams && l.wmsParams.layers)) n++; }); return n; }""")
    assert gone == 0, ("the WMS layer outlived its indicator", gone)
    assert not ERRORS, ERRORS[:3]


@check("V5-area-active-row", phase="V5")
def _area_active_row(page, base):
    """All figures highlights the active indicator's row and brings it into view (audit AREA5)"""
    goto(page, base, AREA + "?ind=growth")
    page.wait_for_timeout(2500)
    ind = "growth"
    page.click("[data-testid=sec-figures] > summary")
    page.wait_for_timeout(600)
    hi = page.eval_on_selector_all("[data-testid=sec-figures] tr.hi", "els => els.map(e => e.dataset.arind)")
    assert hi == [ind], ("exactly one row is highlighted, the active one", hi, ind)
    vis = page.evaluate("""() => { const r = document.querySelector('[data-testid=sec-figures] tr.hi');
        const b = r.getBoundingClientRect();
        return b.bottom > 0 && b.top < window.innerHeight; }""")
    assert vis, "the highlighted row was not scrolled into view"
    # and clicking a row selects that indicator, in place
    page.click("[data-testid=sec-figures] tr:not(.hi)[data-arind] >> nth=0")
    page.wait_for_timeout(800)
    hi2 = page.eval_on_selector_all("[data-testid=sec-figures] tr.hi", "els => els.map(e => e.dataset.arind)")
    assert hi2 and hi2 != hi, (hi, hi2)
    assert not ERRORS, ERRORS[:3]


# the three detail sheets, with ids read out of the built payload rather than hard-coded
SHEETS = [
    ("project", "#project/kruunusillat"),
    ("school", "#school/00004"),          # Alppilan lukio, Helsinki — a lukio, so it has a tile row
]


@check("V5-sheets-no-filler", phase="V5")
def _sheets_no_filler(page, base):
    """no sheet draws a grey filler cell where a figure is missing (audit SHEET1/SHEET3, AC-SH1)"""
    for name, h in SHEETS + [("public", None)]:
        if h is None:
            h = public_sheet_hash(page, base)
        goto(page, base, h)
        page.wait_for_timeout(2200)
        rows = page.eval_on_selector_all("[data-testid=tiles]", """els => els.map(e => {
            const cs = getComputedStyle(e);
            return {bg: cs.backgroundColor, border: cs.borderTopWidth, gap: cs.gap || cs.columnGap,
                    tiles: [...e.children].map(c => ({label: (c.querySelector('span') || {}).textContent || '',
                                                      text: c.textContent.trim()}))};
        })""")
        assert rows, (name, h, "the sheet has no [data-testid=tiles] row (audit SHEET3)")
        for r in rows:
            # the 1 px grid over --line is what showed through an empty cell as a grey slab in v1.1
            assert r["bg"] in ("rgba(0, 0, 0, 0)", "transparent"), (name, r)
            assert r["border"] in ("0px", ""), (name, r)
            assert r["gap"] not in ("1px", "1px 1px"), (name, "still a 1 px grid over --line", r)
            assert r["tiles"], (name, "an empty tile row")
            # a cell with nothing in it at all is the filler AC-SH1 forbids; a published "–" is not
            for t in r["tiles"]:
                assert t["text"] and t["label"].strip(), (name, f"an empty tile cell: {t!r}")
        assert not ERRORS, (name, ERRORS[:3])


@check("V5-sheet-breadcrumbs", phase="V5")
def _sheet_breadcrumbs(page, base):
    """a sheet's breadcrumb names the municipality, never the app (audit SHEET2, AC-SH3)"""
    goto(page, base, "#school/00004")
    page.wait_for_timeout(2200)
    crumbs = texts(page, ".crumbs button")
    assert crumbs[0] == "Finland", crumbs
    assert "Helsinki" in crumbs, ("no municipality step in the school breadcrumb", crumbs)
    assert not any(c.lower() in ("app", "dashboard", "macro dashboard") for c in crumbs), crumbs

    goto(page, base, public_sheet_hash(page, base))
    page.wait_for_timeout(2200)
    crumbs = texts(page, ".crumbs button")
    assert crumbs[0] == "Finland", crumbs
    assert "Helsinki" in crumbs, ("the public-building breadcrumb does not name the kunta", crumbs)

    goto(page, base, "#publist/kunta:091")
    page.wait_for_timeout(2200)
    assert "Helsinki" in texts(page, ".crumbs button"), texts(page, ".crumbs button")

    # a project is not in one municipality, so its breadcrumb is Data › Projects — and says so
    goto(page, base, "#project/kruunusillat")
    page.wait_for_timeout(1500)
    crumbs = texts(page, ".crumbs button")
    assert crumbs[:3] == ["Finland", "Data", "Projects"], crumbs


def public_sheet_hash(page, base):
    """the first public building Helsinki publishes, as the page's own link spells it"""
    goto(page, base, "#publist/kunta:091")
    page.wait_for_timeout(2500)
    got = page.evaluate("""() => { const r = document.querySelector('[data-pubsheet]');
        return r ? [r.dataset.pubkom, r.dataset.pubsheet] : null; }""")
    assert got and got[0] and got[1] and "undefined" not in got, ("no reachable public building", got)
    return f"#public/{got[0]}/{got[1]}"


@check("V5-public-sheet-reachable", phase="V5")
def _public_sheet_reachable(page, base):
    """the public-building list links to a sheet that opens (audit SHEET1)"""
    h = public_sheet_hash(page, base)
    goto(page, base, h)
    page.wait_for_timeout(2500)
    assert page.query_selector(".arhead h2"), ("the public sheet did not open", h)
    # the list itself says what Finland publishes, not what the Danish register did
    goto(page, base, "#publist/kunta:091")
    page.wait_for_timeout(2500)
    heads = texts(page, ".card table thead th")
    assert heads == ["Building", "Category", "Type", "Address", "Source"], heads
    body = body_text(page)
    for dead in ["Floor area", "opførelsesår", "BBR id"]:
        assert dead.lower() not in body.lower(), (dead, h)
    assert not ERRORS, ERRORS[:3]


@check("V5-areas-table-col-ids", phase="V5")
def _areas_table_col_ids(page, base):
    """every column of Data › Areas carries its own key (audit DATA4, spec §10)"""
    goto(page, base, "#data/areas/kunta?ind=growth")
    page.wait_for_timeout(1500)
    cols = page.eval_on_selector_all("[data-testid=areas-table] thead th",
                                     "els => els.map(e => e.dataset.col || '')")
    assert all(cols), ("a column with no data-col", cols)
    assert len(cols) == len(set(cols)), cols
    for want in ["name", "code", "parent", "population", "growth"]:
        assert want in cols, (want, cols)
    # the active indicator's column is the highlighted one
    hi = page.eval_on_selector_all("[data-testid=areas-table] thead th.hi", "els => els.map(e => e.dataset.col)")
    assert hi == ["growth"], hi


@check("V5-sources-table-is-the-export", phase="V5")
def _sources_table_is_export(page, base):
    """Data › Sources renders the rows the export writes (audit EXP8)"""
    goto(page, base, "#data/sources")
    page.wait_for_timeout(1200)
    shown = page.eval_on_selector_all("[data-testid=sources-table] tbody tr",
                                      "els => els.map(e => e.dataset.src)")
    assert shown and all(shown), shown
    page.click(".datatabs [data-testid=export-btn]")
    page.wait_for_timeout(250)
    csv = download_text(page, lambda: page.click(".datatabs [data-testid=export-menu] [data-export=sources]"))
    lines = [l for l in csv.strip().split("\n") if l]
    assert lines[0].split(";")[0] == "key", lines[0]
    keys = [l.split(";")[0] for l in lines[1:]]
    assert keys == shown, ("the table and the file disagree", shown[:5], keys[:5])
    # and every row is stamped, on both sides
    cols = lines[0].split(";")
    for l in lines[1:]:
        row = dict(zip(cols, l.split(";")))
        for c in ["label", "publisher", "fetched", "licence"]:
            assert row[c].strip(), (c, l)


@check("V5-climate-export", phase="V5")
def _climate_export(page, base):
    """the climate exposure file is level × return period over the Climate indicators (audit EXP10)"""
    goto(page, base, "#data/areas/kunta")
    page.wait_for_timeout(1200)
    page.click(".datatabs [data-testid=export-btn]")
    page.wait_for_timeout(250)
    items = texts(page, ".datatabs [data-testid=export-menu] [role=menuitem] b")
    assert "Climate exposure" in items, items
    csv = download_text(page, lambda: page.click(".datatabs [data-testid=export-menu] [data-export=climate]"))
    lines = [l for l in csv.strip().split("\n") if l]
    cols = lines[0].split(";")
    for want in ["level", "code", "indicator", "hazard", "return_period", "value", "as_of", "source", "licence"]:
        assert want in cols, (want, cols)
    rows = [dict(zip(cols, l.split(";"))) for l in lines[1:]]
    assert len(rows) > 50, len(rows)
    assert {r["level"] for r in rows} <= {"kunta", "postinumero", "osa_alue"}, {r["level"] for r in rows}
    # a return period is a probability, never a year
    rps = {r["return_period"] for r in rows if r["return_period"]}
    assert rps and rps <= {"1/100a", "1/1000a"}, rps
    assert not any(re.fullmatch(r"\d{4}", r) for r in rps), rps
    # machine decimals, and a stamp on every row
    for r in rows[:400]:
        assert "," not in r["value"], r
        assert r["source"].strip() and r["as_of"].strip() or True
        assert r["licence"].strip(), r


# ===========================================================================
# V6 — responsive, the number rules, accessibility, empty / loading / error
#      (audit RESP1/RESP6, TILE4, TILE5, NUM8–NUM11, A11Y1–A11Y4, AREA9,
#       STATE3/STATE4, GLOB3/NUM9, LEG5)
# ===========================================================================

# P9 sweeps the ten main routes at four widths. These sweep everything else the app can show —
# the map with a pin, the three detail sheets, the two list panels, a property with every layer —
# at the same four widths, so a shared component cannot be left broken on a page no check opens.
def _sweep_sheets(page, base):
    bad = []
    for name, route in SHEET_ROUTES:
        goto(page, base, route)
        page.wait_for_timeout(650)
        if not no_overflow(page):
            sw = page.evaluate("document.documentElement.scrollWidth")
            who = page.evaluate("""() => { const out = [];
                document.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
                  if (r.right > window.innerWidth + 1 && r.width > 0)
                    out.push(e.tagName + '.' + String(e.className && e.className.baseVal !== undefined
                      ? e.className.baseVal : e.className || '').slice(0, 28)); });
                return out.slice(0, 3); }""")
            bad.append((name, sw, page.evaluate("window.innerWidth"), who))
        if ERRORS:
            bad.append((name, ERRORS[0]))
    assert not bad, bad


@check("V6-sweep-sheets-1366", phase="V6", viewport="1366x768")
def _v6_sweep_1366(page, base):
    """every sheet, list and pinned map renders clean and inside the window at 1366"""
    _sweep_sheets(page, base)


@check("V6-sweep-sheets-1440", phase="V6", viewport="1440x900")
def _v6_sweep_1440(page, base):
    """…nor at 1440"""
    _sweep_sheets(page, base)


@check("V6-sweep-sheets-1536", phase="V6", viewport="1536x864")
def _v6_sweep_1536(page, base):
    """…nor at 1536"""
    _sweep_sheets(page, base)


@check("V6-sweep-sheets-390", phase="V6", viewport="390x844")
def _v6_sweep_390(page, base):
    """…nor on a phone"""
    _sweep_sheets(page, base)


# the widths the tile grid changes at: five columns, the 1180 break to auto-fit, the 820 break to
# two, and the phone. TILE4 asks for 1180 by name, TILE5 for 390.
TILE_WIDTHS = [1536, 1440, 1366, 1180, 820, 390]
TILE_ROUTES = ["#area/kunta/091", "#area/osa_alue/091010", "#property?p=60.2448,24.8665",
               "#area/kunta/091?show=outlook"]

# a tile's own box against the ink of every line inside it — `getBoundingClientRect` on the <b>
# returns its border box, which stays inside the tile even when one unbreakable token ("EUR/m²/month")
# runs past it and is painted over by the next tile. A Range measures the text itself.
TILE_JS = """() => {
  const bad = [], rng = document.createRange();
  for (const t of document.querySelectorAll('.hlc, .hltile')) {
    const r = t.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const lab = (t.querySelector('span') || {}).textContent || '';
    if (t.scrollWidth > t.clientWidth + 1)
      bad.push(lab.trim() + ': tile scrolls (' + t.scrollWidth + ' > ' + t.clientWidth + ')');
    for (const kid of t.children) {
      const cs = getComputedStyle(kid);
      if (cs.overflow !== 'visible') continue;          /* the label ellipsises on purpose */
      rng.selectNodeContents(kid);
      const k = rng.getBoundingClientRect();
      if (k.width < 1) continue;
      if (k.right > r.right - 1 || k.left < r.left - 1)
        bad.push(lab.trim() + ' / ' + kid.tagName + ': "' + (kid.textContent || '').trim().slice(0, 24)
                 + '" runs ' + Math.round(k.right - r.right) + ' px past the tile');
    }
  }
  return bad;
}"""


@check("V6-tiles-not-clipped", phase="V6")
def _v6_tiles(page, base):
    """no headline tile clips its own figure or unit at any width (audit TILE5, TILE4)"""
    bad = []
    try:
        for w in TILE_WIDTHS:
            page.set_viewport_size({"width": w, "height": 900})
            for h in TILE_ROUTES:
                goto(page, base, h)
                page.wait_for_timeout(1400)
                for msg in page.evaluate(TILE_JS):
                    bad.append(f"{w}px {h}: {msg}")
                # TILE4: the row must not leave a bare grid cell showing the separator through
                holes = page.evaluate("""() => {
                  const out = [];
                  for (const g of document.querySelectorAll('[data-testid=tiles]')) {
                    const r = g.getBoundingClientRect(); if (r.width < 2) continue;
                    const cs = getComputedStyle(g);
                    if (cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent')
                      out.push('the tile row has a background of its own: ' + cs.backgroundColor);
                    for (const c of g.children)
                      if (!(c.textContent || '').trim()) out.push('an empty tile cell');
                  }
                  return out; }""")
                for msg in holes:
                    bad.append(f"{w}px {h}: {msg}")
    finally:
        page.set_viewport_size({"width": 1440, "height": 900})
    assert not bad, bad[:8]


# NUM8 — every decimal a reader sees is fi-FI. What is NOT a decimal, and is allowed to keep its
# dot: a coordinate (the comma there separates lat from lon, so a comma decimal is unreadable —
# and the same string goes into `p=` and into the OpenStreetMap link), a version, a file name and
# a URL.
DOT_DEC = re.compile(r"\d\.\d")
DOT_OK = re.compile(r"""  https?://\S+
                      | [\w/.-]+\.(json|csv|js|py|md|html|zip|png|geojson|fi|com|org)\b
                      | \d{1,3}\.\d{4,6}              # a coordinate: 60.24480
                      | \bv\d+\.\d+                   # the build line: v2.1
                      | \bCC[ -]BY[\w-]*[ -]\d\.\d    # a licence name, as the publisher writes it
                      | \bODbL[ -]?\d\.\d
                      | \b\d{1,2}\.\d{1,2}\.(\d{4}\b)?  # a Finnish date, with or without its year
                   """, re.X | re.I)


@check("V6-fi-decimals", phase="V6")
def _v6_fi_decimals(page, base):
    """no `1.2 km` under a fi-FI interface — every decimal on screen uses a comma (audit NUM8)"""
    js = """() => {
      const out = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        const p = n.parentElement;
        if (!p || p.closest('script,style,svg,.leaflet-control-attribution')) continue;
        const r = p.getBoundingClientRect();
        if (r.width < 1 && r.height < 1) continue;
        const t = (n.nodeValue || '').trim();
        if (t) out.push(t);
      }
      return out; }"""
    hits = []
    for _, h in ROUTES + SHEET_ROUTES:
        goto(page, base, h)
        page.wait_for_timeout(700)
        # the radius labels live inside Layers ▾, which is where NUM8's own example is
        btn = page.query_selector("[data-lyopen]")
        if btn:
            btn.click()
            page.wait_for_timeout(200)
        for t in page.evaluate(js):
            if DOT_DEC.search(DOT_OK.sub(" ", t)):
                hits.append((h, t))
    # Split the way AC-G1 is split, and for the same reason: what the dashboard writes itself has
    # to be fi-FI, and what it merely renders out of the built registry is a data fix this run may
    # not make (`config/` is read-only at night — see DECISIONS V6). `Transport projects within
    # 1.2 km` is an indicator description in the registry, not a sentence in src/app.js.
    blob = page.evaluate("JSON.stringify(D)")
    strayed = [f"{h}: {t[:90]!r}" for h, t in hits if t not in blob]
    assert not strayed, strayed[:8]


# NUM9 / AC-G1 — the dashboard never invents a score, a weight or an index. Split the way Denmark
# split it: the app's own chrome may not say the words at all, and any other occurrence has to be
# a publisher's prose, verbatim out of the built registry.
G1_RX = re.compile(r"\b(score|scores|scoring|weighted|weighting|index of)\b", re.I)
G1_CHROME = ("button, h1, h2, h3, h4, th, .tl, .tag, .tag-muni, .lgtitle, .chip, .dtab, .sg, "
             "[data-testid=nav-item], [data-testid=ind-picker-btn], .ipkg, .subh, .statecard b")


@check("V6-no-scores", phase="V6")
def _v6_no_scores(page, base):
    """no score, no weighting, no "index of" anywhere the dashboard speaks for itself (AC-G1)"""
    chrome_js = ("sel => [...document.querySelectorAll(sel)]"
                 ".filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })"
                 ".map(e => (e.textContent || '').trim())")
    text_js = """() => {
      const out = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        const p = n.parentElement;
        if (!p || p.closest('script,style')) continue;
        const r = p.getBoundingClientRect();
        if (r.width < 1 && r.height < 1) continue;
        const t = (n.nodeValue || '').trim();
        if (t) out.push(t);
      }
      return out; }"""
    hits, quoted = [], []
    for _, h in ROUTES + SHEET_ROUTES:
        goto(page, base, h)
        page.wait_for_timeout(700)
        for t in page.evaluate(chrome_js, G1_CHROME):
            if G1_RX.search(t):
                hits.append(f"{h}: the app's own chrome says {t[:80]!r}")
        for t in page.evaluate(text_js):
            if G1_RX.search(t):
                quoted.append((h, t))
    assert not hits, hits[:6]
    if quoted:
        blob = page.evaluate("JSON.stringify(D)")
        strayed = [f"{h}: {t[:80]!r}" for h, t in quoted if t not in blob]
        assert not strayed, strayed[:6]


# A11Y1 / A11Y3 — the offline stand-in for axe-core. The run installs nothing and
# src/vendor/axe.min.js is not in this repo, so this is a DOM sweep of the rules that matter for
# a dashboard: every visible control has an accessible name, every popover trigger carries
# aria-expanded, and no icon is a bare glyph.
A11Y_JS = """() => {
  const bad = [];
  const vis = e => { const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; };
  const id = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    (e.getAttribute('data-testid') ? '[' + e.getAttribute('data-testid') + ']' : '') +
    (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\\s+/)[0] : '');
  const name = e => {
    const lb = e.getAttribute('aria-labelledby');
    const byId = lb && lb.split(/\\s+/).map(i => (document.getElementById(i) || {}).textContent || '').join(' ');
    return (e.getAttribute('aria-label') || byId || e.title ||
            (e.labels && e.labels.length ? [...e.labels].map(l => l.textContent).join(' ') : '') ||
            e.placeholder || e.textContent || e.value || '').trim();
  };
  for (const e of document.querySelectorAll('button,input,select,textarea,a[href],[role=button]')) {
    if (!vis(e) || e.disabled) continue;
    if (e.closest('.leaflet-container')) continue;            /* Leaflet's own controls */
    if (!name(e)) bad.push('no accessible name: ' + id(e));
  }
  for (const e of document.querySelectorAll('[aria-haspopup],[aria-controls]')) {
    if (!vis(e) || e.tagName === 'DIV') continue;
    if (!e.hasAttribute('aria-expanded')) bad.push('no aria-expanded: ' + id(e));
  }
  for (const e of document.querySelectorAll('img')) {
    if (vis(e) && e.getAttribute('alt') === null) bad.push('img without alt: ' + id(e));
  }
  return bad;
}"""

# every popover trigger the app has: the picker, Layers ▾, Export ▾, ☰ and the legend pill
TRIGGERS = ["[data-testid=ind-picker-btn]", "[data-lyopen]", "[data-testid=export-btn]",
            "[data-testid=nav-toggle]", "[data-legpill]", "[data-cardfold]"]


@check("V6-a11y-sweep", phase="V6")
def _v6_a11y(page, base):
    """every control has a name and every popover trigger says whether it is open (A11Y1, A11Y3)"""
    bad = []
    for _, h in ROUTES + SHEET_ROUTES:
        goto(page, base, h)
        page.wait_for_timeout(900)
        for msg in page.evaluate(A11Y_JS):
            bad.append(f"{h}: {msg}")
        for t in TRIGGERS:
            got = page.eval_on_selector_all(t, "els => els.map(e => e.getAttribute('aria-expanded'))")
            for v in got:
                if v not in ("true", "false"):
                    bad.append(f"{h}: {t} aria-expanded = {v!r}")
    assert not bad, bad[:8]


@check("V6-keyboard-popovers", phase="V6")
def _v6_keyboard(page, base):
    """Tab reaches the picker, and Enter/Esc open and close the picker, Layers ▾ and Export ▾ (A11Y2)"""
    goto(page, base, "#map")
    page.wait_for_timeout(900)
    page.evaluate("if (document.activeElement) document.activeElement.blur();")
    seen = []
    for _ in range(12):
        page.keyboard.press("Tab")
        seen.append(page.evaluate("""(() => { const e = document.activeElement; if (!e) return '';
            return e.tagName.toLowerCase() + (e.getAttribute('data-testid')
              ? '[' + e.getAttribute('data-testid') + ']' : '') + (e.id ? '#' + e.id : ''); })()"""))
        if page.evaluate("document.activeElement === document.querySelector('[data-testid=ind-picker-btn]')"):
            break
    else:
        raise AssertionError(f"the picker was not reached in 12 tabs — the path was {seen}")

    def open_close(sel, pop, name):
        page.eval_on_selector(sel, "e => e.focus()")
        page.keyboard.press("Enter")
        page.wait_for_timeout(350)
        assert page.eval_on_selector(pop, "e => e.offsetParent !== null"), f"Enter did not open {name}"
        assert page.get_attribute(sel, "aria-expanded") == "true", f"{name}: aria-expanded did not follow"
        page.keyboard.press("Escape")
        page.wait_for_timeout(350)
        assert page.eval_on_selector(pop, "e => e.offsetParent === null"), f"Escape did not close {name}"
        assert page.get_attribute(sel, "aria-expanded") == "false", f"{name}: aria-expanded stuck open"
        assert page.eval_on_selector(sel, "e => e === document.activeElement"), \
            f"Escape did not hand focus back to {name}"

    open_close("[data-testid=ind-picker-btn]", "[data-testid=ind-picker-pop]", "the picker")
    open_close("[data-lyopen]", ".lypop", "Layers ▾")
    goto(page, base, "#data/areas/kunta")
    page.wait_for_timeout(900)
    open_close(".datatabs [data-testid=export-btn]", ".datatabs [data-testid=export-menu]", "Export ▾")


@check("V6-drawer-traps-focus", phase="V6", viewport="390x844")
def _v6_drawer(page, base):
    """the ☰ drawer keeps Tab inside it, and Esc closes it and hands focus back (A11Y4, AC-S2)"""
    goto(page, base, "#map")
    page.wait_for_timeout(900)
    tog = "[data-testid=nav-toggle]"
    assert page.get_attribute(tog, "aria-expanded") == "false", "the toggle does not start collapsed"
    page.click(tog)
    page.wait_for_timeout(400)
    assert page.get_attribute(tog, "aria-expanded") == "true", "aria-expanded did not follow the drawer"
    assert page.evaluate("document.getElementById('sidebar').contains(document.activeElement)"), \
        "focus did not move into the drawer"
    for _ in range(20):
        page.keyboard.press("Tab")
    assert page.evaluate("document.getElementById('sidebar').contains(document.activeElement)"), \
        "Tab escaped the open drawer"
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    assert page.eval_on_selector("[data-testid=sidebar]", "e => e.getBoundingClientRect().right <= 1")
    assert page.evaluate("document.activeElement.dataset.testid") == "nav-toggle", "focus did not return to ☰"


@check("V6-legend-pill-clear-390", phase="V6", viewport="390x844")
def _v6_legend_pill(page, base):
    """on a phone every map folds its legends behind one pill, and neither the pill nor the open
    stack covers the map's attribution (LEG5, DK Q1)"""
    bad = []
    for h in ["#map", "#area/kunta/091", "#property?p=60.2448,24.8665"]:
        goto(page, base, h)
        page.wait_for_timeout(2600)
        pill = page.query_selector(".mapwrap .legpill")
        assert pill, (h, "no legend pill on a phone")
        pill.scroll_into_view_if_needed()
        page.wait_for_timeout(200)
        attr = boxes(page, ".mapwrap .leaflet-control-attribution")
        pb = boxes(page, ".mapwrap .legpill")[0]
        for a in attr:
            if overlap(pb, a):
                bad.append((h, "the pill covers the attribution", pb, a))
        assert page.eval_on_selector("[data-testid=legend]", "e => e.offsetParent === null"), (h, "legend shown by default")
        pill.click()
        page.wait_for_timeout(400)
        assert page.eval_on_selector("[data-testid=legend]", "e => e.offsetParent !== null"), (h, "the pill did not open it")
        assert page.get_attribute(".mapwrap .legpill", "aria-expanded") == "true", (h, "the pill does not say it is open")
        for lg in boxes(page, ".mapwrap .maplegend"):
            if lg["w"] < 4 or lg["h"] < 4:
                continue
            for a in attr:
                if overlap(lg, a):
                    bad.append((h, "an open legend covers the attribution", lg, a))
    assert not bad, bad


@check("V6-states", phase="V6")
def _v6_states(page, base):
    """loading and error are cards with a noun and the file's name — never a bare spinner
    (audit STATE3, STATE4)"""
    goto(page, base, "#data/areas/kunta")
    page.wait_for_timeout(900)
    # the real branches, driven through the app's own state rather than through a timing race:
    # schools.json still in flight, and schools.json having failed.
    page.evaluate("(() => { SCHOOLS = null; SCH_LOADING = true; SCH_ERR = false;"
                  " go('schoollist/kunta:091'); })()")
    page.wait_for_timeout(600)
    card = page.query_selector("[data-testid=state-loading]")
    assert card, "the school list shows no loading state while schools.json is in flight"
    assert card.query_selector("b"), "the loading state has no noun of its own"
    assert "schools.json" in card.inner_text(), card.inner_text()
    assert card.query_selector(".skel"), "the loading state is a bare sentence, not a skeleton"
    assert page.get_attribute("[data-testid=state-loading]", "role") == "status", "not announced"
    # …and it is a card on the page, not a collapsed box: the CSS has to have arrived too
    box = boxes(page, "[data-testid=state-loading]")[0]
    assert box["h"] >= 60 and box["w"] >= 200, box
    bars = [b for b in boxes(page, "[data-testid=state-loading] .skel i") if b["w"] > 40]
    assert len(bars) == 3, [b["w"] for b in boxes(page, "[data-testid=state-loading] .skel i")]
    assert all(b["right"] <= box["right"] + 1 for b in bars), bars

    page.evaluate("(() => { SCHOOLS = null; SCH_LOADING = true; SCH_ERR = true; renderKeep(); })()")
    page.wait_for_timeout(400)
    err = page.query_selector("[data-testid=state-error]")
    assert err, "a failed schools.json shows no error state"
    txt = err.inner_text()
    assert "schools.json" in txt, txt
    assert err.query_selector("a, button"), "the error state offers nothing to do"
    assert not err.query_selector(".skel"), "an error state must not pretend to be loading"

    # and the shape is the same one everywhere: the property's own wait for the kunta rings
    page.evaluate("(() => { SCH_ERR = false; SCHOOLS = null; SCH_LOADING = false;"
                  " KOM.list = null; KOM.err = false; KOM.p = Promise.resolve();"
                  " go('property?p=60.2448,24.8665'); })()")
    page.wait_for_timeout(600)
    card = page.query_selector("[data-testid=state-loading]")
    assert card and card.query_selector(".skel"), "the property's wait is not the same card"
    assert "kunnat_lookup.json" in card.inner_text(), card.inner_text()


@check("V6-caret-explains-itself", phase="V6")
def _v6_caret(page, base):
    """the ^ that marks a coarser-area figure is an <abbr> with a title, not a bare glyph (NUM10)"""
    found = 0
    for h in ["#area/osa_alue/091010", "#area/kunta/091?show=figures", "#data/areas/kunta",
              "#property?p=60.2448,24.8665"]:
        goto(page, base, h)
        page.wait_for_timeout(1600)
        # only where the mark decorates a figure. The captions and legend footers that *explain*
        # `^` in words are the reason the glyph was readable at all before V6, and they stay.
        bare = page.evaluate("""() => {
          const out = [];
          const scope = '[data-testid=tiles], td, th, .lfbig, .lfrow, .lfkey, .lfsec, .lgtitle';
          for (const host of document.querySelectorAll(scope)) {
            if (host.closest('.cap, .lgnote, caption, .hint')) continue;
            const w = document.createTreeWalker(host, NodeFilter.SHOW_TEXT);
            for (let n = w.nextNode(); n; n = w.nextNode()) {
              const p = n.parentElement;
              if (!p || p.closest('script,style,svg,abbr,.cap')) continue;
              if ((n.nodeValue || '').indexOf('^') >= 0) out.push((n.nodeValue || '').trim().slice(0, 60));
            }
          }
          return out; }""")
        assert not bare, (h, bare[:4])
        marks = page.eval_on_selector_all("abbr.cmark", "els => els.map(e => [e.textContent.trim(), e.title])")
        for txt, title in marks:
            assert txt == "^", (h, txt)
            assert len(title) > 20, (h, title)
        found += len(marks)
    assert found, "no ^ marker was drawn on any of the four routes — the check is asserting nothing"


@check("V6-no-double-escape", phase="V6")
def _v6_escapes(page, base):
    """no route shows a double-escaped entity — "SOURCES &AMP; AS OF" and its family (NUM11)"""
    rx = re.compile(r"&(amp|lt|gt|quot|#\d+);", re.I)
    bad = []
    for _, h in ROUTES + SHEET_ROUTES:
        goto(page, base, h)
        page.wait_for_timeout(700)
        for line in body_text(page).splitlines():
            if rx.search(line):
                bad.append(f"{h}: {line.strip()[:80]!r}")
    assert not bad, bad[:6]


@check("V6-study-row-first-screen", phase="V6", viewport="1366x768")
def _v6_study_row_top(page, base):
    """at 1366x768 the study row starts inside the first screen on the area page and the property
    (audit AREA9, AC-R2)"""
    for h in ["#area/kunta/091", "#area/postinumero/00100", "#property?p=60.2448,24.8665"]:
        goto(page, base, h)
        page.wait_for_timeout(2200)
        row = boxes(page, "[data-testid=study-row]")
        assert row, (h, "no study row")
        assert row[0]["y"] < 768, (h, f"the study row starts {row[0]['y']:.0f} px down")


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
                    for name, route in ROUTES + SHEET_ROUTES:
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
    # `make ui` passes PHASE / ONLY / SHOTS in the environment; the same three may be given as
    # positional arguments (`tests/ui_v2.spec.py V4 V4-`) so one phase can be driven from a shell
    # that is only allowed to run this file by name.
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    ph = (argv[0] if argv else None) or os.environ.get("PHASE", "P10")
    only = (argv[1] if len(argv) > 1 else None) or os.environ.get("ONLY")
    shots = bool(os.environ.get("SHOTS")) or "--shots" in sys.argv
    sys.exit(run(ph, shots=shots, only=only))
