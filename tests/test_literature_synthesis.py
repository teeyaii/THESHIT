import tempfile
import unittest
from pathlib import Path
from evidence_review import canonical_hash
from literature_synthesis import matrix,export,safe_cell
from test_evidence_review import fixture,decision

def note(idx):
    r=idx["records"][0]
    return {"note_id":"N1","evidence_id":r["evidence_id"],"record_sha256":canonical_hash(r),
            "author_reviewed":True,"author_id":"synthetic-fixture","theme":"Demo theme",
            "study_design":"Fixture design","population_context":"Fixture population",
            "constructs":"Fixture construct","finding_note":r["claim"],
            "limitations_note":"Fixture limitation","applicability_note":"Fixture context","direction":"NULL"}

class SynthesisTests(unittest.TestCase):
    def test_review_gate_and_export(self):
        idx=fixture();n=note(idx)
        decisions=[decision(idx,"a"),decision(idx,"b")]
        qa=matrix(idx,decisions,[n])
        self.assertEqual(len(qa["rows"]),1)
        self.assertEqual(qa["themes"][0]["distinct_source_count"],1)
        self.assertFalse(qa["final_acceptance"])
        self.assertEqual(len(matrix(idx,decisions[:1],[n])["blocked"]),1)
        with tempfile.TemporaryDirectory() as d:
            export(idx,decisions,[n],Path(d)/"out")
            self.assertTrue((Path(d)/"out/literature_notes_review.csv").exists())
    def test_changed_finding_and_duplicate(self):
        idx=fixture();n=note(idx);decisions=[decision(idx,"a"),decision(idx,"b")]
        self.assertEqual(len(matrix(idx,decisions,[dict(n,finding_note="New claim")])["blocked"]),1)
        with self.assertRaises(ValueError):matrix(idx,decisions,[n,dict(n,note_id="N2")])
    def test_formula_escaped(self):
        self.assertEqual(safe_cell("  =1+1"),"'  =1+1")
        self.assertEqual(safe_cell("normal"),"normal")
