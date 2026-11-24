import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from core_oss import (dependency_inventory, synthetic_excel_roundtrip,
                      alpha_covariance, simple_regression_check)
from research_demo import alpha

class CoreOSSTests(unittest.TestCase):
    def test_excel_thai(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "SYNTHETIC_fixture.xlsx"
            rows = synthetic_excel_roundtrip(p)
            self.assertEqual(rows[0][0], "SYNTHETIC - NOT RESEARCH EVIDENCE")
            self.assertEqual(rows[1], ("ทดสอบภาษาไทย", 4))
            with self.assertRaises(FileExistsError):
                synthetic_excel_roundtrip(p)

    def test_alpha_independent(self):
        for values in ([[1,2,2],[2,4,3],[3,3,4],[4,5,5]],
                       [[1,4],[2,2],[3,3],[4,1]]):
            self.assertAlmostEqual(alpha_covariance(values), alpha(pd.DataFrame(values)), places=12)
        self.assertIsNone(alpha_covariance([[1,2],[1,2],[1,2]]))
        with self.assertRaises(ValueError):
            alpha_covariance([[1,2],[3,float("nan")]])

    def test_scipy_statsmodels(self):
        x = np.array([1,2,3,4,5,6])
        y = np.array([2,3,2,5,4,7])
        result = simple_regression_check(x,y)
        fit = sm.OLS(y, sm.add_constant(x)).fit()
        self.assertAlmostEqual(result["slope"], fit.params[1], places=12)
        self.assertAlmostEqual(result["intercept"], fit.params[0], places=12)
        self.assertAlmostEqual(result["pvalue"], fit.pvalues[1], places=12)
        self.assertAlmostEqual(result["r_squared"], fit.rsquared, places=12)
        with self.assertRaises(ValueError):
            simple_regression_check([1,1,1], [1,2,3])

    def test_inventory(self):
        names = {r["name"].lower() for r in dependency_inventory()}
        self.assertTrue({"openpyxl","scipy","statsmodels"}.issubset(names))
