import tempfile
import unittest
from pathlib import Path
from docx import Document
from evidence_engine import candidate_atlas, locate_word_paragraphs, digest
from test_oss_adapters import tiny_pdf

class EvidenceTests(unittest.TestCase):
    def test_atlas(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"sources"
            root.mkdir()
            pdf=root/"fixture.pdf"
            tiny_pdf(pdf)
            before=digest(pdf)
            output=Path(d)/"out"
            index=candidate_atlas([
                {"evidence_id":"EV-001","source_file":"fixture.pdf","phrase":"evidence test"},
                {"evidence_id":"EV-002","source_file":"fixture.pdf","phrase":"not present"},
                {"evidence_id":"EV-003","source_file":"missing.pdf","phrase":"missing"},
            ],root,output)
            first,second,third=index["records"]
            self.assertEqual(first["status"],"CANDIDATE_UNVERIFIED")
            self.assertEqual(second["status"],"NO_MATCH")
            self.assertEqual(third["status"],"NOT_ACCESSIBLE")
            hit=first["hits"][0]
            self.assertEqual(hit["physical_page"],1)
            self.assertEqual(hit["image_sha256"],digest(output/hit["image"]))
            self.assertEqual(first["source_sha256"],before)
            self.assertEqual(digest(pdf),before)
            self.assertEqual(len(Document(output/"candidate_atlas.docx").inline_shapes),1)
            self.assertTrue((output/"evidence_index.json").exists())
    def test_invalid_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"src"
            root.mkdir()
            for source,key in [("../bad.pdf","EV-1"),("fixture.pdf","../bad")]:
                with self.assertRaises(ValueError):
                    candidate_atlas([{"evidence_id":key,"source_file":source,
                                      "phrase":"test"}],root,Path(d)/"out")
    def test_duplicate_id(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"src"
            root.mkdir()
            row={"evidence_id":"EV-1","source_file":"fixture.pdf","phrase":"test"}
            with self.assertRaises(ValueError):
                candidate_atlas([row,row],root,Path(d)/"out")
    def test_word_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"fixture.docx"
            doc=Document()
            p=doc.add_paragraph()
            p.add_run("evidence ")
            p.add_run("test")
            doc.add_table(rows=1,cols=1).cell(0,0).text="evidence test"
            doc.save(path)
            before=digest(path)
            result=locate_word_paragraphs(path,"evidence test")
            self.assertEqual(len(result["locations"]),2)
            self.assertEqual(result["document_sha256"],before)
            self.assertEqual(digest(path),before)
