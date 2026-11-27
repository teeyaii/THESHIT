import tempfile
import unittest
from pathlib import Path
from thai_benchmark import evaluate,edit_distance,file_hash
from test_oss_adapters import tiny_pdf

class ThaiBenchmarkTests(unittest.TestCase):
    def test_thai_normalization(self):
        self.assertEqual(edit_distance("ภาษา ไทย","ภาษาไทย"),0)
        self.assertEqual(edit_distance("ภาษาไทย","ภาษไทย"),1)
    def test_metrics_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.pdf";tiny_pdf(p)
            row={"case_id":"DEMO1","mode":"native","source_file":p.name,
                 "source_sha256":file_hash(p),"license_reviewed":True,
                 "source_kind":"native","region_id":"fixture-region","bbox":[0,0,100,100],
                 "physical_page":1,"printed_page":"12","text":"ภาษาไทย",
                 "table_cells":{"T1/R1/C1":"42"}}
            ref={"reference_status":"INDEPENDENTLY_REVIEWED","cases":[row]}
            pred={"cases":[dict(row,table_cells={"T1/R1/C1":"43"})]}
            report=evaluate(ref,pred,d)
            self.assertEqual(report["modes"]["native"]["accuracy"],1)
            self.assertEqual(report["table_cell_accuracy"],0)
            self.assertEqual(report["locator_accuracy"],1)
            self.assertFalse(report["proposed_text_locator_gate"])
            pred["cases"][0]["physical_page"]=2
            qa=evaluate(ref,pred,d)
            self.assertEqual(qa["modes"]["native"]["character_error_rate"],1)
            self.assertEqual(qa["text_cer_ignoring_locator"],0)
            self.assertEqual(evaluate(ref,{"cases":[]},d)["locator_accuracy"],0)
    def test_ground_truth_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                evaluate({"reference_status":"DRAFT","cases":[]},{"cases":[]},d)

    def test_extra_cells_and_required_region(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.pdf";tiny_pdf(p)
            row={"case_id":"DEMO1","mode":"native","source_file":p.name,"source_sha256":file_hash(p),
                 "license_reviewed":True,"physical_page":1,"printed_page":"5","text":"กำหนด",
                 "source_kind":"native","region_id":"r1","bbox":[0,0,100,100],"table_cells":{"T1/R1/C1":"10"}}
            ref={"reference_status":"INDEPENDENTLY_REVIEWED","cases":[row]}
            pred={"cases":[dict(row,table_cells={"T1/R1/C1":"10","T1/R9/C9":"EXTRA"})]}
            qa=evaluate(ref,pred,d)
            self.assertEqual(qa["table_metrics"]["extras_count"],1)
            self.assertEqual(qa["table_metrics"]["precision"],0.5)
            self.assertEqual(qa["table_metrics"]["recall"],1)
            self.assertEqual(qa["table_cell_accuracy"],0.5)
            for key in ("bbox","source_kind","region_id","printed_page"):
                bad=dict(row);del bad[key]
                with self.assertRaises(ValueError):evaluate(dict(ref,cases=[bad]),pred,d)
            pred["cases"].append(dict(row,case_id="extra"))
            self.assertEqual(len(evaluate(ref,pred,d)["unexpected_prediction_cases"]),1)
            control=dict(row,mode="ocr",source_kind="rasterized_control")
            qa=evaluate(dict(ref,cases=[control]),{"cases":[control]},d)
            self.assertEqual(qa["source_kind_metrics"]["rasterized_control"]["cases"],1)
            self.assertEqual(qa["source_kind_metrics"]["genuine_scan"]["cases"],0)
            self.assertFalse(qa["proposed_text_locator_gate"])
