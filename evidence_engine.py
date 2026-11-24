"""Local evidence candidates and atlas. Never auto-verify a research claim."""
import hashlib
import json
import re
from pathlib import Path
import pdfplumber
from docx import Document
from docx.shared import Inches

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def candidate_atlas(manifest, source_dir, output_dir):
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
        if not isinstance(phrase, str) or not phrase.strip():
            raise ValueError("Nonempty search phrase required")
        prepared.append((row, src))
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for row, src in prepared:
        record = {"evidence_id": row["evidence_id"], "claim": row.get("claim", ""),
                  "source_file": row["source_file"], "phrase": row["phrase"],
                  "status": "NOT_ACCESSIBLE", "hits": []}
        if not src.is_file():
            records.append(record)
            continue
        try:
            record["source_sha256"] = digest(src)
            with pdfplumber.open(src) as pdf:
                text_pages = 0
                for page in pdf.pages:
                    if (page.extract_text() or "").strip():
                        text_pages += 1
                    for hit in page.search(row["phrase"], regex=False, return_chars=False) or []:
                        box = [hit[k] for k in ("x0","top","x1","bottom")]
                        left, top, right, bottom = page.bbox
                        crop = (max(left, box[0]-20), max(top, box[1]-30),
                                min(right, box[2]+20), min(bottom, box[3]+30))
                        name = f'{row["evidence_id"]}_{len(record["hits"])+1:03d}.png'
                        page.crop(crop).to_image(resolution=150).save(out / name)
                        record["hits"].append({"physical_page":page.page_number,
                            "matched_text":hit["text"], "bbox":box, "crop_bbox":list(crop),
                            "image":name, "image_sha256":digest(out/name)})
                record["status"] = ("CANDIDATE_UNVERIFIED" if record["hits"] else
                                    "NO_TEXT_LAYER" if text_pages == 0 else "NO_MATCH")
                record["text_pages"] = text_pages
                record["total_pages"] = len(pdf.pages)
            if digest(src) != record["source_sha256"]:
                raise ValueError("Source changed during extraction")
        except Exception as exc:
            record["status"] = "EXTRACTION_ERROR"
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
