"""Bounded local text-layer extraction with optional Tesseract OCR fallback."""
import csv
import io
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import pdfplumber

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def ocr_capabilities():
    binary=shutil.which("tesseract")
    if not binary:
        return {"available":False,"languages":[],"version":None}
    version=subprocess.run([binary,"--version"],capture_output=True,text=True,
                           timeout=10,check=True).stdout.splitlines()[0]
    languages=subprocess.run([binary,"--list-langs"],capture_output=True,text=True,
                             timeout=10,check=True).stdout.splitlines()
    return {"available":True,"languages":[x.strip() for x in languages[1:] if x.strip()],
            "version":version}

def parse_tsv(tsv):
    words=[]
    for row in csv.DictReader(io.StringIO(tsv),delimiter="\t"):
        if row.get("level")!="5" or not (row.get("text") or "").strip():
            continue
        x,y,w,h=(int(row[key]) for key in ("left","top","width","height"))
        if min(x,y)<0 or min(w,h)<=0:
            raise ValueError("Invalid OCR bounding box")
        confidence=float(row["conf"])
        words.append({"text":row["text"],"confidence":confidence,
                      "pixel_bbox":[x,y,x+w,y+h]})
    return words

def extract_pdf(path, *, max_pages=20, dpi=200, ocr=True, force_ocr=False):
    """No network calls. Prefer native text; OCR candidates are not verified evidence."""
    path=Path(path).resolve()
    if path.suffix.lower()!=".pdf" or not path.is_file():
        raise ValueError("Existing local PDF required")
    if type(max_pages) is not int or not 1<=max_pages<=100 or type(dpi) is not int or not 100<=dpi<=300:
        raise ValueError("max_pages 1–100 and dpi 100–300 required")
    original=sha(path)
    pages=[]
    with pdfplumber.open(path) as doc:
        total=len(doc.pages)
        for page in doc.pages[:max_pages]:
            text=page.extract_text() or ""
            row={"physical_page":page.page_number,"status":"TEXT_LAYER_CANDIDATE",
                 "text":text,"words":[]}
            if text.strip() and not force_ocr:
                pages.append(row);continue
            row.update(status="NO_TEXT_LAYER",text="")
            if not ocr:
                pages.append(row);continue
            cap=ocr_capabilities()
            if not cap["available"] or not {"tha","eng"}.issubset(cap["languages"]):
                row["status"]="OCR_BLOCKED_MISSING_ENGINE_OR_LANGUAGE"
                pages.append(row);continue
            pixels=(page.width*dpi/72)*(page.height*dpi/72)
            if pixels>20_000_000:
                row["status"]="OCR_BLOCKED_PIXEL_LIMIT"
                pages.append(row);continue
            with tempfile.TemporaryDirectory() as d:
                image=Path(d)/"page.png"
                page.to_image(resolution=dpi).save(image)
                row["raster_sha256"]=sha(image)
                row["dpi"]=dpi
                try:
                    process=subprocess.run([shutil.which("tesseract"),str(image),"stdout",
                        "-l","tha+eng","--psm","6","tsv"],capture_output=True,
                        text=True,encoding="utf-8",errors="strict",timeout=60,check=True)
                    row["words"]=parse_tsv(process.stdout)
                    row["text"]=" ".join(w["text"] for w in row["words"])
                    row["status"]="OCR_CANDIDATE_UNVERIFIED" if row["words"] else "OCR_NO_MATCH"
                    row["engine"]=cap["version"]
                except (subprocess.SubprocessError,UnicodeError,ValueError,KeyError):
                    row["status"]="OCR_EXTRACTION_ERROR"
            pages.append(row)
    if sha(path)!=original:
        raise ValueError("Source changed during extraction")
    return {"source_sha256":original,"review_required":True,"total_pages":total,
            "processed_pages":len(pages),"truncated":len(pages)<total,"pages":pages,
            "limitations":"OCR text and pixel boxes are candidates. Verify against the original page; not semantic evidence."}
