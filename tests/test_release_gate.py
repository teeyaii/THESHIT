import json
import unittest
from release_gate import evaluate,CONFIG
SHA="a"*40
def attestation(g):
    return {"gate":g,"commit_sha":SHA,"status":"PASS","reason":"Synthetic test attestation",
            "reviewer":"fixture","evidence_sha256":"b"*64}

class GateTests(unittest.TestCase):
    def test_missing_blocked(self):
        r=evaluate([],SHA);self.assertEqual(r["status"],"BLOCKED")
        self.assertEqual(len(r["remaining"]),12);self.assertFalse(r["final_acceptance"])
    def test_all_still_manual(self):
        gates=json.loads(CONFIG.read_text())["required_gates"]
        r=evaluate([attestation(g) for g in gates],SHA)
        self.assertEqual(r["status"],"READY_FOR_MANUAL_RELEASE_REVIEW")
        self.assertFalse(r["final_acceptance"]);self.assertFalse(r["real_data_enabled"])
    def test_stale_duplicate_and_missing_evidence(self):
        r=attestation("combined_ci")
        with self.assertRaises(ValueError):evaluate([r,r],SHA)
        with self.assertRaises(ValueError):evaluate([dict(r,commit_sha="c"*40)],SHA)
        with self.assertRaises(ValueError):evaluate([dict(r,evidence_sha256="")],SHA)
