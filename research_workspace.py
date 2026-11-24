"""Offline, read-only navigation for a verified synthetic rehearsal bundle."""
import argparse
import json
from html import escape
from pathlib import Path
from urllib.parse import quote
from full_rehearsal import verify
from statistical_engine import LABEL

REPO="https://github.com/teeyaii/THESHIT"
LINKS=[
    ("โครงเล่ม 5 บท","SYNTHETIC_integrated_thesis.docx","ตัวอย่างสังเคราะห์ — ยังไม่ได้ตรวจ Word จริง"),
    ("บทความวิจัย","computed_outputs/article/SYNTHETIC_RU_article.docx","แม่แบบบทความฉบับจริงยังไม่ยืนยัน"),
    ("ตารางสถิติ Excel","computed_outputs/report/SYNTHETIC_tables.xlsx","ข้อมูลสังเคราะห์"),
    ("PDF ตัวอย่าง","computed_outputs/pdf/SYNTHETIC_preview.pdf","PDF แยกจากเล่ม ไม่ใช่ Word final"),
    ("ภาพหลักฐาน","highlights/E1_001_candidate_highlight.png","หลักฐานจำลอง"),
    ("ทะเบียนอ้างอิง","references/REFERENCE_DRAFT.docx","รายการตัวอย่าง ไม่ใช่แหล่งจริง"),
    ("ตารางทบทวนวรรณกรรม","notes/literature_notes_review.csv","บันทึกตัวอย่าง"),
    ("ผลตรวจอ้างอิง","claim_qa.json","ตรวจความเชื่อมโยงตามรายการที่กำหนด"),
    ("ผลตรวจสี","color_qa.json","ตรวจเฉพาะโครงสร้าง"),
    ("ผลตรวจ Style","computed_outputs/SYNTHETIC_style_inventory.json","มีรายการที่ยังต้องยืนยัน"),
    ("รายการตรวจรับ","computed_outputs/release_gate_unattested.json","ยังไม่รับรอง V1.0"),
    ("Manifest","REHEARSAL_MANIFEST.json","รายการ hash ของไฟล์ในชุด"),
]

def build(bundle,output):
    root=Path(bundle).resolve();out=Path(output).resolve()
    if out.parent!=root.parent or out.suffix.lower()!=".html" or out.exists():
        raise ValueError("New HTML beside the bundle required")
    qa=verify(root)
    if qa["label"]!=LABEL or qa["status"]!="INTEGRATED_SYNTHETIC_REHEARSAL_PASS":
        raise ValueError("Only verified synthetic rehearsal")
    rc=qa["computed_outputs"]
    if qa["release_status"]!="BLOCKED" or qa["final_acceptance"] is not False:
        raise ValueError("Unexpected release state")
    manifest=json.loads((root/"REHEARSAL_MANIFEST.json").read_text(encoding="utf-8"))
    metrics=[("ไฟล์ที่ตรวจ hash",len(manifest["files"])),
             ("โครงสร้างบท",rc["thesis"]["chapters"]),
             ("เซลล์ต่อรูปแบบ",rc["report"]["cells_verified_each_format"]),
             ("อักขระไฮไลต์",qa["color_characters_verified"]),
             ("Style ที่ต้องยืนยัน",rc["style_counts"]["UNRESOLVED"])]
    for _,v in metrics:
        if type(v) is not int or v<0:raise ValueError("Invalid metric")
    cards="".join(f'<div class="metric"><span>{escape(label)}</span><strong>{v}</strong></div>' for label,v in metrics)
    links=[]
    for title,rel,desc in LINKS:
        target=root/rel
        if not target.is_file():continue
        href=quote(root.name,safe="")+"/"+quote(rel,safe="/")
        links.append(f'<a class="module" href="{escape(href,quote=True)}"><strong>{escape(title)}</strong><span>{escape(desc)}</span></a>')
    html=f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>THESHIT Research Workspace</title>
<style>
:root{{color-scheme:dark;--bg:#101216;--panel:#1c2129;--ink:#f5f6f8;--muted:#c0c7d2;--line:#39434f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}
main{{max-width:860px;margin:auto;padding:22px 16px 40px}}h1{{font-size:28px;margin:0}}h2{{font-size:18px;margin:26px 0 10px}}
p{{margin:6px 0;color:var(--muted)}}.notice{{border:1px solid var(--line);border-radius:12px;padding:14px;margin:18px 0;overflow-wrap:anywhere}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}
.metric,.module{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;min-width:0;overflow-wrap:anywhere}}
.metric strong{{display:block;font-size:28px}}.metric span,.module span{{display:block;color:var(--muted);font-size:14px}}
.module{{color:var(--ink);text-decoration:none;display:block;min-height:88px}}
a:focus-visible{{outline:3px solid white;outline-offset:3px}}footer{{margin-top:24px;color:var(--muted);font-size:14px}}
@media(max-width:360px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>THESHIT</h1><p>Research Workspace · RU MBA 2569</p>
<div class="notice"><strong>{escape(LABEL)}</strong><p>ชุดทดสอบออฟไลน์เท่านั้น ไม่ใช่ผลวิจัยจริงหรือสถานะสด</p>
<p>Release: BLOCKED · Word visual QA: NOT_EXECUTED</p>
<p>Commit: {escape(qa["commit_sha"])}</p></div>
<h2>ผลตรวจจากชุดไฟล์นี้</h2><div class="grid">{cards}</div>
<h2>เอกสารและหลักฐาน</h2><div class="grid">{"".join(links)}</div>
<h2>ควบคุมงานผ่าน GitHub</h2><div class="grid">
<a class="module" href="{REPO}/actions"><strong>GitHub Actions</strong><span>ตรวจและรัน workflow ด้วยบัญชีที่ได้รับสิทธิ์</span></a>
<a class="module" href="{REPO}/issues/18"><strong>Release backlog</strong><span>งานตรวจรับที่ยังไม่ปิด</span></a></div>
<footer>เปิด HTML พร้อมโฟลเดอร์ชุดทดสอบที่อยู่ข้างกัน ลิงก์ไฟล์ขึ้นอยู่กับเบราว์เซอร์หรือแอปที่เปิด ไม่มีการอัปโหลดข้อมูล การเข้าสู่ระบบ สคริปต์ หรือบริการประมวลผลในหน้านี้ ยังไม่ได้ทดสอบบน iPhone จริง</footer>
</main></body></html>"""
    with out.open("x",encoding="utf-8") as f:f.write(html)
    return {"status":"OFFLINE_WORKSPACE_CREATED","links":len(links),"files_verified":len(manifest["files"]),
            "release_status":"BLOCKED","deployed":False,"iphone_visual_qa":"NOT_EXECUTED"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();print(json.dumps(build(a.bundle,a.output),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
