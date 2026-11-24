"""Non-destructive candidate highlighting and read-only Word color coverage."""
import hashlib
import json
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw
from docx import Document
from docx.oxml.ns import qn
from evidence_engine import digest

COLOR = re.compile(r"[0-9A-Fa-f]{6}\Z")

def rgb(value):
    if not isinstance(value, str) or not COLOR.fullmatch(value):
        raise ValueError("Expected six-digit RGB hex without #")
    return value.upper()

def inside(root, name):
    candidate = (root / name).resolve()
    if root not in candidate.parents:
        raise ValueError("Path outside approved directory")
    return candidate

def box(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError("Invalid bounding box")
    b = tuple(float(x) for x in value)
    if not all(map(math.isfinite, b)) or b[0] >= b[2] or b[1] >= b[3]:
        raise ValueError("Invalid bounding box")
    return b

def highlight_candidates(index, source_dir, candidate_dir, output_dir, source_colors):
    """Overlay a rectangle on already extracted candidate crops; never verify claims."""
    src, cand, out = (Path(p).resolve() for p in (source_dir, candidate_dir, output_dir))
    if out.exists() or out in (src, cand) or any(root in out.parents for root in (src,cand)):
        raise ValueError("Separate new output directory required")
    if index.get("review_required") is not True:
        raise ValueError("Expected unverified candidate index")
    pending = []
    used = set()
    for record in index["records"]:
        if record.get("status") != "CANDIDATE_UNVERIFIED":
            continue
        source = inside(src, record["source_file"])
        if digest(source) != record["source_sha256"]:
            raise ValueError("Source hash mismatch")
        color = rgb(source_colors[record["source_file"]])
        for hit in record["hits"]:
            original = inside(cand, hit["image"])
            if original.suffix.lower() != ".png" or digest(original) != hit["image_sha256"]:
                raise ValueError("Candidate image hash mismatch")
            x0,y0,x1,y1 = box(hit["bbox"])
            a,b,c,d = box(hit["crop_bbox"])
            if not (a <= x0 < x1 <= c and b <= y0 < y1 <= d):
                raise ValueError("Match outside crop")
            name = original.stem + "_candidate_highlight.png"
            if name in used:
                raise ValueError("Duplicate output filename")
            used.add(name)
            pending.append((record,hit,original,name,color,(x0,y0,x1,y1),(a,b,c,d)))
    out.mkdir(parents=True)
    rows=[]
    for record,hit,original,name,color,(x0,y0,x1,y1),(a,b,c,d) in pending:
        with Image.open(original) as im:
            base=im.convert("RGBA")
        w,h=base.size
        scale=lambda x,y: ((x-a)*w/(c-a),(y-b)*h/(d-b))
        overlay=Image.new("RGBA",base.size)
        draw=ImageDraw.Draw(overlay)
        red,green,blue=(int(color[i:i+2],16) for i in (0,2,4))
        draw.rectangle([scale(x0,y0),scale(x1,y1)],fill=(red,green,blue,65),
                       outline=(red,green,blue,200),width=1)
        Image.alpha_composite(base,overlay).convert("RGB").save(out/name)
        rows.append({"evidence_id":record["evidence_id"],"source_file":record["source_file"],
                     "physical_page":hit["physical_page"],"source_sha256":record["source_sha256"],
                     "candidate_image_sha256":hit["image_sha256"],"color":color,
                     "bbox":hit["bbox"],"crop_bbox":hit["crop_bbox"],"image":name,
                     "image_sha256":digest(out/name),"status":"CANDIDATE_UNVERIFIED"})
    result={"review_required":True,"annotation_method":"translucent rectangle on extracted crop",
            "records":rows}
    (out/"highlight_index.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result

def run_fill(run):
    """Explicit run shading only; unsupported formatting is not treated as a match."""
    pr=run._r.rPr
    if pr is None:
        return None
    shd=pr.find(qn("w:shd"))
    if shd is None:
        return None
    value=shd.get(qn("w:fill"))
    pattern=shd.get(qn("w:val"))
    if pattern not in (None,"clear","solid") or shd.get(qn("w:themeFill")):
        return None
    return value.upper() if value and COLOR.fullmatch(value) else None

def audit_body_shading(doc_path, spans):
    """Read-only exact code-point intervals on body paragraphs; no semantic inference."""
    original_hash=digest(doc_path)
    doc=Document(doc_path)
    expected={}
    for row in spans:
        i,start,end=row["paragraph"],row["start"],row["end"]
        if any(type(x) is not int for x in (i,start,end)) or not 0 <= i < len(doc.paragraphs):
            raise ValueError("Invalid paragraph or interval")
        p=doc.paragraphs[i]
        if not 0 <= start < end <= len(p.text) or p.text[start:end] != row["text"]:
            raise ValueError("Exact span text mismatch")
        target=rgb(row["color"])
        for j in range(start,end):
            key=(i,j)
            if key in expected and expected[key] != target:
                raise ValueError("Conflicting expected source colors")
            expected[key]=target
    actual={}
    unsupported=[]
    for i,p in enumerate(doc.paragraphs):
        if "".join(r.text for r in p.runs) != p.text:
            unsupported.append(i)
            continue
        offset=0
        for run in p.runs:
            fill=run_fill(run)
            for j in range(offset,offset+len(run.text)):
                if fill:
                    actual[(i,j)]=fill
            offset+=len(run.text)
    missing=[list(k) for k in expected if k[0] not in unsupported and k not in actual]
    wrong=[list(k) for k in expected if k in actual and actual[k]!=expected[k]]
    unexpected=[list(k) for k in actual if k not in expected]
    match=sum(actual.get(k)==v for k,v in expected.items())
    if digest(doc_path)!=original_hash:
        raise ValueError("Document changed during audit")
    return {"status":"STRUCTURAL_ONLY_REVIEW_REQUIRED","source_sha256":original_hash,
            "expected_characters":len(expected),"matched_characters":match,
            "missing":missing,"wrong_color":wrong,"unexpected":unexpected,
            "unsupported_paragraphs":unsupported,
            "limitations":"Body paragraphs; explicit run shading only. No tables, semantic audit or Word visual QA."}
