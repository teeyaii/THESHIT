"""Bounded public PDF first-page pilot. Not independent benchmark ground truth."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
import pdfplumber
from thai_benchmark import normalize

# Article titles and first printed page visually checked from publisher first pages.
# Attribution: publisher landing pages in docs/THAI_BENCHMARK.md (CC BY 4.0).
SOURCES=[
("THB01","https://so01.tci-thaijo.org/index.php/CMUJLSS/article/download/284261/183495/1234228",182,"การพัฒนาศาลยุติธรรมสู่ระบบดิจิทัล: แนวทางเชิงนโยบายและการบริหารงานยุติธรรม"),
("THB02","https://so01.tci-thaijo.org/index.php/CMUJLSS/article/download/282673/183498/1237411",205,"การเยียวยาความเสียหายในคดีคอลเซ็นเตอร์ตามพระราชบัญญัติป้องกันและปราบปรามการฟอกเงิน พ.ศ.2542"),
("THB03","https://so01.tci-thaijo.org/index.php/CMUJLSS/article/download/281941/183506/1234294",305,"ช่องว่างและข้อเสนอเพื่อพัฒนากรอบกฎหมายว่าด้วยการป้องกันการฟอกเขียวของประเทศไทยในประเด็นการกล่าวอ้างด้านสิ่งแวดล้อมที่ทำให้เข้าใจผิด: การวิเคราะห์เปรียบเทียบกับกรณีศึกษาของสหภาพยุโรป สหรัฐอเมริกา และสหราชอาณาจักร"),
("THB04","https://so02.tci-thaijo.org/index.php/edubuu/article/download/282795/188761/1314731",120,"การพัฒนาเกมแบบสถานการณ์จำลองเพื่อส่งเสริมการรู้ดิจิทัล สำหรับนักเรียนชั้นมัธยมศึกษาตอนปลาย"),
("THB05","https://so02.tci-thaijo.org/index.php/edubuu/article/download/282686/188760/1314730",103,"แนวทางการพัฒนาภาวะผู้นำดิจิทัลของครูในสหวิทยาเขตสตรีประเสริฐศิลป์ สังกัดสำนักงานเขตพื้นที่การศึกษามัธยมศึกษาจันทบุรี ตราด")]
MAX_BYTES=20*1024*1024

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

def fetch(url):
    if url not in {r[1] for r in SOURCES}:
        raise ValueError("Only fixed publisher sources permitted")
    request=Request(url,headers={"User-Agent":"THESHIT-public-research-benchmark/1.0","Accept":"application/pdf"})
    with build_opener(NoRedirect()).open(request,timeout=25) as response:
        data=response.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES or not data.startswith(b"%PDF-"):
        raise ValueError("PDF expected within size limit")
    return data

def inspect_one(data,title,printed_page):
    if not data.startswith(b"%PDF-") or len(data)>MAX_BYTES:
        raise ValueError("Invalid PDF input")
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        first=pdf.pages[0]
        text=first.extract_text() or ""
        return {"source_sha256":hashlib.sha256(data).hexdigest(),"total_pages":len(pdf.pages),
                "physical_page":1,"printed_page_visual_reference":printed_page,
                "native_text_present":bool(text.strip()),
                "title_exact_normalized_substring":normalize(title) in normalize(text),
                "status":"PILOT_METRICS_ONLY"}

def probe(fetcher=fetch):
    rows=[]
    for sid,url,page,title in SOURCES:
        try:
            row=inspect_one(fetcher(url),title,page)
        except Exception as exc:
            row={"status":"BLOCKED_OR_FAILED","error_type":type(exc).__name__}
        rows.append({"source_id":sid,**row})
    return {"status":"PUBLIC_FIRST_PAGE_PILOT_ONLY","records":rows,
            "limitations":"No PDF or page text exported. Title check and visual page reference only. No independent CER, table, OCR or printed-page extraction validation."}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    report=probe()
    p=Path(args.output);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8") as f:
        json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))
    return 0 if all(r["status"]=="PILOT_METRICS_ONLY" for r in report["records"]) else 1
if __name__=="__main__":
    raise SystemExit(main())
