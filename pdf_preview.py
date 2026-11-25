"""Synthetic DOCX-to-PDF preview. LibreOffice is never Microsoft Word finalization."""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path

import pdfplumber
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Mm

from academic_writing import draft, verify_draft
from statistical_engine import LABEL

FONT="Noto Sans Thai"
LATIN_FONT="Noto Sans"
PREVIEW="SYNTHETIC PREVIEW ONLY - NOT WORD FINALIZATION"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def norm(value):
    return "".join(c for c in unicodedata.normalize("NFC",value) if not c.isspace())

def apply_font(run,size,thai=False):
    name=FONT if thai else LATIN_FONT
    run.font.name=name
    run.font.size=Pt(size)
    pr=run._element.get_or_add_rPr()
    for attr in ("ascii","hAnsi","eastAsia","cs"):
        pr.rFonts.set(qn("w:"+attr),name)
    sz=OxmlElement("w:szCs")
    sz.set(qn("w:val"),str(round(size*2)))
    pr.append(sz)
    if thai:
        cs=OxmlElement("w:cs")
        pr.append(cs)
        lang=OxmlElement("w:lang")
        lang.set(qn("w:val"),"th-TH")
        lang.set(qn("w:bidi"),"th-TH")
        pr.append(lang)

def line(doc,text,size=12):
    p=doc.add_paragraph()
    p.paragraph_format.space_after=Pt(6)
    for chunk in re.findall(r"[\u0e00-\u0e7f]+|[^\u0e00-\u0e7f]+",text):
        thai="\u0e00"<=chunk[0]<="\u0e7f"
        apply_font(p.add_run(chunk),size,thai=thai)
    return p

def prepare_docx(report,path):
    d=draft(report)
    verify_draft(report,d)
    target=Path(path)
    if target.exists():
        raise FileExistsError(target)
    doc=Document()
    section=doc.sections[0]
    section.page_width=Mm(210);section.page_height=Mm(297)
    section.left_margin=section.right_margin=Mm(22)
    section.top_margin=section.bottom_margin=Mm(20)
    apply_font(section.header.paragraphs[0].add_run(LABEL),10)
    apply_font(section.footer.paragraphs[0].add_run(PREVIEW),10)
    line(doc,LABEL,14)
    line(doc,PREVIEW,11)
    # Short labeled groups avoid line-wrap ambiguity in PDF extraction.
    source_hash=d["source_sha256"]
    source_markers=[f"SHA256 part {i+1}/4: {source_hash[i*16:(i+1)*16]}" for i in range(4)]
    for marker in source_markers:
        line(doc,marker,9)
    for paragraph in d["paragraphs"]:
        line(doc,paragraph["section"],13)
        line(doc,paragraph["text"],12)
    line(doc,"Discussion: "+d["discussion_status"],10)
    line(doc,"Numeric fact register",13)
    markers=[]
    for fact in d["facts"]:
        marker=f'{fact["id"]} = {fact["rendered"]}'
        markers.append(marker);line(doc,marker,11)
    doc.save(target)
    return {"label":LABEL,"source_sha256":d["source_sha256"],
            "source_markers":source_markers,"markers":markers,"paragraphs":[p["text"] for p in d["paragraphs"]],
            "docx_sha256":sha(target)}

def inspect_pdf(path,expected):
    source=Path(path)
    with pdfplumber.open(source) as pdf:
        if not pdf.pages:
            raise ValueError("PDF has no pages")
        text="\n".join(p.extract_text() or "" for p in pdf.pages)
        pages=len(pdf.pages)
    # Record pdfplumber mismatches separately; Poppler is the independent text gate.
    plumber_flat=norm(text)
    poppler=shutil.which("pdftotext")
    if not poppler:
        raise RuntimeError("BLOCKED: Poppler pdftotext unavailable")
    extracted=subprocess.run([poppler,"-layout",str(source),"-"],capture_output=True,text=True,
                             encoding="utf-8",errors="strict",check=True,timeout=30).stdout
    flat=norm(extracted)
    plumber_missing=[i for i,p in enumerate(expected["paragraphs"]) if norm(p) not in plumber_flat]
    markers=[m for m in expected["markers"] if norm(m) not in flat]
    missing_paragraphs=[i for i,p in enumerate(expected["paragraphs"]) if norm(p) not in flat]
    # Compatibility normalization is diagnostic only; it cannot rescue the strict gate.
    compat=lambda value:"".join(c for c in unicodedata.normalize("NFKC",value) if not c.isspace())
    compat_flat=compat(extracted)
    compatibility_only_matches=[i for i in missing_paragraphs if compat(expected["paragraphs"][i]) in compat_flat]
    label_ok=norm(LABEL) in flat and norm(PREVIEW) in flat
    hash_ok=all(norm(marker) in flat for marker in expected["source_markers"])
    return {"label":LABEL,"pdf_sha256":sha(source),"page_count":pages,
            "native_text_present":bool(flat),"source_hash_text_present":hash_ok,
            "preview_labels_present":label_ok,"fact_markers_checked":len(expected["markers"]),
            "missing_fact_markers":markers,"paragraphs_checked":len(expected["paragraphs"]),
            "missing_paragraph_indices":missing_paragraphs,
            "paragraph_text_extractor":"Poppler pdftotext -layout; NFC and whitespace removed",
            "pdfplumber_missing_paragraph_indices":plumber_missing,
            "nfkc_only_paragraph_matches":compatibility_only_matches,
            "fact_text_gate":label_ok and hash_ok and not markers,
            "paragraph_text_gate":not missing_paragraphs,
            "word_visual_qa":"NOT_EXECUTED","academic_acceptance":False}

def render_preview(report,output_dir,*,timeout=90):
    exe=shutil.which("libreoffice") or shutil.which("soffice")
    if not exe:
        raise RuntimeError("BLOCKED: LibreOffice preview runtime unavailable")
    fc=shutil.which("fc-match")
    if not fc:
        raise RuntimeError("BLOCKED: fontconfig unavailable")
    match=subprocess.run([fc,"-f","%{family}",FONT],capture_output=True,text=True,check=True,timeout=10).stdout
    latin_match=subprocess.run([fc,"-f","%{family}",LATIN_FONT],capture_output=True,text=True,check=True,timeout=10).stdout
    if FONT not in match or latin_match!=LATIN_FONT:
        raise RuntimeError("BLOCKED: expected Thai and Latin fonts not installed")
    out=Path(output_dir).resolve()
    out.mkdir(parents=True,exist_ok=False)
    doc=out/"SYNTHETIC_preview.docx"
    pdf=out/"SYNTHETIC_preview.pdf"
    expected=prepare_docx(report,doc)
    version=subprocess.run([exe,"--version"],capture_output=True,text=True,check=True,timeout=20).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        profile=(Path(tmp)/"profile").as_uri()
        subprocess.run([exe,"-env:UserInstallation="+profile,"--headless","--convert-to","pdf",
                        "--outdir",str(out),str(doc)],check=True,capture_output=True,timeout=timeout)
    if not pdf.is_file():
        raise RuntimeError("Preview renderer did not produce PDF")
    if sha(doc)!=expected["docx_sha256"]:
        raise ValueError("DOCX source was modified by renderer")
    qa=inspect_pdf(pdf,expected)
    qa.update(renderer=version,font_family=match,latin_font_family=latin_match,docx_sha256=expected["docx_sha256"],
              source_sha256=expected["source_sha256"],
              status="PREVIEW_TEXT_PASS" if qa["fact_text_gate"] and qa["paragraph_text_gate"]
                       else "PREVIEW_TEXT_REVIEW_REQUIRED")
    (out/"SYNTHETIC_preview_qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf-8")
    return qa

def main():
    import argparse
    from statistical_engine import analyze
    import numpy as np
    import pandas as pd
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    rng=np.random.default_rng(24);x=rng.normal(size=(64,2))
    data=pd.DataFrame({"x1":x[:,0],"x2":x[:,1],"y":x[:,0]+rng.normal(size=64)})
    report=analyze(data,["x1","x2"],"y",source_label=LABEL)
    qa=render_preview(report,args.output)
    print(json.dumps(qa,indent=2))
    return 0 if qa["fact_text_gate"] and qa["paragraph_text_gate"] else 1

if __name__=="__main__":
    raise SystemExit(main())
