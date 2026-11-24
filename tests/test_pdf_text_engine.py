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

    def test_r41_01_word_confidence_boundaries(self):
        header="level\tleft\ttop\twidth\theight\tconf\ttext\n"
        # Tesseract non-word structural rows commonly have confidence -1.
        self.assertEqual(parse_tsv(header+"1\t0\t0\t10\t12\t-1\t\n"),[])
        self.assertEqual(parse_tsv(header+"5\t2\t3\t10\t12\t-1\t\n"),[])
        for value in ("0","100","92.1"):
            with self.subTest(value=value):
                words=parse_tsv(header+"5\t2\t3\t10\t12\t"+value+"\tword\n")
                self.assertEqual(words[0]["confidence"],float(value))
        for value in ("150","100.01","-0.01","-1","nan","inf","-inf","1e309"):
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,"Invalid OCR word confidence"):
                parse_tsv(header+"5\t2\t3\t10\t12\t"+value+"\tword\n")

    @unittest.skipUnless(os.name=="posix","Executable fixture uses POSIX shell")
    def test_r41_01_extract_entrypoint_rejects_invalid_confidence(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/"fixture.pdf";tiny_pdf(path);before=sha(path)
            binary=root/"tesseract"
            binary.write_text(
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                " --version) echo 'tesseract test fixture';;\n"
                " --list-langs) printf 'List of available languages (2):\\neng\\ntha\\n';;\n"
                " *) printf 'level\\tleft\\ttop\\twidth\\theight\\tconf\\ttext\\n5\\t2\\t3\\t10\\t12\\t95\\tvalid\\n5\\t2\\t3\\t10\\t12\\t%s\\tword\\n' \"$THESHIT_TEST_CONF\";;\n"
                "esac\n",encoding="utf-8")
            binary.chmod(0o755)
            for value in ("150","-1","nan","inf","-inf","100","0"):
                with self.subTest(value=value),patch.dict(os.environ,{"PATH":str(root)+os.pathsep+os.environ.get("PATH",""),"THESHIT_TEST_CONF":value}):
                    result=extract_pdf(path,force_ocr=True)
                    row=result["pages"][0]
                    if value in ("100","0"):
                        self.assertEqual(row["status"],"OCR_CANDIDATE_UNVERIFIED")
                        self.assertEqual(row["words"][1]["confidence"],float(value))
                    else:
                        self.assertEqual(row["status"],"OCR_EXTRACTION_ERROR")
                        self.assertEqual(row["words"],[])
                        self.assertEqual(row["text"],"")
                    self.assertEqual(result["source_sha256"],before)
                    self.assertEqual(sha(path),before)
