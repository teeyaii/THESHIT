import tempfile
import unittest
from pathlib import Path
from reviewed_references import prepare,export

def fixture():
    return {"reference_id":"R1","metadata_review_status":"REVIEWED","reviewer_id":"fixture",
            "type":"journal_article","apa_author_labels":["Example, A.","Fixture, B."],
            "reviewed_sort_key":"example","year":2003,"title":"Synthetic test","journal":"Fixture Journal",
            "volume":"12","issue":"3","pages":"1–9","doi":"10.1234/fixture"}

class ReferenceTests(unittest.TestCase):
    def test_old_year_and_italics(self):
        r=fixture();e=prepare([r])["entries"][0]["segments"]
        self.assertEqual(e[0]["text"],"Example, A., & Fixture, B. (2003). Synthetic test. ")
        self.assertEqual(e[1],{"text":"Fixture Journal, 12","italic":True})
        self.assertEqual(e[2]["text"],"(3), 1–9. https://doi.org/10.1234/fixture")
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(export([r],Path(d)/"out")["final_acceptance"])
    def test_unreviewed_duplicate_and_missing(self):
        r=fixture()
        with self.assertRaises(ValueError):prepare([dict(r,metadata_review_status="CANDIDATE")])
        with self.assertRaises(ValueError):prepare([r,dict(r,reference_id="R2")])
        with self.assertRaises(ValueError):prepare([dict(r,pages=None)])
    def test_long_author_list(self):
        r=fixture();r["apa_author_labels"]=[f"Author{i}, A." for i in range(21)]
        t=prepare([r])["entries"][0]["segments"][0]["text"]
        self.assertIn("Author18, A., … Author20, A.",t)
        self.assertNotIn("Author19,",t)
