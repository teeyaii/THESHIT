import tempfile
import unittest
from pathlib import Path
import pandas as pd
import pyreadstat
from docx import Document
from research_demo import fixture, LABEL
from oss_adapters import (validate_fixture, export_demo_docx, export_demo_sav,
                          pdf_text_matches, dependency_versions)

def tiny_pdf(path):
    stream = b"BT /F1 12 Tf 30 100 Td (SYNTHETIC evidence test) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.write_bytes(data)

class AdapterTests(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(len(dependency_versions()), 4)
    def test_pandera(self):
        df = fixture()
        pd.testing.assert_frame_equal(validate_fixture(df), df)
        df.iloc[0,0] = 8
        with self.assertRaises(ValueError):
            validate_fixture(df)
    def test_sav_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "SYNTHETIC.sav"
            expected = export_demo_sav(path)
            actual, meta = pyreadstat.read_sav(str(path))
            pd.testing.assert_frame_equal(actual, expected, check_dtype=False)
            self.assertEqual(meta.file_label, LABEL)
    def test_docx(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "SYNTHETIC.docx"
            export_demo_docx(path)
            doc = Document(str(path))
            self.assertEqual(doc.paragraphs[0].text, LABEL)
            self.assertEqual(len(doc.tables[0].rows), 5)
    def test_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "SYNTHETIC.pdf"
            tiny_pdf(path)
            hits = pdf_text_matches(path, "evidence test")
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["page"], 1)
            self.assertEqual(hits[0]["status"], "CANDIDATE_UNVERIFIED")
            self.assertEqual(len(hits[0]["source_sha256"]), 64)
            self.assertEqual(pdf_text_matches(path, "not present"), [])
