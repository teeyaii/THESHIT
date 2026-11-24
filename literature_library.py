"""Private/local bibliography store. Metadata candidates are never verified evidence."""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from research_discovery import normalize_doi, group_candidates, STATUS

SCHEMA = """
CREATE TABLE IF NOT EXISTS variants (
    digest TEXT PRIMARY KEY, provider TEXT NOT NULL, doi TEXT,
    title TEXT, record_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS variants_doi ON variants(doi);
"""
def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

class LiteratureLibrary:
    def __init__(self, db_path):
        self.path = Path(db_path)
        if self.path.suffix.lower() not in (".sqlite", ".sqlite3", ".db"):
            raise ValueError("Use a local SQLite database in an approved private workspace")
        if not self.path.parent.is_dir():
            raise ValueError("Database directory must already exist")
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.executescript(SCHEMA)

    def ingest(self, records):
        """Atomic import; identical records are idempotent, changed variants retained."""
        rows = []
        for record in records:
            if record.get("status") != STATUS or not isinstance(record.get("provider"), str):
                raise ValueError("Expected explicitly unverified provider candidate")
            if not isinstance(record.get("source_record"), dict):
                raise ValueError("Original provider metadata required")
            row = dict(record)
            row["doi"] = normalize_doi(row.get("doi"))
            if row.get("title") is not None and not isinstance(row["title"], str):
                raise ValueError("Invalid title")
            payload = canonical(row)
            key = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            rows.append((key, row["provider"], row["doi"], row.get("title"), payload))
        with closing(sqlite3.connect(self.path)) as conn, conn:
            before = conn.total_changes
            conn.executemany("INSERT OR IGNORE INTO variants VALUES (?,?,?,?,?)", rows)
            return conn.total_changes - before

    def records(self, doi=None):
        with closing(sqlite3.connect(self.path)) as conn:
            if doi is None:
                rows = conn.execute("SELECT record_json FROM variants ORDER BY digest")
            else:
                value = normalize_doi(doi)
                if not value:
                    raise ValueError("Invalid DOI")
                rows = conn.execute("SELECT record_json FROM variants WHERE doi=? ORDER BY digest", (value,))
            return [json.loads(row[0]) for row in rows]

    def groups(self):
        return group_candidates(self.records())

    def export_review(self, destination):
        """Exclusive creation of a review bundle, with no automatic selection or verification."""
        groups = self.groups()
        result = {"status": STATUS, "review_required": True, "groups": groups,
                  "variant_count": sum(len(g["variants"]) for g in groups)}
        with Path(destination).open("x", encoding="utf-8") as out:
            json.dump(result, out, ensure_ascii=False, indent=2, allow_nan=False)
        return result

def citation_candidate(record):
    """Neutral CSL-like fields for human review; literal author names avoid invented parsing."""
    if record.get("status") != STATUS:
        raise ValueError("Expected candidate record")
    if not record.get("title"):
        raise ValueError("Title missing; review source metadata")
    item = {"id": hashlib.sha256(canonical(record).encode()).hexdigest(),
            "title": record["title"],
            "author": [{"literal": name} for name in record.get("authors", [])]}
    if normalize_doi(record.get("doi")):
        item["DOI"] = normalize_doi(record["doi"])
    if type(record.get("year")) is int:
        item["issued"] = {"date-parts": [[record["year"]]]}
    if record.get("venue"):
        item["container-title"] = record["venue"]
    return {"status": STATUS, "fields": item, "type_review_required": True}
