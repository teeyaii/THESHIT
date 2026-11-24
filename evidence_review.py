"""Reconcile independent human/AI-assisted source-review decisions; never auto-verify evidence."""
from hashlib import sha256
import json
import re

HEX=re.compile(r"[0-9a-f]{64}\Z")
DECISIONS={"SUPPORTS","PARTIAL","CONTRADICTS","NOT_ASSESSED"}

def canonical_hash(record):
    data=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
    return sha256(data.encode("utf-8")).hexdigest()

def review_ledger(index, decisions):
    """Each decision is tied to an exact evidence record and inspected source locator.

    No automated semantic inference. Reviewer identity/independence is an attestation,
    not authenticated by this module. No final academic release decision is made.
    """
    if index.get("review_required") is not True:
        raise ValueError("Expected candidate evidence index")
    records={}
    for row in index["records"]:
        eid=row["evidence_id"]
        if not isinstance(eid,str) or not eid or eid in records:
            raise ValueError("Invalid or duplicate evidence ID")
        records[eid]=row
    ledger={eid:[] for eid in records}
    seen=set()
    for decision in decisions:
        eid=decision["evidence_id"]
        if eid not in records:
            raise ValueError("Unknown evidence ID")
        record=records[eid]
        who=decision["reviewer_id"]
        if not isinstance(who,str) or not who.strip() or len(who)>100:
            raise ValueError("Invalid reviewer ID")
        normalized_who=who.strip().casefold()
        if (eid,normalized_who) in seen:
            raise ValueError("Duplicate reviewer for evidence ID")
        seen.add((eid,normalized_who))
        if decision["record_sha256"]!=canonical_hash(record):
            raise ValueError("Stale or altered evidence record")
        outcome=decision["decision"]
        if outcome not in DECISIONS or not isinstance(decision.get("rationale"),str) or not decision["rationale"].strip():
            raise ValueError("Review decision and rationale required")
        if outcome!="NOT_ASSESSED":
            if decision.get("full_context_reviewed") is not True:
                raise ValueError("Full source context attestation required")
            digest=decision.get("source_sha256")
            if not isinstance(digest,str) or not HEX.fullmatch(digest) or digest!=record.get("source_sha256"):
                raise ValueError("Review source hash mismatch")
            page=decision.get("physical_page")
            quote=decision.get("source_excerpt")
            if type(page) is not int or page<1 or not isinstance(quote,str) or not quote.strip():
                raise ValueError("Page and actual source excerpt required")
            if page>record.get("total_pages",0):
                raise ValueError("Page outside recorded source")
            image_hash=decision.get("candidate_image_sha256")
            if not any(h.get("physical_page")==page and h.get("image_sha256")==image_hash
                       for h in record.get("hits",[]) if isinstance(image_hash,str) and HEX.fullmatch(image_hash)):
                raise ValueError("Review locator is not an indexed candidate")
        ledger[eid].append(decision)
    results=[]
    for eid,record in records.items():
        reviews=ledger[eid]
        assessed=[r for r in reviews if r["decision"]!="NOT_ASSESSED"]
        outcomes={r["decision"] for r in assessed}
        if len(outcomes)>1:
            status="DISAGREEMENT_REQUIRES_RECONCILIATION"
        elif len(assessed)<2:
            status="INCOMPLETE_INDEPENDENT_REVIEW"
        else:
            status="REVIEWER_AGREEMENT_"+next(iter(outcomes))
        results.append({"evidence_id":eid,"record_sha256":canonical_hash(record),
                        "candidate_status":record["status"],"status":status,
                        "review_count":len(reviews),"assessed_count":len(assessed),
                        "reviews":reviews})
    counts={}
    for row in results:
        key=row["status"];counts[key]=counts.get(key,0)+1
    return {"status":"REVIEW_LEDGER_ONLY","final_acceptance":False,
            "counts":counts,"records":results,
            "limitations":"Reviewer attestations only; excerpts and semantic judgments require independent source inspection. No automatic VERIFIED status."}
