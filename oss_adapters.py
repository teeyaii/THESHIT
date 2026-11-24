"""Local adapters. CI uses generated fixtures only; never upload private data."""
from pathlib import Path
import importlib.metadata as metadata

import pandas as pd
import pandera.pandas as pa
import pdfplumber
import pyreadstat
from docx import Document
from codebook import load_codebook, audit
from research_demo import LABEL, fixture, run_demo
from pdf_limits import check_pdf, checked_pages, stream_digest, run_bounded, ResourceLimitError, MAX_MATCHES

def dependency_versions():
    return {name: metadata.version(name) for name in
            ("pdfplumber", "python-docx", "pandera", "pyreadstat")}

def validate_fixture(df):
    _, groups, _ = load_codebook()
    if not audit(df, groups)["passed"]:
        raise ValueError("Synthetic audit failed")
    schema = pa.DataFrameSchema({
        item: pa.Column(int, checks=pa.Check.in_range(1, 5), nullable=False)
        for cols in groups.values() for item in cols
    }, strict=True, ordered=True, coerce=False)
    return schema.validate(df)

def pdf_text_matches(path, phrase):
    path=check_pdf(path)
    return run_bounded("matches",{"path":str(path),"phrase":phrase})

def _pdf_text_matches(path, phrase):
    """Return candidate evidence coordinates, not verified claim support.
    Text-layer PDF only. Page number is physical, one-based.
    """
    if not isinstance(phrase,str) or not phrase.strip() or len(phrase)>10000:
        raise ValueError("Nonempty search phrase required")
    path = check_pdf(path)
    digest = stream_digest(path)
    matches = []
    with pdfplumber.open(path) as pdf:
        for page in checked_pages(pdf):
            for hit in page.search(phrase, regex=False, return_chars=False) or []:
                if len(matches)>=MAX_MATCHES:raise ResourceLimitError("PDF match limit exceeded")
                matches.append({"page": page.page_number, "text": hit["text"],
                    "bbox": [hit[k] for k in ("x0", "top", "x1", "bottom")],
                    "source_sha256": digest, "status": "CANDIDATE_UNVERIFIED"})
    if stream_digest(check_pdf(path))!=digest:raise ValueError("Source changed during extraction")
    return matches

def export_demo_sav(path, n=100, seed=42):
    df = validate_fixture(fixture(n, seed))
    labels = {col: LABEL + " " + col for col in df.columns}
    pyreadstat.write_sav(df, str(path), column_labels=labels, file_label=LABEL)
    return df

def export_demo_docx(path, n=100, seed=42):
    report = run_demo(n, seed)
    doc = Document()
    doc.add_heading(LABEL, 0)
    doc.add_paragraph("Generated fixture; not actual respondents or research findings.")
    doc.add_paragraph("Seed: " + str(seed) + "; synthetic rows: " + str(n))
    doc.add_paragraph("Codebook SHA-256: " + report["codebook_sha256"])
    table = doc.add_table(rows=1, cols=3)
    for cell, text in zip(table.rows[0].cells, ("Construct", "Mean", "SD")):
        cell.text = text
    for name, stats in report["descriptive"].items():
        for cell, text in zip(table.add_row().cells,
                              (name, f'{stats["mean"]:.4f}', f'{stats["std"]:.4f}')):
            cell.text = text
    doc.add_paragraph(LABEL)
    doc.save(str(path))
