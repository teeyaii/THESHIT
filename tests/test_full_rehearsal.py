import tempfile
import unittest
from pathlib import Path
from full_rehearsal import run,verify

class FullRehearsalTests(unittest.TestCase):
    def test_connected_workflow(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"rehearsal"
            qa=run(root,"a"*40)
            self.assertEqual(qa,verify(root))
            self.assertEqual(qa["claims"],1)
            self.assertEqual(qa["references"],1)
            self.assertEqual(qa["notes"],1)
            self.assertTrue(qa["negative_review_blocked"])
            self.assertFalse(qa["final_acceptance"])
            self.assertEqual(qa["release_status"],"BLOCKED")
            (root/"claim_qa.json").write_text("altered",encoding="utf-8")
            with self.assertRaises(ValueError):verify(root)
