"""Deterministic synthetic academic draft with machine-checkable fact references."""
import hashlib
import json
import math
from pathlib import Path
from report_engine import validate,source_hash
from statistical_engine import LABEL

DRAFT="DRAFT_REVIEW_REQUIRED"
def fmt(v):
    if type(v) not in (int,float) or not math.isfinite(v):
        raise ValueError("Expected finite numeric fact")
    return str(v) if type(v) is int else format(v,".8g")

def safe_name(v):
    if not isinstance(v,str) or not v.strip() or any(ord(c)<32 for c in v):
        raise ValueError("Invalid variable name")
    return v

def draft(report):
    """Use only precomputed numerical results. No empirical statements or causal claims."""
    validate(report)
    model=report["model"]
    facts=[]
    def add(fid,path,value):
        facts.append({"id":fid,"json_path":path,"value":value,"rendered":fmt(value)})
        return fmt(value)
    def number(fid,key):
        return add(fid,"/"+key,report[key])
    paragraphs=[{"id":"methods-1","section":"Methods","fact_ids":[],
                 "text":"ใช้การถดถอยเชิงเส้นพหุคูณแบบนำตัวแปรเข้าสมการพร้อมกัน รายงานค่าประมาณแบบ OLS และความคลาดเคลื่อนมาตรฐานแบบ HC3 โดยใช้ข้อมูลสังเคราะห์เพื่อทดสอบระบบเท่านั้น"}]
    a=number("F01","n_input");b=number("F02","n_complete");c=number("F03","n_excluded")
    paragraphs.append({"id":"results-cases","section":"Results","fact_ids":["F01","F02","F03"],
                       "text":f"ข้อมูลทดสอบมีจำนวน {a} รายการ ใช้วิเคราะห์ {b} รายการ และไม่นำมาวิเคราะห์ {c} รายการ"})
    fields=[("F04","r_squared","R²"),("F05","adjusted_r_squared","Adjusted R²"),
            ("F06","f","F"),("F07","f_p","p ของ F"),("F08","df_residual","Residual df")]
    parts=[name+" = "+add(fid,"/model/"+key,model[key]) for fid,key,name in fields]
    paragraphs.append({"id":"results-model","section":"Results","fact_ids":[r[0] for r in fields],
                       "text":"ผลการวิเคราะห์แบบจำลองในชุดข้อมูลสังเคราะห์: "+", ".join(parts)})
    for i,row in enumerate(model["coefficients"]):
        if i==0:
            continue
        base=f"/model/coefficients/{i}"
        ids=[]
        def val(field,idx=None):
            fid=f"C{i}-{field}"+(f"-{idx}" if idx is not None else "")
            ids.append(fid)
            value=row[field] if idx is None else row[field][idx]
            path=base+"/"+field+("/"+str(idx) if idx is not None else "")
            return add(fid,path,value)
        variable=safe_name(row["variable"])
        coefficient=val("b")
        beta=val("beta_standardized")
        p=val("p")
        hp=val("hc3_p")
        lo=val("hc3_ci95",0)
        hi=val("hc3_ci95",1)
        se=val("hc3_se")
        paragraphs.append({"id":f"results-coeff-{i}","section":"Results","fact_ids":ids,
                           "text":f"ตัวแปร {variable}: B = {coefficient}, β = {beta}, p แบบ OLS = {p}, SE แบบ HC3 = {se}, p แบบ HC3 = {hp} และช่วงความเชื่อมั่น 95% แบบ HC3 [{lo}, {hi}]"})
    paragraphs.append({"id":"limitations-1","section":"Limitations","fact_ids":[],
                       "text":"ผลทั้งหมดเป็นการทดสอบด้วยข้อมูลสังเคราะห์ ไม่ใช่ผลการเก็บข้อมูลจริง ไม่ใช้สรุปเหตุและผล ไม่ใช้รับรองสมมติฐานของงานวิจัย และยังต้องตรวจสอบโดยผู้ประเมินอิสระ"})
    return {"label":LABEL,"status":DRAFT,"source_sha256":source_hash(report),
            "paragraphs":paragraphs,"facts":facts,"human_review_required":True,
            "discussion_status":"BLOCKED_NO_INDEPENDENTLY_APPROVED_SOURCES",
            "final_acceptance":False}

def verify_draft(report,document):
    expected=draft(report)
    if expected!=document:
        raise ValueError("Draft or fact ledger differs from computed results")
    return {"status":"DETERMINISTIC_DRAFT_QA_PASS","fact_count":len(expected["facts"]),
            "paragraph_count":len(expected["paragraphs"]),"academic_acceptance":False}

def export_draft(report,output_dir):
    document=draft(report)
    qa=verify_draft(report,document)
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=False)
    (out/"SYNTHETIC_draft.json").write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    lines=[LABEL,DRAFT,"Source SHA256: "+document["source_sha256"],""]
    for p in document["paragraphs"]:
        lines.extend([p["section"]+" / "+p["id"],p["text"],"Fact IDs: "+", ".join(p["fact_ids"]),""])
    lines.append("Discussion: "+document["discussion_status"])
    (out/"SYNTHETIC_draft.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return qa
