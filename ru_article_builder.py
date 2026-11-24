"""Synthetic article structure with independent, explicitly unapproved layout."""
import hashlib
import json
from pathlib import Path
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm,Pt
from academic_writing import draft,verify_draft
from statistical_engine import LABEL
from report_engine import source_hash

PROFILE=Path(__file__).with_name("config")/"ru_article_profile.example.json"
NOTICE="SYNTHETIC ARTICLE STRUCTURE — NOT FOR SUBMISSION"

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def model(report):
    d=draft(report);verify_draft(report,d)
    sections=[
        ("Title","ตัวอย่างโครงสร้างบทความวิจัย / Synthetic article structure"),
        ("Author information","รอข้อมูลผู้เขียนที่ได้รับอนุญาต"),
        ("บทคัดย่อ","รอบทคัดย่อจากงานที่ได้รับอนุมัติ"),
        ("Abstract","Pending approved English abstract."),
        ("คำสำคัญ / Keywords","รอคำสำคัญจากงานที่ได้รับอนุมัติ"),
        ("ความเป็นมาและความสำคัญของปัญหา","รอเนื้อหาและหลักฐานที่ผ่านการตรวจ"),
        ("วัตถุประสงค์การวิจัย","รอวัตถุประสงค์ที่ได้รับอนุมัติ"),
        ("สมมติฐานการวิจัย","รอสมมติฐานที่ได้รับอนุมัติ"),
        ("ขอบเขตของการวิจัย","รอขอบเขตที่ได้รับอนุมัติ"),
        ("แนวคิด ทฤษฎี และงานวิจัยที่เกี่ยวข้อง","รอแหล่งอ้างอิงที่ผ่านการตรวจ ไม่จำกัดอายุงานเพียงอย่างเดียว"),
        ("วิธีการดำเนินการวิจัย","ต่อไปนี้เป็นวิธีทดสอบซอฟต์แวร์ ไม่ใช่วิธีวิจัยภาคสนาม"),
    ]
    sections.extend(("Methods fixture",p["text"]) for p in d["paragraphs"] if p["section"]=="Methods")
    sections.append(("การวิเคราะห์ข้อมูล","รอแผนการวิเคราะห์ที่ได้รับอนุมัติ"))
    sections.append(("ผลการวิจัย","ข้อมูลสังเคราะห์เพื่อทดสอบการแสดงผลเท่านั้น"))
    sections.extend(("Results fixture",p["text"]) for p in d["paragraphs"] if p["section"]=="Results")
    sections.extend([("อภิปรายผล","ระงับการอภิปรายจนกว่าจะมีผลจริงและหลักฐานที่ผ่านการตรวจ"),
                     ("ข้อจำกัด","ไม่ใช้ผลสังเคราะห์เป็นผลการวิจัย"),
                     ("ข้อเสนอแนะ","รอผลการวิจัยจริง"),
                     ("เอกสารอ้างอิง","ยังไม่มีแหล่งอ้างอิงที่ตรวจรับสำหรับบทความนี้")])
    return {"label":LABEL,"notice":NOTICE,"status":"SYNTHETIC_ARTICLE_STRUCTURE_ONLY",
            "source_sha256":source_hash(report),"sections":[list(r) for r in sections],
            "facts":d["facts"],"official_article_template_verified":False,
            "final_acceptance":False}

def build(report,output_dir):
    data=model(report)
    profile=json.loads(PROFILE.read_text(encoding="utf-8"))
    if profile["status"]!="SYNTHETIC_LAYOUT_ONLY" or profile["official_article_template_verified"]:
        raise ValueError("Only synthetic unapproved example layout enabled")
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=False)
    doc=Document()
    sec=doc.sections[0];sec.page_width=Mm(profile["paper_mm"][0]);sec.page_height=Mm(profile["paper_mm"][1])
    for side,mm in profile["margins_mm"].items():
        setattr(sec,side+"_margin",Mm(mm))
    for name,key,bold in [("RA Title","title_pt",True),("RA Heading","heading_pt",True),("RA Body","body_pt",False)]:
        s=doc.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        s.font.name=profile["font"];s.font.size=Pt(profile[key]);s.font.bold=bold
        pr=s._element.get_or_add_rPr()
        for attr in ("ascii","hAnsi","eastAsia","cs"):
            pr.rFonts.set(qn("w:"+attr),profile["font"])
        size=OxmlElement("w:szCs");size.set(qn("w:val"),str(profile[key]*2));pr.append(size)
        s.paragraph_format.line_spacing=profile["line_spacing"]
        s.paragraph_format.widow_control=True
        s.paragraph_format.keep_with_next=bold
    doc.core_properties.author="THESHIT synthetic fixture"
    sec.header.paragraphs[0].text=NOTICE
    sec.header.paragraphs[0].style=doc.styles["RA Body"]
    sec.footer.paragraphs[0].text=NOTICE
    sec.footer.paragraphs[0].style=doc.styles["RA Body"]
    expected=[[ "RA Title",NOTICE],["RA Body","Source SHA256: "+data["source_sha256"]]]
    for heading,body in data["sections"]:
        expected.extend([["RA Heading",heading],["RA Body",body]])
    for style,text in expected:
        doc.add_paragraph(text,style=style)
    path=out/"SYNTHETIC_RU_article.docx";doc.save(path)
    data.update(expected_paragraphs=expected,docx_sha256=digest(path),
                layout_profile_sha256=digest(PROFILE))
    (out/"SYNTHETIC_article_manifest.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return verify(out)

def verify(output_dir):
    out=Path(output_dir)
    m=json.loads((out/"SYNTHETIC_article_manifest.json").read_text(encoding="utf-8"))
    path=out/"SYNTHETIC_RU_article.docx"
    if m["label"]!=LABEL or m["official_article_template_verified"] or m["docx_sha256"]!=digest(path) or m["layout_profile_sha256"]!=digest(PROFILE):
        raise ValueError("Invalid article manifest or hash mismatch")
    doc=Document(path)
    if [[p.style.name,p.text] for p in doc.paragraphs]!=m["expected_paragraphs"]:
        raise ValueError("Article content/style mismatch")
    if doc.sections[0].header.paragraphs[0].text!=NOTICE or doc.sections[0].footer.paragraphs[0].text!=NOTICE:
        raise ValueError("Missing synthetic markers")
    return {"status":"SYNTHETIC_ARTICLE_STRUCTURE_QA_PASS","paragraphs_checked":len(doc.paragraphs),
            "facts_in_manifest":len(m["facts"]),"official_article_template_verified":False,
            "word_visual_qa":"NOT_EXECUTED","final_acceptance":False}
