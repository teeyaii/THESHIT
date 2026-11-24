# PDF preview / document finalization boundary
Produces only a generated synthetic document from the verified deterministic academic draft. Uses a dedicated Ubuntu preview job, LibreOffice Writer and Noto Sans Thai (SIL Open Font License; review the actual distribution notices). No actual research files, target institution template or private fonts in public CI.

Preview labels appear in the source document and header/footer. The program reports renderer, font, source/document/PDF hashes, page count, numeric fact register presence, and normalized paragraph substring matches. The fact/text checks are not visual layout or semantic acceptance. Paragraph mismatches must be inspected; do not mark full text parity if the paragraph gate is false. Dedicated preview CI fails if source hash, preview labels or numeric fact markers are missing. No new persistent server.

Microsoft Word Desktop, actual licensed target font, TOC/page-number verification, table and page layout inspection and final export remain separate. Never label a LibreOffice preview as a Microsoft Word pass. Final Word visual QA remains NOT_EXECUTED. No academic acceptance, real survey or participant data.

Initial preview run 45326199174 produced a PDF and all numeric fact markers, but source hash text and Thai paragraph parity failed. The source SHA-256 is rendered in four labeled 16-character groups to avoid long-line wrapping; every group must match. Thai paragraph parity remains an independent explicit gate, not silently waived.
