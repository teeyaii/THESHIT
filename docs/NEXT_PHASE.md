# THESHIT — next phase / V1.0 readiness backlog
Core baseline: main c5760d8b65666a4243f88f4b6b9f4c72ab854931 after PR #14 merge. PRs #1–16 merged; discovery live run 45325131643 returned 2/2 title+DOI records from each provider. All five workflows for the PR passed. This is not full V1.0 acceptance. Combined regression on a fresh branch must pass before accepting the closeout.

## A. Thai public-source benchmark
- Choose at least five legally accessible, reuse-permitted Thai academic sources covering native text, tables, multi-column and scanned pages, with documented permissions. No private documents or copied source PDFs on public GitHub without explicit redistribution rights.
- Have a reviewer prepare independent ground truth: physical and printed page number, text excerpts, table cell values and page coordinates. Keep licensed source material in an approved workspace, and publish only permissible metrics and code.
- Report native/OCR character error rate (Unicode normalization policy fixed), exact table-cell accuracy, locator accuracy, failure cases and manual review requirements. Proposed initial acceptance: at least 95% character accuracy for clean native text, at least 90% for selected legible scans, 100% checked source/page provenance for any accepted evidence. Record scope and do not generalize to all Thai documents.
- Compare existing pdfplumber/Tesseract stack with Docling only if measured limitations justify dependency and compute cost. No mandatory GROBID/Docling deployment.

## B. Academic writing engine
- Use structured fact records from computed statistics and independently reviewed evidence, with immutable identifiers and provenance. Separate methods, results, discussion and limitations.
- Deterministic narrative first: exact numeric values, confidence intervals, missingness and null/negative findings; do not assert causation or hypothesis support beyond predeclared rules.
- Any AI-drafted synthesis is DRAFT_REVIEW_REQUIRED, must reference approved source records, and is checked by a separate reviewer. No fabricated DOI, quote, author, approval, or empirical data.
- Acceptance: every rendered numeric statement matches computed JSON; every evidence claim has a reviewer disposition; unsupported or inconsistent claims block export readiness. Synthetic fixtures remain visibly labeled.

## C. PDF and document finalization
- Generate a generic synthetic document preview using an appropriate licensed Thai font. Compare source text, page count, tables, headings, headers and footers; record render engine.
- Microsoft Word Desktop + actual licensed target font required for Word-specific final visual acceptance, TOC/page numbering and final PDF export when the target institution requires it. Do not substitute another renderer and mark Word QA passed.
- Acceptance: export checks, text consistency, visual inspection and environment provenance; label unverified previews as such.

- Mandatory formatting acceptance profile: see docs/DOCUMENT_FORMAT_ACCEPTANCE.md and config/document_format_profile.example.json. Separate font, paragraph, styles, margins, pagination, table/figure, references, TOC, source shading and full Word visual gates from PDF text QA. Template-specific settings are not assumed.

## D. Mobile control
- First version: read-only responsive static dashboard linked to GitHub Actions; no login, data upload, secrets, network proxy or real study data. Public pages may expose only generic software/demo status.
- Later: authenticated private workspace with separate authorization, threat model, retention and backup decisions. Render/Supabase not required for current stage.
- Acceptance: mobile viewport tests, accessible controls, no secret exposure, no real-data route and clear distinction between demo and real.

## E. Independent final QA
- Codex: reproduce clean environment, all module and integration tests, dependency/security review, output hashes, benchmark reconciliation.
- Claude: independently assess source-review and narrative methodology, limits and document samples; do not use a synthetic output as empirical evidence.
- Owner: review blockers, authorize release. Do not declare V1.0 with blocked mandatory gates.

## Scope lock
Questionnaires, personnel registry, real-data ingestion and project-specific research are explicitly paused. Core-first, public code only. No paid infrastructure or service provisioning without owner approval. A new feature branch/PR per stage; CI is a software gate, not academic acceptance.

## RU MBA working profile update
Target latest applicable 2569 guide (official listing verified, PDF contents unavailable); retain 2568 fallback values as provisional. Project chapter title 22 pt and no literature-age exclusion. See docs/RU_2569_WORKING_POLICY.md. Independent style and Word Desktop validation remain required.
