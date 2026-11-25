import tempfile
import unittest
from pathlib import Path
from docx import Document
from citation_language_qa import language_candidates
from ru_thesis_builder import build,verify,demo_report,PROFILE

class RUThesisTests(unittest.TestCase):
    def test_synthetic_structure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"structure"
            qa=build(demo_report(),p)
            self.assertEqual(qa["chapters"],5)
            self.assertEqual(qa["profile"],PROFILE)
            self.assertFalse(qa["final_acceptance"])
            self.assertEqual(qa["toc_status"],"FIELD_PRESENT_NOT_UPDATED")
            self.assertEqual(verify(p),qa)
            self.assertNotIn("THAI_RUN_WITHOUT_CS",{w["code"] for w in language_candidates(p/"SYNTHETIC_RU_structure.docx")["warnings"]})
            doc=Document(p/"SYNTHETIC_RU_structure.docx")
            self.assertEqual(doc.styles["RU Chapter"].font.size.pt,20)
            self.assertEqual(doc.styles["RU Body"].font.size.pt,16)
            self.assertFalse(doc.styles["RU Chapter"].font.bold)
            self.assertEqual(doc.styles["RU Subheading"].font.size.pt,20)
            self.assertEqual(doc.styles["RU Subheading 2"].font.size.pt,18)
            self.assertEqual(doc.styles["RU TOC Title"].font.size.pt,22)
            self.assertEqual(doc.styles["RU Bibliography Title"].font.size.pt,18)
            self.assertIn("สารบัญตาราง",[p.text for p in doc.paragraphs])
            self.assertIn("สารบัญภาพ",[p.text for p in doc.paragraphs])
            self.assertIn("คำปฏิญาณตน",[p.text for p in doc.paragraphs])
            self.assertEqual(doc.styles["RU Body"].font.name,"Browallia New")
            self.assertEqual(doc.styles["RU Body"].paragraph_format.first_line_indent.inches,0.5)
            self.assertTrue(doc.styles["RU Chapter"].paragraph_format.page_break_before)
            with self.assertRaises(FileExistsError):
                build(demo_report(),p)
    def test_tampered_document(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"structure";build(demo_report(),p)
            path=p/"SYNTHETIC_RU_structure.docx"
            doc=Document(path);doc.add_paragraph("Unexpected");doc.save(path)
            with self.assertRaises(ValueError):
                verify(p)
    def test_real_mode_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"structure";report=demo_report();report["label"]="REAL"
            with self.assertRaises(ValueError):
                build(report,p)
            self.assertFalse(p.exists())
