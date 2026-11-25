import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from docx import Document
from statistical_engine import analyze,LABEL
from pdf_preview import prepare_docx,render_preview,PREVIEW

def sample():
    rng=np.random.default_rng(24);x=rng.normal(size=60)
    return analyze(pd.DataFrame({"x":x,"y":x+rng.normal(size=60)}),["x"],"y",source_label=LABEL)

class PDFPreviewTests(unittest.TestCase):
    def test_prepare(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.docx"
            expected=prepare_docx(sample(),p)
            self.assertGreater(len(expected["markers"]),10)
            self.assertEqual(len(expected["source_markers"]),4)
            self.assertEqual("".join(m.split(": ")[1] for m in expected["source_markers"]),expected["source_sha256"])
            doc=Document(p)
            self.assertEqual(doc.paragraphs[0].text,LABEL)
            self.assertIn(PREVIEW,doc.paragraphs[1].text)
            self.assertEqual(doc.sections[0].header.paragraphs[0].text,LABEL)
            with self.assertRaises(FileExistsError):
                prepare_docx(sample(),p)

    def test_optional_renderer(self):
        if os.getenv("THESHIT_REQUIRE_PDF_PREVIEW")!="1":
            self.skipTest("Dedicated preview workflow supplies LibreOffice and Noto fonts")
        with tempfile.TemporaryDirectory() as d:
            qa=render_preview(sample(),Path(d)/"preview")
            self.assertTrue(qa["fact_text_gate"])
            self.assertTrue(qa["paragraph_text_gate"])
            self.assertFalse(qa["academic_acceptance"])
            self.assertEqual(qa["word_visual_qa"],"NOT_EXECUTED")
            self.assertGreater(qa["page_count"],0)

    def test_split_sara_am_not_normalized_away(self):
        from pdf_preview import norm
        self.assertNotEqual(norm("กำหนด"),norm("กําหนด"))
        self.assertEqual(norm("ภาษา ไทย"),norm("ภาษาไทย"))
