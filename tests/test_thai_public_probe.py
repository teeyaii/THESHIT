import unittest
import tempfile
from pathlib import Path
from thai_public_probe import inspect_one,probe,SOURCES
from test_oss_adapters import tiny_pdf

class PublicProbeTests(unittest.TestCase):
    def test_inspect_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.pdf";tiny_pdf(p)
            r=inspect_one(p.read_bytes(),"evidence test",10)
            self.assertEqual(r["total_pages"],1)
            self.assertTrue(r["native_text_present"])
            self.assertTrue(r["title_exact_normalized_substring"])
            self.assertEqual(r["status"],"PILOT_METRICS_ONLY")
    def test_no_fake_results(self):
        def failed(url):
            raise RuntimeError("network unavailable")
        r=probe(failed)
        self.assertEqual(len(r["records"]),len(SOURCES))
        self.assertTrue(all(x["status"]=="BLOCKED_OR_FAILED" for x in r["records"]))
