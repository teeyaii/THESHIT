"""SYNTHETIC ONLY. Independent uniform responses, not research evidence."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

GROUPS = {"PE": 3, "EE": 4, "SI": 4, "BI": 3}
ITEMS = {g: [f"{g}{i+1}" for i in range(k)] for g, k in GROUPS.items()}
LABEL = "SYNTHETIC - NOT RESEARCH EVIDENCE"

def fixture(n=100, seed=42):
    if n < 10:
        raise ValueError("At least 10 synthetic rows required")
    rng = np.random.default_rng(seed)
    columns = [c for group in ITEMS.values() for c in group]
    return pd.DataFrame(rng.integers(1, 6, (n, len(columns))), columns=columns)

def validate(df):
    expected = [c for group in ITEMS.values() for c in group]
    if list(df.columns) != expected or len(df) < 10:
        raise ValueError("Unexpected schema or sample size")
    if not df.isin([1, 2, 3, 4, 5]).all().all():
        raise ValueError("Complete integer Likert 1–5 values required")

def alpha(items):
    k = items.shape[1]
    total = items.sum(axis=1).var(ddof=1)
    return None if total <= 0 else float(k/(k-1)*(1-items.var(ddof=1).sum()/total))

def run_demo(n=100, seed=42):
    df = fixture(n, seed)
    validate(df)
    scores = pd.DataFrame({g: df[cols].mean(axis=1) for g, cols in ITEMS.items()})
    x = sm.add_constant(scores[["PE", "EE", "SI"]])
    if np.linalg.matrix_rank(x) != x.shape[1] or scores.BI.var() == 0:
        raise ValueError("Degenerate synthetic fixture")
    ols = sm.OLS(scores.BI, x).fit()
    robust = ols.get_robustcov_results(cov_type="HC3")
    return {"label": LABEL, "source": "independent uniform synthetic fixture",
            "seed": seed, "n": n,
            "descriptive": scores.describe().to_dict(),
            "alpha": {g: alpha(df[cols]) for g, cols in ITEMS.items()},
            "correlation": scores.corr().to_dict(),
            "ols": {"r_squared": float(ols.rsquared),
                    "coefficients": ols.params.to_dict(),
                    "p_values": ols.pvalues.to_dict(),
                    "hc3_p_values": dict(zip(x.columns, map(float, robust.pvalues)))},
            "limitations": "Demo only; not validated research results or evidence of reliability."}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=LABEL)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = run_demo(args.n, args.seed)
    folder = Path("outputs")
    folder.mkdir(exist_ok=True)
    path = folder / "SYNTHETIC_demo.json"
    path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(LABEL, path)
