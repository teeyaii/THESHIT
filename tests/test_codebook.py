import unittest
from codebook import load_codebook, audit
from research_demo import fixture, run_demo

class CodebookTests(unittest.TestCase):
    def test_mapping(self):
        book, groups, digest = load_codebook()
        self.assertEqual(sum(map(len, groups.values())), 14)
        self.assertFalse(book["real_data_enabled"])
        self.assertEqual(len(digest), 64)
    def test_audit(self):
        _, groups, _ = load_codebook()
        df = fixture()
        self.assertTrue(audit(df, groups)["passed"])
        self.assertFalse(audit(df.drop(columns=["PE1"]), groups)["passed"])
        df = df.astype(object)
        df.loc[0, "PE1"] = True
        df.loc[1, "PE1"] = "4"
        df.loc[2, "PE1"] = None
        result = audit(df, groups)
        self.assertEqual(result["invalid_cells"], 2)
        self.assertEqual(result["missing_cells"], 1)
        self.assertFalse(result["passed"])
    def test_provenance(self):
        report = run_demo()
        self.assertEqual(report["codebook_sha256"], load_codebook()[2])
        self.assertTrue(report["data_audit"]["passed"])
