"""Generic core adapters. No real-data intake or network calls."""
from importlib import metadata
from pathlib import Path
import math
import numpy as np
from openpyxl import Workbook, load_workbook
from scipy import stats

def dependency_inventory():
    """Installed metadata, not a legal determination or a vulnerability scan."""
    rows = []
    for d in metadata.distributions():
        m = d.metadata
        rows.append({"name": m.get("Name", ""), "version": d.version,
                     "license_expression": m.get("License-Expression"),
                     "license": m.get("License"),
                     "license_classifiers": [c for c in m.get_all("Classifier", [])
                                             if c.startswith("License ::")],
                     "license_files": m.get_all("License-File", []),
                     "project_urls": m.get_all("Project-URL", [])})
    return sorted(rows, key=lambda row: (row["name"].lower(), row["version"]))

def synthetic_excel_roundtrip(path):
    """Write/read a fixed, explicitly synthetic interoperability fixture."""
    p = Path(path)
    if p.exists():
        raise FileExistsError(p)
    w = Workbook()
    s = w.active
    s.title = "SYNTHETIC_FIXTURE"
    s.append(["SYNTHETIC - NOT RESEARCH EVIDENCE", "ค่า"])
    s.append(["ทดสอบภาษาไทย", 4])
    w.save(p)
    r = load_workbook(p, read_only=True, data_only=True)
    try:
        return list(r.active.values)
    finally:
        r.close()

def alpha_covariance(values):
    """Independent covariance-based alpha; undefined for constant total scores."""
    a = np.asarray(values, dtype=float)
    if a.ndim != 2 or min(a.shape) < 2 or not np.isfinite(a).all():
        raise ValueError("Need finite matrix with >=2 rows and >=2 items")
    cov = np.cov(a, rowvar=False, ddof=1)
    total = float(cov.sum())
    if not math.isfinite(total) or total <= 0:
        return None
    k = a.shape[1]
    return float(k / (k - 1) * (1 - np.trace(cov) / total))

def simple_regression_check(x, y):
    """Independent SciPy simple regression check; not multivariable/HC3 parity."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 1 or x.shape != y.shape or len(x) < 3 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Need paired finite vectors")
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        raise ValueError("Constant input")
    r = stats.linregress(x, y)
    return {"intercept": float(r.intercept), "slope": float(r.slope),
            "pvalue": float(r.pvalue), "r_squared": float(r.rvalue ** 2)}
