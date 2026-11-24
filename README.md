# THESHIT
General-purpose Research Operating System — Core First, Cloud First, Human Approval.

## Synthetic core release candidate
This public repository is generic software only. No real-data intake, personnel registry or project-specific questionnaire. Synthetic output is not field data or research evidence.

## Run locally or in GitHub Actions
Python 3.11 on Linux is the reference environment:
```sh
python -m pip install -r requirements-oss.txt
python -m unittest discover -s tests -v
python theshit_cli.py demo --output outputs/SYNTHETIC_E2E
python theshit_cli.py verify --output outputs/SYNTHETIC_E2E
```
For mobile/cloud control after merge, open Actions → Synthetic end-to-end research demo → Run workflow, then download the explicitly labeled synthetic artifact.

## Modules
- Research Discovery: Crossref/OpenAlex metadata candidates (live API acceptance pending).
- Literature Library: SQLite candidate variants, DOI grouping, review export.
- Evidence: PDF candidate crops, hashes, source-color overlays and structural Word shading audit.
- PDF text: native extraction and optional Tesseract Thai/English OCR.
- Statistics: generic synthetic regression, diagnostics, explicit missingness and independent OLS/HC3 checks; legacy 14-item demo remains available.
- Report: computed JSON, DOCX, XLSX and Markdown; structural table verification.
- Core OSS CI: dependency lock candidate, hashes, package metadata and vulnerability scan.

Read docs/CORE_RELEASE_GATE.md for pending release gates. No automatic evidence verification, live study collection, Word visual QA or academic acceptance is claimed. Keep private materials out of the repo. Human approval before merge and release.
