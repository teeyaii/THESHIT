# THESHIT — Core System First / Open Source gate
Pause project-specific questionnaire development, personnel registry, real intake and deployment. Public repository is software only.

## Selected additions
- openpyxl 3.1.5 — https://github.com/ericgazoni/openpyxl (MIT per upstream metadata); fixed synthetic Excel interoperability and Thai Unicode test.
- SciPy 1.15.3 — https://github.com/scipy/scipy (BSD-3-Clause per upstream metadata); independent simple-regression cross-check. Does not establish SPSS parity or validate HC3.
- pip-tools 7.5.0 — https://github.com/jazzband/pip-tools (BSD); CI generates a platform-specific hashed lock candidate.
- pip-audit 2.9.0 — https://github.com/pypa/pip-audit (Apache-2.0); dependency advisory scan. Scan success is not a guarantee of security.
- Existing adapters remain: pdfplumber, python-docx, Pandera, pyreadstat. No duplicates added.

## Gates
1. Resolve all core dependencies and generate hashed Linux/Python 3.11 lock candidate.
2. Install from candidate using --require-hashes, run pip check, all tests, then synthetic demo.
3. Export license metadata inventory and run pip-audit. Unknown or conflicting license metadata requires human review; no automatic legal clearance.
4. Review CI artifact and commit a reviewed lock in a separate PR before release. The input file is NOT a full lock; CI output is a candidate.
5. Preserve existing Evidence Engine work separately. Thai PDF extraction/OCR, semantic evidence review, Microsoft Word visual QA, multivariable and HC3 parity remain pending.

## Core-first roadmap
- Open source integration and supply chain QA
- Discovery and bibliography (Crossref/OpenAlex adapters; mock network in tests)
- Evidence and Thai document processing (PDF rendering, provenance; no auto-verification)
- General statistical engine and independent checks
- Academic report/document templates from computed results
- Independent end-to-end QA
- Mobile control interface, only after core acceptance

Evaluate Docling, GROBID, Tesseract Thai, Quarto, Pingouin and Streamlit individually before adoption. No additional servers or real study material.
