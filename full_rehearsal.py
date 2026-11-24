"""Integrated synthetic rehearsal of research workflow; never an empirical study."""
import argparse
import json
import hashlib
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from rc_verification import run as run_rc,verify as verify_rc
from theshit_cli import tiny_pdf
from research_discovery import discover
from literature_library import LiteratureLibrary
from evidence_engine import candidate_atlas,digest
from evidence_highlight import highlight_candidates
from evidence_review import canonical_hash
from claim_evidence_qa import reconcile
from reviewed_references import export as export_refs
from literature_synthesis import export as export_notes
from document_coverage import inventory,audit
from manuscript_preservation import preservation_diff
from statistical_engine import LABEL

CLAIM="SYNTHETIC evidence fixture"
CITATION="(Fixture, 2003)"
NOTICE="SYNTHETIC SOFTWARE TEST — NOT FOR SUBMISSION"
COLOR="FFE066"

def write(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")

def file_map(root):
    out={}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():raise ValueError("Symlink prohibited")
        if p.is_file() and p!=root/"REHEARSAL_MANIFEST.json":
            out[p.relative_to(root).as_posix()]=digest(p)
    return out

def run(root,commit,*,pdf=False):
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    rc=run_rc(root/"computed_outputs",commit,pdf=pdf)
    sources=root/"sources";sources.mkdir()
    source=sources/"SYNTHETIC_fixture.pdf";tiny_pdf(source)
    # No live query or fabricated citation presented as real.
    def mock(url,headers):
        return {"message":{"items":[{"title":["SYNTHETIC fixture article"],"author":[{"family":"Fixture","given":"A."}],"published":{"date-parts":[[2003]]},"container-title":["SYNTHETIC fixture journal"]}]}}
    candidates=discover("synthetic fixture",fetch=mock)
    library=LiteratureLibrary(root/"literature.sqlite3")
    if library.ingest(candidates)!=1 or library.ingest(candidates)!=0:
        raise ValueError("Library idempotence failure")
    library.export_review(root/"literature_review.json")
    idx=candidate_atlas([{"evidence_id":"E1","source_file":source.name,"phrase":CLAIM,"claim":CLAIM}],sources,root/"evidence")
    row=idx["records"][0];hit=row["hits"][0]
    highlights=highlight_candidates(idx,sources,root/"evidence",root/"highlights",{source.name:COLOR})
    if len(highlights["records"])!=1:raise ValueError("Expected fixture crop")
    # These simulated review inputs are explicitly fixture-only, not actual independent reviews.
    decisions=[{"evidence_id":"E1","reviewer_id":who,"record_sha256":canonical_hash(row),
                "decision":"SUPPORTS","rationale":NOTICE,"full_context_reviewed":True,
                "source_sha256":row["source_sha256"],"physical_page":hit["physical_page"],
                "source_excerpt":hit["matched_text"],"candidate_image_sha256":hit["image_sha256"]}
               for who in ("SYNTHETIC_FIXTURE_A","SYNTHETIC_FIXTURE_B")]
    ref={"reference_id":"R1","metadata_review_status":"REVIEWED","reviewer_id":"SYNTHETIC_FIXTURE",
         "type":"journal_article","apa_author_labels":["Fixture, A."],"reviewed_sort_key":"fixture",
         "year":2003,"title":candidates[0]["title"],"journal":candidates[0]["venue"],
         "volume":"1","pages":"1–1","source_sha256":row["source_sha256"]}
    refs=export_refs([ref],root/"references")
    note={"note_id":"N1","evidence_id":"E1","record_sha256":canonical_hash(row),
          "author_reviewed":True,"author_id":"SYNTHETIC_FIXTURE","theme":"Software test",
          "study_design":"Generated software fixture","population_context":"No actual participants",
          "constructs":"Fixture only","finding_note":CLAIM,"limitations_note":NOTICE,
          "applicability_note":"No empirical inference","direction":"NOT_COMPARABLE"}
    notes=export_notes(idx,decisions,[note],root/"notes")
    if notes["blocked"] or len(notes["rows"])!=1:raise ValueError("Notes gate failed")
    baseline=root/"computed_outputs/thesis/SYNTHETIC_RU_structure.docx"
    before=digest(baseline)
    doc=Document(baseline)
    original=[(p.style.name,p.text) for p in doc.paragraphs]
    chapter3=next(p for p in doc.paragraphs if p.style.name=="RU Chapter" and p.text.startswith("บทที่ 3"))
    p=chapter3.insert_paragraph_before(style="RU Body")
    r=p.add_run(CLAIM);shade=OxmlElement("w:shd");shade.set(qn("w:fill"),COLOR);r._r.get_or_add_rPr().append(shade)
    p.add_run(" "+CITATION)
    appendix=next(p for p in doc.paragraphs if p.style.name=="RU Appendix")
    rp=appendix.insert_paragraph_before(style="RU Reference")
    rp.paragraph_format.left_indent=914400//2
    rp.paragraph_format.first_line_indent=-914400//2
    for segment in refs["entries"][0]["segments"]:
        run=rp.add_run(segment["text"]);run.italic=segment["italic"]
    path=root/"SYNTHETIC_integrated_thesis.docx";doc.save(path)
    actual=Document(path)
    added={(p.style.name,p.text),(rp.style.name,rp.text)}
    if [(p.style.name,p.text) for p in actual.paragraphs if (p.style.name,p.text) not in added]!=original:
        raise ValueError("Existing paragraph changes detected")
    if [[[c.text for c in r.cells] for r in t.rows] for t in actual.tables]!=[[[c.text for c in r.cells] for r in t.rows] for t in Document(baseline).tables]:
        raise ValueError("Existing table changes detected")
    if digest(baseline)!=before:raise ValueError("Baseline modified")
    diff=preservation_diff(baseline,path)
    if diff["added_parts"] or diff["removed_parts"] or diff["changed_parts"]!=["word/document.xml"]:
        raise ValueError("Unexpected ancillary part modification")
    inv=inventory(path)
    loc=next(p for p in inv["paragraphs"] if p["part"]=="word/document.xml" and p["text"]==CLAIM+" "+CITATION)
    common={"part":loc["part"],"paragraph":loc["paragraph"]}
    cita={"document_sha256":inv["source_sha256"],"references":[ref],
          "citations":[{"citation_id":"C1",**common,"start":len(CLAIM)+1,"end":len(loc["text"]),
                        "exact_text":CITATION,"reference_ids":["R1"],"claim_review_status":"REVIEWED"}]}
    links=[{"claim_id":"CL1",**common,"start":0,"end":len(CLAIM),"exact_text":CLAIM,
            "citation_ids":["C1"],"evidence_ids":["E1"],"evidence_record_sha256":{"E1":canonical_hash(row)},"evidence_reference_ids":{"E1":"R1"}}]
    qa=reconcile(path,cita,idx,decisions,links,sources,root/"evidence")
    if not qa["declared_links_consistent"]:raise ValueError("Evidence chain failed")
    incomplete=reconcile(path,cita,idx,decisions[:1],links,sources,root/"evidence")
    if incomplete["declared_links_consistent"]:raise ValueError("Missing reviewer bypass")
    coverage=audit(path,[{**common,"start":0,"end":len(CLAIM),"text":CLAIM,"color":COLOR}],expected_sha256=inv["source_sha256"])
    if coverage["matched_characters"]!=len(CLAIM) or any(coverage[k] for k in ("missing","wrong_color","unresolved","unexpected")):
        raise ValueError("Highlight parity failed")
    for name,obj in {"fixture_reviews":decisions,"citation_manifest":cita,"claim_links":links,"claim_qa":qa,
                     "negative_review_qa":incomplete,"color_qa":coverage,"preservation_qa":diff}.items():
        write(root/(name+".json"),obj)
    summary={"label":LABEL,"status":"INTEGRATED_SYNTHETIC_REHEARSAL_PASS","commit_sha":commit,
             "discovery":"MOCK_ONLY","review_decisions":"SYNTHETIC_FIXTURES_ONLY",
             "references":len(refs["entries"]),"notes":len(notes["rows"]),"claims":len(qa["claims"]),
             "color_characters_verified":coverage["matched_characters"],"negative_review_blocked":True,
             "baseline_sha256":before,"computed_source_sha256":rc["source_sha256"],
             "integrated_thesis_sha256":digest(path),"computed_outputs":rc,
             "release_status":"BLOCKED","final_acceptance":False,
             "limitations":"One generated evidence source, fixture reviews, mock discovery; integrated thesis copy only structurally checked. PDF is separate computed preview, not export of integrated thesis. No real data or Word visual acceptance."}
    write(root/"REHEARSAL_SUMMARY.json",summary)
    write(root/"REHEARSAL_MANIFEST.json",{"label":LABEL,"commit_sha":commit,"files":file_map(root)})
    return verify(root)

def verify(root):
    root=Path(root);m=json.loads((root/"REHEARSAL_MANIFEST.json").read_text(encoding="utf-8"))
    s=json.loads((root/"REHEARSAL_SUMMARY.json").read_text(encoding="utf-8"))
    if m["label"]!=LABEL or m["commit_sha"]!=s["commit_sha"] or m["files"]!=file_map(root):
        raise ValueError("Rehearsal manifest mismatch")
    if s["computed_outputs"]!=verify_rc(root/"computed_outputs") or s["final_acceptance"] is not False or s["release_status"]!="BLOCKED":
        raise ValueError("Rehearsal state mismatch")
    return s

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("command",choices=["demo","verify"])
    p.add_argument("--output",required=True);p.add_argument("--commit");p.add_argument("--pdf",action="store_true");a=p.parse_args()
    if a.command=="demo" and not a.commit:p.error("--commit required")
    print(json.dumps(run(a.output,a.commit,pdf=a.pdf) if a.command=="demo" else verify(a.output),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
