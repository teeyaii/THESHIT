"""Local evidence candidates and atlas. Never auto-verify a research claim."""
import tempfile
import json
import re
from pathlib import Path
import pdfplumber
from docx import Document
from docx.shared import Inches
from pdf_limits import (stream_digest, check_pdf, checked_pages, check_raster,
                        run_bounded, ResourceLimitError, MAX_MATCHES)

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
def digest(path):
    return stream_digest(path)

def candidate_atlas(manifest, source_dir, output_dir):
    """Publish only a complete atlas, from a wall-clock-bounded worker."""
    root=Path(source_dir).resolve();out=Path(output_dir).resolve()
    if out==root or root in out.parents or out.exists():
        raise ValueError("Separate new output directory required")
    if not isinstance(manifest,list) or len(manifest)>500:
        raise ResourceLimitError("Evidence manifest row limit exceeded")
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".atlas-",dir=out.parent) as tmp:
        staged=Path(tmp)/"atlas"
        result=run_bounded("atlas",{"manifest":manifest,"source_dir":str(root),"output_dir":str(staged)},timeout=300)
        if out.exists():raise ValueError("Output directory already exists")
        staged.rename(out)
        return result

def _candidate_atlas(manifest, source_dir, output_dir):
    """Manifest list: evidence_id, source_file, phrase, optional claim.
    Local use only. New output directory required to prevent stale evidence.
    """
    root = Path(source_dir).resolve()
    out = Path(output_dir).resolve()
    if out == root or root in out.parents:
        raise ValueError("Separate source and output directories required")
    prepared = []
    seen = set()
    for row in manifest:
        key = row["evidence_id"]
        if not ID.fullmatch(key) or key in seen:
            raise ValueError("Invalid or duplicate evidence ID")
        seen.add(key)
        src = (root / row["source_file"]).resolve()
        if root not in src.parents or src.suffix.lower() != ".pdf":
            raise ValueError("Source must be a PDF within source directory")
        phrase = row["phrase"]
        if not isinstance(phrase, str) or not phrase.strip() or len(phrase)>10000:
            raise ValueError("Nonempty search phrase required")
        prepared.append((row, src))
    out.mkdir(parents=True, exist_ok=False)
    records = [];total_hits=0
    for row, src in prepared:
        record = {"evidence_id": row["evidence_id"], "claim": row.get("claim", ""),
                  "source_file": row["source_file"], "phrase": row["phrase"],
                  "status": "NOT_ACCESSIBLE", "hits": []}
        if not src.is_file():
            records.append(record)
            continue
        created=[]
        try:
            check_pdf(src)
            record["source_sha256"] = digest(src)
            with pdfplumber.open(src) as pdf:
                text_pages = 0
                pages=checked_pages(pdf)
                for page in pages:
                    text=page.extract_text() or ""
                    if len(text)>2_000_000:raise ResourceLimitError("PDF page text limit exceeded")
                    if text.strip():
                        text_pages += 1
                    for hit in page.search(row["phrase"], regex=False, return_chars=False) or []:
                        if total_hits+len(record["hits"])>=MAX_MATCHES:
                            raise ResourceLimitError("Atlas match limit exceeded")
                        check_raster(page,150)
                        box = [hit[k] for k in ("x0","top","x1","bottom")]
                        left, top, right, bottom = page.bbox
                        crop = (max(left, box[0]-20), max(top, box[1]-30),
                                min(right, box[2]+20), min(bottom, box[3]+30))
                        name = f'{row["evidence_id"]}_{len(record["hits"])+1:03d}.png'
                        created.append(out/name)
                        page.crop(crop).to_image(resolution=150).save(out / name)
                        record["hits"].append({"physical_page":page.page_number,
                            "matched_text":hit["text"], "bbox":box, "crop_bbox":list(crop),
                            "image":name, "image_sha256":digest(out/name)})
                record["status"] = ("CANDIDATE_UNVERIFIED" if record["hits"] else
                                    "NO_TEXT_LAYER" if text_pages == 0 else "NO_MATCH")
                record["text_pages"] = text_pages
                record["total_pages"] = len(pages)
            if digest(check_pdf(src)) != record["source_sha256"]:
                raise ValueError("Source changed during extraction")
            total_hits+=len(record["hits"])
        except Exception as exc:
            for image in created:image.unlink(missing_ok=True)
            record["hits"]=[]
            record["status"] = "RESOURCE_LIMIT" if isinstance(exc,ResourceLimitError) else "EXTRACTION_ERROR"
            record["error_type"] = type(exc).__name__
        records.append(record)
    index = {"schema_version": "0.3", "review_required": True, "records": records}
    (out/"evidence_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    doc = Document()
    doc.add_heading("Evidence Atlas — candidates, not verified", 0)
    doc.add_paragraph("Physical page numbers; semantic claim support and printed page labels require review.")
    for record in records:
        doc.add_heading(record["evidence_id"] + " — " + record["status"], 1)
        doc.add_paragraph("Source: " + record["source_file"])
        doc.add_paragraph("Claim: " + record["claim"])
        doc.add_paragraph("Search: " + record["phrase"])
        if record.get("source_sha256"):
            doc.add_paragraph("SHA-256: " + record["source_sha256"])
        for hit in record["hits"]:
            doc.add_paragraph(f'Physical page {hit["physical_page"]}: {hit["matched_text"]}')
            doc.add_picture(str(out/hit["image"]), width=Inches(4.8))
    doc.save(out/"candidate_atlas.docx")
    return index

def locate_word_paragraphs(path, phrase):
    """Read-only body and top-level table paragraph locations; no editing."""
    if not phrase.strip():
        raise ValueError("Nonempty phrase required")
    doc = Document(path)
    locations = []
    for i, p in enumerate(doc.paragraphs):
        if phrase in p.text:
            locations.append({"kind":"body","paragraph":i,"text":p.text})
    for ti, table in enumerate(doc.tables):
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                for pi, p in enumerate(cell.paragraphs):
                    if phrase in p.text:
                        locations.append({"kind":"table","table":ti,"row":ri,
                                          "column":ci,"paragraph":pi,"text":p.text})
    return {"document_sha256":digest(path),"locations":locations,
            "status":"CANDIDATE_UNVERIFIED"}
