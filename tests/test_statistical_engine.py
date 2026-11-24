import json
import unittest
import numpy as np
import pandas as pd
from statistical_engine import analyze,LABEL

def fixture():
    rng=np.random.default_rng(20261124)
    x=rng.normal(size=(80,2))
    return pd.DataFrame({"a":x[:,0],"b":x[:,1],
                         "y":0.7*x[:,0]-0.5*x[:,1]+rng.normal(size=80)})

class StatisticalTests(unittest.TestCase):
    def test_full_report(self):
        report=analyze(fixture(),["a","b"],"y",source_label=LABEL)
        self.assertEqual(report["n_complete"],80)
        self.assertEqual(report["model"]["independent_ols_hc3_check"],"PASS")
        rows=report["model"]["coefficients"]
        self.assertEqual([r["variable"] for r in rows],["const","a","b"])
        self.assertGreater(rows[1]["b"],0)
        self.assertLess(rows[2]["b"],0)
        self.assertIsNotNone(rows[2]["hc3_ci95"][0])
        self.assertIn("breusch_pagan_p",report["diagnostics"])
        json.dumps(report,allow_nan=False)

    def test_missing_cases(self):
        data=fixture();data.loc[0,"a"]=np.nan;data.loc[0,"b"]=np.nan
        with self.assertRaises(ValueError):
            analyze(data,["a","b"],"y",source_label=LABEL)
        r=analyze(data,["a","b"],"y",source_label=LABEL,missing_policy="complete_case")
        self.assertEqual((r["n_input"],r["n_complete"],r["n_excluded"]),(80,79,1))
        self.assertEqual(r["missing_by_variable"]["a"],1)
        self.assertEqual(r["missing_by_variable"]["b"],1)

    def test_rank_and_nonfinite(self):
        data=fixture();data["b"]=data["a"]
        with self.assertRaises(ValueError):
            analyze(data,["a","b"],"y",source_label=LABEL)
        data=fixture();data.loc[1,"a"]=np.inf
        with self.assertRaises(ValueError):
            analyze(data,["a","b"],"y",source_label=LABEL,missing_policy="complete_case")

    def test_real_mode_closed(self):
        with self.assertRaises(ValueError):
            analyze(fixture(),["a","b"],"y",source_label="REAL")
        with self.assertRaises(ValueError):
            analyze(fixture(),["a","a"],"y",source_label=LABEL)
