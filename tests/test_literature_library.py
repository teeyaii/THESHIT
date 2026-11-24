import tempfile
import unittest
from pathlib import Path
from literature_library import LiteratureLibrary, citation_candidate
from research_discovery import STATUS

def row(title="ตัวอย่างจำลอง", year=2020, doi="10.1234/test", provider="crossref"):
    return {"status": STATUS, "provider": provider, "doi": doi, "title": title,
            "year": year, "authors": ["Fixture Author"], "source_record": {"fixture": True}}

class LibraryTests(unittest.TestCase):
    def test_ingest_idempotence_and_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"private.sqlite3"
            lib=LiteratureLibrary(p)
            self.assertEqual(lib.ingest([row(),row()]),1)
            self.assertEqual(lib.ingest([row()]),0)
            self.assertEqual(LiteratureLibrary(p).records("https://doi.org/10.1234/TEST"),[row()])

    def test_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            lib=LiteratureLibrary(Path(d)/"local.db")
            lib.ingest([row(),row("Different",2021,provider="openalex"),row(doi=None)])
            groups=lib.groups()
            self.assertEqual(len(groups),2)
            conflict=next(g for g in groups if g["doi"])
            self.assertTrue(conflict["title_conflict"])
            self.assertTrue(conflict["year_conflict"])
            target=Path(d)/"review.json"
            self.assertEqual(lib.export_review(target)["variant_count"],3)
            with self.assertRaises(FileExistsError):
                lib.export_review(target)

    def test_reject_unverified_status_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            lib=LiteratureLibrary(Path(d)/"local.db")
            invalid=dict(row(),status="VERIFIED")
            with self.assertRaises(ValueError):
                lib.ingest([row(),invalid])
            self.assertEqual(lib.records(),[])

    def test_citation_literal_and_missing(self):
        candidate=citation_candidate(row())
        self.assertEqual(candidate["fields"]["author"],[{"literal":"Fixture Author"}])
        self.assertEqual(candidate["fields"]["issued"],{"date-parts":[[2020]]})
        self.assertTrue(candidate["type_review_required"])
        self.assertNotIn("issued",citation_candidate(row(year=None))["fields"])
        with self.assertRaises(ValueError):
            citation_candidate(row(title=None))
