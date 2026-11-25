"""Bind exact manuscript claims, citation spans, source PDFs and independent review decisions."""
import re
from pathlib import Path
from hashlib import sha256
from document_coverage import inventory
from citation_language_qa import review_citations,index
from evidence_review import review_ledger,canonical_hash
from evidence_engine import digest

HEX=re.compile(r"[0-9a-f]{64}\Z")

def local_file(root,name,expected,suffix):
    p=(root/name).resolve()
    if root not in p.parents or p.suffix.lower()!=suffix or not p.is_file():
        raise ValueError("Missing or out-of-scope evidence file")
    if not isinstance(expected,str) or not HEX.fullmatch(expected) or digest(p)!=expected:
        raise ValueError("Evidence file hash mismatch")
    return p

def reconcile(doc_path,citation_manifest,evidence_index,decisions,claim_links,source_dir,crop_dir):
    """Read-only reconciliation of declared claims. Independent inventory and semantic review still required."""
    inv=inventory(doc_path)
    cita=review_citations(doc_path,citation_manifest)
    refs=index(citation_manifest["references"],"reference_id")
    cites=index(citation_manifest["citations"],"citation_id")
    records=index(evidence_index["records"],"evidence_id")
    ledger=index(review_ledger(evidence_index,decisions)["records"],"evidence_id")
    links=index(claim_links,"claim_id")
    if not links:raise ValueError("Explicit claim inventory required")
    src_root=Path(source_dir).resolve();crop_root=Path(crop_dir).resolve()
    paras={(r["part"],r["paragraph"]):r for r in inv["paragraphs"]}
    covered=set();results=[]
    for cid,c in links.items():
        issues=[]
        p=paras.get((c["part"],c["paragraph"]))
        start,end=c["start"],c["end"]
        exact=c["exact_text"]
        span_ok=bool(p and type(start) is int and type(end) is int and 0<=start<end<=len(p["text"]) and p["text"][start:end]==exact)
        if not span_ok:issues.append("CLAIM_SPAN_MISMATCH")
        elif p["structural_flags"]:issues.append("COMPLEX_PARAGRAPH_REVIEW")
        citids=c["citation_ids"]
        if not isinstance(citids,list) or not citids or len(citids)!=len(set(citids)):
            raise ValueError("Nonempty unique citation IDs required")
        cited=set()
        for k in citids:
            if k not in cites:issues.append("UNKNOWN_CITATION");continue
            cs=cites[k]
            if (cs["part"],cs["paragraph"])!=(c["part"],c["paragraph"]):
                issues.append("CITATION_NOT_IN_CLAIM_PARAGRAPH")
            cited.update(cs["reference_ids"]);covered.add(k)
        evidence_ids=c["evidence_ids"]
        if not isinstance(evidence_ids,list) or not evidence_ids or len(evidence_ids)!=len(set(evidence_ids)):
            raise ValueError("Nonempty unique evidence IDs required")
        supported=set()
        for eid in evidence_ids:
            row=records.get(eid)
            if row is None:issues.append("UNKNOWN_EVIDENCE");continue
            if row.get("claim")!=exact:issues.append("EVIDENCE_CLAIM_TEXT_MISMATCH");continue
            if row.get("status")!="CANDIDATE_UNVERIFIED" or ledger[eid]["status"]!="REVIEWER_AGREEMENT_SUPPORTS":
                issues.append("EVIDENCE_REVIEW_INCOMPLETE_OR_NOT_SUPPORTING");continue
            if c.get("evidence_record_sha256",{}).get(eid)!=canonical_hash(row):
                issues.append("STALE_EVIDENCE_LINK");continue
            rid=c.get("evidence_reference_ids",{}).get(eid)
            ref=refs.get(rid)
            if rid not in cited or not ref or ref.get("metadata_review_status")!="REVIEWED":
                issues.append("UNREVIEWED_OR_UNCITED_REFERENCE");continue
            source_hash=row.get("source_sha256")
            if ref.get("source_sha256")!=source_hash:
                issues.append("REFERENCE_SOURCE_HASH_MISMATCH");continue
            try:
                local_file(src_root,row["source_file"],source_hash,".pdf")
                for review in ledger[eid]["reviews"]:
                    if review["decision"]!="SUPPORTS":continue
                    matches=[h for h in row["hits"] if h["physical_page"]==review["physical_page"] and h["image_sha256"]==review["candidate_image_sha256"]]
                    if not matches:raise ValueError("Missing reviewed crop")
                    for hit in matches:
                        local_file(crop_root,hit["image"],hit["image_sha256"],".png")
            except (ValueError,OSError,KeyError):
                issues.append("SOURCE_OR_CROP_INTEGRITY_FAILURE");continue
            supported.add(rid)
        if cited-supported:issues.append("CITED_REFERENCES_WITHOUT_SUPPORTING_LINK")
        results.append({"claim_id":cid,"issues":sorted(set(issues)),"declared_links_ready_for_review":not issues})
    missing=sorted(set(cites)-covered)
    return {"status":"CLAIM_EVIDENCE_RECONCILIATION_ONLY","document_sha256":inv["source_sha256"],
            "claims":results,"unlinked_citation_ids":missing,"citation_issues":cita["issues"],
            "declared_links_consistent":not missing and cita["declared_links_consistent"] and all(not r["issues"] for r in results),
            "final_acceptance":False,"limitations":"Exact claims, reviewed file identity and reviewer attestations only. No automated semantic validation, independent inventory completeness or reviewer authentication."}

def audit_multi_source_spans(doc_path,citation_manifest,evidence_index,decisions,claim_links,source_dir,crop_dir,spans,*,source_colors,multi_source_color):
    """One explicit RGB convention for jointly cited sources; never automatic semantic approval."""
    from document_coverage import audit
    from evidence_highlight import rgb
    qa=reconcile(doc_path,citation_manifest,evidence_index,decisions,claim_links,source_dir,crop_dir)
    if not qa["declared_links_consistent"]:
        raise ValueError("All declared claim/source links must reconcile first")
    claims=index(claim_links,"claim_id");citations=index(citation_manifest["citations"],"citation_id")
    references=index(citation_manifest["references"],"reference_id")
    palette={k:rgb(v) for k,v in source_colors.items()}
    multi=rgb(multi_source_color)
    if multi in palette.values():raise ValueError("Multi-source color must be distinct")
    approved=[];mapping=[];seen=set()
    for span in spans:
        cid=span["claim_id"];claim=claims[cid]
        if cid in seen:raise ValueError("Duplicate claim shading specification")
        seen.add(cid)
        sources=span["sources"]
        if not isinstance(sources,list) or not sources or any(not isinstance(x,str) for x in sources) or len(sources)!=len(set(sources)):
            raise ValueError("Unique reference IDs required for each span")
        cited={rid for k in claim["citation_ids"] for rid in citations[k]["reference_ids"]}
        if set(sources)!=cited or any(rid not in references or rid not in palette for rid in sources):
            raise ValueError("Shading must cover exactly every reconciled cited reference")
        hashes={references[rid]["source_sha256"] for rid in sources}
        if len(hashes)!=len(sources):raise ValueError("Duplicate physical source in shading convention")
        expected=multi if len(sources)>1 else palette[sources[0]]
        if rgb(span["color"])!=expected:raise ValueError("Incorrect source shading color convention")
        approved.append({"part":claim["part"],"paragraph":claim["paragraph"],"start":claim["start"],"end":claim["end"],"text":claim["exact_text"],"color":expected})
        mapping.append({"claim_id":cid,"sources":sorted(sources),"color":expected})
    if not approved:raise ValueError("Explicit source shading spans required")
    return {"status":"MULTI_SOURCE_SHADING_REVIEW_ONLY","coverage":audit(doc_path,approved,expected_sha256=qa["document_sha256"]),"source_mapping":mapping,"final_acceptance":False}
