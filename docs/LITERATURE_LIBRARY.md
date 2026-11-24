# Literature Library / bibliography
Local SQLite, Python standard library only. Store in an authorized private workspace. No server or credentials required.
- Ingest Research Discovery candidate records; preserve the full provider payload and SHA-256 identity.
- Identical imports are idempotent; conflicting provider records are not overwritten.
- Group by normalized DOI, not title similarity. No DOI means unresolved; identical full records are still deduplicated.
- Export an unverified JSON review bundle or CSL-like candidate fields with literal authors. Item type and final formatting require review; this is not a validated CSL export.
- No automatic claim verification, source access, copyright clearance, retraction status, or full-text acquisition.
- Public CI uses synthetic metadata, temporary database and exports only.
- Never commit local database files or research exports, even if metadata is public, without review.

Example: LiteratureLibrary(Path("private")/"literature.sqlite3").ingest(discover("public topic"))
Create the private directory first; inspect conflicts and source records before selecting a reference.
