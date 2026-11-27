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

    def test_explicit_role_sizes_and_flexible_table(self):
        from ru_thesis_builder import make_styles
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"roles.docx"
            doc=Document()
            make_styles(doc,get_profile(PROFILE))
            for style,txt in [("RU Subheading","Heading"),("RU Subheading 2","Subheading"),
                              ("RU TOC Title","Contents"),("RU Bibliography Title","References"),
                              ("RU Front","Unverified front title"),("RU Notice","Synthetic notice"),
                              ("RU Caption","Table caption")]:
                doc.add_paragraph(txt,style=style)
            doc.save(path)
            mapping={"RUSubheading":"heading1","RUSubheading2":"heading2",
                     "RUTOCTitle":"toc_title","RUBibliographyTitle":"bibliography_title",
                     "RUFront":"front_title","RUNotice":"fixture_notice","RUCaption":"caption"}
            qa=audit_styles(path,mapping)
            sizes=[c for c in qa["checks"] if c["field"]=="sz"]
            self.assertEqual([c["expected"] for c in sizes],[20,18,22,18,None,16,12])
            self.assertEqual([c["status"] for c in sizes],["PASS","PASS","PASS","PASS","UNRESOLVED","PASS","PASS"])
            self.assertEqual(sizes[5]["basis"],"SYNTHETIC_FIXTURE_CONVENTION_NOT_UNIVERSITY_RULE")
            self.assertFalse(qa["final_acceptance"])
            doc.paragraphs[1].runs[0].font.size=Pt(20)
            doc.save(path)
            self.assertTrue(any(c["location"].startswith("body/p:1/") and c["field"]=="sz" and c["status"]=="FAIL" for c in audit_styles(path,mapping)["checks"]))

    def test_ia42_style_audit_detects_bad_caption_and_role_margin(self):
        from ru_thesis_builder import build,demo_report,SECTION_ROLES
        from docx.shared import Inches
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"thesis";build(demo_report(),root)
            path=root/"SYNTHETIC_RU_structure.docx";doc=Document(path)
            doc.styles["RU Caption"].font.size=Pt(16)
            doc.styles["RU Caption"]._element.rPr.find(qn("w:szCs")).set(qn("w:val"),"32")
            doc.sections[1].top_margin=Inches(1.5)
            doc.sections[5].top_margin=Inches(1)
            doc.save(path)
            qa=audit_styles(path,{"RUCaption":"caption"},section_roles=SECTION_ROLES)
            failed=[c for c in qa["checks"] if c["status"]=="FAIL"]
            self.assertTrue(any(c["field"]=="szCs" and c["expected"]==12 for c in failed))
            self.assertEqual({c["location"] for c in failed if c["field"]=="top_margin_mm"},{"section:1","section:5"})
