"""Read-only DOCX structural inventory and explicit run-color coverage, not semantic review."""
from hashlib import sha256
from pathlib import Path
import re
from zipfile import ZipFile
from lxml import etree

W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS={"w":W,"mc":"http://schemas.openxmlformats.org/markup-compatibility/2006"}
PART=re.compile(r"word/(?:document|header\d+|footer\d+|footnotes|endnotes)\.xml\Z")
HEX=re.compile(r"[A-Fa-f0-9]{6}\Z")
MAX_XML=32*1024*1024
MAX_PARTS=100
def q(name):
    return "{"+W+"}"+name

def explicit_color(run):
    props=run.find(q("rPr"))
    if props is None:
        return None,False
    shade=props.find(q("shd"))
    marker=props.find(q("highlight"))
    if marker is not None and marker.get(q("val")) not in (None,"none"):
        return None,True
    if shade is None:
        return None,False
    fill=shade.get(q("fill"))
    if shade.get(q("themeFill")) or shade.get(q("val")) not in (None,"clear","solid") or not fill or not HEX.fullmatch(fill):
        return None,True
    return fill.upper(),False

def para_record(p,index,part):
    text=[]; colors=[]; unsupported=set(); structural=[]; thai_without_cs=[]
    if p.xpath(".//w:p",namespaces=NS):
        structural.append("NESTED_PARAGRAPH_CONTAINER")
    if p.xpath(".//w:ins | .//w:del | .//w:moveFrom | .//w:moveTo | .//w:fldSimple | .//w:fldChar | .//w:instrText",namespaces=NS):
        structural.append("TRACKED_CHANGE_OR_FIELD")
    if p.xpath(".//mc:AlternateContent",namespaces=NS):
        structural.append("ALTERNATE_CONTENT")
    for r in p.xpath(".//w:r",namespaces=NS):
        if next(r.iterancestors(q("p")),None) is not p:
            continue
        fill,unknown=explicit_color(r)
        props=r.find(q("rPr")); cs=props.find(q("cs")) if props is not None else None
        explicit_cs=cs is not None and cs.get(q("val"),"true") in ("1","true","on")
        for child in r:
            if child.tag==q("t"):
                value=child.text or ""
            elif child.tag==q("tab"):
                value="\t"
            elif child.tag in (q("br"),q("cr")):
                value="\n"
            elif child.tag==q("noBreakHyphen"):
                value="\u2011"
            elif child.tag==q("softHyphen"):
                value="\u00ad"
            else:
                if child.tag in (q("sym"),q("drawing"),q("pict"),q("object"),q("footnoteReference"),q("endnoteReference")):
                    structural.append("NON_TEXT_RUN_CONTENT")
                continue
            if unknown:
                unsupported.update(range(len(colors),len(colors)+len(value)))
            if not explicit_cs:
                for match in re.finditer(r"[\u0e00-\u0e7f]+",value):
                    thai_without_cs.append([len(colors)+match.start(),len(colors)+match.end()])
            text.append(value);colors.extend([fill]*len(value))
    return {"part":part,"paragraph":index,"text":"".join(text),"colors":colors,
            "unknown_color_offsets":sorted(unsupported),"structural_flags":sorted(set(structural)),
            "thai_without_direct_cs_spans":thai_without_cs,
            "table_depth":sum(1 for _ in p.iterancestors(q("tbl")))}

def inventory(doc_path):
    p=Path(doc_path)
    before=sha256(p.read_bytes()).hexdigest()
    records=[]
    with ZipFile(p) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):
            raise ValueError("Duplicate ZIP member names")
        parts=sorted(n for n in names if PART.fullmatch(n))
        if "word/document.xml" not in parts or len(parts)>MAX_PARTS:
            raise ValueError("Missing main part or excessive XML parts")
        if sum(z.getinfo(name).file_size for name in parts)>MAX_XML:
            raise ValueError("Document XML size limit exceeded")
        for name in parts:
            raw=z.read(name)
            parser=etree.XMLParser(resolve_entities=False,load_dtd=False,no_network=True,huge_tree=False)
            root=etree.fromstring(raw,parser)
            if root.getroottree().docinfo.doctype:
                raise ValueError("DTD not accepted")
            for i,paragraph in enumerate(root.xpath(".//w:p",namespaces=NS)):
                records.append(para_record(paragraph,i,name))
    if sha256(p.read_bytes()).hexdigest()!=before:
        raise ValueError("Document changed during inventory")
    return {"source_sha256":before,"paragraphs":records,
            "limitations":"Direct run RGB shading only; style inheritance, named highlights, themes and visual Word layout not resolved."}

def audit(doc_path, spans, *, expected_sha256):
    """Approved exact spans; no automatic judgment of what needs citation."""
    data=inventory(doc_path)
    if data["source_sha256"]!=expected_sha256:
        raise ValueError("Approved span document SHA-256 mismatch")
    paragraphs={(p["part"],p["paragraph"]):p for p in data["paragraphs"]}
    expected={}
    for span in spans:
        key=(span["part"],span["paragraph"])
        if type(key[1]) is not int or key not in paragraphs:
            raise ValueError("Unknown paragraph location")
        p=paragraphs[key]; start,end=span["start"],span["end"]
        color=span["color"]
        if (type(start) is not int or type(end) is not int or not 0<=start<end<=len(p["text"])
                or p["text"][start:end]!=span["text"] or not isinstance(color,str) or not HEX.fullmatch(color)):
            raise ValueError("Invalid approved span")
        for j in range(start,end):
            k=(*key,j)
            if k in expected and expected[k]!=color.upper():
                raise ValueError("Conflicting approved source colors")
            expected[k]=color.upper()
    missing=[];wrong=[];unresolved=[];unexpected=[];matched=0
    for key,p in paragraphs.items():
        unknown=set(p["unknown_color_offsets"])
        structural=bool(p["structural_flags"])
        for j,actual in enumerate(p["colors"]):
            loc=(*key,j)
            target=expected.get(loc)
            if structural or j in unknown:
                if target is not None:
                    unresolved.append(list(loc))
                continue
            if target is None:
                if actual is not None:unexpected.append(list(loc))
            elif actual==target:matched+=1
            elif actual is None:missing.append(list(loc))
            else:wrong.append(list(loc))
    return {"source_sha256":data["source_sha256"],"status":"STRUCTURAL_ONLY_REVIEW_REQUIRED",
            "paragraph_count":len(paragraphs),"expected_characters":len(expected),
            "matched_characters":matched,"missing":missing,"wrong_color":wrong,
            "unresolved":unresolved,"unexpected":unexpected,
            "flagged_paragraphs":[{"part":p["part"],"paragraph":p["paragraph"],
                                   "flags":p["structural_flags"],"unknown_color_count":len(p["unknown_color_offsets"])}
                                  for p in paragraphs.values() if p["structural_flags"] or p["unknown_color_offsets"]],
            "limitations":data["limitations"]+" No semantic, citation, or style-based completeness assertion."}
