"""Fixed public title pilot comparing native PDF text extractors, not a full benchmark."""
import argparse
import json
import subprocess
import shutil
import tempfile
from pathlib import Path
from thai_public_probe import SOURCES,MAX_BYTES,fetch,inspect_one
from thai_benchmark import normalize

def poppler_first_page(data):
    if not data.startswith(b"%PDF-") or len(data)>MAX_BYTES:
        raise ValueError("Invalid PDF")
    exe=shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("Poppler unavailable")
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/"source.pdf"
        path.write_bytes(data)
        result=subprocess.run([exe,"-f","1","-l","1","-layout","-enc","UTF-8",str(path),"-"],
                              capture_output=True,check=True,timeout=30)
        if len(result.stdout)>2*1024*1024:
            raise ValueError("Text output exceeds limit")
        return result.stdout.decode("utf-8",errors="strict")

def compare(fetcher=fetch,extractor=poppler_first_page):
    rows=[]
    for sid,url,page,title in SOURCES:
        row={"source_id":sid}
        try:
            data=fetcher(url)
            base=inspect_one(data,title,page)
            row.update(base)
            try:
                text=extractor(data)
                row["poppler_title_match"]=normalize(title) in normalize(text)
                row["poppler_text_present"]=bool(text.strip())
                row["comparison_status"]="PILOT_COMPARISON_ONLY"
            except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as exc:
                row.update(comparison_status="BLOCKED_OR_FAILED",error_type=type(exc).__name__)
        except Exception as exc:
            row.update(comparison_status="BLOCKED_OR_FAILED",error_type=type(exc).__name__)
        rows.append(row)
    complete=[r for r in rows if r["comparison_status"]=="PILOT_COMPARISON_ONLY"]
    return {"status":"PUBLIC_TITLE_COMPARISON_ONLY","normalization":"NFC; whitespace removed",
            "sources":len(rows),"compared":len(complete),
            "pdfplumber_exact":sum(bool(r["title_exact_normalized_substring"]) for r in complete),
            "poppler_exact":sum(bool(r["poppler_title_match"]) for r in complete),
            "records":rows,"final_acceptance":False,
            "limitations":"Same first-page titles and exact matching as prior pilot. No extractor selection, no independent CER, OCR, table or semantic verification."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True);a=p.parse_args()
    report=compare();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))
    return 0 if report["compared"]==report["sources"] else 1
if __name__=="__main__":
    raise SystemExit(main())
