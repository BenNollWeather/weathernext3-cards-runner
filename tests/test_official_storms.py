"""JTWC Southern Hemisphere ids. These do not download warnings."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebook" / "weathernext3_cyclones.ipynb"

WARNING = """\
WTPS51 PGTW 162100
WARNING    ATCG MIL 04P SWP 261116193946
2026111618 04P {name}     004  01 260 07 SATL 030
T000 089S 1626W 085 R034 045 NE QD
"""


def load_naming():
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    src = "".join(nb["cells"][1]["source"])
    src = "\n".join(line for line in src.splitlines() if not line.startswith("%"))
    src = src.split("# ---------------------------------------------------------------- run", 1)[0]
    namespace = {"__name__": "weathernext3_naming"}
    exec(compile(src, str(NOTEBOOK), "exec"), namespace)
    return namespace


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self, files):
        self.files = files
        self.calls = []

    def get(self, url, timeout=None, headers=None):
        self.calls.append(url)
        if url not in self.files:
            raise requests.RequestException(url)
        return FakeResponse(self.files[url])


def feed(namespace, files):
    base = namespace["JTWC_BASE"]
    payload = {base + "/rss/jtwc.rss": " ".join(
        path for path in files if path.endswith(".tcw"))}
    payload.update({base + "/" + path: body for path, body in files.items()})
    payload["https://www.nhc.noaa.gov/CurrentStorms.json"] = '{"activeStorms":[]}'
    namespace["SESSION"] = FakeSession(payload)
    return namespace["official_storms"]({})


class OfficialStormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_naming()

    def test_a_southern_hemisphere_warning_also_uses_the_previous_year(self):
        storms = feed(self.ns, {
            "products/sh0427.tcw": WARNING.format(name="XAVIER"),
            "products/io0526.tcw": WARNING.format(name="AKVAN"),
            "products/sh9027.tcw": WARNING.format(name="INVEST"),
        })
        self.assertEqual(storms["SH042027"]["label"], "Severe Tropical Cyclone Xavier")
        self.assertEqual(storms["SH042026"]["label"], "Severe Tropical Cyclone Xavier")
        self.assertTrue(storms["SH042026"]["named"])
        self.assertIn("IO052026", storms)
        self.assertNotIn("IO052025", storms)
        self.assertNotIn("SH902027", storms)
        self.assertNotIn("SH902026", storms)
        self.assertFalse(any(url.endswith("sh9027.tcw") for url in self.ns["SESSION"].calls))

    def test_a_real_previous_year_warning_keeps_its_name(self):
        storms = feed(self.ns, {
            "products/sh0427.tcw": WARNING.format(name="XAVIER"),
            "products/sh0426.tcw": WARNING.format(name="NARELLE"),
        })
        self.assertEqual(storms["SH042027"]["label"], "Severe Tropical Cyclone Xavier")
        self.assertEqual(storms["SH042026"]["label"], "Severe Tropical Cyclone Narelle")
        self.assertEqual(storms["SH042025"]["label"], "Severe Tropical Cyclone Narelle")


if __name__ == "__main__":
    unittest.main()
