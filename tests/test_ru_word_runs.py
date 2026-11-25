import tempfile
import unittest
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from ru_word_runs import add_script_runs,THAI
from citation_language_qa import language_candidates

class ThaiRunTests(unittest.TestCase):
    def test_exact_mixed_script_text_and_properties(self):
        doc=Document()
        text="ภาษาไทย ABC\tทดสอบ 123\nสระอำ"
        p=add_script_runs(doc.add_paragraph(),text)
        self.assertEqual(p.text,text)
        for run in p.runs:
            pr=run._r.rPr
            if THAI.search(run.text):
                self.assertIsNotNone(pr.find(qn("w:cs")))
                self.assertEqual(pr.find(qn("w:lang")).get(qn("w:bidi")),"th-TH")
                self.assertTrue(all(THAI.fullmatch(c) for c in run.text))
            elif pr is not None:
                self.assertIsNone(pr.find(qn("w:cs")))
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/"fixture.docx"
            doc.save(target)
            self.assertEqual(Document(target).paragraphs[0].text,text)
            self.assertNotIn("THAI_RUN_WITHOUT_CS",{w["code"] for w in language_candidates(target)["warnings"]})

    def test_direct_cs_missing_or_disabled_warns_without_edit(self):
        doc=Document()
        p=doc.add_paragraph("ABC ไทย")
        add_script_runs(p," ดี")
        run=p.add_run(" เสีย")
        cs=OxmlElement("w:cs");cs.set(qn("w:val"),"0")
        run._r.get_or_add_rPr().append(cs)
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/"fixture.docx";doc.save(target)
            before=target.read_bytes()
            result=language_candidates(target)
            warnings=[w for w in result["warnings"] if w["code"]=="THAI_RUN_WITHOUT_CS"]
            self.assertEqual([p.text[w["start"]:w["end"]] for w in warnings],["ไทย","เสีย"])
            self.assertEqual(target.read_bytes(),before)
            self.assertEqual(result["automatic_edits"],0)
