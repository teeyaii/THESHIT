"""One bounded public-topic request per provider. No private queries or raw payload export."""
import argparse
import json
from pathlib import Path
from research_discovery import discover,normalize_doi,STATUS

QUERY="open access scholarly communication"

def smoke(fetch=None):
    results={}
    for provider in ("crossref","openalex"):
        kwargs={"provider":provider,"limit":2}
        if fetch is not None:
            kwargs["fetch"]=fetch
        if provider=="openalex":
            kwargs["allow_anonymous"]=True
        try:
            rows=discover(QUERY,**kwargs)
            if not rows or not all(r["provider"]==provider and r["status"]==STATUS for r in rows):
                raise ValueError("Unexpected metadata")
            if not any(r.get("title") and normalize_doi(r.get("doi")) for r in rows):
                raise ValueError("No title and DOI metadata pair")
            results[provider]={"status":"PASS","count":len(rows),
                               "title_doi_pairs":sum(bool(r.get("title") and normalize_doi(r.get("doi"))) for r in rows)}
        except (RuntimeError,ValueError,KeyError,TypeError,OSError) as exc:
            results[provider]={"status":"BLOCKED_OR_FAILED","error_type":type(exc).__name__}
    return {"mode":"MOCK" if fetch is not None else "LIVE_PUBLIC_METADATA",
            "providers":results,"limitations":"Connectivity and metadata shape only; no claim or full text verified."}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=smoke()
    path=Path(args.output)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
    return 0 if all(r["status"]=="PASS" for r in result["providers"].values()) else 1

if __name__=="__main__":
    raise SystemExit(main())
