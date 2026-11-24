"""Release checklist reconciliation; never grant automatic final approval."""
import json
import re
from pathlib import Path
CONFIG=Path(__file__).with_name("config")/"release_gate.json"
HEX=re.compile(r"[0-9a-f]{64}\Z")
def evaluate(records,commit_sha):
    config=json.loads(CONFIG.read_text(encoding="utf-8"))
    if not isinstance(commit_sha,str) or not re.fullmatch(r"[0-9a-f]{40}",commit_sha):
        raise ValueError("Exact release candidate commit required")
    expected=config["required_gates"];allowed=set(config["statuses"]);rows={}
    for r in records:
        gate=r["gate"]
        if gate not in expected or gate in rows or r["status"] not in allowed:
            raise ValueError("Unknown/duplicate gate or status")
        if r.get("commit_sha")!=commit_sha:
            raise ValueError("Stale gate record")
        if not isinstance(r.get("reason"),str) or not r["reason"].strip():
            raise ValueError("Reason required")
        if r["status"]=="PASS":
            if not isinstance(r.get("reviewer"),str) or not r["reviewer"].strip():
                raise ValueError("Reviewer attestation required")
            if not isinstance(r.get("evidence_sha256"),str) or not HEX.fullmatch(r["evidence_sha256"]):
                raise ValueError("Evidence artifact hash required")
        rows[gate]=r
    results=[rows.get(g,{"gate":g,"status":"NOT_EXECUTED","reason":"No gate record"}) for g in expected]
    remaining=[r["gate"] for r in results if r["status"]!="PASS"]
    return {"target":config["target"],"commit_sha":commit_sha,"gates":results,
            "status":"BLOCKED" if remaining else "READY_FOR_MANUAL_RELEASE_REVIEW",
            "remaining":remaining,"real_data_enabled":False,"final_acceptance":False,
            "limitations":"Attestations and hashes are not verified evidence by themselves. Independent actual review and explicit release action required."}

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--commit",required=True);p.add_argument("--records",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    report=evaluate(json.loads(Path(a.records).read_text(encoding="utf-8")),a.commit)
    with Path(a.output).open("x",encoding="utf-8") as f:json.dump(report,f,indent=2)
    return 1 if report["remaining"] else 0
if __name__=="__main__":
    raise SystemExit(main())
