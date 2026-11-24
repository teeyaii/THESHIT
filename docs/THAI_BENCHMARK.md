# Thai publication benchmark protocol
Status: ground truth and real extraction runs pending. The candidate catalog contains five publisher pages that explicitly display CC BY 4.0 as checked on 2026-11-24. Individual PDF, third-party content, layout diversity and attribution must still be checked before processing. No publisher PDFs or excerpts committed.

## Candidate catalog (publisher landing pages)
| ID | Publisher and article | License shown |
|---|---|---|
| THB01 | [Digital courts](https://so01.tci-thaijo.org/index.php/CMUJLSS/article/view/284261) — CMU Journal of Law and Social Sciences 19(1), 182–204 | CC BY 4.0 |
| THB02 | [Call center fraud remedies](https://so01.tci-thaijo.org/index.php/CMUJLSS/article/view/282673) — CMU Journal of Law and Social Sciences 19(1), 205–227 | CC BY 4.0 |
| THB03 | [Greenwashing legal framework](https://so01.tci-thaijo.org/index.php/CMUJLSS/article/view/281941) — CMU Journal of Law and Social Sciences 19(1), 305–338 | CC BY 4.0 |
| THB04 | [Digital literacy simulation game](https://so02.tci-thaijo.org/index.php/edubuu/article/view/282795) — Burapha Journal of Education 37(1), 120–134 | CC BY 4.0 |
| THB05 | [Digital leadership of teachers](https://so02.tci-thaijo.org/index.php/edubuu/article/view/282686) — Burapha Journal of Education 37(1), 103–119 | CC BY 4.0 |

These are candidate sources, not a representative sample. Add legally permitted scanned/multicolumn examples if the five lack those layouts. Use a deliberately rasterized permitted page only as a separate controlled OCR benchmark, not an authentic scan.

## Independent annotation and scoring
1. In approved private storage download the originals, record SHA-256, printed and physical pages, rights and attribution. Select passages and tables before extracting.
2. Separate reviewer transcribes reference text and cells without viewing predictions. Record identity/independence locally; do not commit personal information.
3. Reference JSON: reference_status=INDEPENDENTLY_REVIEWED, cases array: case_id, mode(native/ocr), source_file, source_sha256, license_reviewed=true, physical_page, printed_page, text, table_cells (keys identifying table,row,column).
4. Predictions JSON: cases with matching case_id, mode, source_sha256, physical_page, printed_page, text, table_cells. Run existing native/OCR extraction independently; retain missing cases. Do not silently substitute ground truth. Table extraction still requires a dedicated adapter and matched region definition.
5. python thai_benchmark.py --reference private/reference.json --predictions private/predictions.json --source-dir private/sources --output private/benchmark.json
6. Score NFC Unicode code points ignoring whitespace, Levenshtein CER (can exceed 100%), pooled accuracy by mode, exact cell accuracy and locator match. Wrong/missing locator counts as empty prediction. Report missing cases and errors. Proposed text thresholds 95% native, 90% OCR; require 100% locator match. Table gate requires independent review, not automatic pass.
7. Tests exercise generated fixtures only. No real benchmark accuracy is claimed; real corpus selection, independent transcription, predictions and review remain open.

## First-page pilot
Publisher PDFs opened and first-page visuals checked on 2026-11-24: THB01 printed 182 (23 pages), THB02 205 (23), THB03 305 (34), THB04 120 (15), THB05 103 (17). The public probe downloads only the five fixed direct PDF URLs into memory, extracts the first page with pdfplumber, reports hashes, native text presence and normalized title match only. It uploads no PDFs or text. This is not independent ground truth, authentic scan coverage, CER, table or source-page acceptance. Network failures remain blocked. Published content rights remain subject to publisher license and any third-party exclusions.
