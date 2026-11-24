"""Check the dedicated Linux/Python 3.11 runtime against reviewed exact versions."""
import json
from importlib import metadata
from pathlib import Path
from packaging.utils import canonicalize_name

def parse_pins(path):
    pins={}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if not line or line.startswith("#"):
            continue
        parts=line.split("==")
        if len(parts)!=2 or not all(parts):
            raise ValueError("Expected exact package pin")
        name,version=canonicalize_name(parts[0]),parts[1]
        if name in pins:
            raise ValueError("Duplicate pin: "+name)
        pins[name]=version
    return pins

def compare(expected, actual):
    return {"missing":sorted(expected.keys()-actual.keys()),
            "unexpected":sorted(actual.keys()-expected.keys()),
            "mismatch":[{"name":k,"expected":expected[k],"actual":actual[k]}
                        for k in sorted(expected.keys()&actual.keys()) if expected[k]!=actual[k]]}

def main():
    pins=parse_pins(Path(__file__).with_name("requirements-core-linux-py311.constraints.txt"))
    actual={canonicalize_name(d.metadata["Name"]):d.version for d in metadata.distributions()}
    differences=compare(pins,actual)
    passed=not any(differences.values())
    print(json.dumps({"expected_count":len(pins),"actual_count":len(actual),
                      "status":"PASS" if passed else "FAIL","differences":differences},indent=2))
    return 0 if passed else 1

if __name__=="__main__":
    raise SystemExit(main())
