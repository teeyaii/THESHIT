"""Researcher-authored literature notes matrix; never generates research conclusions."""
from pathlib import Path
import csv
import json
from evidence_review import review_ledger,canonical_hash
from citation_language_qa import index

FIELDS=("theme","study_design","population_context","constructs","finding_note","limitations_note","applicability_note")
DIRECTIONS={"POSITIVE","NEGATIVE","NULL","MIXED","DESCRIPTIVE","NOT_COMPARABLE"}

def text(value):
    if not isinstance(value,str) or not value.strip():
        raise ValueError("Explicit researcher-reviewed note required")
    return value.strip()

def matrix(evidence_index,decisions,notes):
    """Each note must quote the exact already-reviewed claim; grouping is not inference."""
    records=index(evidence_index["records"],"evidence_id")
    review=index(review_ledger(evidence_index,decisions)["records"],"evidence_id")
    entries=index(notes,"note_id")
    if not entries:raise ValueError("No notes")
    rows=[];blocked=[];themes={};seen=set()
    for nid,n in entries.items():
        eid=n["evidence_id"]
        r=records.get(eid)
        if not r or n.get("record_sha256")!=canonical_hash(r):
            blocked.append({"note_id":nid,"reason":"UNKNOWN_OR_STALE_EVIDENCE"});continue
        if r.get("status")!="CANDIDATE_UNVERIFIED" or review[eid]["status"]!="REVIEWER_AGREEMENT_SUPPORTS":
            blocked.append({"note_id":nid,"reason":"REVIEW_NOT_SUPPORTING_OR_INCOMPLETE"});continue
        if n.get("author_reviewed") is not True or n.get("finding_note")!=r.get("claim"):
            blocked.append({"note_id":nid,"reason":"AUTHOR_REVIEW_OR_EXACT_FINDING_MISSING"});continue
        text(n["author_id"])
        direction=n["direction"]
        if direction not in DIRECTIONS:raise ValueError("Explicit direction category required")
        values={f:text(n[f]) for f in FIELDS}
        key=(eid,values["theme"])
        if key in seen:raise ValueError("Duplicate evidence in same theme")
        seen.add(key)
        row={"note_id":nid,"evidence_id":eid,"record_sha256":canonical_hash(r),
             "source_sha256":r["source_sha256"],"direction":direction,**values}
        rows.append(row)
        group=themes.setdefault(values["theme"],{"note_ids":[],"sources":set(),"directions":set()})
        group["note_ids"].append(nid);group["sources"].add(r["source_sha256"]);group["directions"].add(direction)
    groups=[]
    for theme,g in sorted(themes.items()):
        directions=g["directions"]
        groups.append({"theme":theme,"note_ids":g["note_ids"],"distinct_source_count":len(g["sources"]),
                       "direction_labels":sorted(directions),
                       "mixed_direction_labels":len(directions&{"POSITIVE","NEGATIVE","NULL","MIXED"})>1 or "MIXED" in directions,
                       "interpretation":"RESEARCHER_REVIEW_REQUIRED"})
    return {"status":"LITERATURE_NOTES_MATRIX_ONLY","rows":rows,"blocked":blocked,"themes":groups,
            "final_acceptance":False,"limitations":"Notes and direction labels are supplied by the researcher; no effect pooling, vote-counting inference, source independence or academic authorship claim."}

def safe_cell(value):
    value=str(value)
    return "'"+value if value.lstrip().startswith(("=","+","-","@")) or value.startswith(("\t","\r","\n")) else value

def export(evidence_index,decisions,notes,output_dir):
    report=matrix(evidence_index,decisions,notes)
    root=Path(output_dir);root.mkdir(parents=True,exist_ok=False)
    (root/"literature_notes_review.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    columns=["note_id","evidence_id","record_sha256","source_sha256","direction",*FIELDS]
    with (root/"literature_notes_review.csv").open("x",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for row in report["rows"]:
            writer.writerow({k:safe_cell(v) for k,v in row.items()})
    return report
