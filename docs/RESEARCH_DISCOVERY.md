# Research Discovery — metadata candidates
Core-first module. Standard-library HTTP adapters for Crossref and OpenAlex; no new third-party dependency.

- Crossref: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- OpenAlex: https://help.openalex.org/api/authentication/ and https://help.openalex.org/api/searching/
- Use public research-topic queries only; never send private material or participant information.
- OpenAlex adapter requires OPENALEX_API_KEY in the environment (or explicitly passed at runtime). Never commit or print keys.
- Crossref optionally supports mailto for polite use; no credentials required for public access.
- discover returns normalized metadata plus source records; group_candidates groups exact normalized DOIs and flags conflicting titles/years. No title-only automatic deduplication.
- Explicit bounded requests, timeout, response limit, no automatic retries or redirects. Rate limits and provider failures are exposed rather than inventing results.
- No full-text download, rights clearance, semantic claim verification, or retraction check in this version. Metadata is CANDIDATE_UNVERIFIED, not evidence.
- Unit tests use synthetic mocked provider responses. Live smoke test and provider quota verification remain pending. Public CI must not send real project queries or require secrets.

Example in a permitted private runtime:
    from research_discovery import discover, group_candidates
    results = discover("public research topic", limit=5)
    print(group_candidates(results))

Next: local literature index, identifier/retraction verification, export to bibliography formats, and link to evidence candidates. Questionnaire and real data work remain paused.
