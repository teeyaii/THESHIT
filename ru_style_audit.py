"""Read-only RU role/style inventory, with explicit template-dependent checks."""
import hashlib
import json
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from ru_format_audit import get_profile, paragraph_property, property_nodes, font_value, size_value

PROFILE="ru_mba_campus_2569_working"
ROLES={"body","chapter","heading","table","caption","bibliography","toc_title","appendix_divider","heading1","heading2","front_title","bibliography_title","fixture_notice","heading3","heading4","heading5","table_label"}
PARAGRAPH_FIELDS={"alignment","first_line_indent","left_indent","right_indent",
                  "space_before","space_after","line_spacing","line_spacing_rule",
                  "keep_with_next","keep_together","page_break_before","widow_control"}

def style_value(p,key):
    value=paragraph_property(p,key)
    if value is None:
        return None
    if key in {"alignment","line_spacing_rule"}:
        return int(value)
    if hasattr(value,"pt"):
        return round(value.pt,4)
    return value

def role_rules(profile,role):
    size={"body":profile["body"]["size_pt"],"chapter":profile["chapter_size_pt"],
          "bibliography":profile.get("bibliography_pt"),"toc_title":profile.get("toc_title_pt"),
          "appendix_divider":profile.get("appendix_divider_pt"),
          "caption":profile.get("table_caption_pt")}.get(role)
    levels=profile.get("heading_sizes_pt")
    if role in ("heading1","heading2") and levels:
        size=levels[0 if role=="heading1" else 1]
    if role=="bibliography_title":
        size=profile.get("bibliography_pt")
    if role=="fixture_notice":
        size=profile["body"]["size_pt"]
    rules={"size_pt":size,"font":profile["body"]["font"]}
    if role=="table":rules["minimum_pt"]=profile.get("table_text_min_pt")
    if role=="table_label":rules["size_pt"]=None
    if role=="body" and profile["body"]["first_line_mm"] is not None:
        rules["paragraph"]={"first_line_indent":profile["body"]["first_line_mm"]*72/25.4}
    else:
        rules["paragraph"]={}
    return rules

def audit_styles(path,role_by_style,template_rules=None,profile_id=PROFILE,*,section_roles=None):
    """Classify paragraph styles explicitly; missing classifications are unresolved."""
    if not isinstance(role_by_style,dict) or not role_by_style or set(role_by_style.values())-ROLES:
        raise ValueError("Explicit supported style-role mapping required")
    template_rules=template_rules or {}
    if set(template_rules)-ROLES or any(set(v)-PARAGRAPH_FIELDS for v in template_rules.values()):
        raise ValueError("Unsupported paragraph template rule")
    profile=get_profile(profile_id)
    p=Path(path);before=hashlib.sha256(p.read_bytes()).hexdigest()
    doc=Document(p);checks=[];inventory=[];seen=set()
    def compare(loc,field,actual,expected):
        if actual is None or expected is None:
            status="UNRESOLVED"
        elif isinstance(expected,(int,float)) and not isinstance(expected,bool):
            status="PASS" if isinstance(actual,(int,float)) and abs(actual-expected)<=0.05 else "FAIL"
        else:
            status="PASS" if actual==expected else "FAIL"
        checks.append({"location":loc,"field":field,"actual":actual,"expected":expected,"status":status})
    if section_roles is not None:
        margins=profile["margins_mm"]["top_by_role"]
        if len(section_roles)!=len(doc.sections) or any(role not in margins for role in section_roles):
            raise ValueError("One valid explicit role per section required")
        for i,(sec,role) in enumerate(zip(doc.sections,section_roles)):
            compare(f"section:{i}","top_margin_mm",sec.top_margin.mm if sec.top_margin is not None else None,margins[role])
            checks[-1]["reason"]="RU p9 / physical11; explicit section role only, actual pagination requires Word"
    def paragraph(p,loc):
        if not p.text.strip():
            return
        role=role_by_style.get(p.style.style_id)
        values={k:style_value(p,k) for k in sorted(PARAGRAPH_FIELDS)}
        inventory.append({"location":loc,"style":p.style.style_id,"role":role,"paragraph_properties":values})
        if role is None:
            compare(loc,"style_classification",None,"explicit role")
            return
        rules=role_rules(profile,role)
        if role in ("heading","heading1","heading2","heading3","heading4","heading5") and profile.get("heading_weight_alignment_status")=="UNRESOLVED_CONFLICT":
            compare(loc,"heading_weight_alignment",None,None)
            checks[-1]["reason"]="UNRESOLVED_CONFLICT X-02: printed p4 versus p10"
        expected={**template_rules.get(role,{}),**rules["paragraph"]}
        for field,target in expected.items():
            compare(loc,field,values[field],target)
        if "".join(r.text for r in p.runs)!=p.text:
            compare(loc,"complex_runs",None,"manual review")
        for i,r in enumerate(p.runs):
            if not r.text.strip():
                continue
            nodes=list(property_nodes(r,p))
            thai=any("\u0e00"<=c<="\u0e7f" for c in r.text)
            latin=any(c.isascii() and c.isalnum() for c in r.text)
            rloc=f"{loc}/run:{i}"
            for slot in (["cs"] if thai else [])+(["ascii","hAnsi"] if latin or not thai else []):
                compare(rloc,"font_"+slot,font_value(nodes,slot),rules["font"])
            for tag in (["szCs"] if thai else [])+(["sz"] if latin or not thai else []):
                compare(rloc,tag,size_value(nodes,tag),rules["size_pt"])
                if role=="table" and rules.get("minimum_pt") is not None:
                    actual=checks[-1]["actual"];minimum=rules["minimum_pt"]
                    checks[-1].update(expected=minimum,status="UNRESOLVED" if actual is None else ("PASS" if actual>=minimum else "FAIL"),reason="Minimum table text size, printed p11 / physical 13; visual legibility still pending")
                elif role=="caption" and rules["size_pt"] is not None:
                    checks[-1]["reason"]="RU p11 / physical13: caption 12 pt, distinct from table cell minimum"
                elif role=="table_label":
                    checks[-1]["reason"]="Table label role; exact size and rendering require template/Word review."
                elif role=="front_title" and rules["size_pt"] is None:
                    checks[-1]["reason"]="Front-matter role is not necessarily a TOC heading; exact title size requires approved template."
                elif role=="fixture_notice":
                    checks[-1]["basis"]="SYNTHETIC_FIXTURE_CONVENTION_NOT_UNIVERSITY_RULE"
    def tables(items,prefix):
        for ti,t in enumerate(items):
            if profile.get("table_text_min_pt") is not None:
                borders=t._tbl.tblPr.find(qn("w:tblBorders"))
                direct=[borders.find(qn("w:"+side)) if borders is not None else None for side in ("left","right","insideV")]
                actual=None if any(e is None for e in direct) else all(e.get(qn("w:val")) in ("nil","none") for e in direct)
                compare(f"{prefix}/table:{ti}","no_direct_vertical_borders",actual,True)
                checks[-1]["reason"]="Direct table borders only; cell/style overrides require Word review (printed p11)."
            for ri,row in enumerate(t.rows):
                for ci,cell in enumerate(row.cells):
                    if cell._tc in seen:
                        continue
                    seen.add(cell._tc)
                    loc=f"{prefix}/table:{ti}/row:{ri}/cell:{ci}"
                    for pi,p in enumerate(cell.paragraphs):
                        paragraph(p,f"{loc}/p:{pi}")
                    tables(cell.tables,loc)
    for i,p0 in enumerate(doc.paragraphs):
        paragraph(p0,f"body/p:{i}")
    tables(doc.tables,"body")
    if not inventory:
        raise ValueError("No nonempty paragraph inventory")
    fields=[]
    for elem in doc._element.iter(qn("w:instrText")):
        token=(elem.text or "").strip().split()
        if token and token[0].upper() in {"TOC","PAGE","NUMPAGES","SEQ","REF"}:
            fields.append(token[0].upper())
    for elem in doc._element.iter(qn("w:fldSimple")):
        token=(elem.get(qn("w:instr")) or "").strip().split()
        if token and token[0].upper() in {"TOC","PAGE","NUMPAGES","SEQ","REF"}:
            fields.append(token[0].upper())
    if hashlib.sha256(p.read_bytes()).hexdigest()!=before:
        raise ValueError("Source changed during audit")
    return {"status":"STRUCTURAL_STYLE_INVENTORY_ONLY","profile_id":profile_id,"source_sha256":before,
            "counts":{s:sum(x["status"]==s for x in checks) for s in ("PASS","FAIL","UNRESOLVED")},
            "inventory":inventory,"checks":checks,"manual_conflicts":profile.get("manual_conflicts",[]),"main_part_field_tokens":fields,
            "final_acceptance":False,"word_visual_qa":"NOT_EXECUTED",
            "limitations":"Explicit role mapping and scoped property inheritance only. Missing rules, document defaults, themes, table geometry, field results, headers/footers, numbering and true layout require template/Word review."}

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx",required=True)
    parser.add_argument("--style-map",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    mapping=json.loads(Path(args.style_map).read_text(encoding="utf-8"))
    result=audit_styles(args.docx,mapping["role_by_style"],mapping.get("paragraph_rules"),section_roles=mapping.get("section_roles"))
    with Path(args.output).open("x",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    return 1 if result["counts"]["FAIL"] or result["counts"]["UNRESOLVED"] else 0

if __name__=="__main__":
    raise SystemExit(main())
