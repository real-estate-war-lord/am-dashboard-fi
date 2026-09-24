"""scripts/statfin.py — the pure parts, no network.

`rows()` is the one place a wrong answer would be silent: json-stat2 packs every cell into
one flat array, and an off-by-one in the index maths gives the right number for the wrong
area. These tests pin the unpacking against a hand-built dataset whose every cell is known,
and against a real 13mx response copied from the 2026-09-24 probe.

Run: python3 -m unittest discover -s tests
"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import statfin  # noqa: E402


def ds(ids, sizes, cats, values, labels=None):
    dim = {}
    for i, d in enumerate(ids):
        dim[d] = {"category": {"index": {c: k for k, c in enumerate(cats[i])},
                               "label": (labels or {}).get(d, {c: c for c in cats[i]})}}
    return {"id": list(ids), "size": list(sizes), "dimension": dim, "value": list(values)}


class Rows(unittest.TestCase):
    def test_last_dimension_varies_fastest(self):
        """json-stat2 is row-major: with 2 areas × 3 years the years move first."""
        d = ds(["area", "year"], [2, 3], [["091", "837"], ["2023", "2024", "2025"]],
               [1, 2, 3, 4, 5, 6])
        got = [(r["area"], r["year"], r["value"]) for r in statfin.rows(d)]
        self.assertEqual(got, [("091", "2023", 1), ("091", "2024", 2), ("091", "2025", 3),
                               ("837", "2023", 4), ("837", "2024", 5), ("837", "2025", 6)])

    def test_three_dimensions(self):
        d = ds(["a", "b", "c"], [2, 2, 2], [["x", "y"], ["p", "q"], ["m", "n"]], list(range(8)))
        got = {(r["a"], r["b"], r["c"]): r["value"] for r in statfin.rows(d)}
        self.assertEqual(got[("x", "p", "m")], 0)
        self.assertEqual(got[("x", "p", "n")], 1)
        self.assertEqual(got[("x", "q", "m")], 2)
        self.assertEqual(got[("y", "q", "n")], 7)
        self.assertEqual(len(got), 8)

    def test_suppressed_cell_stays_none(self):
        """A suppressed figure is null all the way through. It is never a zero."""
        d = ds(["area"], [3], [["00100", "00120", "00130"]], [7735, None, 0])
        got = {r["area"]: r["value"] for r in statfin.rows(d)}
        self.assertIsNone(got["00120"])
        self.assertEqual(got["00130"], 0)
        self.assertNotEqual(got["00120"], got["00130"])

    def test_category_index_as_list(self):
        """Some PxWeb responses give category.index as a list rather than a map."""
        d = ds(["area"], [2], [["091", "837"]], [1, 2])
        d["dimension"]["area"]["category"]["index"] = ["091", "837"]
        self.assertEqual([r["area"] for r in statfin.rows(d)], ["091", "837"])

    def test_real_13mx_response(self):
        """ashi/13mx, 2025, Helsinki + Tampere, building types total — probed 2026-09-24.

        Helsinki 4 983 EUR/m2 on 10 455 sales; Tampere 2 979 on 4 320.
        """
        d = ds(["timeperiod_y", "kunta_1_20150101", "talotyyppi_5_20111209", "contentscode"],
               [1, 2, 1, 2], [["2025"], ["091", "837"], ["0"], ["keskihinta_aritm_nw", "lkm_julk20"]],
               [4983, 10455, 2979, 4320],
               labels={"kunta_1_20150101": {"091": "Helsinki", "837": "Tampere"}})
        by = {(r["kunta_1_20150101"], r["contentscode"]): r["value"] for r in statfin.rows(d)}
        self.assertEqual(by[("091", "keskihinta_aritm_nw")], 4983)
        self.assertEqual(by[("091", "lkm_julk20")], 10455)
        self.assertEqual(by[("837", "keskihinta_aritm_nw")], 2979)
        self.assertEqual(statfin.labels(d, "kunta_1_20150101")["091"], "Helsinki")


class TableNames(unittest.TestCase):
    def test_split(self):
        self.assertEqual(statfin.split_table("ashi/13mt"), ("StatFin", "ashi", "13mt"))
        self.assertEqual(statfin.split_table("StatFin_Passiivi:asvu/13eb_2025q4"),
                         ("StatFin_Passiivi", "asvu", "13eb_2025q4"))

    def test_split_rejects_a_bare_id(self):
        """'13mt' is not unique across databases — the config must always say which one."""
        with self.assertRaises(ValueError):
            statfin.split_table("13mt")

    def test_api_url(self):
        self.assertEqual(statfin.table_url("ashi/13mt"),
                         "https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin/ashi/13mt.px")

    def test_verify_at_source_url(self):
        self.assertEqual(statfin.ui_url("ashi/13mt"),
                         "https://pxdata.stat.fi/PxWeb/pxweb/en/StatFin/StatFin__ashi/13mt.px/")

    def test_archive_api_path_uses_the_long_id(self):
        """Live StatFin serves '13mt.px'; the frozen archive serves the long spelling."""
        self.assertEqual(statfin.table_url("StatFin_Passiivi:asvu/13eb_2025q4"),
                         "https://pxdata.stat.fi/PxWeb/api/v1/en/StatFin_Passiivi/asvu/"
                         "statfinpas_asvu_pxt_13eb_2025q4.px")

    def test_archive_url_uses_the_archive_prefix(self):
        self.assertEqual(statfin.ui_url("StatFin_Passiivi:asvu/13eb_2025q4"),
                         "https://pxdata.stat.fi/PxWeb/pxweb/en/StatFin_Passiivi/"
                         "StatFin_Passiivi__asvu/statfinpas_asvu_pxt_13eb_2025q4.px/")


class Codes(unittest.TestCase):
    def test_leading_zeros_survive(self):
        """int('091') is 91, and 91 is Jokioinen, not Helsinki. Codes stay strings."""
        d = ds(["area"], [2], [["091", "005"]], [694392, 9000])
        self.assertEqual([r["area"] for r in statfin.rows(d)], ["091", "005"])


if __name__ == "__main__":
    unittest.main()
