"""THESHIT synthetic end-to-end rehearsal; no real study intake or live queries."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from research_discovery import discover
from literature_library import LiteratureLibrary
from evidence_engine import candidate_atlas
from evidence_highlight import highlight_candidates,audit_body_shading
from pdf_text_engine import extract_pdf
from statistical_engine import analyze,LABEL
from report_engine import build_report,verify_report

def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tiny_pdf(path):
    stream=b"BT /F1 12 Tf 30 100 Td (SYNTHETIC evidence fixture) Tj ET"
    objects=[b"<< /Type /Catalog /Pages 2 0 R >>",
             b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
             b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
             b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
             b"<< /Length "+str(len(stream)).encode()+b" >>\nstream\n"+stream+b"\nendstream"]
    data=bytearray(b"%PDF-1.4\n");offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(data));data.extend(f"{i} 0 obj\n".encode()+obj+b"\nendobj\n")
    pos=len(data);data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{pos}\n%%EOF\n".encode())
    path.write_bytes(data)

def file_map(root):
    records={}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("Symlink in bundle")
        if p.is_file() and p!=root/"MANIFEST.json":
            records[p.relative_to(root).as_posix()]=digest(p)
    return records

def run_demo(output_dir):
    root=Path(output_dir).resolve();root.mkdir(parents=True,exist_ok=False)
    sources=root/"sources";sources.mkdir()
    def fake_provider(url,headers):
        return {"message":{"items":[{"title":["SYNTHETIC metadata fixture"],
                                     "author":[{"name":"Fixture Author"}]}]}}
    records=discover("synthetic test",fetch=fake_provider)
    lib=LiteratureLibrary(root/"literature.sqlite3")
    if lib.ingest(records)!=1 or lib.ingest(records)!=0:
        raise ValueError("Library import check failed")
    lib.export_review(root/"literature_review.json")
    pdf=sources/"SYNTHETIC_source.pdf";tiny_pdf(pdf)
    native=extract_pdf(pdf,ocr=False);dump(root/"native_text.json",native)
    if native["pages"][0]["status"]!="TEXT_LAYER_CANDIDATE":
        raise ValueError("Native extraction failed")
    candidate=candidate_atlas([{"evidence_id":"DEMO1","source_file":pdf.name,
                                "phrase":"evidence fixture"}],sources,root/"candidates")
    highlighted=highlight_candidates(candidate,sources,root/"candidates",root/"highlights",
                                     {pdf.name:"FFE066"})
    if len(highlighted["records"])!=1:
        raise ValueError("Expected one evidence candidate")
    word=sources/"SYNTHETIC_word.docx";doc=Document()
    phrase="SYNTHETIC evidence fixture"
    run=doc.add_paragraph().add_run(phrase)
    shade=OxmlElement("w:shd");shade.set(qn("w:fill"),"FFE066")
    run._r.get_or_add_rPr().append(shade);doc.save(word)
    coverage=audit_body_shading(word,[{"paragraph":0,"start":0,"end":len(phrase),
                                     "text":phrase,"color":"FFE066"}])
    if coverage["matched_characters"]!=len(phrase):
        raise ValueError("Word shading fixture did not match")
    dump(root/"word_coverage.json",coverage)
    rng=np.random.default_rng(20261124);x=rng.normal(size=(64,2))
    frame=pd.DataFrame({"x1":x[:,0],"x2":x[:,1],
                       "y":0.5*x[:,0]-0.4*x[:,1]+rng.normal(size=64)})
    report=analyze(frame,["x1","x2"],"y",source_label=LABEL)
    qa=build_report(report,root/"report");dump(root/"report_qa.json",qa)
    manifest={"label":LABEL,"seed":20261124,"fixture_rows":64,
              "checks":{"discovery":"MOCK_ONLY","library":"PASS","native_pdf":"PASS",
                        "candidate_highlight":"PASS","word_shading":"STRUCTURAL_ONLY",
                        "statistics":"PASS","report":"STRUCTURAL_PASS"},
              "files":file_map(root)}
    dump(root/"MANIFEST.json",manifest)
    return verify_demo(root)

def verify_demo(output_dir):
    root=Path(output_dir).resolve()
    manifest=json.loads((root/"MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("label")!=LABEL or manifest.get("files")!=file_map(root):
        raise ValueError("Synthetic bundle manifest mismatch")
    report=verify_report(root/"report")
    saved=json.loads((root/"report_qa.json").read_text(encoding="utf-8"))
    if report!=saved:
        raise ValueError("Report QA mismatch")
    return {"label":LABEL,"status":"SYNTHETIC_E2E_PASS","files_verified":len(manifest["files"]),
            "report_cells_verified_each_format":report["cells_verified_each_format"],
            "limitations":"Mock discovery; no empirical study, actual citation verification, Word visual or live provider acceptance."}

def main():
    parser=argparse.ArgumentParser(description=LABEL)
    parser.add_argument("command",choices=["demo","verify"])
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    print(json.dumps((run_demo if args.command=="demo" else verify_demo)(args.output),indent=2))
if __name__=="__main__":
    main()
