"""Explicit citation-span reconciliation and Thai editorial candidate warnings."""
import hashlib
import re
from pathlib import Path
from document_coverage import inventory
from research_discovery import normalize_doi

def index(rows,key):
    result={}
    for row in rows:
        k=row[key]
        if not isinstance(k,str) or not k.strip() or k in result:
            raise ValueError("Invalid or duplicate ID")
        result[k]=row
    return result

def review_citations(path,manifest):
    """Exact spans supplied by independent inventory, not automatic citation discovery."""
    inv=inventory(path)
    if inv["source_sha256"]!=manifest["document_sha256"]:
        raise ValueError("Stale citation manifest")
    refs=index(manifest["references"],"reference_id")
    spans=index(manifest["citations"],"citation_id")
    paras={(r["part"],r["paragraph"]):r for r in inv["paragraphs"]}
    issues=[];used=set();dois={}
    for rid,ref in refs.items():
        if not isinstance(ref.get("title"),str) or not ref["title"].strip():
            issues.append({"reference_id":rid,"code":"MISSING_TITLE"})
        if ref.get("doi"):
            doi=normalize_doi(ref["doi"])
            if not doi:issues.append({"reference_id":rid,"code":"INVALID_DOI"})
            elif doi in dois:issues.append({"reference_id":rid,"code":"DUPLICATE_DOI","other_reference_id":dois[doi]})
            else:dois[doi]=rid
        if ref.get("metadata_review_status")!="REVIEWED":
            issues.append({"reference_id":rid,"code":"METADATA_REVIEW_PENDING"})
        # Publication year is metadata, never an age cutoff.
        if type(ref.get("year")) is not int or not 1<=ref["year"]<=3000:
            issues.append({"reference_id":rid,"code":"YEAR_REVIEW_REQUIRED"})
    for cid,c in spans.items():
        p=paras.get((c["part"],c["paragraph"]))
        start,end=c["start"],c["end"]
        if not p or type(start) is not int or type(end) is not int or not 0<=start<end<=len(p["text"]) or p["text"][start:end]!=c["exact_text"]:
            issues.append({"citation_id":cid,"code":"SPAN_MISMATCH"})
            continue
        ids=c["reference_ids"]
        if not isinstance(ids,list) or not ids or any(not isinstance(i,str) for i in ids) or len(ids)!=len(set(ids)):
            issues.append({"citation_id":cid,"code":"INVALID_REFERENCE_LINKS"})
            continue
        for rid in ids:
            if rid not in refs:
                issues.append({"citation_id":cid,"code":"MISSING_REFERENCE","reference_id":rid})
            else:used.add(rid)
        if c.get("claim_review_status")!="REVIEWED":
            issues.append({"citation_id":cid,"code":"CLAIM_REVIEW_PENDING"})
    for rid in sorted(refs.keys()-used):
        issues.append({"reference_id":rid,"code":"UNCITED_REFERENCE_REVIEW"})
    if not spans:issues.append({"code":"NO_CITATION_INVENTORY"})
    return {"status":"CITATION_LINK_QA_ONLY","source_sha256":inv["source_sha256"],
            "references":len(refs),"citation_spans":len(spans),"issues":issues,
            "declared_links_consistent":bool(spans) and not issues,"age_cutoff":None,
            "final_acceptance":False,
            "limitations":"Only declared spans and metadata assertions; not APA formatting, independent discovery, source truth or semantic completeness."}

PATTERNS={
 "THAI_INTERNAL_MULTISPACE":r"[\u0e00-\u0e7f]([ \u00a0]{2,})[\u0e00-\u0e7f]",
 "ZERO_WIDTH_OR_SOFT_HYPHEN":r"[\u200b\u200c\u200d\ufeff\u00ad]",
 "UNREPLACED_PLACEHOLDER":r"\b(?:TODO|TBD|INSERT CITATION)\b|\[ใส่อ้างอิง\]",
 "DOUBLE_PUNCTUATION":r"[!?]{2,}|[.]{4,}",
}
def language_candidates(path):
    inv=inventory(path)
    warnings=[]
    for p in inv["paragraphs"]:
        for code,pattern in PATTERNS.items():
            for m in re.finditer(pattern,p["text"],flags=re.IGNORECASE):
                warnings.append({"part":p["part"],"paragraph":p["paragraph"],"start":m.start(),"end":m.end(),"code":code})
    return {"status":"EDITORIAL_CANDIDATES_ONLY","source_sha256":inv["source_sha256"],
            "warnings":warnings,"automatic_edits":0,"final_acceptance":False,
            "limitations":"Some whitespace, zero-width marks and punctuation are legitimate. Human review required; no AI authorship detection or automatic language correction."}
