import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from pdf_text_engine import extract_pdf,ocr_capabilities,parse_tsv,sha,OCRConfigurationError
from test_oss_adapters import tiny_pdf

class PDFTextTests(unittest.TestCase):
    def test_native_text(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"fixture.pdf";tiny_pdf(path)
            before=sha(path)
            result=extract_pdf(path,ocr=False)
            self.assertEqual(result["pages"][0]["status"],"TEXT_LAYER_CANDIDATE")
            self.assertIn("SYNTHETIC evidence test",result["pages"][0]["text"])
            self.assertEqual(before,sha(path))
            self.assertTrue(result["review_required"])

    def test_tsv(self):
        header="level\tleft\ttop\twidth\theight\tconf\ttext\n"
        words=parse_tsv(header+"5\t2\t3\t10\t12\t92.1\tภาษาไทย\n")
        self.assertEqual(words[0]["pixel_bbox"],[2,3,12,15])
        self.assertEqual(words[0]["text"],"ภาษาไทย")

    def test_thai_ocr_integration(self):
        required=os.environ.get("THESHIT_REQUIRE_THAI_OCR")=="1"
        cap=ocr_capabilities()
        if not cap["available"] or not {"tha","eng"}.issubset(cap["languages"]) or not shutil.which("fc-match"):
            if required:
                self.fail("Required Thai OCR engine/language/font discovery unavailable")
            self.skipTest("Optional Thai OCR runtime not installed")
        fontpath=subprocess.check_output(["fc-match","-f","%{file}","Noto Sans Thai"],text=True)
        if "NotoSansThai" not in fontpath.replace(" ",""):
            if required:
                self.fail("Noto Sans Thai fixture font unavailable")
            self.skipTest("Optional Thai font unavailable")
        with tempfile.TemporaryDirectory() as d:
            img=Image.new("RGB",(1200,360),"white")
            font=ImageFont.truetype(fontpath,88)
            draw=ImageDraw.Draw(img)
            draw.text((90,70),"ภาษาไทย",font=font,fill="black")
            path=Path(d)/"fixture.pdf"
            img.save(path,resolution=200)
            r=extract_pdf(path,dpi=200)
            self.assertEqual(r["pages"][0]["status"],"OCR_CANDIDATE_UNVERIFIED")
            self.assertIn("ภาษาไทย",r["pages"][0]["text"].replace(" ",""))
            self.assertTrue(r["pages"][0]["words"])
            self.assertEqual(r["source_sha256"],sha(path))

    def test_codex_s3_invalid_header_distinguished_from_empty_page(self):
        for value in ("","ภาษาไทย\n","level\ttext\n5\tfoo\n"):
            with self.assertRaises(OCRConfigurationError):parse_tsv(value)
        header="level\tleft\ttop\twidth\theight\tconf\ttext\n"
        self.assertEqual(parse_tsv(header),[])
        with self.assertRaisesRegex(ValueError,"Malformed"):
            parse_tsv(header+"5\t2\t3\n")
