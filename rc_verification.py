"""Run all document outputs from a single synthetic computed report and reconcile provenance."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from academic_writing import draft, verify_draft, export_draft
from report_engine import build_report, verify_report, source_hash
from ru_thesis_builder import build as build_thesis, verify as verify_thesis, demo_report
from ru_article_builder import build as build_article, verify as verify_article
from pdf_preview import render_preview
from theshit_cli import run_demo, verify_demo
from mobile_dashboard import build as build_dashboard
from ru_style_audit import audit_styles, PROFILE
from citation_language_qa import language_candidates
from release_gate import evaluate
from statistical_engine import LABEL

def write(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")

def hashes(root):
    result={}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():raise ValueError("Symlink in RC output")
        if p.is_file() and p.name!="RC_MANIFEST.json":
            result[p.relative_to(root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def run(out,commit,*,pdf=False):
    root=Path(out);root.mkdir(parents=True,exist_ok=False)
    report=demo_report()
    source=source_hash(report)
    write(root/"SYNTHETIC_computed_report.json",report)
    narrative=draft(report)
    text_qa=verify_draft(report,narrative)
    export_draft(report,root/"writing")
    report_qa=build_report(report,root/"report")
    thesis_qa=build_thesis(report,root/"thesis")
    article_qa=build_article(report,root/"article")
    for rel in ("writing/SYNTHETIC_draft.json","thesis/SYNTHETIC_structure_manifest.json","article/SYNTHETIC_article_manifest.json"):
        obj=json.loads((root/rel).read_text(encoding="utf-8"))
        if obj["source_sha256"]!=source or obj.get("final_acceptance") is not False:
            raise ValueError("Cross-output source or acceptance mismatch")
    if verify_report(root/"report")!=report_qa or verify_thesis(root/"thesis")!=thesis_qa or verify_article(root/"article")!=article_qa:
        raise ValueError("Reopened document verification mismatch")
    thesis_path=root/"thesis/SYNTHETIC_RU_structure.docx"
    mapping={"RUBody":"body","RUChapter":"chapter","RUFront":"front_title","RUFrontEntry":"front_title","RUTOCTitle":"toc_title","RUBibliographyTitle":"bibliography_title",
             "RUNotice":"fixture_notice",
             "RUSubheading":"heading1","RUSubheading2":"heading2","RUTable":"table","RUCaption":"caption","RUTableLabel":"table_label","RUSubheading3":"heading3","RUSubheading4":"heading4","RUSubheading5":"heading5",
             "RUReference":"bibliography","RUAppendix":"appendix_divider"}
    # Non-TOC front titles and flexible table/caption sizes stay unresolved; notice is a fixture convention.
    style_qa=audit_styles(thesis_path,mapping,section_roles=thesis_qa["section_roles"])
    write(root/"SYNTHETIC_style_inventory.json",style_qa)
    write(root/"SYNTHETIC_language_candidates.json",language_candidates(thesis_path))
    preview={"status":"NOT_EXECUTED","word_visual_qa":"NOT_EXECUTED"}
    if pdf:
        preview=render_preview(report,root/"pdf")
        if preview["source_sha256"]!=source or not preview["fact_text_gate"] or not preview["paragraph_text_gate"]:
            raise ValueError("PDF preview consistency failed")
    e2e=run_demo(root/"core_demo")
    if verify_demo(root/"core_demo")!=e2e:raise ValueError("Core bundle mismatch")
    dashboard=build_dashboard(root/"core_demo",root/"dashboard/index.html")
    gate=evaluate([],commit)
    write(root/"release_gate_unattested.json",gate)
    summary={"label":LABEL,"commit_sha":commit,"source_sha256":source,
             "status":"COMBINED_SYNTHETIC_OUTPUT_QA_PASS",
             "facts":text_qa["fact_count"],"report":report_qa,"thesis":thesis_qa,
             "article":article_qa,"style_counts":style_qa["counts"],"pdf":preview,
             "core":e2e,"dashboard":dashboard,"release_status":gate["status"],
             "final_acceptance":False}
    write(root/"RC_SUMMARY.json",summary)
    write(root/"RC_MANIFEST.json",{"label":LABEL,"commit_sha":commit,"files":hashes(root)})
    return verify(root)

def verify(out):
    root=Path(out);m=json.loads((root/"RC_MANIFEST.json").read_text(encoding="utf-8"))
    s=json.loads((root/"RC_SUMMARY.json").read_text(encoding="utf-8"))
    if m["label"]!=LABEL or m["commit_sha"]!=s["commit_sha"] or m["files"]!=hashes(root):
        raise ValueError("RC manifest mismatch")
    if s["final_acceptance"] is not False or s["release_status"]!="BLOCKED":
        raise ValueError("Invalid release state")
    return s

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["demo","verify"])
    p.add_argument("--output",required=True);p.add_argument("--commit")
    p.add_argument("--pdf",action="store_true")
    a=p.parse_args()
    if a.command=="demo":
        commit=a.commit or subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
        summary=run(a.output,commit,pdf=a.pdf)
    else:summary=verify(a.output)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
