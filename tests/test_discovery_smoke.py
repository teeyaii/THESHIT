import unittest
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
from discovery_smoke import smoke
from research_discovery import discover

class SmokeTests(unittest.TestCase):
    @patch.dict("os.environ",{"OPENALEX_API_KEY":""})
    def test_anon_and_mock(self):
        def fake(url,headers):
            self.assertNotIn("Authorization",headers)
            if "crossref.org" in url:
                return {"message":{"items":[{"DOI":"10.1234/test","title":["Fixture"]}]}}
            self.assertEqual(parse_qs(urlparse(url).query)["filter"],["has_doi:true"])
            return {"results":[{"doi":"https://doi.org/10.1234/test","display_name":"Fixture"}]}
        out=smoke(fake)
        self.assertEqual(out["mode"],"MOCK")
        self.assertEqual(out["providers"]["openalex"]["status"],"PASS")
        self.assertEqual(out["providers"]["crossref"]["status"],"PASS")
        with self.assertRaises(ValueError):
            discover("test",provider="openalex",fetch=fake)

    def test_failure_is_not_pass(self):
        def failed(url,headers):
            raise RuntimeError("Provider unavailable")
        out=smoke(failed)
        self.assertTrue(all(x["status"]=="BLOCKED_OR_FAILED" for x in out["providers"].values()))
