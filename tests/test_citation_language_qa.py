import tempfile
import unittest
from pathlib import Path
from docx import Document
from document_coverage import inventory
from citation_language_qa import review_citations,language_candidates

class CitationLanguageTests(unittest.TestCase):
    def test_old_reference_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.docx";doc=Document();text="ตัวอย่าง (Fixture, 2003)";doc.add_paragraph(text);doc.save(p)
            ref={"reference_id":"R1","title":"Synthetic reference","year":2003,"metadata_review_status":"REVIEWED"}
            c={"citation_id":"C1","part":"word/document.xml","paragraph":0,"start":text.index("("),"end":len(text),
               "exact_text":"(Fixture, 2003)","reference_ids":["R1"],"claim_review_status":"REVIEWED"}
            m={"document_sha256":inventory(p)["source_sha256"],"references":[ref],"citations":[c]}
            result=review_citations(p,m)
            self.assertTrue(result["declared_links_consistent"])
            self.assertIsNone(result["age_cutoff"])
            self.assertFalse(result["final_acceptance"])
            c["reference_ids"]=["UNKNOWN"]
            self.assertFalse(review_citations(p,m)["declared_links_consistent"])
            m["document_sha256"]="0"*64
            with self.assertRaises(ValueError):review_citations(p,m)
    def test_warnings_no_edits(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.docx";doc=Document();doc.add_paragraph("ภาษา  ไทย TODO");doc.save(p)
            before=p.read_bytes()
            result=language_candidates(p)
            self.assertEqual({w["code"] for w in result["warnings"]},{"THAI_INTERNAL_MULTISPACE","UNREPLACED_PLACEHOLDER"})
            self.assertEqual(p.read_bytes(),before)
            self.assertEqual(result["automatic_edits"],0)
    def test_empty_inventory_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.docx";Document().save(p)
            r=review_citations(p,{"document_sha256":inventory(p)["source_sha256"],"references":[],"citations":[]})
            self.assertFalse(r["declared_links_consistent"])
