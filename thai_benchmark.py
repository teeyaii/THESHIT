"""Score independently transcribed Thai PDF ground truth without auto-accepting it."""
import hashlib
import json
import unicodedata
from pathlib import Path

MODES={"native":0.95,"ocr":0.90}
def normalize(text):
    if not isinstance(text,str):
        raise ValueError("Text must be a string")
    # Thai combining signs remain separate code points; ignore whitespace only.
    return "".join(c for c in unicodedata.normalize("NFC",text) if not c.isspace())

def edit_distance(a,b):
    a,b=normalize(a),normalize(b)
    if len(a)*len(b)>25_000_000:
        raise ValueError("Split long passages into independently annotated regions")
    prev=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        curr=[i]
        for j,y in enumerate(b,1):
            curr.append(min(curr[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
        prev=curr
    return prev[-1]

def file_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def indexed(rows):
    out={}
    for r in rows:
        k=r["case_id"]
        if not isinstance(k,str) or not k or k in out:
            raise ValueError("Invalid or duplicate case ID")
        out[k]=r
    return out

def evaluate(reference,predictions,source_dir):
    """No PDF text is emitted. Source identity and page checks are mandatory.
    Reference must be transcribed separately, not copied from extraction output.
    """
    if reference.get("reference_status")!="INDEPENDENTLY_REVIEWED":
        raise ValueError("Independent ground truth required")
    root=Path(source_dir).resolve()
    refs=indexed(reference["cases"])
    preds=indexed(predictions["cases"])
    if not refs or set(preds)-set(refs):
        raise ValueError("Missing ground truth or unexpected predictions")
    totals={mode:{"characters":0,"edits":0,"cases":0,"missing":0} for mode in MODES}
    records=[]; sources=set(); table_total=0; table_correct=0; locators=0
    for case_id,r in refs.items():
        mode=r["mode"]
        if mode not in MODES or r.get("license_reviewed") is not True:
            raise ValueError("Unsupported mode or unreviewed source license")
        p=(root/r["source_file"]).resolve()
        if root not in p.parents or not p.is_file() or p.suffix.lower()!=".pdf":
            raise ValueError("Source outside benchmark directory or unavailable")
        digest=file_hash(p)
        if digest!=r["source_sha256"]:
            raise ValueError("Ground truth source changed")
        sources.add(digest)
        expected=normalize(r["text"])
        if not expected or type(r["physical_page"]) is not int or r["physical_page"]<1:
            raise ValueError("Text and physical page required")
        pred=preds.get(case_id)
        locator=bool(pred and pred.get("source_sha256")==digest and pred.get("physical_page")==r["physical_page"]
                     and pred.get("printed_page")==r.get("printed_page") and pred.get("mode")==mode)
        if locator:
            locators+=1
        actual=pred["text"] if locator else ""
        errors=edit_distance(expected,actual)
        n=len(expected)
        totals[mode]["characters"]+=n;totals[mode]["edits"]+=errors
        totals[mode]["cases"]+=1;totals[mode]["missing"]+=int(not locator)
        cells=r.get("table_cells",{})
        predicted_cells=pred.get("table_cells",{}) if locator else {}
        if not isinstance(cells,dict) or not isinstance(predicted_cells,dict):
            raise ValueError("Use table/row/column keyed cell dictionaries")
        matched=sum(k in predicted_cells and normalize(v)==normalize(predicted_cells[k]) for k,v in cells.items())
        table_total+=len(cells);table_correct+=matched
        records.append({"case_id":case_id,"source_sha256":digest,"mode":mode,"reference_characters":n,
                        "edit_distance":errors,"character_error_rate":errors/n,
                        "locator_match":locator,"table_cells":len(cells),"table_cells_exact":matched})
    for mode,t in totals.items():
        t["character_error_rate"]=t["edits"]/t["characters"] if t["characters"] else None
        t["accuracy"]=1-t["character_error_rate"] if t["characters"] else None
        t["threshold_met"]=bool(t["characters"] and t["accuracy"]>=MODES[mode] and not t["missing"])
    return {"status":"METRICS_ONLY_REVIEW_REQUIRED","sources":len(sources),"cases":len(refs),
            "modes":totals,"locator_accuracy":locators/len(refs),
            "table_cell_accuracy":table_correct/table_total if table_total else None,
            "table_cell_count":table_total,"records":records,
            "proposed_text_locator_gate":len(sources)>=5 and all(t["threshold_met"] for t in totals.values())
                and locators==len(refs) and table_total>0,
            "limitations":"Reference independence and licenses are attestations. No automatic academic or table-accuracy acceptance."}

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",required=True)
    parser.add_argument("--predictions",required=True)
    parser.add_argument("--source-dir",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    ref=json.loads(Path(args.reference).read_text(encoding="utf-8"))
    pred=json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    report=evaluate(ref,pred,args.source_dir)
    with Path(args.output).open("x",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
if __name__=="__main__":
    main()
