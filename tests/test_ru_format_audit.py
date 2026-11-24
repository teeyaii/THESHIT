import tempfile
import unittest
from pathlib import Path
from docx import Document
from docx.shared import Mm,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from ru_format_audit import audit,get_profile

PROFILE="ru_mba_campus_2568"
def fixture(path,bad=False):
    d=Document()
    sec=d.sections[0]
    sec.page_width=Mm(210);sec.page_height=Mm(297)
    sec.left_margin=Mm(38.1);sec.right_margin=Mm(25.4)
    sec.bottom_margin=Mm(25.4);sec.top_margin=Mm(38.1)
    normal=d.styles["Normal"]
    normal.paragraph_format.first_line_indent=Mm(12.7)
    p=d.add_paragraph()
    r=p.add_run("ตัวอย่าง Thai")
    r.font.name="Browallia New";r.font.size=Pt(16)
    pr=r._r.get_or_add_rPr()
    pr.rFonts.set(qn("w:cs"),"Browallia New")
    sz=OxmlElement("w:szCs");sz.set(qn("w:val"),"32");pr.append(sz)
    if bad:
        p.paragraph_format.first_line_indent=Mm(0)
        r.font.name="Arial"
    d.save(path)

class RUAuditTests(unittest.TestCase):
    def test_profile_conflict_retained(self):
        self.assertIsNone(get_profile(PROFILE)["chapter_size_pt"])
        self.assertEqual(get_profile(PROFILE)["chapter_size_candidates_pt"],[20,22])
        self.assertEqual(get_profile("ru_mba_excellence_bus7096")["chapter_size_pt"],24)
    def test_scoped_match_and_override(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"sample.docx";fixture(p)
            out=audit(p,PROFILE,["Normal"],["numbered_page"])
            self.assertEqual(out["counts"]["FAIL"],0)
            self.assertEqual(out["counts"]["UNRESOLVED"],0)
            self.assertFalse(out["final_acceptance"])
            fixture(p,bad=True)
            out=audit(p,PROFILE,["Normal"],["numbered_page"])
            self.assertGreaterEqual(out["counts"]["FAIL"],3)
    def test_unknown_role(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"sample.docx";fixture(p)
            out=audit(p,PROFILE,["Normal"],["unknown"])
            self.assertGreater(out["counts"]["UNRESOLVED"],0)
            with self.assertRaises(ValueError):
                audit(p,PROFILE,["Normal"],[])
