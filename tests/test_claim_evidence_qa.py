import tempfile
import unittest
from pathlib import Path
from docx import Document
from evidence_engine import candidate_atlas,digest
from evidence_review import canonical_hash
from document_coverage import inventory
from claim_evidence_qa import reconcile
from test_oss_adapters import tiny_pdf

class ClaimTests(unittest.TestCase):
    def fixture(self,root):
        sources=root/"sources";sources.mkdir()
        tiny_pdf(sources/"fixture.pdf")
        exact="Synthetic claim"
        d=Document();text=exact+" (Fixture, 2003)";d.add_paragraph(text)
        path=root/"fixture.docx";d.save(path)
        idx=candidate_atlas([{"evidence_id":"E1","source_file":"fixture.pdf","phrase":"evidence test","claim":exact}],sources,root/"crops")
        row=idx["records"][0];hit=row["hits"][0]
        decisions=[{"evidence_id":"E1","reviewer_id":who,"record_sha256":canonical_hash(row),
                    "decision":"SUPPORTS","rationale":"Synthetic test attestation","full_context_reviewed":True,
                    "source_sha256":row["source_sha256"],"physical_page":hit["physical_page"],
                    "source_excerpt":hit["matched_text"],"candidate_image_sha256":hit["image_sha256"]}
                   for who in ("fixture-a","fixture-b")]
        m={"document_sha256":inventory(path)["source_sha256"],"references":[{"reference_id":"R1","title":"Synthetic reference","year":2003,"metadata_review_status":"REVIEWED","source_sha256":row["source_sha256"]}],
           "citations":[{"citation_id":"C1","part":"word/document.xml","paragraph":0,"start":text.index("("),"end":len(text),"exact_text":"(Fixture, 2003)","reference_ids":["R1"],"claim_review_status":"REVIEWED"}]}
        links=[{"claim_id":"CL1","part":"word/document.xml","paragraph":0,"start":0,"end":len(exact),"exact_text":exact,
                "citation_ids":["C1"],"evidence_ids":["E1"],"evidence_record_sha256":{"E1":canonical_hash(row)},"evidence_reference_ids":{"E1":"R1"}}]
        return path,m,idx,decisions,links,sources,root/"crops"

    def test_chain_and_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d))
            qa=reconcile(*args)
            self.assertTrue(qa["declared_links_consistent"]);self.assertFalse(qa["final_acceptance"])
            row=args[2]["records"][0];crop=args[-1]/row["hits"][0]["image"]
            crop.write_bytes(b"altered")
            self.assertFalse(reconcile(*args)["declared_links_consistent"])
    def test_disagreement_and_wrong_source(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d))
            args[3][1]["decision"]="PARTIAL"
            self.assertFalse(reconcile(*args)["declared_links_consistent"])
            args[3][1]["decision"]="SUPPORTS"
            args[1]["references"][0]["source_sha256"]="0"*64
            self.assertFalse(reconcile(*args)["declared_links_consistent"])
    def test_stale_link(self):
        with tempfile.TemporaryDirectory() as d:
            args=self.fixture(Path(d));args[4][0]["evidence_record_sha256"]["E1"]="0"*64
            self.assertFalse(reconcile(*args)["declared_links_consistent"])
