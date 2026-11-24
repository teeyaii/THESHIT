import tempfile
import unittest
from pathlib import Path
from rc_verification import run,verify

class RCTest(unittest.TestCase):
    def test_combined_provenance_and_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"rc"
            qa=run(out,"a"*40)
            self.assertEqual(qa,verify(out))
            self.assertEqual(qa["thesis"]["chapters"],5)
            self.assertEqual(qa["release_status"],"BLOCKED")
            self.assertFalse(qa["final_acceptance"])
            (out/"SYNTHETIC_language_candidates.json").write_text("tampered",encoding="utf-8")
            with self.assertRaises(ValueError):verify(out)
