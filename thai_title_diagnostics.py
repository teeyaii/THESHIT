"""Character-distance diagnostics for the fixed public title pilot, not full-page CER."""
import argparse
import io
import json
from pathlib import Path
import pdfplumber
from thai_benchmark import normalize
from thai_public_probe import SOURCES,fetch,inspect_one
from thai_extraction_comparison import poppler_first_page

def nearest_substring_distance(reference,page_text):
    a,b=normalize(reference),normalize(page_text)
    if not a or len(a)*len(b)>25_000_000:
        raise ValueError("Nonempty bounded reference required")
    # Free prefix/suffix of the extracted page; compare the nearest contiguous substring.
    prev=[0]*(len(b)+1)
    for i,c in enumerate(a,1):
        row=[i]
        for j,d in enumerate(b,1):
            row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+(c!=d)))
        prev=row
    return min(prev)

def diagnostic(fetcher=fetch,poppler=poppler_first_page):
    records=[]
    for sid,url,page,title in SOURCES:
        row={"source_id":sid}
        try:
            data=fetcher(url)
            base=inspect_one(data,title,page)
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                native=pdf.pages[0].extract_text() or ""
            other=poppler(data)
            n=len(normalize(title))
            row.update(source_sha256=base["source_sha256"],physical_page=1,
                       reference_character_count=n,status="TITLE_DIAGNOSTIC_ONLY",
                       pdfplumber_min_edits=nearest_substring_distance(title,native),
                       poppler_min_edits=nearest_substring_distance(title,other))
            for key in ("pdfplumber","poppler"):
                row[key+"_relative_distance"]=row[key+"_min_edits"]/n
        except Exception as exc:
            row.update(status="BLOCKED_OR_FAILED",error_type=type(exc).__name__)
        records.append(row)
    return {"status":"PUBLIC_TITLE_DIAGNOSTIC_ONLY","records":records,
            "complete":sum(r["status"]=="TITLE_DIAGNOSTIC_ONLY" for r in records),
            "final_acceptance":False,
            "limitations":"Minimum edit distance to any substring of first page, optimistic diagnostic not independent CER. Exact baseline not replaced. No text reconstruction or normalization beyond NFC/whitespace. No raw source text exported."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True);a=p.parse_args()
    r=diagnostic();path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f:json.dump(r,f,indent=2)
    print(json.dumps(r,indent=2))
    return 0 if r["complete"]==len(SOURCES) else 1
if __name__=="__main__":
    raise SystemExit(main())
