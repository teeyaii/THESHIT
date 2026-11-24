import tempfile
import unittest
from pathlib import Path
from thai_extraction_comparison import compare
from thai_public_probe import SOURCES
from test_oss_adapters import tiny_pdf

class ComparisonTests(unittest.TestCase):
    def test_same_pdf_and_no_auto_accept(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.pdf";tiny_pdf(p);data=p.read_bytes()
            titles=iter(row[3] for row in SOURCES)
            r=compare(lambda url:data,lambda payload:next(titles))
            self.assertEqual(r["compared"],5)
            self.assertEqual(r["pdfplumber_exact"],0)
            self.assertEqual(r["poppler_exact"],5)
            self.assertFalse(r["final_acceptance"])
            self.assertEqual(len({row["source_sha256"] for row in r["records"]}),1)
    def test_missing_extractor(self):
        def failed(data):raise RuntimeError("missing")
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.pdf";tiny_pdf(p)
            r=compare(lambda url:p.read_bytes(),failed)
            self.assertEqual(r["compared"],0)
            self.assertTrue(all(x["comparison_status"]=="BLOCKED_OR_FAILED" for x in r["records"]))
