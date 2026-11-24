"""Versioned demo schema. Not an approved research instrument."""
import hashlib
import json
from pathlib import Path
import pandas as pd

def load_codebook():
    raw = (Path(__file__).resolve().parent / "config/demo_codebook.json").read_bytes()
    book = json.loads(raw)
    if book["status"] != "DEMO_ONLY_UNVERIFIED" or book["real_data_enabled"] is not False:
        raise ValueError("Only synthetic demo codebooks permitted")
    groups = {g["id"]: g["items"] for g in book["constructs"]}
    if groups != {g: [f"{g}{i+1}" for i in range(n)] for g,n in {"PE":3,"EE":4,"SI":4,"BI":3}.items()}:
        raise ValueError("Unexpected demo codebook mapping")
    if book["scale"] != {"min":1,"max":5} or book["missing_policy"] != "reject_for_demo":
        raise ValueError("Unexpected demo rules")
    return book, groups, hashlib.sha256(raw).hexdigest()

def audit(df, groups):
    expected = [c for cols in groups.values() for c in cols]
    schema_ok = list(df.columns) == expected
    missing = int(df.isna().sum().sum())
    invalid = 0
    if schema_ok:
        for col in expected:
            for value in df[col]:
                if pd.isna(value):
                    continue
                if isinstance(value, (bool, str)) or type(value).__name__ == "bool_" or value not in (1,2,3,4,5):
                    invalid += 1
    return {"rows": len(df), "schema_ok": schema_ok, "missing_cells": missing,
            "invalid_cells": invalid,
            "passed": schema_ok and len(df) >= 10 and missing == 0 and invalid == 0}
