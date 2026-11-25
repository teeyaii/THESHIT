"""Deterministic synthetic academic draft with machine-checkable fact references."""
import hashlib
import json
import math
from pathlib import Path
from report_engine import validate,source_hash
from statistical_engine import LABEL

DRAFT="DRAFT_REVIEW_REQUIRED"
def fmt(v, *, p_value=False, bounded=False):
    if type(v) not in (int,float) or not math.isfinite(v):
        raise ValueError("Expected finite numeric fact")
    if p_value:
        if not 0<=v<=1:raise ValueError("Invalid p value")
        return "< .001" if v<.001 else f"{v:.3f}".removeprefix("0")
    if type(v) is int:return str(v)
    text=f"{v:.3f}"
    if bounded:text=text.replace("-0.","-.") if text.startswith("-0.") else text.removeprefix("0") if text.startswith("0.") else text
    return text

def p_expression(value):
    return value if value.startswith("<") else "= "+value

def safe_name(v):
    if not isinstance(v,str) or not v.strip() or any(ord(c)<32 for c in v):
        raise ValueError("Invalid variable name")
    return v

def draft(report):
    """Use only precomputed numerical results. No empirical statements or causal claims."""
    validate(report)
    model=report["model"];primary=model["primary_inference"]
    robust=primary=="HC3"
    se_key,p_key,ci_key=("hc3_se","hc3_p","hc3_ci95") if robust else ("se","p","ci95")
    facts=[]
    def add(fid,path,value):
        field=path.rsplit("/",1)[-1]
        rendered=fmt(value,p_value=field in ("p","hc3_p","f_p","hc3_f_p"),bounded=field in ("r_squared","adjusted_r_squared"))
        facts.append({"id":fid,"json_path":path,"value":value,"rendered":rendered})
        return rendered
    def number(fid,key):
        return add(fid,"/"+key,report[key])
    paragraphs=[{"id":"methods-1","section":"Methods","fact_ids":[],
                 "text":f"ใช้การถดถอยเชิงเส้นพหุคูณแบบนำตัวแปรเข้าสมการพร้อมกัน ค่าประมาณแบบ OLS ใช้การอนุมานแบบ {primary} เป็นหลัก โดยใช้ข้อมูลสังเคราะห์เพื่อทดสอบระบบเท่านั้น"}]
    a=number("F01","n_input");b=number("F02","n_complete");c=number("F03","n_excluded")
    paragraphs.append({"id":"results-cases","section":"Results","fact_ids":["F01","F02","F03"],
                       "text":f"ข้อมูลทดสอบมีจำนวน {a} รายการ ใช้วิเคราะห์ {b} รายการ และไม่นำมาวิเคราะห์ {c} รายการ"})
    fields=[("F04","r_squared","R²"),("F05","adjusted_r_squared","Adjusted R²"),
            ("F06","hc3_f" if robust else "f",f"F ({primary})"),
            ("F07","hc3_f_p" if robust else "f_p","p"),("F08","df_residual","df residual"),("F09","df_model","df model")]
    parts=[]
    for fid,key,name in fields:
        value=add(fid,"/model/"+key,model[key])
        parts.append(name+" "+(p_expression(value) if key.endswith("f_p") else "= "+value))
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
        pv=val(p_key)
        lo=val(ci_key,0)
        hi=val(ci_key,1)
        se=val(se_key)
        paragraphs.append({"id":f"results-coeff-{i}","section":"Results","fact_ids":ids,
                           "text":f"ตัวแปร {variable}: B = {coefficient}, β = {beta}, ความคลาดเคลื่อนมาตรฐานแบบ {primary} = {se}, ค่า p {p_expression(pv)} และช่วงความเชื่อมั่น 95% แบบ {primary} [{lo}, {hi}]"})
    paragraphs.append({"id":"limitations-1","section":"Limitations","fact_ids":[],
                       "text":"ผลทั้งหมดเป็นการทดสอบด้วยข้อมูลสังเคราะห์ ไม่ใช่ผลการเก็บข้อมูลจริง ไม่ใช้สรุปเหตุและผล ไม่ใช้รับรองสมมติฐานของงานวิจัย และยังต้องตรวจสอบโดยผู้ประเมินอิสระ"})
    return {"label":LABEL,"status":DRAFT,"source_sha256":source_hash(report),
            "paragraphs":paragraphs,"facts":facts,"primary_inference":primary,"human_review_required":True,
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
