"""Read-only offline HTML view of a verified synthetic bundle; no real data or live API."""
from html import escape
from pathlib import Path
from theshit_cli import verify_demo
from statistical_engine import LABEL

REPO="https://github.com/teeyaii/THESHIT"
LINKS=[
    ("GitHub Repository",REPO,"Source code and documentation"),
    ("Run synthetic demo",REPO+"/actions/workflows/core-demo.yml","Run workflow on GitHub with authorized account"),
    ("Open Source QA",REPO+"/actions/workflows/core-oss.yml","Dependency and security checks"),
    ("Thai OCR QA",REPO+"/actions/workflows/thai-ocr.yml","Synthetic OCR test"),
    ("Live discovery smoke",REPO+"/actions/workflows/discovery-live.yml","Fixed public metadata connectivity"),
    ("V1.0 release gates",REPO+"/issues/18","Pending validation and independent QA"),
]
def dashboard_html(qa):
    if qa.get("label")!=LABEL or qa.get("status")!="SYNTHETIC_E2E_PASS":
        raise ValueError("Only verified synthetic demo summary")
    files=qa["files_verified"];cells=qa["report_cells_verified_each_format"]
    if any(type(v) is not int or v<1 for v in (files,cells)):
        raise ValueError("Invalid counters")
    link_cards="".join(f'<a class="module" href="{escape(url,quote=True)}"><strong>{escape(title)}</strong><span>{escape(desc)}</span></a>'
                       for title,url,desc in LINKS)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>THESHIT — Synthetic control dashboard</title>
<style>
:root{{color-scheme:dark;--bg:#101216;--panel:#1b1f26;--ink:#f3f4f7;--muted:#abb4c3;--line:#333b47;--accent:#a6ebc9}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}}
main{{max-width:850px;margin:auto;padding:24px 18px 40px}}header{{display:flex;gap:14px;align-items:center;margin-bottom:26px}}
.logo{{font-weight:800;font-size:23px;background:#303843;border-radius:12px;padding:12px}}h1{{font-size:24px;margin:0}}p{{margin:6px 0;color:var(--muted)}}
.notice{{border:1px solid var(--line);border-radius:12px;padding:14px;margin:18px 0;overflow-wrap:anywhere}}
h2{{font-size:17px;margin:26px 0 10px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
.metric,.module{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;min-width:0}}
.metric b{{display:block;font-size:27px;color:var(--accent)}}.metric span,.module span{{display:block;color:var(--muted);font-size:14px}}
.module{{color:var(--ink);text-decoration:none;display:block;min-height:92px;overflow-wrap:anywhere}}.module:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}
footer{{margin-top:26px;color:var(--muted);font-size:13px}}@media(max-width:380px){{.grid{{grid-template-columns:1fr}}main{{padding:18px 14px}}}}
</style></head><body><main>
<header><div class="logo" aria-hidden="true">TS.</div><div><h1>THESHIT</h1><p>Research Operating System</p></div></header>
<div class="notice"><strong>{escape(LABEL)}</strong><p>Read-only snapshot of one verified synthetic run. Not live service status, not research findings.</p></div>
<h2>Verified demo output</h2><div class="grid">
<div class="metric"><span>Manifest files checked</span><b>{files}</b></div>
<div class="metric"><span>Table cells checked per format</span><b>{cells}</b></div>
</div>
<h2>Cloud control</h2><div class="grid">{link_cards}</div>
<footer>Actions open GitHub; this file cannot run jobs by itself. No sign-in, uploads, tracking, data intake, or real study processing. Final V1.0 acceptance remains pending.</footer>
</main></body></html>'''

def build(bundle,output):
    qa=verify_demo(bundle)
    target=Path(output)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("x",encoding="utf-8") as f:
        f.write(dashboard_html(qa))
    return {"status":"OFFLINE_SYNTHETIC_DASHBOARD_CREATED",
            "files_verified":qa["files_verified"],"cells_verified":qa["report_cells_verified_each_format"],
            "deployed":False,"mobile_visual_qa":"PENDING"}

def main():
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();print(json.dumps(build(a.bundle,a.output),indent=2))
if __name__=="__main__":
    main()
