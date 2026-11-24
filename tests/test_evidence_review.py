import unittest
from evidence_review import review_ledger,canonical_hash

def fixture():
    row={"evidence_id":"DEMO1","status":"CANDIDATE_UNVERIFIED","claim":"Synthetic claim",
         "source_sha256":"a"*64,"total_pages":2,
         "hits":[{"physical_page":1,"image_sha256":"b"*64}]}
    return {"review_required":True,"records":[row]}

def decision(index,reviewer,outcome="SUPPORTS"):
    row=index["records"][0]
    return {"evidence_id":row["evidence_id"],"record_sha256":canonical_hash(row),
            "reviewer_id":reviewer,"decision":outcome,"rationale":"Synthetic test attestation",
            "full_context_reviewed":True,"source_sha256":"a"*64,"physical_page":1,
            "source_excerpt":"Synthetic source excerpt","candidate_image_sha256":"b"*64}

class EvidenceReviewTests(unittest.TestCase):
    def test_incomplete_and_agreement(self):
        index=fixture()
        self.assertEqual(review_ledger(index,[])["records"][0]["status"],"INCOMPLETE_INDEPENDENT_REVIEW")
        a=decision(index,"reviewer-a");b=decision(index,"reviewer-b")
        result=review_ledger(index,[a,b])
        self.assertEqual(result["records"][0]["status"],"REVIEWER_AGREEMENT_SUPPORTS")
        self.assertFalse(result["final_acceptance"])

    def test_disagreement_and_partial(self):
        index=fixture()
        a=decision(index,"reviewer-a");b=decision(index,"reviewer-b","PARTIAL")
        self.assertEqual(review_ledger(index,[a,b])["records"][0]["status"],"DISAGREEMENT_REQUIRES_RECONCILIATION")
        a["decision"]="PARTIAL"
        self.assertEqual(review_ledger(index,[a,b])["records"][0]["status"],"REVIEWER_AGREEMENT_PARTIAL")

    def test_stale_source_and_duplicate(self):
        index=fixture()
        a=decision(index,"reviewer-a")
        with self.assertRaises(ValueError):
            review_ledger(index,[a,decision(index,"REVIEWER-A")])
        b=decision(index,"reviewer-b");b["candidate_image_sha256"]="c"*64
        with self.assertRaises(ValueError):
            review_ledger(index,[a,b])
        b=decision(index,"reviewer-b");index["records"][0]["claim"]="Changed"
        with self.assertRaises(ValueError):
            review_ledger(index,[b])

    def test_missing_context(self):
        index=fixture();a=decision(index,"reviewer-a")
        a["full_context_reviewed"]=False
        with self.assertRaises(ValueError):
            review_ledger(index,[a])
        a["decision"]="NOT_ASSESSED"
        self.assertEqual(review_ledger(index,[a])["records"][0]["assessed_count"],0)
