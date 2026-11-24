import tempfile
import unittest
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from document_coverage import inventory,audit

def shade(run,color):
    s=OxmlElement("w:shd")
    s.set(qn("w:fill"),color);s.set(qn("w:val"),"clear")
    run._r.get_or_add_rPr().append(s)

class CoverageTests(unittest.TestCase):
    def test_parts_nested_tables_and_hyperlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.docx"; doc=Document()
            para=doc.add_paragraph()
            shade(para.add_run("ภาษา"),"FFE066")
            link=OxmlElement("w:hyperlink")
            r=OxmlElement("w:r");t=OxmlElement("w:t");t.text="ไทย"
            r.append(t);link.append(r);para._p.append(link)
            table=doc.add_table(rows=1,cols=1)
            cell=table.cell(0,0);shade(cell.paragraphs[0].add_run("table"),"FFE066")
            nested=cell.add_table(rows=1,cols=1)
            shade(nested.cell(0,0).paragraphs[0].add_run("nested"),"FFE066")
            shade(doc.sections[0].header.paragraphs[0].add_run("header"),"FFE066")
            shade(doc.sections[0].footer.paragraphs[0].add_run("footer"),"FFE066")
            doc.save(p)
            inv=inventory(p); rows={r["text"]:r for r in inv["paragraphs"] if r["text"]}
            self.assertEqual(rows["nested"]["table_depth"],2)
            self.assertEqual(rows["ภาษาไทย"]["colors"],["FFE066"]*4+[None]*3)
            self.assertTrue(rows["header"]["part"].startswith("word/header"))
            spans=[{"part":row["part"],"paragraph":row["paragraph"],"start":0,
                    "end":len(txt),"text":txt,"color":"FFE066"}
                   for txt,row in rows.items()]
            out=audit(p,spans,expected_sha256=inv["source_sha256"])
            self.assertEqual(len(out["missing"]),3)
            self.assertEqual(out["expected_characters"]-out["matched_characters"],3)
            self.assertEqual(out["unexpected"],[])
            self.assertEqual(inventory(p)["source_sha256"],inv["source_sha256"])

    def test_unknown_and_wrong_color(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.docx";doc=Document();para=doc.add_paragraph()
            shade(para.add_run("a"),"0000FF")
            run=para.add_run("b");h=OxmlElement("w:highlight");h.set(qn("w:val"),"yellow")
            run._r.get_or_add_rPr().append(h)
            shade(para.add_run("c"),"FFE066")
            doc.save(p)
            inv=inventory(p)
            spans=[{"part":"word/document.xml","paragraph":0,"start":0,"end":2,
                    "text":"ab","color":"FFE066"}]
            result=audit(p,spans,expected_sha256=inv["source_sha256"])
            self.assertEqual(len(result["wrong_color"]),1)
            self.assertEqual(len(result["unresolved"]),1)
            self.assertEqual(len(result["unexpected"]),1)
            with self.assertRaises(ValueError):
                audit(p,spans,expected_sha256="0"*64)
