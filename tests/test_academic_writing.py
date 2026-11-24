import tempfile
import unittest
from pathlib import Path
from copy import deepcopy
import numpy as np
import pandas as pd
from statistical_engine import analyze,LABEL
from academic_writing import draft,verify_draft,export_draft

def sample():
    rng=np.random.default_rng(210);x=rng.normal(size=(70,2))
    return analyze(pd.DataFrame({"a":x[:,0],"b":x[:,1],"y":-x[:,0]+rng.normal(size=70)}),
                   ["a","b"],"y",source_label=LABEL)

class WritingTests(unittest.TestCase):
    def test_all_facts_reproducible(self):
        report=sample();d=draft(report);q=verify_draft(report,d)
        self.assertEqual(q["status"],"DETERMINISTIC_DRAFT_QA_PASS")
        self.assertFalse(d["final_acceptance"])
        self.assertLess(next(f["value"] for f in d["facts"] if f["id"]=="C1-b"),0)
        self.assertEqual(len([p for p in d["paragraphs"] if p["id"].startswith("results-coeff-")]),2)
        for f in d["facts"]:
            cursor=report
            for key in f["json_path"].strip("/").split("/"):
                cursor=cursor[int(key)] if isinstance(cursor,list) else cursor[key]
            self.assertEqual(cursor,f["value"])
        self.assertEqual(d["discussion_status"],"BLOCKED_NO_INDEPENDENTLY_APPROVED_SOURCES")

    def test_tamper_and_real_mode(self):
        report=sample();d=deepcopy(draft(report));d["paragraphs"][1]["text"]="Fabricated result"
        with self.assertRaises(ValueError):
            verify_draft(report,d)
        report["label"]="REAL"
        with self.assertRaises(ValueError):
            draft(report)

    def test_export(self):
        with tempfile.TemporaryDirectory() as path:
            out=Path(path)/"draft"
            self.assertGreater(export_draft(sample(),out)["fact_count"],10)
            self.assertIn(LABEL,(out/"SYNTHETIC_draft.txt").read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                export_draft(sample(),out)
