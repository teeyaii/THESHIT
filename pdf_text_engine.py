"""Bounded local text-layer extraction with optional Tesseract OCR fallback."""
import csv
import io
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import pdfplumber
from pdf_limits import check_pdf, checked_pages, run_bounded, ResourceLimitError

class OCRConfigurationError(ValueError):
    """The requested TSV format is unavailable or has an invalid header."""

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
    reader=csv.DictReader(io.StringIO(tsv),delimiter="\t")
    required={"level","left","top","width","height","conf","text"}
    fields=reader.fieldnames or []
    if not required.issubset(fields) or len(fields)!=len(set(fields)):
        raise OCRConfigurationError("Expected Tesseract TSV header; check configs/tsv")
    for row in reader:
        if None in row or any(row.get(k) is None for k in required):
            raise ValueError("Malformed OCR TSV row")
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
    """Bound native/OCR work in a separate worker process."""
    path=check_pdf(path)
    return run_bounded("extract",{"path":str(path),"max_pages":max_pages,"dpi":dpi,
                                  "ocr":ocr,"force_ocr":force_ocr})

def _extract_pdf(path, *, max_pages=20, dpi=200, ocr=True, force_ocr=False):
    """No network calls. Prefer native text; OCR candidates are not verified evidence."""
    path=check_pdf(path)
    if type(max_pages) is not int or not 1<=max_pages<=100 or type(dpi) is not int or not 100<=dpi<=300:
        raise ValueError("max_pages 1–100 and dpi 100–300 required")
    original=sha(path)
    pages=[]
    with pdfplumber.open(path) as doc:
        all_pages=checked_pages(doc);total=len(all_pages)
        for page in all_pages[:max_pages]:
            text=page.extract_text() or ""
            if len(text)>2_000_000:raise ResourceLimitError("PDF page text limit exceeded")
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
                    if len(process.stdout)>8_000_000:raise ResourceLimitError("OCR TSV output limit exceeded")
                    row["words"]=parse_tsv(process.stdout)
                    row["text"]=" ".join(w["text"] for w in row["words"])
                    row["status"]="OCR_CANDIDATE_UNVERIFIED" if row["words"] else "OCR_NO_MATCH"
                    row["engine"]=cap["version"]
                except OCRConfigurationError:
                    row["status"]="OCR_CONFIGURATION_ERROR"
                except ResourceLimitError:
                    row["status"]="OCR_BLOCKED_OUTPUT_LIMIT"
                except (subprocess.SubprocessError,UnicodeError,ValueError,KeyError):
                    row["status"]="OCR_EXTRACTION_ERROR"
            pages.append(row)
    if sha(check_pdf(path))!=original:
        raise ValueError("Source changed during extraction")
    return {"source_sha256":original,"review_required":True,"total_pages":total,
            "processed_pages":len(pages),"truncated":len(pages)<total,"pages":pages,
            "limitations":"OCR text and pixel boxes are candidates. Verify against the original page; not semantic evidence."}
