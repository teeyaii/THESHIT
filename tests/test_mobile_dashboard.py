import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from theshit_cli import run_demo
from mobile_dashboard import build,dashboard_html,LINKS
from statistical_engine import LABEL

class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags=[];self.links=[];self.viewport=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);self.tags.append(tag)
        if tag=="a":self.links.append(a["href"])
        if tag=="meta" and a.get("name")=="viewport":self.viewport=True

class DashboardTests(unittest.TestCase):
    def test_static_contract(self):
        html=dashboard_html({"label":LABEL,"status":"SYNTHETIC_E2E_PASS",
                             "files_verified":16,"report_cells_verified_each_format":132})
        parser=Scan();parser.feed(html)
        self.assertEqual(parser.links,[r[1] for r in LINKS])
        self.assertTrue(parser.viewport)
        self.assertFalse(set(parser.tags)&{"form","input","script","iframe","img","link"})
        self.assertIn(LABEL,html)
        self.assertIn("Not live service status",html)
        with self.assertRaises(ValueError):
            dashboard_html({"label":"REAL","status":"SYNTHETIC_E2E_PASS"})

    def test_from_verified_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=root/"demo";run_demo(bundle)
            target=root/"index.html";result=build(bundle,target)
            self.assertTrue(target.is_file())
            self.assertFalse(result["deployed"])
            with self.assertRaises(FileExistsError):
                build(bundle,target)
            (bundle/"native_text.json").write_text("changed",encoding="utf-8")
            with self.assertRaises(ValueError):
                build(bundle,root/"tampered.html")
