import tempfile
import unittest
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from ru_format_audit import get_profile
from ru_style_audit import audit_styles,PROFILE

def fixture(path,chapter_size):
    doc=Document()
    h=doc.add_paragraph("Chapter 1",style="Heading 1")
    for run in h.runs:
        run.font.name="Browallia New";run.font.size=Pt(chapter_size)
    p=doc.add_paragraph("Body")
    p.paragraph_format.first_line_indent=Pt(36)
    p.paragraph_format.space_after=Pt(6)
    p.paragraph_format.line_spacing=1.5
    for run in p.runs:
        run.font.name="Browallia New";run.font.size=Pt(16)
    table=doc.add_table(rows=1,cols=1)
    table.cell(0,0).text="Table fixture"
    nested=table.cell(0,0).add_table(rows=1,cols=1)
    nested.cell(0,0).text="Nested fixture"
    fld=OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"),"TOC")
    doc.add_paragraph()._p.append(fld)
    doc.save(path)

class RUStyleTests(unittest.TestCase):
    def test_policy(self):
        p=get_profile(PROFILE)
        self.assertEqual(p["target_year_be"],2569)
        self.assertEqual(p["chapter_size_pt"],20)
        self.assertIsNone(p["literature_policy"]["max_age_years"])
        self.assertFalse(p["literature_policy"]["age_is_exclusion"])
        self.assertEqual(p["latest_guide_status"],"2569_SELECTED_PAGES_VISUALLY_VERIFIED")
        self.assertIsNone(get_profile("ru_mba_campus_2568")["chapter_size_pt"])

    def test_chapter_and_spacing(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"fixture.docx"
            fixture(path,20)
            mapping={"Heading1":"chapter","Normal":"body"}
            qa=audit_styles(path,mapping,{"body":{"space_after":6,"line_spacing":1.5}})
            chapter=[c for c in qa["checks"] if c["location"].startswith("body/p:0/") and c["field"]=="sz"]
            self.assertEqual(chapter[0]["status"],"PASS")
            self.assertIn("TOC",qa["main_part_field_tokens"])
            self.assertTrue(any("/table:0" in p["location"] for p in qa["inventory"]))
            self.assertFalse(qa["final_acceptance"])
            fixture(path,22)
            qa=audit_styles(path,mapping)
            self.assertTrue(any(c["field"]=="sz" and c["location"].startswith("body/p:0/") and c["status"]=="FAIL" for c in qa["checks"]))
    def test_unknown_role(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"fixture.docx";fixture(path,20)
            qa=audit_styles(path,{"Heading1":"chapter"})
            self.assertTrue(any(c["field"]=="style_classification" and c["status"]=="UNRESOLVED" for c in qa["checks"]))
            with self.assertRaises(ValueError):
                audit_styles(path,{"Normal":"unknown"})
