import tempfile
import unittest
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from manuscript_preservation import assemble_synthetic,preservation_diff,LABEL

def make(path,fragment=False,complex=False):
    d=Document();d.add_paragraph(LABEL)
    r=d.add_paragraph().add_run("ข้อความตัวอย่าง" if fragment else "Base")
    sh=OxmlElement("w:shd");sh.set(qn("w:fill"),"FFE066");r._r.get_or_add_rPr().append(sh)
    d.add_table(rows=1,cols=1).cell(0,0).text="fixture"
    if complex:
        d.add_paragraph()._p.append(OxmlElement("w:fldSimple"))
    d.save(path)

class PreservationTests(unittest.TestCase):
    def test_compatible_append(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);a=p/"a.docx";b=p/"b.docx";out=p/"out.docx"
            make(a);make(b,True)
            r=assemble_synthetic(a,[b],out)
            self.assertEqual(r["blocks_verified"],6)
            self.assertEqual(preservation_diff(a,out)["changed_parts"],["word/document.xml"])
            doc=Document(out)
            self.assertEqual(len(doc.tables),2)
            self.assertEqual(doc.paragraphs[-1].runs[0]._r.rPr.find(qn("w:shd")).get(qn("w:fill")),"FFE066")
            self.assertFalse(r["real_manuscript_assembly"])
    def test_complex_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);a=p/"a.docx";b=p/"b.docx";make(a);make(b,True,True)
            with self.assertRaises(ValueError):assemble_synthetic(a,[b],p/"out.docx")
            self.assertFalse((p/"out.docx").exists())
    def test_style_change_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);a=p/"a.docx";b=p/"b.docx";make(a);make(b)
            doc=Document(b);doc.styles["Normal"].font.name="Other";doc.save(b)
            with self.assertRaises(ValueError):assemble_synthetic(a,[b],p/"out.docx")
