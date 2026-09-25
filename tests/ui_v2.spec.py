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
        assert items == ["view", "areas", "projects", "property", "sources"], items
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
    ("map_layers", "#map/091?infra=1&public=1&services=1"),
    ("property_layers", "#property?p=60.2448,24.8665&lay=infra,public,buildings"),
    ("area_show_all", "#area/kunta/091?show=outlook,figures,sub"),
    ("schoollist", "#schoollist/kunta:091"),
    ("publist", "#publist/kunta:091"),
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
    ph = os.environ.get("PHASE", "P10")
    sys.exit(run(ph, shots=bool(os.environ.get("SHOTS")), only=os.environ.get("ONLY")))
