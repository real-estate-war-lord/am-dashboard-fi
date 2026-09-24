"""Kunta codes keep their leading zero, everywhere, in both languages.

`091` is Helsinki. `91` is nothing. The Danish edition this repository was forked from
normalised codes with `String(Number(code))`, which is harmless there — no Danish kommune
code starts with a zero — and silently wrong here. It turned Helsinki, Espoo, Vantaa and
every other `0xx` kunta into a lookup miss, so the test-property pin reported the centre of
Helsinki as "in water or outside Finland" while Tampere and Turku worked perfectly. A bug
that only touches a third of the country and never raises is exactly what a test is for.

These tests guard the shape of the data and the one idiom that broke it.
"""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "app.js"
PROC = ROOT / "data" / "processed"


def strip_comments(js: str) -> str:
    """Block and line comments out, so a cautionary note about an idiom is not read as a use."""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return re.sub(r"^\s*//.*$", "", js, flags=re.M)


class AppJsNeverStripsALeadingZero(unittest.TestCase):
    def setUp(self):
        self.code = strip_comments(APP.read_text(encoding="utf-8"))

    def test_string_number_is_not_used_to_normalise_a_code(self):
        hits = re.findall(r"String\(Number\([^)]*\)\)", self.code)
        self.assertEqual(hits, [], "use kcode() — String(Number(\"091\")) is \"91\": " + "; ".join(hits))

    def test_kcode_exists_and_pads_to_three(self):
        self.assertIn("const kcode =", self.code)
        m = re.search(r"const kcode = [^\n]*", self.code)
        self.assertIn('padStart(3, "0")', m.group(0))

    def test_no_four_digit_padding_survives_from_the_danish_edition(self):
        hits = re.findall(r'padStart\(4,\s*"0"\)', self.code)
        self.assertEqual(hits, [], "Finnish kunta files are three digits, not four")


class ProcessedDataKeepsThreeCharacterCodes(unittest.TestCase):
    def test_makro_municipality_codes(self):
        f = PROC / "makro.json"
        if not f.exists():
            self.skipTest("no makro.json built yet")
        d = json.loads(f.read_text(encoding="utf-8"))
        for m in d["municipalities"]:
            self.assertIsInstance(m["code"], str, f"{m['name']}: a code is a string, never a number")
            self.assertEqual(len(m["code"]), 3, f"{m['name']}: code {m['code']!r} is not three characters")
        zeros = [m for m in d["municipalities"] if m["code"].startswith("0")]
        self.assertGreater(len(zeros), 25, "Finland has 36 kunnat with a 0xx code; if none survived, a cast ate them")
        by_code = {m["code"]: m["name"] for m in d["municipalities"]}
        self.assertEqual(by_code.get("091"), "Helsinki")
        self.assertEqual(by_code.get("049"), "Espoo")
        self.assertEqual(by_code.get("092"), "Vantaa")

    def test_postal_codes_keep_five_characters(self):
        f = PROC / "makro.json"
        if not f.exists():
            self.skipTest("no makro.json built yet")
        d = json.loads(f.read_text(encoding="utf-8"))
        for a in d["areas"]:
            self.assertEqual(len(a["nr"]), 5, f"postal code {a['nr']!r} is not five characters")
            self.assertEqual(len(a["muni"]), 3, f"{a['nr']}: kunta {a['muni']!r} is not three characters")
        self.assertTrue(any(a["nr"] == "00100" for a in d["areas"]), "00100 lost its leading zeros")

    def test_address_files_are_named_by_the_padded_code(self):
        d = PROC / "addr"
        if not d.exists():
            self.skipTest("no address files built yet")
        for f in d.glob("*.json"):
            if f.name == "manifest.json":
                continue
            self.assertRegex(f.stem, r"^\d{3}$", f"{f.name}: an address file is named by its three-character code")


if __name__ == "__main__":
    unittest.main()
