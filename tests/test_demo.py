import unittest
import pandas as pd
from research_demo import fixture, validate, run_demo, LABEL, alpha

class DemoTests(unittest.TestCase):
    def test_reproducible(self):
        pd.testing.assert_frame_equal(fixture(), fixture())
        self.assertEqual(run_demo(), run_demo())
    def test_schema(self):
        df = fixture()
        validate(df)
        self.assertEqual(df.shape, (100, 14))
    def test_bad_response(self):
        df = fixture()
        df.iloc[0, 0] = 9
        with self.assertRaises(ValueError):
            validate(df)
    def test_missing(self):
        df = fixture().astype(float)
        df.iloc[0, 0] = float("nan")
        with self.assertRaises(ValueError):
            validate(df)
    def test_report(self):
        report = run_demo()
        self.assertEqual(report["label"], LABEL)
        self.assertEqual(set(report["ols"]["hc3_p_values"]), {"const", "PE", "EE", "SI"})
        self.assertTrue(0 <= report["ols"]["r_squared"] <= 1)
    def test_alpha_constant(self):
        self.assertIsNone(alpha(pd.DataFrame({"a": [3,3], "b": [3,3]})))
