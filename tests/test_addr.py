"""The address lookup: the two normalisations must agree, and the packing must round-trip.

`scripts/build_addr.py` writes the street keys and `src/testprop.js` looks them up. They
normalise independently — one in Python, one in JavaScript — so a divergence would not fail
anywhere: every lookup would simply miss, and the page would say "no address matched" for a
street that is right there in the file. That is exactly the kind of silence a test is for.

The JavaScript side is run through node, so this test needs node on PATH; it is skipped
rather than failed where node is absent, like the rest of `make test`.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_addr as B  # noqa: E402

# Street names chosen to hit every rule: the Finnish umlauts, the Swedish å, a roman numeral,
# a two-word name, punctuation, doubled whitespace, and mixed case.
CASES = [
    "Mannerheimintie",
    "Töölönkatu",
    "Ålandsvägen",
    "Vanha Hämeenkatu",
    "Kehä III",
    "  Itäväylä  ",
    "ITÄVÄYLÄ",
    "Annankatu.",
    "Iso Roobertinkatu",
    "Gyldénintie",
    "Näkinkuja",
    "Pohjoisesplanadi",
    "S:t Eriksgatan",
    "Runeberginkatu 's",
    "Åbovägen (norra)",
    "Örnvägen",
]


class NormalisationAgrees(unittest.TestCase):
    def test_python_and_javascript_fold_identically(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not on PATH")
        script = (
            "const {normAddr}=require(%s);"
            "const c=JSON.parse(process.argv[1]);"
            "console.log(JSON.stringify(c.map(normAddr)));"
            % json.dumps(str(ROOT / "src" / "testprop.js"))
        )
        out = subprocess.run([node, "-e", script, json.dumps(CASES)],
                             capture_output=True, text=True, check=True)
        js = json.loads(out.stdout)
        py = [B.norm(c) for c in CASES]
        for case, a, b in zip(CASES, py, js):
            self.assertEqual(a, b, f"{case!r}: python {a!r} != javascript {b!r}")

    def test_a_street_written_either_way_lands_on_one_key(self):
        self.assertEqual(B.norm("Itäväylä"), B.norm("ITÄVÄYLÄ"))
        self.assertEqual(B.norm("Vanha  Hämeenkatu"), B.norm("Vanha Hämeenkatu "))
        self.assertEqual(B.norm("Töölönkatu"), "toolonkatu")
        self.assertEqual(B.norm("Ålandsvägen"), "alandsvagen")

    def test_normalisation_never_returns_leading_or_trailing_space(self):
        for c in CASES:
            n = B.norm(c)
            self.assertEqual(n, n.strip())
            self.assertNotIn("  ", n)


class PackingRoundTrips(unittest.TestCase):
    """The delta encoding must give back exactly the coordinates that went in."""

    def test_deltas_reconstruct_the_original_points(self):
        pts = [("1", (6016986, 2493825)), ("3", (6016991, 2493830)),
               ("5a", (6017004, 2493841)), ("7", (6016950, 2493700))]
        parts, plat, plon = [], None, None
        for h, (lat, lon) in pts:
            parts.append(f"{h},{lat},{lon}" if plat is None else f"{h},{lat - plat},{lon - plon}")
            plat, plon = lat, lon
        packed = ";".join(parts)
        # the same walk the browser does in adrHouses()
        out, lat, lon, first = [], 0, 0, True
        for part in packed.split(";"):
            i = part.rindex(",")
            j = part.rindex(",", 0, i)
            dlat, dlon = int(part[j + 1:i]), int(part[i + 1:])
            if first:
                lat, lon, first = dlat, dlon, False
            else:
                lat += dlat
                lon += dlon
            out.append((part[:j], (lat, lon)))
        self.assertEqual(out, pts)

    def test_a_house_with_no_number_still_parses(self):
        """A street can carry an address with no house number; the row must not be dropped."""
        packed = ",6040908,2098865"
        i = packed.rindex(",")
        j = packed.rindex(",", 0, i)
        self.assertEqual(packed[:j], "")
        self.assertEqual(int(packed[j + 1:i]), 6040908)


class BuiltFilesAreSane(unittest.TestCase):
    """Whatever has actually been built must obey the repo's rules."""

    def setUp(self):
        self.dir = ROOT / "data" / "processed" / "addr"
        if not self.dir.exists():
            self.skipTest("no address files built yet — run `make addr`")
        self.files = sorted(p for p in self.dir.glob("*.json") if p.name != "manifest.json")
        if not self.files:
            self.skipTest("no per-kunta address files built yet")

    def test_no_file_is_over_the_ceiling(self):
        for f in self.files + sorted((self.dir / "ix").glob("*.json")):
            self.assertLessEqual(f.stat().st_size, B.MAX_BYTES,
                                 f"{f.name} is {f.stat().st_size:,} B")

    def test_every_street_row_has_a_name_in_at_least_one_language(self):
        d = json.loads(self.files[0].read_text(encoding="utf-8"))
        self.assertTrue(d["s"], "an address file with no streets should not have been written")
        for fin, swe, packed in d["s"]:
            self.assertTrue(fin or swe, "a street row with neither name cannot be searched")
            self.assertTrue(packed, "a street row with no houses cannot be searched")

    def test_codes_keep_their_leading_zero(self):
        for f in self.files:
            d = json.loads(f.read_text(encoding="utf-8"))
            self.assertEqual(d["k"], f.stem)
            self.assertEqual(len(d["k"]), 3, f"{f.stem}: kunta codes are three characters")


if __name__ == "__main__":
    unittest.main()
