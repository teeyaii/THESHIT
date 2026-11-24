"""RU MBA working-profile synthetic thesis skeleton. Never an empirical thesis."""
import hashlib
import json
from pathlib import Path
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt
from ru_format_audit import get_profile
from academic_writing import draft,verify_draft
from statistical_engine import LABEL
from report_engine import source_hash

PROFILE="ru_mba_campus_2569_working"
NOTICE="SYNTHETIC ONLY — NOT FOR ACADEMIC SUBMISSION"
CHAPTERS=[("1","บทนำ"),("2","แนวคิด ทฤษฎี และงานวิจัยที่เกี่ยวข้อง"),
          ("3","วิธีดำเนินการวิจัย"),("4","ผลการวิเคราะห์ข้อมูล"),
          ("5","สรุปผล อภิปรายผล และข้อเสนอแนะ")]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def element(tag,**attrs):
    e=OxmlElement("w:"+tag)
    for k,v in attrs.items():
        e.set(qn("w:"+k),str(v))
    return e

def font_props(style,font,size,bold=False):
    style.font.name=font;style.font.size=Pt(size);style.font.bold=bold
    pr=style._element.get_or_add_rPr()
    for slot in ("ascii","hAnsi","eastAsia","cs"):
        pr.rFonts.set(qn("w:"+slot),font)
    pr.append(element("szCs",val=round(size*2)))
    pr.append(element("bCs",val=1 if bold else 0))
    pr.append(element("lang",val="th-TH",bidi="th-TH"))

def make_styles(doc,profile):
    font=profile["body"]["font"];body=profile["body"]["size_pt"]
    specs={"RU Body":(body,False),"RU Chapter":(profile["chapter_size_pt"],profile["chapter_bold"]),
           "RU Front":(22,True),"RU TOC Title":(profile["toc_title_pt"],True),"RU Bibliography Title":(profile["bibliography_pt"],True),"RU Subheading":(profile["heading_sizes_pt"][0],profile["heading_bold"]), "RU Subheading 2":(profile["heading_sizes_pt"][1],profile["heading_bold"]),
           "RU Table":(body,False),"RU Caption":(body,False),
           "RU Reference":(profile["bibliography_pt"],False),
           "RU Appendix":(profile["appendix_divider_pt"],True),
           "RU Notice":(body,True)}
    for name,(size,bold) in specs.items():
        s=doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        font_props(s,font,size,bold)
        p=s.paragraph_format
        # Preview conventions only; spacing awaits approved current template.
        p.space_before=Pt(0);p.space_after=Pt(0);p.line_spacing=1.0
        p.widow_control=True;p.keep_with_next=False;p.keep_together=False
        p.first_line_indent=Mm(profile["body"]["first_line_mm"] if name=="RU Body" else 0)
        p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        if name in ("RU Chapter","RU Front","RU TOC Title","RU Bibliography Title","RU Appendix"):
            p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.keep_with_next=True;p.keep_together=True;p.page_break_before=True
        if name in ("RU Subheading","RU Subheading 2"):
            p.keep_with_next=True;p.keep_together=True
        if name in ("RU Chapter","RU Subheading","RU Subheading 2"):
            s._element.get_or_add_pPr().append(element("outlineLvl",val=0 if name=="RU Chapter" else (1 if name=="RU Subheading" else 2)))

def field(paragraph,instruction,placeholder):
    r=paragraph.add_run()
    r._r.append(element("fldChar",fldCharType="begin",dirty="true"))
    instr=element("instrText")
    instr.set("{http://www.w3.org/XML/1998/namespace}space","preserve")
    instr.text=" "+instruction+" "
    r._r.append(instr)
    r._r.append(element("fldChar",fldCharType="separate"))
    t=element("t");t.text=placeholder;r._r.append(t)
    r._r.append(element("fldChar",fldCharType="end"))

def set_section(sec,profile):
    sec.page_width=Mm(profile["paper_mm"][0]);sec.page_height=Mm(profile["paper_mm"][1])
    sec.left_margin=Mm(profile["margins_mm"]["left"])
    sec.right_margin=Mm(profile["margins_mm"]["right"])
    sec.bottom_margin=Mm(profile["margins_mm"]["bottom"])
    # One uniform numbered-page margin is a provisional preview convention.
    sec.top_margin=Mm(profile["margins_mm"]["top_by_role"]["numbered_page"])
    sec.header_distance=Mm(12.7);sec.footer_distance=Mm(12.7)

def plan(report):
    d=draft(report);verify_draft(report,d)
    return {"label":LABEL,"profile":PROFILE,"source_sha256":source_hash(report),
            "chapters":[{"number":n,"title":t} for n,t in CHAPTERS],
            "numeric_draft":d,
            "pending":["Current approved 2569 Word template and remaining manual reconciliation",
                       "Independent source review and study protocol",
                       "Actual licensed fonts and full Microsoft Word visual QA",
                       "TOC, page fields, section-specific margins, references and academic review"],
            "final_acceptance":False}

def build(report,output_dir):
    p=plan(report);profile=get_profile(PROFILE)
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=False)
    doc=Document();make_styles(doc,profile);set_section(doc.sections[0],profile)
    doc.core_properties.title="THESHIT synthetic RU MBA structure"
    doc.core_properties.author="THESHIT synthetic fixture"
    doc.sections[0].header.paragraphs[0].text=NOTICE
    doc.sections[0].header.paragraphs[0].style=doc.styles["RU Notice"]
    expected=[]
    def add(text,style="RU Body"):
        expected.append([style,text])
        return doc.add_paragraph(text,style=style)
    title=add(NOTICE,"RU Notice");title.alignment=WD_ALIGN_PARAGRAPH.CENTER
    add("โครงสร้างการค้นคว้าอิสระ มหาวิทยาลัยรามคำแหง (ตัวอย่างระบบ)","RU Front").paragraph_format.page_break_before=False
    add("Working profile 2569 — ยังไม่ใช่แม่แบบที่อนุมัติ")
    add("ปกใน / ปกรอง","RU Front")
    add("ตำแหน่งข้อมูลตามแม่แบบที่ได้รับอนุมัติ")
    add("คำปฏิญาณตน","RU Front")
    add("รอผู้วิจัยตรวจและลงนามด้วยตนเอง ไม่สร้างคำรับรองหรือลายเซ็น")
    add("บทคัดย่อ","RU Front")
    add("รอข้อความบทคัดย่อภาษาไทยจากงานวิจัยจริงที่ได้รับอนุมัติ")
    add("Abstract","RU Front")
    add("English abstract pending approved research.")
    add("กิตติกรรมประกาศ","RU Front")
    add("รอข้อความจากผู้วิจัย")
    add("สารบัญ","RU TOC Title")
    toc=doc.add_paragraph(style="RU Body")
    field(toc,'TOC \\t "RU Chapter,1,RU Subheading,2,RU Subheading 2,3" \\h \\z',"TOC PENDING WORD UPDATE")
    add("สารบัญตาราง","RU Front")
    add("รออัปเดตสารบัญตารางใน Word")
    add("สารบัญภาพ","RU Front")
    add("รออัปเดตสารบัญภาพใน Word")
    # Field placeholder is not an accepted table of contents.
    main=doc.add_section(WD_SECTION_START.NEW_PAGE)
    set_section(main,profile)
    main.header.is_linked_to_previous=False
    head=main.header.paragraphs[0];head.style=doc.styles["RU Notice"];head.text=NOTICE
    main.footer.is_linked_to_previous=False
    foot=main.footer.paragraphs[0];foot.style=doc.styles["RU Notice"];foot.text=NOTICE
    field(head,"PAGE","PAGE PENDING")
    for n,t in CHAPTERS:
        heading=add("บทที่ "+n+"\n"+t,"RU Chapter")
        if n=="1":heading.paragraph_format.page_break_before=False
        if n in ("1","2","3"):
            add("ส่วนนี้เป็นตำแหน่งสำหรับเนื้อหาที่ได้รับอนุมัติ ยังไม่มีข้อค้นพบหรือแหล่งอ้างอิงจริง")
        if n=="4":
            add("ผลทดสอบสังเคราะห์เท่านั้น ไม่ใช่ผลวิจัย","RU Subheading")
            for item in p["numeric_draft"]["paragraphs"]:
                if item["section"]=="Results":
                    add(item["text"])
            add("ตารางตัวอย่างค่าประมาณจากข้อมูลสังเคราะห์","RU Caption")
            rows=[["Variable","B","HC3 p"]]+[[r["variable"],format(r["b"],".8g"),format(r["hc3_p"],".8g")]
                                             for r in report["model"]["coefficients"]]
            table=doc.add_table(rows=len(rows),cols=3)
            table.style="Table Grid"
            table.rows[0]._tr.get_or_add_trPr().append(element("tblHeader",val="true"))
            for i,row in enumerate(rows):
                for j,value in enumerate(row):
                    para=table.cell(i,j).paragraphs[0];para.style=doc.styles["RU Table"];para.text=value
        if n=="5":
            add("การอภิปรายผลถูกระงับจนกว่าจะมีหลักฐานและผลการศึกษาจริงที่ผ่านการตรวจรับ")
    add("บรรณานุกรม","RU Bibliography Title")
    add("ยังไม่มีรายการอ้างอิงที่ได้รับการตรวจรับ ไม่สร้างรายการอ้างอิงสมมติ","RU Reference")
    add("ภาคผนวก","RU Appendix")
    add("รอเอกสารที่ได้รับอนุมัติ ไม่มีแบบสอบถามหรือข้อมูลบุคคลในตัวอย่างนี้")
    add("แบบเปิดเผยการใช้ AI — รอแบบจริงและการยืนยันโดยผู้วิจัย","RU Subheading")
    add("ประวัติผู้เขียน","RU Front")
    add("รอข้อมูลที่ได้รับอนุญาต ไม่สร้างประวัติสมมติ")
    doc.settings.element.append(element("updateFields",val="true"))
    target=out/"SYNTHETIC_RU_structure.docx";doc.save(target)
    manifest={"label":LABEL,"notice":NOTICE,"profile":PROFILE,"source_sha256":p["source_sha256"],
              "expected_paragraphs":expected,"table_rows":rows,"docx_sha256":sha(target),
              "pending":p["pending"],"final_acceptance":False}
    (out/"SYNTHETIC_structure_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    return verify(out)

def verify(output_dir):
    out=Path(output_dir)
    manifest=json.loads((out/"SYNTHETIC_structure_manifest.json").read_text(encoding="utf-8"))
    path=out/"SYNTHETIC_RU_structure.docx"
    if manifest["label"]!=LABEL or manifest["profile"]!=PROFILE or manifest["docx_sha256"]!=sha(path):
        raise ValueError("Synthetic structure provenance mismatch")
    doc=Document(path)
    actual=[[p.style.name,p.text] for p in doc.paragraphs if p.text.strip() and p.text!="TOC PENDING WORD UPDATE"]
    if actual!=manifest["expected_paragraphs"]:
        raise ValueError("Paragraph text/style mismatch")
    if len(doc.tables)!=1 or [[c.text for c in r.cells] for r in doc.tables[0].rows]!=manifest["table_rows"]:
        raise ValueError("Table mismatch")
    chapters=[p for p in doc.paragraphs if p.style.name=="RU Chapter"]
    if [p.text for p in chapters]!=["บทที่ "+n+"\n"+t for n,t in CHAPTERS]:
        raise ValueError("Chapter order mismatch")
    profile=get_profile(PROFILE)
    for name,size in (("RU Body",profile["body"]["size_pt"]),("RU Chapter",profile["chapter_size_pt"])):
        style=doc.styles[name]
        rpr=style._element.rPr
        if style.font.name!=profile["body"]["font"] or style.font.size.pt!=size or rpr.rFonts.get(qn("w:cs"))!=profile["body"]["font"] or rpr.find(qn("w:szCs")).get(qn("w:val"))!=str(size*2):
            raise ValueError("Named style font mismatch")
    if doc.styles["RU Chapter"].paragraph_format.page_break_before is not True:
        raise ValueError("Chapter break rule missing")
    instructions=[(x.text or "").strip() for x in doc._element.iter(qn("w:instrText"))]
    if not any(x.startswith("TOC ") for x in instructions):
        raise ValueError("TOC field missing")
    if len(doc.sections)!=2:
        raise ValueError("Front/main section count mismatch")
    return {"status":"SYNTHETIC_STRUCTURE_QA_PASS","chapters":len(chapters),
            "paragraphs_checked":len(actual),"table_rows_checked":len(manifest["table_rows"]),
            "profile":PROFILE,"docx_sha256":sha(path),"toc_status":"FIELD_PRESENT_NOT_UPDATED",
            "word_visual_qa":"NOT_EXECUTED","final_acceptance":False}

def demo_report():
    import numpy as np
    import pandas as pd
    from statistical_engine import analyze
    rng=np.random.default_rng(2569);x=rng.normal(size=(64,2))
    return analyze(pd.DataFrame({"x1":x[:,0],"x2":x[:,1],
                               "y":0.5*x[:,0]-0.3*x[:,1]+rng.normal(size=64)}),
                   ["x1","x2"],"y",source_label=LABEL)

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["demo","verify"]);p.add_argument("--output",required=True)
    a=p.parse_args()
    print(json.dumps(build(demo_report(),a.output) if a.command=="demo" else verify(a.output),indent=2))
if __name__=="__main__":
    main()
