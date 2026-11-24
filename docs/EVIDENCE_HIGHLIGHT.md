# Evidence highlight and structural audit
- Uses existing pdfplumber/Pillow and python-docx stack; no added runtime service.
- Candidate image overlay is separate from source PDF and original PNG. Verify source and crop hashes, restrict relative paths, validate bounding boxes and source color.
- Bounding rectangle is a visual candidate, not word-exact semantic attribution. Multiline boxes may cover intervening content. Human review required.
- Word shading audit accepts externally approved exact text intervals and explicit RGB fills. It checks body paragraphs only, reports missing/wrong/unexpected positions and unsupported paragraph structures. It does not edit Word, inspect tables or determine what text ought to be highlighted.
- Thai Word Unicode test is not Thai PDF/OCR validation. Printed page labels, table/footnote coverage, font/visual Word QA and semantic review remain pending.
- Never publish private sources, candidate crops, or manuscript spans on public GitHub. Test on generated fixtures only.
