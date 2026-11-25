"""Review-only theory/construct/hypothesis/item/source linkage, not questionnaire validation."""
from citation_language_qa import index

ADAPTATIONS={"DIRECT_TRANSLATION","ADAPTED","NEW_FROM_DEFINITION"}

def required_text(value):
    if not isinstance(value,str) or not value.strip():raise ValueError("Nonempty reviewed text required")
    return value

def review_alignment(manifest):
    if manifest.get("scope")!="SYNTHETIC_ONLY":raise ValueError("Synthetic alignment rehearsal only")
    refs=index(manifest["references"],"reference_id");theories=index(manifest["theories"],"theory_id")
    constructs=index(manifest["constructs"],"construct_id");hypotheses=index(manifest["hypotheses"],"hypothesis_id")
    items=index(manifest["items"],"item_id")
    issues=[]
    def issue(kind,key,code):issues.append({"kind":kind,"id":key,"code":code})
    def reviewed_ref(rid):
        return rid in refs and refs[rid].get("metadata_review_status")=="REVIEWED"
    if not all((refs,theories,constructs,hypotheses,items)):issue("manifest","alignment","EMPTY_INVENTORY")
    for key,t in theories.items():
        required_text(t["name"])
        if not reviewed_ref(t.get("reference_id")):issue("theory",key,"SOURCE_REVIEW_MISSING")
    for key,c in constructs.items():
        required_text(c["definition"])
        if c.get("theory_id") not in theories:issue("construct",key,"UNKNOWN_THEORY")
        if not reviewed_ref(c.get("reference_id")):issue("construct",key,"SOURCE_REVIEW_MISSING")
    linked=set()
    for key,h in hypotheses.items():
        a,b=h.get("predictor_id"),h.get("outcome_id")
        if a==b or a not in constructs or b not in constructs:issue("hypothesis",key,"INVALID_CONSTRUCT_LINK")
        else:linked.update((a,b))
        required_text(h["statement"])
        if not reviewed_ref(h.get("reference_id")):issue("hypothesis",key,"SOURCE_REVIEW_MISSING")
    measured=set()
    for key,i in items.items():
        required_text(i["text"])
        cid=i.get("construct_id")
        if cid not in constructs:issue("item",key,"UNKNOWN_CONSTRUCT")
        else:measured.add(cid)
        if not reviewed_ref(i.get("reference_id")):issue("item",key,"SOURCE_REVIEW_MISSING")
        if i.get("adaptation_type") not in ADAPTATIONS:issue("item",key,"INVALID_ADAPTATION_TYPE")
        elif i["adaptation_type"] in ("DIRECT_TRANSLATION","ADAPTED") and not isinstance(i.get("source_item"),str):issue("item",key,"SOURCE_ITEM_MISSING")
        elif i["adaptation_type"] in ("DIRECT_TRANSLATION","ADAPTED") and not i["source_item"].strip():issue("item",key,"SOURCE_ITEM_MISSING")
        elif i["adaptation_type"]=="NEW_FROM_DEFINITION" and not str(i.get("adaptation_rationale","")).strip():issue("item",key,"DEFINITION_RATIONALE_MISSING")
        if not isinstance(i.get("source_locator"),str) or not i["source_locator"].strip():issue("item",key,"SOURCE_LOCATOR_MISSING")
    for cid in sorted(constructs):
        if cid not in measured:issue("construct",cid,"NO_ITEM")
        if cid not in linked:issue("construct",cid,"NO_HYPOTHESIS_LINK")
    return {"status":"ALIGNMENT_LINKS_REVIEW_ONLY","scope":"SYNTHETIC_ONLY","issues":issues,
            "declared_links_complete":not issues,"semantic_review_required":True,
            "ioc_status":"NOT_EXECUTED","pilot_status":"NOT_EXECUTED","final_acceptance":False,
            "limitations":"Declared linkage and reviewed metadata only; no claim that wording, source meaning, measurement equivalence or content validity is verified."}
