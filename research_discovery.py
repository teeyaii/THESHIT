"""Bibliographic metadata candidates; never proof of a claim or full-text access."""
import json
import os
import re
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

STATUS = "METADATA_CANDIDATE_UNVERIFIED"
DOI = re.compile(r"10\.\d{4,9}/\S+\Z", re.I)
MAX_BYTES = 5_000_000

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def request_json(url, headers):
    request = Request(url, headers=headers)
    try:
        with build_opener(NoRedirect()).open(request, timeout=15) as response:
            raw = response.read(MAX_BYTES + 1)
    except HTTPError as exc:
        raise RuntimeError(f"Provider HTTP {exc.code}; no automatic retry") from None
    except (URLError, TimeoutError):
        raise RuntimeError("Provider connection failed") from None
    if len(raw) > MAX_BYTES:
        raise ValueError("Provider response exceeded size limit")
    return json.loads(raw)

def normalize_doi(value):
    if not isinstance(value, str):
        return None
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value.strip(), flags=re.I)
    return value.lower() if DOI.fullmatch(value) else None

def first_string(values):
    return values[0] if isinstance(values, list) and values and isinstance(values[0], str) else None

def crossref_record(item):
    doi = normalize_doi(item.get("DOI"))
    year = None
    for field in ("published", "published-print", "published-online"):
        parts = (item.get(field) or {}).get("date-parts", [])
        if parts and parts[0] and type(parts[0][0]) is int:
            year = parts[0][0]
            break
    authors = []
    for a in item.get("author") or []:
        name = " ".join(x for x in (a.get("given"), a.get("family")) if isinstance(x, str))
        if not name:
            name = a.get("name")
        if name:
            authors.append(name)
    return {"provider": "crossref", "provider_id": doi,
            "doi": doi, "title": first_string(item.get("title")), "year": year,
            "authors": authors, "venue": first_string(item.get("container-title")),
            "landing_url": "https://doi.org/" + doi if doi else None,
            "source_record": item, "status": STATUS}

def openalex_record(item):
    doi = normalize_doi(item.get("doi"))
    location = item.get("primary_location") or {}
    source = location.get("source") or {}
    return {"provider": "openalex", "provider_id": item.get("id"),
            "doi": doi, "title": item.get("display_name") or item.get("title"),
            "year": item.get("publication_year"),
            "authors": [a["author"]["display_name"] for a in item.get("authorships") or []
                        if (a.get("author") or {}).get("display_name")],
            "venue": source.get("display_name"), "landing_url": location.get("landing_page_url"),
            "source_record": item, "status": STATUS}

def discover(query, provider="crossref", limit=10, fetch=request_json, api_key=None, mailto=None):
    """Explicit, bounded public-metadata query. No automatic network calls on import."""
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError("Query must contain 1–500 characters")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("Limit must be 1–50")
    headers = {"Accept": "application/json", "User-Agent": "THESHIT-Research/0.3"}
    if provider == "crossref":
        params = {"query.bibliographic": query.strip(), "rows": limit}
        if mailto:
            params["mailto"] = mailto
        response = fetch("https://api.crossref.org/works?" + urlencode(params), headers)
        rows = response["message"]["items"]
        convert = crossref_record
    elif provider == "openalex":
        key = api_key or os.getenv("OPENALEX_API_KEY")
        if not key:
            raise ValueError("OPENALEX_API_KEY required for OpenAlex adapter")
        headers["Authorization"] = "Bearer " + key
        params = {"search": query.strip(), "per_page": limit}
        response = fetch("https://api.openalex.org/works?" + urlencode(params), headers)
        rows = response["results"]
        convert = openalex_record
    else:
        raise ValueError("Unknown provider")
    if not isinstance(rows, list):
        raise ValueError("Invalid provider result schema")
    return [convert(item) for item in rows[:limit]]

def group_candidates(records):
    """Group exact DOI matches only; retain all provider variants and disagreements."""
    groups = {}
    for i, row in enumerate(records):
        doi = normalize_doi(row.get("doi"))
        key = ("doi", doi) if doi else ("unresolved", i)
        groups.setdefault(key, []).append(row)
    return [{"doi": key[1] if key[0] == "doi" else None,
             "status": STATUS, "variants": variants,
             "title_conflict": len({v.get("title") for v in variants if v.get("title")}) > 1,
             "year_conflict": len({v.get("year") for v in variants if v.get("year")}) > 1}
            for key, variants in groups.items()]
