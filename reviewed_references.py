"""Conservative reference drafts from explicitly reviewed metadata; RU APA edition conflict remains open."""
from pathlib import Path
import json
from urllib.parse import urlsplit
from docx import Document
from docx.shared import Pt,Mm
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from research_discovery import normalize_doi
from evidence_review import canonical_hash

NOTICE="REFERENCE DRAFT — REVIEW REQUIRED"

def required(value):
    if not isinstance(value,str) or not value.strip() or any(ord(c)<32 for c in value):
        raise ValueError("Reviewed nonempty text required")
    return value.strip()

def common_fields(r):
    if r.get("metadata_review_status")!="REVIEWED":
        raise ValueError("Reviewed reference metadata required")
    required(r["reviewer_id"])
    # Author labels and sentence-case titles must be reviewed explicitly; no guessed transliteration.
    names=r["apa_author_labels"]
    if not isinstance(names,list) or not names:raise ValueError("Reviewed author labels required")
    names=[required(a) for a in names]
    language=r.get("language","en")
    if language not in ("th","en"):raise ValueError("Supported reference language th/en required")
    if len(names)==1:authors=names[0]
    elif len(names)<=20:authors=", ".join(names[:-1])+(" และ " if language=="th" else ", & ")+names[-1]
    else:authors=", ".join(names[:19])+", … "+names[-1]
    year=r["year"]
    if type(year) is not int or not 1<=year<=3000:raise ValueError("Reviewed year required")
    title=required(r["title"]).rstrip(".")
    return authors+" ("+str(year)+"). ",title

def reviewed_link(r):
    if r.get("doi"):
        doi=normalize_doi(r["doi"])
        if not doi:raise ValueError("Invalid DOI")
        return "https://doi.org/"+doi
    if r.get("url"):
        u=required(r["url"]);parts=urlsplit(u)
        if parts.scheme!="https" or not parts.hostname or parts.username or parts.password:raise ValueError("Reviewed HTTPS URL required")
        return u
    return ""

def journal_segments(r):
    if r.get("type")!="journal_article":raise ValueError("Journal type required")
    prefix,title=common_fields(r)
    journal=required(r["journal"]);volume=required(r["volume"])
    issue=r.get("issue")
    pages=r.get("pages");article=r.get("article_number")
    if bool(pages)==bool(article):raise ValueError("Exactly one page range or article number required")
    locator=required(pages) if pages else "Article "+required(article)
    suffix=("("+required(issue)+")" if issue else "")+", "+locator+"."
    link=reviewed_link(r)
    return [(prefix+title+". ",False),
            (journal+", "+volume,True),(suffix+(" "+link if link else ""),False)]

def reference_segments(r):
    kind=r.get("type")
    if kind=="journal_article":return journal_segments(r)
    prefix,title=common_fields(r)
    link=reviewed_link(r)
    if kind=="book":
        tail=required(r["publisher"])+"."
    elif kind=="thesis":
        # Reviewer supplies exact degree and publication/repository description.
        tail="["+required(r["thesis_description"])+", "+required(r["institution"])+"]."
        if r.get("repository"):tail+=" "+required(r["repository"])+"."
    elif kind=="website":
        tail=required(r["site_name"])+"."
        if not link:raise ValueError("Reviewed website URL required")
    else:raise ValueError("Unsupported reference type")
    return [(prefix,False),(title,True),(". "+tail+(" "+link if link else ""),False)]

def prepare(records):
    ids=set();dois=set();entries=[]
    for r in records:
        rid=required(r["reference_id"])
        if rid in ids:raise ValueError("Duplicate reference ID")
        ids.add(rid)
        segs=reference_segments(r)
        doi=normalize_doi(r.get("doi"))
        if doi and doi in dois:raise ValueError("Duplicate DOI")
        if doi:dois.add(doi)
        entries.append({"reference_id":rid,"metadata_sha256":canonical_hash(r),
                        "segments":[{"text":t,"italic":i} for t,i in segs],
                        "sort_key":required(r["reviewed_sort_key"]),"language":r.get("language","en"),"type":r["type"]})
    if not entries:raise ValueError("No reviewed references")
    entries.sort(key=lambda e:(e["sort_key"],e["reference_id"]))
    return {"status":"REFERENCE_DRAFT_ONLY","entries":entries,"final_acceptance":False,
            "language_counts":{lang:sum(e["language"]==lang for e in entries) for lang in ("th","en")},
            "language_count_targets_report_only":{"th":10,"en":5},
            "ru_apa_edition_status":"UNRESOLVED_CONFLICT_X03",
            "limitations":"Reviewer-supplied author labels, casing and order. Journal/book/thesis/website drafts only. Language counts are not country-of-study counts. No DOI existence check, Thai collation guarantee, same-author year suffix or academic acceptance."}

def export(records,output_dir):
    result=prepare(records)
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=False)
    doc=Document()
    doc.add_paragraph(NOTICE)
    for entry in result["entries"]:
        p=doc.add_paragraph()
        p.paragraph_format.left_indent=Mm(12.7);p.paragraph_format.first_line_indent=Mm(-12.7)
        for segment in entry["segments"]:
            run=p.add_run(segment["text"]);run.italic=segment["italic"];run.font.name="Browallia New";run.font.size=Pt(18)
            pr=run._r.get_or_add_rPr();pr.rFonts.set(qn("w:cs"),"Browallia New")
            size=OxmlElement("w:szCs");size.set(qn("w:val"),"36");pr.append(size)
    path=out/"REFERENCE_DRAFT.docx";doc.save(path)
    actual=Document(path)
    if len(actual.paragraphs)!=len(result["entries"])+1:raise ValueError("Reference count mismatch")
    for p,e in zip(actual.paragraphs[1:],result["entries"]):
        if [(r.text,r.italic) for r in p.runs]!=[(s["text"],s["italic"]) for s in e["segments"]]:
            raise ValueError("Reference text/style mismatch")
    (out/"reference_manifest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result
