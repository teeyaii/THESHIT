import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from pdf_limits import MAX_PDF_BYTES,MAX_SOURCE_PAGES,ResourceLimitError,checked_pages,run_bounded
from evidence_engine import candidate_atlas
from pdf_text_engine import extract_pdf,_extract_pdf
from oss_adapters import pdf_text_matches
from test_oss_adapters import tiny_pdf

class PDFLimitTests(unittest.TestCase):
    def test_oversized_local_pdf_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/"large.pdf"
            with p.open("wb") as f:f.write(b"%PDF-1.4\n");f.truncate(MAX_PDF_BYTES+1)
            with self.assertRaises(ResourceLimitError):extract_pdf(p)
            with self.assertRaises(ResourceLimitError):pdf_text_matches(p,"phrase")
            # Source and output are separate; a blocked record cannot become a candidate.
            src=root/"source";src.mkdir();p.rename(src/p.name)
            qa=candidate_atlas([{"evidence_id":"E1","source_file":p.name,"phrase":"phrase"}],src,root/"atlas")
            self.assertEqual(qa["records"][0]["status"],"RESOURCE_LIMIT")
            self.assertEqual(qa["records"][0]["hits"],[])
            self.assertFalse(list((root/"atlas").glob("*.png")))

    def test_page_count_limit(self):
        with self.assertRaises(ResourceLimitError):
            checked_pages(SimpleNamespace(pages=[None]*(MAX_SOURCE_PAGES+1)))
        with self.assertRaises(ResourceLimitError):
            checked_pages(SimpleNamespace(pages=[]))
        self.assertEqual(len(checked_pages(SimpleNamespace(pages=[None]))),1)

    def test_worker_timeout_and_invalid_operation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.pdf";tiny_pdf(p)
            with self.assertRaisesRegex(ResourceLimitError,"wall-clock"):
                run_bounded("extract",{"path":str(p),"ocr":False},timeout=0.001)
        with self.assertRaises(ValueError):
            run_bounded("unknown",{})

    def test_worker_timeout_does_not_publish_partial_atlas(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=root/"source";src.mkdir();out=root/"atlas"
            def partial(operation,kwargs,timeout):
                staged=Path(kwargs["output_dir"]);staged.mkdir()
                (staged/"partial.png").write_bytes(b"partial")
                raise ResourceLimitError("timeout")
            with patch("evidence_engine.run_bounded",side_effect=partial):
                with self.assertRaises(ResourceLimitError):
                    candidate_atlas([],src,out)
            self.assertFalse(out.exists())
            self.assertFalse(list(root.glob(".atlas-*")))

    def test_missing_tsv_configuration_status(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.pdf";tiny_pdf(p)
            cap={"available":True,"languages":["tha","eng"],"version":"fixture"}
            with patch("pdf_text_engine.ocr_capabilities",return_value=cap), patch("pdf_text_engine.shutil.which",return_value="/fixture/tesseract"), patch("pdf_text_engine.subprocess.run",return_value=SimpleNamespace(stdout="plain OCR text")):
                result=_extract_pdf(p,force_ocr=True)
            self.assertEqual(result["pages"][0]["status"],"OCR_CONFIGURATION_ERROR")
            self.assertEqual(result["pages"][0]["words"],[])
