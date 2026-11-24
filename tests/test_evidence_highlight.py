import tempfile
import unittest
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from evidence_engine import candidate_atlas,digest
from evidence_highlight import highlight_candidates,audit_body_shading
from test_oss_adapters import tiny_pdf

class HighlightTests(unittest.TestCase):
    def test_render_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            sources=root/"sources";sources.mkdir()
            pdf=sources/"fixture.pdf";tiny_pdf(pdf)
            source_hash=digest(pdf)
            candidates=root/"candidates"
            index=candidate_atlas([{"evidence_id":"EV1","source_file":"fixture.pdf",
                                  "phrase":"evidence test"}],sources,candidates)
            out=root/"highlighted"
            result=highlight_candidates(index,sources,candidates,out,{"fixture.pdf":"FFE066"})
            row=result["records"][0]
            self.assertEqual(row["source_sha256"],source_hash)
            self.assertEqual(digest(pdf),source_hash)
            self.assertEqual(row["image_sha256"],digest(out/row["image"]))
            self.assertNotEqual(row["image_sha256"],row["candidate_image_sha256"])
            self.assertTrue(result["review_required"])
            with self.assertRaises(ValueError):
                highlight_candidates(index,sources,candidates,out,{"fixture.pdf":"FFE066"})

    def test_reject_tampered_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);sources=root/"sources";sources.mkdir()
            pdf=sources/"fixture.pdf";tiny_pdf(pdf)
            candidates=root/"candidates"
            index=candidate_atlas([{"evidence_id":"EV1","source_file":"fixture.pdf",
                                  "phrase":"evidence test"}],sources,candidates)
            pdf.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                highlight_candidates(index,sources,candidates,root/"highlighted",{"fixture.pdf":"FFE066"})
            self.assertFalse((root/"highlighted").exists())

    def test_exact_thai_shading(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.docx";doc=Document()
            para=doc.add_paragraph()
            run=para.add_run("ไทย")
            shading=OxmlElement("w:shd");shading.set(qn("w:fill"),"FFE066")
            run._r.get_or_add_rPr().append(shading)
            para.add_run(" test");doc.save(p)
            result=audit_body_shading(p,[{"paragraph":0,"start":0,"end":4,
                "text":"ไทย ","color":"FFE066"}])
            self.assertEqual(result["expected_characters"],4)
            self.assertEqual(result["matched_characters"],3)
            self.assertEqual(result["missing"],[[0,3]])
            self.assertEqual(result["source_sha256"],digest(p))
            with self.assertRaises(ValueError):
                audit_body_shading(p,[{"paragraph":0,"start":0,"end":3,"text":"bad","color":"FFE066"}])
