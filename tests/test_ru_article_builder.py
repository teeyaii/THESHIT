import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from docx import Document
from citation_language_qa import language_candidates
from statistical_engine import analyze,LABEL
from ru_article_builder import build,verify

def sample():
    rng=np.random.default_rng(2569);x=rng.normal(size=48)
    return analyze(pd.DataFrame({"x":x,"y":x+rng.normal(size=48)}),["x"],"y",source_label=LABEL)

class ArticleTests(unittest.TestCase):
    def test_structure(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"article";qa=build(sample(),out)
            self.assertEqual(qa,verify(out))
            self.assertNotIn("THAI_RUN_WITHOUT_CS",{w["code"] for w in language_candidates(out/"SYNTHETIC_RU_article.docx")["warnings"]})
            self.assertFalse(qa["official_article_template_verified"])
            self.assertFalse(qa["final_acceptance"])
            doc=Document(out/"SYNTHETIC_RU_article.docx")
            self.assertIn("Abstract",[p.text for p in doc.paragraphs])
            self.assertAlmostEqual(doc.sections[0].left_margin.inches,1.5)
            self.assertAlmostEqual(doc.sections[0].right_margin.inches,1.0)
            self.assertIn("สมมติฐานการวิจัย",[p.text for p in doc.paragraphs])
            self.assertIn("เอกสารอ้างอิง",[p.text for p in doc.paragraphs])
            self.assertGreater(qa["facts_in_manifest"],0)
            doc.add_paragraph("tampered");doc.save(out/"SYNTHETIC_RU_article.docx")
            with self.assertRaises(ValueError):
                verify(out)
    def test_reject_real(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"article";r=sample();r["label"]="REAL"
            with self.assertRaises(ValueError):
                build(r,out)
            self.assertFalse(out.exists())
