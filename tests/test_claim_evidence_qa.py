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

    def test_multi_source_color_requires_all_reconciled_sources(self):
        from claim_evidence_qa import audit_multi_source_spans
        with tempfile.TemporaryDirectory() as d:
            path,m,idx,decisions,links,sources,crops=self.fixture(Path(d))
            spans=[{"claim_id":"CL1","sources":["R1"],"color":"FFE066"}]
            args=(path,m,idx,decisions,links,sources,crops)
            result=audit_multi_source_spans(*args,spans,source_colors={"R1":"FFE066"},multi_source_color="AAFFAA")
            self.assertEqual(result["source_mapping"][0]["sources"],["R1"])
            self.assertFalse(result["final_acceptance"])
            for wrong in (["R1","R2"],["R1","R1"],[]):
                with self.assertRaises(ValueError):
                    audit_multi_source_spans(*args,[dict(spans[0],sources=wrong)],source_colors={"R1":"FFE066","R2":"FFBBBB"},multi_source_color="AAFFAA")
            with self.assertRaises(ValueError):
                audit_multi_source_spans(path,m,idx,decisions[:1],links,sources,crops,spans,source_colors={"R1":"FFE066"},multi_source_color="AAFFAA")

    def test_multi_source_positive_with_two_distinct_reviewed_sources(self):
        from claim_evidence_qa import audit_multi_source_spans
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=root/"sources";src.mkdir()
            tiny_pdf(src/"a.pdf");tiny_pdf(src/"b.pdf")
            with (src/"b.pdf").open("ab") as fh:fh.write(b"\n% distinct synthetic fixture\n")
            exact="Synthetic claim"
            idx=candidate_atlas([{"evidence_id":eid,"source_file":name,"phrase":"evidence test","claim":exact}
                                 for eid,name in (("E1","a.pdf"),("E2","b.pdf"))],src,root/"crops")
            doc=Document();p=doc.add_paragraph();run=p.add_run(exact)
            shade=OxmlElement("w:shd");shade.set(qn("w:fill"),"AAFFAA");run._r.get_or_add_rPr().append(shade)
            citation="(Fixture, 2003; Fixture, 2004)";p.add_run(" "+citation)
            path=root/"fixture.docx";doc.save(path)
            refs=[];decisions=[];hashes={};links={}
            for i,row in enumerate(idx["records"],1):
                eid=row["evidence_id"];rid=f"R{i}";hit=row["hits"][0]
                refs.append({"reference_id":rid,"title":"Synthetic reference "+rid,"year":2002+i,"metadata_review_status":"REVIEWED","source_sha256":row["source_sha256"]})
                hashes[eid]=canonical_hash(row);links[eid]=rid
                for who in ("fixture-a","fixture-b"):
                    decisions.append({"evidence_id":eid,"reviewer_id":who,"record_sha256":hashes[eid],"decision":"SUPPORTS",
                                      "rationale":"Synthetic test only","full_context_reviewed":True,"source_sha256":row["source_sha256"],
                                      "physical_page":hit["physical_page"],"source_excerpt":hit["matched_text"],"candidate_image_sha256":hit["image_sha256"]})
            m={"document_sha256":inventory(path)["source_sha256"],"references":refs,
               "citations":[{"citation_id":"C1","part":"word/document.xml","paragraph":0,"start":len(exact)+1,
                             "end":len(exact)+1+len(citation),"exact_text":citation,"reference_ids":["R1","R2"],"claim_review_status":"REVIEWED"}]}
            claims=[{"claim_id":"CL1","part":"word/document.xml","paragraph":0,"start":0,"end":len(exact),
                     "exact_text":exact,"citation_ids":["C1"],"evidence_ids":["E1","E2"],"evidence_record_sha256":hashes,"evidence_reference_ids":links}]
            spans=[{"claim_id":"CL1","sources":["R1","R2"],"color":"AAFFAA"}]
            args=(path,m,idx,decisions,claims,src,root/"crops",spans)
            colors={"R1":"FFE066","R2":"FFBBBB"}
            qa=audit_multi_source_spans(*args,source_colors=colors,multi_source_color="AAFFAA")
            self.assertEqual(qa["coverage"]["matched_characters"],len(exact))
            self.assertFalse(qa["final_acceptance"])
            spans[0]["sources"]=["R1"]
            with self.assertRaises(ValueError):audit_multi_source_spans(*args,source_colors=colors,multi_source_color="AAFFAA")
