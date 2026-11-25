"""General-purpose synthetic analysis. No real-data intake or hypothesis targeting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import jarque_bera
from statsmodels.stats.outliers_influence import variance_inflation_factor
from scipy import stats

LABEL = "SYNTHETIC - NOT RESEARCH EVIDENCE"

def finite(value):
    value=float(value)
    return value if np.isfinite(value) else None

def independent_fit(x, y):
    """Independent SVD/lstsq OLS and HC3 sandwich covariance."""
    beta=np.linalg.lstsq(x,y,rcond=None)[0]
    residual=y-x@beta
    inverse=np.linalg.pinv(x)
    leverage=np.einsum("ij,ji->i",x,inverse)
    if np.any(1-leverage <= 1e-10):
        raise ValueError("HC3 undefined for near-unit leverage")
    adjusted=residual/(1-leverage)
    hc3=(inverse*adjusted**2)@inverse.T
    return beta,hc3

def analyze(frame, predictors, outcome, *, source_label, missing_policy="reject"):
    """Analyze an explicitly synthetic numeric fixture, with no implicit case exclusion."""
    if source_label != LABEL:
        raise ValueError("Only explicitly synthetic input is enabled")
    if not isinstance(frame,pd.DataFrame) or not frame.columns.is_unique:
        raise ValueError("Unique named dataframe columns required")
    if not isinstance(predictors,(list,tuple)) or not predictors:
        raise ValueError("At least one predictor")
    fields=[outcome,*predictors]
    if any(not isinstance(s,str) or not s or s=="const" for s in fields) or len(set(fields))!=len(fields):
        raise ValueError("Distinct nonempty variable names, excluding const")
    if missing_policy not in ("reject","complete_case"):
        raise ValueError("Missing-data policy must be explicit")
    numeric=frame.loc[:,fields]
    if not all(pd.api.types.is_numeric_dtype(numeric[c]) and not pd.api.types.is_bool_dtype(numeric[c]) and not pd.api.types.is_complex_dtype(numeric[c]) for c in fields):
        raise ValueError("Real-valued numeric columns only")
    numeric=numeric.astype(float)
    if np.isinf(numeric.to_numpy()).any():
        raise ValueError("Infinite values not allowed")
    excluded=numeric.isna().any(axis=1)
    if missing_policy=="reject" and excluded.any():
        raise ValueError("Missing data under reject policy")
    clean=numeric.loc[~excluded]
    n=len(clean)
    if n<=len(predictors)+2:
        raise ValueError("Insufficient complete rows for regression")
    y=clean[outcome].to_numpy()
    design=sm.add_constant(clean[list(predictors)],has_constant="add")
    x=design.to_numpy()
    if np.ptp(y)==0 or np.linalg.matrix_rank(x)!=x.shape[1]:
        raise ValueError("Constant outcome or rank-deficient design")
    fit=sm.OLS(y,design).fit()
    total=float(fit.centered_tss);residual=float(fit.ssr)
    if not np.isfinite(total) or total<=0 or not np.isfinite(residual) or residual<0:
        raise ValueError("Outcome variance outside supported numerical range")
    # Dimensionless ratio: changing the units of y must not change this guard.
    if residual/total<=np.finfo(float).eps:
        raise ValueError("Near-perfect fit; inference is degenerate")
    robust=fit.get_robustcov_results(cov_type="HC3",use_t=True)
    beta,cov=independent_fit(x,y)
    outcome_scale=np.sqrt(total/n)
    # Compare in standardized outcome units rather than a fixed raw-unit tolerance.
    if not np.allclose(beta/outcome_scale,fit.params.to_numpy()/outcome_scale,rtol=1e-7,atol=1e-9) or not np.allclose(cov/total*n,robust.cov_params()/total*n,rtol=1e-7,atol=1e-9):
        raise ValueError("Independent OLS/HC3 cross-check failed")
    policy=json.loads((Path(__file__).with_name("config")/"analysis_reporting.json").read_text(encoding="utf-8"))
    primary=policy["primary_inference"]
    if primary not in ("OLS","HC3") or policy.get("scope")!="SYNTHETIC_ONLY":
        raise ValueError("Invalid synthetic reporting policy")
    # Test all non-intercept coefficients jointly in scale-independent units.
    q=len(predictors)
    cb=beta[1:]/outcome_scale;cc=cov[1:,1:]/total*n
    if np.linalg.matrix_rank(cc)!=q:
        raise ValueError("HC3 joint test covariance rank deficient")
    wald_f=float(cb@np.linalg.solve(cc,cb)/q)
    wald_p=float(stats.f.sf(wald_f,q,fit.df_resid))
    restriction=np.eye(q+1)[1:]
    joint=robust.f_test(restriction)
    if not np.allclose([wald_f,wald_p],[float(np.asarray(joint.fvalue).item()),float(np.asarray(joint.pvalue).item())],rtol=1e-7,atol=1e-12):
        raise ValueError("Independent HC3 joint test cross-check failed")
    ci=fit.conf_int().to_numpy()
    rci=robust.conf_int()
    coeff=[]
    for i,name in enumerate(design.columns):
        coeff.append({"variable":name,"b":finite(beta[i]),
             "beta_standardized":None if i==0 else finite(beta[i]*clean[name].std(ddof=1)/clean[outcome].std(ddof=1)),
             "se":finite(fit.bse.iloc[i]),"p":finite(fit.pvalues.iloc[i]),
             "ci95":[finite(v) for v in ci[i]],
             "hc3_se":finite(robust.bse[i]),"hc3_p":finite(robust.pvalues[i]),
             "hc3_ci95":[finite(v) for v in rci[i]],
             "vif":None if i==0 else finite(variance_inflation_factor(x,i))})
    lm,lmp,_,_=het_breuschpagan(fit.resid,x)
    jb,jbp,_,_=jarque_bera(fit.resid)
    cooks=fit.get_influence().cooks_distance[0]
    threshold=4/n
    positions=np.flatnonzero(~excluded.to_numpy())
    influential=[{"input_row_1based":int(positions[i]+1),"cooks_distance":float(value)}
                 for i,value in enumerate(cooks) if value>threshold]
    descriptives={name:{"n":n,"mean":finite(clean[name].mean()),
                         "sd":finite(clean[name].std(ddof=1)),
                         "min":finite(clean[name].min()),"max":finite(clean[name].max())}
                  for name in fields}
    return {"label":LABEL,"n_input":len(frame),"n_complete":n,
            "n_excluded":int(excluded.sum()),
            "missing_policy":missing_policy,
            "missing_by_variable":{k:int(v) for k,v in numeric.isna().sum().items()},
            "predictors":list(predictors),"outcome":outcome,
            "descriptives":descriptives,"correlation":clean.corr().to_dict(),
            "model":{"r_squared":finite(fit.rsquared),"adjusted_r_squared":finite(fit.rsquared_adj),
                     "f":finite(fit.fvalue),"f_p":finite(fit.f_pvalue),
                     "df_residual":finite(fit.df_resid),"df_model":q,"coefficients":coeff,
                     "primary_inference":primary,"hc3_f":finite(wald_f),"hc3_f_p":finite(wald_p),
                     "hc3_joint_check":"PASS",
                     "hc3_inference":"Student t; residual degrees of freedom",
                     "independent_ols_hc3_check":"PASS"},
            "diagnostics":{"breusch_pagan_lm":finite(lm),"breusch_pagan_p":finite(lmp),
                           "jarque_bera":finite(jb),"jarque_bera_p":finite(jbp),
                           "max_cooks_distance":finite(np.max(cooks)),"cooks_threshold":threshold,
                           "cooks_cases_flagged":len(influential)},
            "influential_cases":{"rule":"Cook D > 4/n_complete; inspect only, no automatic exclusion","cases":influential},
            "limitations":"Synthetic fixture only; associations, not causation. Model and assumptions require independent methodological review."}
