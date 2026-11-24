import tempfile
import unittest
from pathlib import Path
from html.parser import HTMLParser
from full_rehearsal import run
from research_workspace import build

class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.tags=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag)
        if tag=="a":self.links.append(dict(attrs)["href"])

class WorkspaceTests(unittest.TestCase):
    def test_verified_bundle_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle=root/"SYNTHETIC_RC";run(bundle,"a"*40)
            output=root/"WORKSPACE.html";r=build(bundle,output)
            self.assertFalse(r["deployed"])
            self.assertEqual(r["release_status"],"BLOCKED")
            parser=Page();parser.feed(output.read_text(encoding="utf-8"))
            self.assertFalse(set(parser.tags)&{"script","form","input","iframe","img"})
            local=[x for x in parser.links if x.startswith("SYNTHETIC_RC/")]
            self.assertEqual(len(local),r["links"])
            for path in local:self.assertTrue((root/path).is_file())
            self.assertIn("NOT_EXECUTED",output.read_text(encoding="utf-8"))
            with self.assertRaises(ValueError):build(bundle,output)
            (bundle/"claim_qa.json").write_text("tampered",encoding="utf-8")
            with self.assertRaises(ValueError):build(bundle,root/"bad.html")
