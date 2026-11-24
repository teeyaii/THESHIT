"""Conservative DOCX preservation and append-only assembly of compatible synthetic fragments."""
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
from copy import deepcopy
from lxml import etree

W="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS={"w":W}
MAIN="word/document.xml"
LABEL="SYNTHETIC ONLY — NOT FOR ACADEMIC SUBMISSION"
LIMIT=100*1024*1024

def q(name):return "{"+W+"}"+name
def digest(data):return sha256(data).hexdigest()

def package(path):
    with ZipFile(path) as z:
        entries=z.infolist()
        if len(entries)>2000 or sum(e.file_size for e in entries)>LIMIT or len({e.filename for e in entries})!=len(entries):
            raise ValueError("Unsupported package size or duplicate parts")
        if any(e.flag_bits & 1 for e in entries):
            raise ValueError("Encrypted part unsupported")
        return {e.filename:z.read(e) for e in entries}

def parse(data):
    root=etree.fromstring(data,etree.XMLParser(resolve_entities=False,no_network=True,load_dtd=False))
    if root.getroottree().docinfo.doctype:raise ValueError("DTD unsupported")
    return root

def preservation_diff(original,copy):
    """Exact OPC part-byte differences; no text or file paths disclosed."""
    a,b=package(original),package(copy)
    added=sorted(b.keys()-a.keys());removed=sorted(a.keys()-b.keys())
    changed=[k for k in sorted(a.keys()&b.keys()) if a[k]!=b[k]]
    return {"added_parts":added,"removed_parts":removed,"changed_parts":changed,
            "unchanged_parts":len(a.keys()&b.keys())-len(changed),
            "status":"EXACT_PARTS_MATCH" if not (added or removed or changed) else "DIFFERENCES_REQUIRE_REVIEW",
            "word_visual_qa":"NOT_EXECUTED"}

def body_blocks(parts):
    root=parse(parts[MAIN]);body=root.find(q("body"))
    if body is None or len(body)==0 or body[-1].tag!=q("sectPr"):
        raise ValueError("Expected one terminal section")
    blocks=list(body)[:-1]
    if any(b.tag not in (q("p"),q("tbl")) for b in blocks):
        raise ValueError("Unsupported body block")
    if any(b.xpath(".//w:sectPr | .//w:bookmarkStart | .//w:bookmarkEnd | .//w:commentRangeStart | .//w:commentRangeEnd | .//w:commentReference | .//w:drawing | .//w:pict | .//w:object | .//w:footnoteReference | .//w:endnoteReference | .//w:fldChar | .//w:fldSimple | .//w:instrText | .//w:hyperlink | .//w:numPr | .//w:ins | .//w:del | .//w:moveFrom | .//w:moveTo | .//w:sdt",namespaces=NS) for b in blocks):
        raise ValueError("Complex package references require independent merge tooling")
    if any(any("relationships" in k for e in b.iter() for k in e.attrib) for b in blocks):
        raise ValueError("Relationship references unsupported")
    return root,body,blocks

def canon(element):
    return etree.tostring(element,method="c14n",exclusive=True)

def assemble_synthetic(base_path,fragments,output_path):
    """Append body blocks only when all non-main parts and section properties match.
    Refuse complex cross-package links. Preserve original files; not real manuscript intake.
    """
    if not fragments:raise ValueError("At least one fragment required")
    paths=[Path(base_path),*map(Path,fragments)]
    output=Path(output_path)
    if output.exists() or output.suffix.lower()!=".docx":raise ValueError("New DOCX output required")
    original_hashes=[digest(p.read_bytes()) for p in paths]
    base=package(paths[0]);root,body,blocks=body_blocks(base)
    if not any("".join(b.itertext()).find(LABEL)>=0 for b in blocks):
        raise ValueError("Explicit synthetic base label required")
    expected=[canon(b) for b in blocks]
    for p in paths[1:]:
        parts=package(p)
        if {k:v for k,v in base.items() if k!=MAIN}!={k:v for k,v in parts.items() if k!=MAIN}:
            raise ValueError("Incompatible package styles, media or relationships")
        _,other,extra=body_blocks(parts)
        if canon(other[-1])!=canon(body[-1]):raise ValueError("Different section properties")
        if not any(LABEL in "".join(b.itertext()) for b in extra):raise ValueError("Synthetic fragment label required")
        for b in extra:
            expected.append(canon(b));body.insert(len(body)-1,deepcopy(b))
    updated=dict(base);updated[MAIN]=etree.tostring(root,encoding="UTF-8",xml_declaration=True,standalone=True)
    with ZipFile(output,"x") as z:
        for k,v in updated.items():z.writestr(k,v)
    actual=package(output)
    _,_,actual_blocks=body_blocks(actual)
    if [canon(b) for b in actual_blocks]!=expected or any(actual[k]!=v for k,v in base.items() if k!=MAIN):
        raise ValueError("Assembly preservation check failed")
    if [digest(p.read_bytes()) for p in paths]!=original_hashes:raise ValueError("Source changed")
    return {"status":"SYNTHETIC_COMPATIBLE_BLOCK_ASSEMBLY_PASS","blocks_verified":len(expected),
            "source_hashes":original_hashes,"output_sha256":digest(output.read_bytes()),
            "word_visual_qa":"NOT_EXECUTED","real_manuscript_assembly":False}
