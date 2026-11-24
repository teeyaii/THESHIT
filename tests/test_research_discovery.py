import unittest
from urllib.parse import urlparse, parse_qs
from research_discovery import discover, group_candidates, normalize_doi, STATUS

class DiscoveryTests(unittest.TestCase):
    def test_crossref_thai_query(self):
        def fake(url, headers):
            self.assertEqual(urlparse(url).netloc, "api.crossref.org")
            self.assertEqual(parse_qs(urlparse(url).query)["query.bibliographic"], ["การวิจัย"])
            self.assertNotIn("Authorization", headers)
            return {"message":{"items":[{"DOI":"10.1234/FIXTURE", "title":["Synthetic fixture"],
                    "published":{"date-parts":[[2020]]},
                    "author":[{"given":"Test","family":"Author"}]}]}}
        row=discover("การวิจัย",fetch=fake)[0]
        self.assertEqual(row["doi"],"10.1234/fixture")
        self.assertEqual(row["year"],2020)
        self.assertEqual(row["authors"],["Test Author"])
        self.assertEqual(row["status"],STATUS)

    def test_openalex_auth(self):
        def fake(url, headers):
            self.assertEqual(urlparse(url).netloc,"api.openalex.org")
            self.assertEqual(headers["Authorization"],"Bearer fixture-key")
            self.assertNotIn("fixture-key",url)
            return {"results":[{"id":"fixture", "doi":"https://doi.org/10.1234/fixture",
                    "display_name":"Synthetic alternate", "publication_year":2021}]}
        row=discover("test",provider="openalex",api_key="fixture-key",fetch=fake)[0]
        self.assertEqual(row["doi"],"10.1234/fixture")
        self.assertNotIn("fixture-key",str(row))
        self.assertEqual(row["status"],STATUS)

    def test_group_conflicts(self):
        rows=[{"doi":"10.1234/abc","title":"A","year":2020},
              {"doi":"https://doi.org/10.1234/ABC","title":"B","year":2021},
              {"doi":None,"title":"A"},{"doi":None,"title":"A"}]
        grouped=group_candidates(rows)
        self.assertEqual(len(grouped),3)
        self.assertEqual(len(grouped[0]["variants"]),2)
        self.assertTrue(grouped[0]["title_conflict"])
        self.assertTrue(grouped[0]["year_conflict"])

    def test_invalid_inputs(self):
        for query,limit in [("",10),("ok",0),("ok",51),("ok",True)]:
            with self.assertRaises(ValueError):
                discover(query,limit=limit)
        self.assertIsNone(normalize_doi("not a doi"))
        with self.assertRaises(ValueError):
            discover("test",provider="unknown")

    def test_no_fabricated_results(self):
        self.assertEqual(discover("test",fetch=lambda u,h:{"message":{"items":[]}}),[])
        with self.assertRaises(KeyError):
            discover("test",fetch=lambda u,h:{})
