"""Read-only scoped RU formatting checks. This is not an effective Word renderer."""
import hashlib
import json
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn

PROFILES=Path(__file__).with_name("config")/"ru_mba_profiles.json"
TOL_MM=0.5
def get_profile(profile_id):
    data=json.loads(PROFILES.read_text(encoding="utf-8"))
    return data["profiles"][profile_id]

def chain(style):
    seen=set()
    while style is not None:
        key=style.style_id
        if key in seen:
            raise ValueError("Cyclic style inheritance")
        seen.add(key)
        yield style
        style=style.base_style

def paragraph_property(p,key):
    value=getattr(p.paragraph_format,key)
    if value is not None:
        return value
    for s in chain(p.style):
        value=getattr(s.paragraph_format,key)
        if value is not None:
            return value
    return None

def property_nodes(run,p):
    yield run._r.rPr
    for s in chain(run.style):
        yield s._element.find(qn("w:rPr"))
    for s in chain(p.style):
        yield s._element.find(qn("w:rPr"))

def font_value(nodes,slot):
    for node in nodes:
        if node is None:
            continue
        f=node.find(qn("w:rFonts"))
        if f is not None:
            if f.get(qn("w:"+slot+"Theme")) is not None or (slot=="cs" and f.get(qn("w:cstheme")) is not None):
                return None
            value=f.get(qn("w:"+slot))
            if value is not None:
                return value
    return None

def size_value(nodes,tag):
    for node in nodes:
        if node is not None:
            e=node.find(qn("w:"+tag))
            if e is not None:
                val=e.get(qn("w:val"))
                return float(val)/2 if val is not None else None
    return None

def audit(path,profile_id,body_style_ids,section_roles):
    """Caller explicitly identifies body styles and each section role.
    No text or private paths are included in the report. No modifications.
    """
    profile=get_profile(profile_id)
    source=Path(path)
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    doc=Document(source)
    if not body_style_ids or len(section_roles)!=len(doc.sections):
        raise ValueError("Explicit body styles and one role per section required")
    if not isinstance(body_style_ids,(list,tuple)) or any(not isinstance(x,str) or not x for x in body_style_ids):
        raise ValueError("Invalid body style list")
    checks=[]
    def check(location,field,actual,expected,tolerance=0):
        status="UNRESOLVED" if actual is None or expected is None else (
            "PASS" if (abs(actual-expected)<=tolerance if isinstance(expected,(float,int)) else actual==expected) else "FAIL")
        checks.append(dict(location=location,field=field,actual=actual,expected=expected,status=status))
    for i,(sec,role) in enumerate(zip(doc.sections,section_roles)):
        loc=f"section:{i}"
        for key,expected in zip(("page_width","page_height"),profile["paper_mm"]):
            v=getattr(sec,key)
            check(loc,key,v.mm if v is not None else None,expected,TOL_MM)
        margins=profile["margins_mm"]
        for key in ("left","right","bottom","top"):
            expected=margins["top_by_role"].get(role) if key=="top" else margins[key]
            v=getattr(sec,key+"_margin")
            check(loc,key+"_margin_mm",v.mm if v is not None else None,expected,TOL_MM)
    body_count=0
    unclassified=0
    for i,p in enumerate(doc.paragraphs):
        if not p.text.strip():
            continue
        if p.style.style_id not in body_style_ids:
            unclassified+=1
            continue
        body_count+=1
        loc=f"body:{i}"
        indent=paragraph_property(p,"first_line_indent")
        check(loc,"first_line_mm",indent.mm if indent is not None else None,profile["body"]["first_line_mm"],TOL_MM)
        # Mixed content and hyperlinks are flagged for additional inspection.
        if "".join(r.text for r in p.runs)!=p.text:
            check(loc,"complex_paragraph",None,"supported")
        for j,r in enumerate(p.runs):
            if not r.text.strip():
                continue
            nodes=list(property_nodes(r,p))
            thai=any("\u0e00"<=c<="\u0e7f" for c in r.text)
            latin=any(c.isascii() and c.isalnum() for c in r.text)
            rloc=loc+f"/run:{j}"
            for slot in (["cs"] if thai else [])+(["ascii","hAnsi"] if latin or not thai else []):
                check(rloc,"font_"+slot,font_value(nodes,slot),profile["body"]["font"])
            for tag in (["szCs"] if thai else [])+(["sz"] if latin or not thai else []):
                check(rloc,tag,size_value(nodes,tag),profile["body"]["size_pt"])
    if not body_count:
        raise ValueError("No explicitly classified body paragraphs")
    if hashlib.sha256(source.read_bytes()).hexdigest()!=before:
        raise ValueError("Source changed during audit")
    counts={s:sum(c["status"]==s for c in checks) for s in ("PASS","FAIL","UNRESOLVED")}
    return {"status":"SCOPED_FORMAT_AUDIT_ONLY","profile_id":profile_id,
            "source_sha256":before,"counts":counts,"body_paragraphs":body_count,
            "unclassified_nonempty_body_paragraphs":unclassified,"checks":checks,
            "profile_conflicts_and_pending":profile["unresolved"],"final_acceptance":False,
            "limitations":"Not full effective Word formatting: excludes document defaults, numbering, table styles, theme resolution, headers, footnotes, visual rendering and actual installed fonts. Section roles are caller attestations; mixed page roles within a section require manual Word review."}

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--docx",required=True);p.add_argument("--profile",required=True)
    p.add_argument("--body-style",action="append",required=True)
    p.add_argument("--section-role",action="append",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=audit(a.docx,a.profile,a.body_style,a.section_role)
    with Path(a.output).open("x",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    return 1 if result["counts"]["FAIL"] or result["counts"]["UNRESOLVED"] else 0
if __name__=="__main__":
    raise SystemExit(main())
