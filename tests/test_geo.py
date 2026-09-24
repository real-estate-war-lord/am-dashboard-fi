"""data/geo — the checks that catch a silently wrong map.

A boundary bug does not crash anything: it just puts a figure on the wrong polygon. These
tests locate eight known points through all four layers and assert the answers, and they
assert the counts and the code shapes that everything downstream joins on.

Skipped when data/geo has not been built (`make geo`), so a fresh clone still passes.

Run: python3 -m unittest discover -s tests
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEO = ROOT / "data" / "geo"
sys.path.insert(0, str(ROOT / "scripts"))
import geo_common as G  # noqa: E402

LAYERS = {"kunnat": "kunta", "postinumerot": "nr", "osa_alueet": "code", "maakunnat": "maakunta"}
_cache = {}


def layer(name):
    if name not in _cache:
        _cache[name] = json.loads((GEO / f"{name}.geojson").read_text(encoding="utf-8"))
    return _cache[name]


def pip(lat, lon, ring):
    """Ray cast. Ring points are [lat, lon]; the ray runs in lon at a fixed lat."""
    inside = False
    for i in range(len(ring) - 1):
        y1, x1 = ring[i]
        y2, x2 = ring[i + 1]
        if (y1 > lat) != (y2 > lat):
            if lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def locate(name, lat, lon):
    """(code, name) of the feature containing the point, holes honoured."""
    key = LAYERS[name]
    hit = None
    for f in layer(name)["features"]:
        p = f["properties"]
        s, w, n, e = p["bb"]
        if not (s <= lat <= n and w <= lon <= e):
            continue
        # an odd number of containing rings means inside the polygon, even means in a hole
        if sum(1 for r in G.rings_of(f["geometry"]) if pip(lat, lon, r)) % 2 == 1:
            hit = (p[key], p.get("name"))
    return hit or (None, None)


@unittest.skipUnless((GEO / "kunnat.geojson").exists(), "data/geo not built — run `make geo`")
class Counts(unittest.TestCase):
    def test_kunta_count_is_the_2026_kuntajako(self):
        self.assertEqual(len(layer("kunnat")["features"]), 308)
        self.assertEqual(layer("kunnat")["meta"]["vintage"], "kuntajako 2026")

    def test_maakunta_count(self):
        self.assertEqual(len(layer("maakunnat")["features"]), 19)

    def test_osa_alue_coverage_is_the_four_helsinki_region_kunnat(self):
        by = {}
        for f in layer("osa_alueet")["features"]:
            k = f["properties"]["kunta"]
            by[k] = by.get(k, 0) + 1
        self.assertEqual(by, {"091": 148, "049": 88, "092": 61, "235": 9})

    def test_paavo_layer_year_is_not_the_statistics_year(self):
        m = layer("postinumerot")["meta"]
        self.assertEqual(m["layer_year"], 2026)
        self.assertEqual(m["statistics_year"], 2024)


@unittest.skipUnless((GEO / "kunnat.geojson").exists(), "data/geo not built — run `make geo`")
class Codes(unittest.TestCase):
    def test_every_code_is_a_string_and_keeps_its_leading_zero(self):
        for name, key in LAYERS.items():
            codes = [f["properties"][key] for f in layer(name)["features"]]
            self.assertTrue(all(isinstance(c, str) for c in codes), name)
            self.assertTrue(any(c.startswith("0") for c in codes), f"{name}: no leading-zero code survived")
        self.assertIn("00100", [f["properties"]["nr"] for f in layer("postinumerot")["features"]])
        self.assertIn("091", [f["properties"]["kunta"] for f in layer("kunnat")["features"]])

    def test_codes_are_unique(self):
        for name, key in LAYERS.items():
            codes = [f["properties"][key] for f in layer(name)["features"]]
            self.assertEqual(len(codes), len(set(codes)), f"{name} has duplicate codes")

    def test_every_postal_area_carries_a_kunta_that_exists(self):
        kunnat = {f["properties"]["kunta"] for f in layer("kunnat")["features"]}
        orphans = [f["properties"]["nr"] for f in layer("postinumerot")["features"]
                   if f["properties"]["kunta"] not in kunnat]
        self.assertEqual(orphans, [])

    def test_every_kunta_carries_a_maakunta(self):
        blank = [f["properties"]["kunta"] for f in layer("kunnat")["features"]
                 if not f["properties"]["region"]]
        self.assertEqual(blank, [])

    def test_every_osa_alue_carries_one_of_the_four_kunnat(self):
        bad = [f["properties"]["code"] for f in layer("osa_alueet")["features"]
               if f["properties"]["kunta"] not in {"091", "049", "092", "235"}]
        self.assertEqual(bad, [])


@unittest.skipUnless((GEO / "kunnat.geojson").exists(), "data/geo not built — run `make geo`")
class KnownPoints(unittest.TestCase):
    """Eight places whose area anyone can look up. If a layer shifts, one of these moves."""

    CASES = [
        ("Helsinki, Senate Square", 60.1699, 24.9522, "091", "01", "00170", "091010"),
        ("Espoo, Tapiola",          60.1760, 24.8050, "049", "01", "02100", "049211"),
        ("Vantaa, Tikkurila",       60.2925, 25.0400, "092", "01", "01300", "092061"),
        ("Kauniainen",              60.2117, 24.7290, "235", "01", "02700", "235002"),
        ("Tampere centre",          61.4978, 23.7610, "837", "06", "33200", None),
        ("Turku centre",            60.4518, 22.2666, "853", "02", "20100", None),
        ("Oulu centre",             65.0121, 25.4651, "564", "17", "90100", None),
        ("Utsjoki, Nuorgam",        70.0800, 27.8900, "890", "19", "99990", None),
    ]

    def test_points_land_in_the_right_areas(self):
        for label, lat, lon, kunta, maakunta, postal, osa in self.CASES:
            with self.subTest(label):
                self.assertEqual(locate("kunnat", lat, lon)[0], kunta)
                self.assertEqual(locate("maakunnat", lat, lon)[0], maakunta)
                self.assertEqual(locate("postinumerot", lat, lon)[0], postal)
                self.assertEqual(locate("osa_alueet", lat, lon)[0], osa)

    def test_kauniainen_is_a_hole_in_espoo_not_a_part_of_it(self):
        """If simplification filled the hole, this point would come back as Espoo."""
        self.assertEqual(locate("kunnat", 60.2117, 24.7290)[0], "235")


@unittest.skipUnless((GEO / "kunnat.geojson").exists(), "data/geo not built — run `make geo`")
class Size(unittest.TestCase):
    def test_no_geo_file_exceeds_the_repo_ceiling(self):
        for name in LAYERS:
            n = (GEO / f"{name}.geojson").stat().st_size
            self.assertLessEqual(n, G.MAX_BYTES, f"{name}.geojson is {n:,} B")


if __name__ == "__main__":
    unittest.main()
