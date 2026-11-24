# Evidence engine v0.3
Local only. Public CI uses generated PDF/DOCX fixtures. Do not commit research PDFs, claims, participant data, evidence images or atlases.
Input: a list of records with evidence_id, source_file (relative PDF path), phrase, optional claim. Run candidate_atlas(manifest, source_dir, output_dir) from Python in an approved private workspace. Output directory must be new and separate from source directory.
Output: evidence_index.json, candidate_atlas.docx, cropped PNG images. Each hit includes physical page, bounding box, image hash and source hash. Crops include surrounding text, but reviewers must inspect full context.
Statuses: CANDIDATE_UNVERIFIED, NO_MATCH, NO_TEXT_LAYER, NOT_ACCESSIBLE, EXTRACTION_ERROR. No automatic VERIFIED. Multiple matches are retained.
locate_word_paragraphs(path, phrase) returns read-only body and top-level table locations, including phrases split across runs. Merged cells may duplicate locations; nested tables, headers, footnotes and tracked changes not covered.
Next gates: Thai PDF extraction, printed page mapping, table-specific evidence, approved source-color mapping and safe run shading on copies, visual Microsoft Word QA, independent semantic review. Do not replace the existing canonical evidence index until reconciliation. No real study claims or sources tested in this PR.
