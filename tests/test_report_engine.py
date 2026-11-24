import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from docx import Document
from openpyxl import load_workbook
from statistical_engine import analyze,LABEL
from report_engine import build_report,verify_report

def result():
    rng=np.random.default_rng(20)
    x=rng.normal(size=40);y=x+rng.normal(size=40)
    return analyze(pd.DataFrame({"=fixture":x,"y":y}),["=fixture"],"y",source_label=LABEL)

class ReportTests(unittest.TestCase):
    def test_roundtrip_and_formula_safety(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"report"
            qa=build_report(result(),out)
            self.assertEqual(qa["structural_qa"],"PASS")
            self.assertEqual(qa["tables"],7)
            self.assertGreater(qa["cells_verified_each_format"],50)
            workbook=load_workbook(out/"SYNTHETIC_tables.xlsx")
            self.assertEqual(workbook["Coefficients"]["A3"].data_type,"s")
            self.assertEqual(workbook["Coefficients"]["A3"].value,"=fixture")
            workbook.close()
            self.assertEqual(verify_report(out),qa)
            with self.assertRaises(FileExistsError):
                build_report(result(),out)
    def test_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"report"
            build_report(result(),out)
            path=out/"SYNTHETIC_report.docx"
            doc=Document(path);doc.tables[0].cell(1,1).text="999";doc.save(path)
            with self.assertRaises(ValueError):
                verify_report(out)
    def test_reject_non_demo(self):
        with tempfile.TemporaryDirectory() as d:
            invalid=result();invalid["label"]="REAL"
            out=Path(d)/"report"
            with self.assertRaises(ValueError):
                build_report(invalid,out)
            self.assertFalse(out.exists())
