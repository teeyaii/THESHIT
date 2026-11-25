import unittest
from research_alignment import review_alignment

def fixture():
    return {"scope":"SYNTHETIC_ONLY","references":[{"reference_id":"R1","metadata_review_status":"REVIEWED"}],
        "theories":[{"theory_id":"T1","name":"Synthetic theory","reference_id":"R1"}],
        "constructs":[{"construct_id":c,"theory_id":"T1","definition":"Synthetic definition "+c,"reference_id":"R1"} for c in ("X","Y")],
        "hypotheses":[{"hypothesis_id":"H1","predictor_id":"X","outcome_id":"Y","statement":"Synthetic relationship","reference_id":"R1"}],
        "items":[{"item_id":c+"1","construct_id":c,"text":"Synthetic item","adaptation_type":"ADAPTED","source_item":"Fixture item 1","source_locator":"Fixture p1","reference_id":"R1"} for c in ("X","Y")]}

class AlignmentTests(unittest.TestCase):
    def test_declared_links_only(self):
        data=fixture();qa=review_alignment(data)
        self.assertTrue(qa["declared_links_complete"])
        self.assertFalse(qa["final_acceptance"]);self.assertEqual(qa["ioc_status"],"NOT_EXECUTED")
        del data["items"][0]["source_item"]
        self.assertIn("SOURCE_ITEM_MISSING",{r["code"] for r in review_alignment(data)["issues"]})
        data["scope"]="REAL"
        with self.assertRaises(ValueError):review_alignment(data)

    def test_new_item_rationale_and_unreviewed_source(self):
        data=fixture();data["items"][0]["adaptation_type"]="NEW_FROM_DEFINITION"
        self.assertIn("DEFINITION_RATIONALE_MISSING",{r["code"] for r in review_alignment(data)["issues"]})
        data["items"][0]["adaptation_rationale"]="Synthetic definition-based item"
        data["references"][0]["metadata_review_status"]="CANDIDATE"
        self.assertFalse(review_alignment(data)["declared_links_complete"])
