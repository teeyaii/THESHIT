"""Score independently transcribed Thai PDF ground truth without auto-accepting it."""
import hashlib
import math
import json
import unicodedata
from pathlib import Path

MODES={"native":0.95,"ocr":0.90}
SOURCE_KINDS={"native","genuine_scan","rasterized_control"}

def valid_bbox(value):
    return isinstance(value,(list,tuple)) and len(value)==4 and all(type(x) in (int,float) and math.isfinite(x) for x in value) and 0<=value[0]<value[2] and 0<=value[1]<value[3]

def table_metrics(cells,predicted):
    if not isinstance(cells,dict) or not isinstance(predicted,dict) or any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) for m in (cells,predicted) for k,v in m.items()):
        raise ValueError("Use table/row/column keyed text dictionaries")
    correct=sum(k in predicted and normalize(v)==normalize(predicted[k]) for k,v in cells.items())
    extras=sorted(set(predicted)-set(cells))
    return {"reference_cells":len(cells),"predicted_cells":len(predicted),"exact_cells":correct,"extras_count":len(extras),"extra_keys":extras}

def aggregate_cells(rows):
    r={k:sum(x[k] for x in rows) for k in ("reference_cells","predicted_cells","exact_cells","extras_count")}
    a,b,c,e=(r[k] for k in ("reference_cells","predicted_cells","exact_cells","extras_count"))
    r.update(precision=c/b if b else None,recall=c/a if a else None,accuracy=c/(a+e) if a+e else None)
    return r
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
    if not refs:raise ValueError("Missing ground truth")
    unexpected=sorted(set(preds)-set(refs))
    extra_cases=[{"case_id":key,**table_metrics({},preds[key].get("table_cells",{}))} for key in unexpected]
    totals={mode:{"characters":0,"edits":0,"cases":0,"missing":0} for mode in MODES}
    records=[]; sources=set(); locators=0
    kinds={k:{"characters":0,"edits":0,"cases":0,"locator_matches":0,"ignoring_locator_edits":0} for k in sorted(SOURCE_KINDS)}
    for case_id,r in refs.items():
        mode=r["mode"]
        kind=r.get("source_kind")
        if kind not in SOURCE_KINDS or not isinstance(r.get("region_id"),str) or not r["region_id"].strip() or not valid_bbox(r.get("bbox")) or not isinstance(r.get("printed_page"),str) or not r["printed_page"].strip():
            raise ValueError("Ground truth requires region_id, positive PDF bbox, source_kind and printed page label")
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
                     and pred.get("printed_page")==r["printed_page"] and pred.get("mode")==mode
                     and pred.get("region_id")==r["region_id"] and pred.get("source_kind")==kind
                     and valid_bbox(pred.get("bbox")) and list(pred["bbox"])==list(r["bbox"]))
        if locator:
            locators+=1
        actual=pred["text"] if locator else ""
        independent_text=pred["text"] if pred else ""
        raw_errors=edit_distance(expected,independent_text)
        errors=edit_distance(expected,actual)
        n=len(expected)
        totals[mode]["characters"]+=n;totals[mode]["edits"]+=errors
        totals[mode]["cases"]+=1;totals[mode]["missing"]+=int(not locator)
        cells=r.get("table_cells",{})
        predicted_cells=pred.get("table_cells",{}) if pred else {}
        # Wrong locator receives no credit; retain all reported cells as false extras.
        tm=table_metrics(cells,predicted_cells if locator else {})
        if not locator:
            fp=table_metrics({},predicted_cells)
            tm["predicted_cells"]=fp["predicted_cells"]
            tm["extras_count"]=fp["extras_count"]
            tm["extra_keys"]=fp["extra_keys"]
        km=kinds[kind];km["characters"]+=n;km["edits"]+=errors;km["cases"]+=1;km["locator_matches"]+=int(locator);km["ignoring_locator_edits"]+=raw_errors
        records.append({"case_id":case_id,"source_sha256":digest,"mode":mode,"source_kind":kind,"reference_characters":n,
                        "edit_distance":errors,"character_error_rate":errors/n,
                        "text_cer_ignoring_locator":raw_errors/n,"raw_text_edits":raw_errors,
                        "locator_match":locator,"table_cells":len(cells),"table_cells_exact":tm["exact_cells"],
                        "table_metrics":{**tm,**aggregate_cells([tm])}})
    for mode,t in totals.items():
        t["character_error_rate"]=t["edits"]/t["characters"] if t["characters"] else None
        t["accuracy"]=1-t["character_error_rate"] if t["characters"] else None
        t["threshold_met"]=bool(t["characters"] and t["accuracy"]>=MODES[mode] and not t["missing"])
    for k,t in kinds.items():
        t["character_error_rate"]=t["edits"]/t["characters"] if t["characters"] else None
        t["text_cer_ignoring_locator"]=t["ignoring_locator_edits"]/t["characters"] if t["characters"] else None
    table=aggregate_cells([r["table_metrics"] for r in records]+extra_cases)
    source_tables={digest:aggregate_cells([r["table_metrics"] for r in records if r["source_sha256"]==digest]) for digest in sorted(sources)}
    return {"status":"METRICS_ONLY_REVIEW_REQUIRED","sources":len(sources),"cases":len(refs),
            "modes":totals,"locator_accuracy":locators/len(refs),
            "table_cell_accuracy":table["accuracy"],"table_cell_count":table["reference_cells"],"table_metrics":table,
            "table_metrics_by_source":source_tables,"unexpected_prediction_cases":extra_cases,
            "source_kind_metrics":kinds,"text_cer_ignoring_locator":sum(r["raw_text_edits"] for r in records)/sum(r["reference_characters"] for r in records),"records":records,
            "proposed_text_locator_gate":len(sources)>=5 and all(t["threshold_met"] for t in totals.values())
                and locators==len(refs) and table["reference_cells"]>0 and not unexpected and not table["extras_count"]
                and all(kinds[k]["cases"]>0 for k in ("native","genuine_scan")),
            "schema_version":"2.0","bbox_rule":"Exact annotated PDF-coordinate region; mismatch receives no locator credit",
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
