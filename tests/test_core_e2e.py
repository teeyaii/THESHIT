import tempfile
import unittest
from pathlib import Path
from theshit_cli import run_demo,verify_demo,LABEL

class CoreE2ETests(unittest.TestCase):
    def test_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"demo"
            r=run_demo(out)
            self.assertEqual(r["label"],LABEL)
            self.assertEqual(r["status"],"SYNTHETIC_E2E_PASS")
            self.assertGreater(r["files_verified"],10)
            self.assertEqual(verify_demo(out),r)
            with self.assertRaises(FileExistsError):
                run_demo(out)
            (out/"native_text.json").write_text("tampered",encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_demo(out)
