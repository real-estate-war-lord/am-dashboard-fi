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
    assert "infra=1" in hash_of(page), hash_of(page)
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
    inner = texts(page, ".maplegend button, .maplegend .only, .maplegend [data-pubcat], "
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
    assert hash_of(page).startswith("#property?p=60.2448,24.8665"), hash_of(page)


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
