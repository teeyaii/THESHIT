"""General-purpose synthetic analysis. No real-data intake or hypothesis targeting."""
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
    if float(fit.ssr)<=np.finfo(float).eps*max(float(fit.centered_tss),1.0):
        raise ValueError("Near-perfect fit; inference is degenerate")
    robust=fit.get_robustcov_results(cov_type="HC3",use_t=True)
    beta,cov=independent_fit(x,y)
    if not np.allclose(beta,fit.params.to_numpy(),rtol=1e-7,atol=1e-9) or not np.allclose(cov,robust.cov_params(),rtol=1e-7,atol=1e-9):
        raise ValueError("Independent OLS/HC3 cross-check failed")
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
                     "df_residual":finite(fit.df_resid),"coefficients":coeff,
                     "hc3_inference":"Student t; residual degrees of freedom",
                     "independent_ols_hc3_check":"PASS"},
            "diagnostics":{"breusch_pagan_lm":finite(lm),"breusch_pagan_p":finite(lmp),
                           "jarque_bera":finite(jb),"jarque_bera_p":finite(jbp),
                           "max_cooks_distance":finite(np.max(fit.get_influence().cooks_distance[0]))},
            "limitations":"Synthetic fixture only; associations, not causation. Model and assumptions require independent methodological review."}
