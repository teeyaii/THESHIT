"""Cross-module regression on the same synthetic bundle, including newer audit modules."""
import json
import tempfile
import unittest
from pathlib import Path

from theshit_cli import run_demo, verify_demo
from document_coverage import inventory, audit
from evidence_review import review_ledger, canonical_hash

class ReleaseIntegrationTests(unittest.TestCase):
    def test_candidate_to_structural_review(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"demo"
            baseline=run_demo(root)
            self.assertEqual(verify_demo(root),baseline)
            index=json.loads((root/"candidates/evidence_index.json").read_text(encoding="utf-8"))
            record=index["records"][0]
            hit=record["hits"][0]
            self.assertEqual(record["status"],"CANDIDATE_UNVERIFIED")
            self.assertEqual(review_ledger(index,[])["records"][0]["status"],
                             "INCOMPLETE_INDEPENDENT_REVIEW")
            decision={"evidence_id":record["evidence_id"],"record_sha256":canonical_hash(record),
                      "reviewer_id":"SYNTHETIC_FIXTURE_A","decision":"SUPPORTS",
                      "rationale":"Synthetic integration fixture, not a human review",
                      "full_context_reviewed":True,"source_sha256":record["source_sha256"],
                      "physical_page":hit["physical_page"],"source_excerpt":hit["matched_text"],
                      "candidate_image_sha256":hit["image_sha256"]}
            other=dict(decision,reviewer_id="SYNTHETIC_FIXTURE_B",decision="PARTIAL")
            result=review_ledger(index,[decision,other])
            self.assertFalse(result["final_acceptance"])
            self.assertEqual(result["records"][0]["status"],"DISAGREEMENT_REQUIRES_RECONCILIATION")
            path=root/"sources/SYNTHETIC_word.docx"
            inv=inventory(path)
            paragraph=next(p for p in inv["paragraphs"] if p["text"]=="SYNTHETIC evidence fixture")
            spans=[{"part":paragraph["part"],"paragraph":paragraph["paragraph"],
                    "start":0,"end":len(paragraph["text"]),"text":paragraph["text"],"color":"FFE066"}]
            out=audit(path,spans,expected_sha256=inv["source_sha256"])
            self.assertEqual(out["matched_characters"],out["expected_characters"])
            self.assertEqual(out["missing"],[])
            self.assertEqual(out["wrong_color"],[])
            self.assertEqual(out["unresolved"],[])
            self.assertEqual(verify_demo(root),baseline)
