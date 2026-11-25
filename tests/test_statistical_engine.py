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

    def test_codex_s1_outcome_unit_invariance(self):
        r=np.random.default_rng(82412);x=r.normal(size=80);y=.4*x+r.normal(size=80)
        baseline=analyze(pd.DataFrame(dict(x=x,y=y)),["x"],"y",source_label=LABEL)
        for scale in (1e-9,1e9):
            with self.subTest(scale=scale):
                report=analyze(pd.DataFrame(dict(x=x,y=y*scale)),["x"],"y",source_label=LABEL)
                for key in ("r_squared","adjusted_r_squared","f","f_p","hc3_f","hc3_f_p"):
                    self.assertAlmostEqual(report["model"][key],baseline["model"][key],places=10)
                for a,b in zip(baseline["model"]["coefficients"],report["model"]["coefficients"]):
                    for key in ("b","se","hc3_se"):
                        self.assertAlmostEqual(a[key],b[key]/scale,places=10)
                    for key in ("p","hc3_p","vif","beta_standardized"):
                        if a[key] is not None:self.assertAlmostEqual(a[key],b[key],places=10)
                    for key in ("ci95","hc3_ci95"):
                        np.testing.assert_allclose(a[key],np.array(b[key])/scale,rtol=1e-8,atol=1e-10)
                for key in baseline["diagnostics"]:
                    self.assertAlmostEqual(baseline["diagnostics"][key],report["diagnostics"][key],places=8)
    def test_perfect_fit_stays_rejected_in_any_units(self):
        x=np.arange(30,dtype=float)
        for scale in (1,1e-9,1e9):
            with self.assertRaisesRegex(ValueError,"Near-perfect fit"):
                analyze(pd.DataFrame(dict(x=x,y=(1+2*x)*scale)),["x"],"y",source_label=LABEL)

    def test_academic_joint_hc3_and_cook_positions(self):
        import statsmodels.api as sm
        data=fixture();data.loc[0,"a"]=np.nan
        report=analyze(data,["a","b"],"y",source_label=LABEL,missing_policy="complete_case")
        clean=data.dropna()
        fit=sm.OLS(clean.y,sm.add_constant(clean[["a","b"]])).fit()
        robust=fit.get_robustcov_results(cov_type="HC3",use_t=True)
        test=robust.f_test(np.eye(3)[1:])
        self.assertAlmostEqual(report["model"]["hc3_f"],float(np.asarray(test.fvalue).item()),places=10)
        self.assertAlmostEqual(report["model"]["hc3_f_p"],float(np.asarray(test.pvalue).item()),places=10)
        self.assertEqual(report["model"]["hc3_joint_check"],"PASS")
        expected=[int(i+1) for i,v in zip(clean.index,fit.get_influence().cooks_distance[0]) if v>4/len(clean)]
        self.assertEqual([v["input_row_1based"] for v in report["influential_cases"]["cases"]],expected)
        self.assertEqual(report["n_complete"],79)
