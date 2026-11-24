# Document formatting — mandatory academic finalization gate
Status: PROVISIONAL policy; template-specific values must be taken from the approved institution/advisor template, not guessed. Generic software only: no private manuscript or licensed font binaries in public GitHub.

## 1. Profile and template
Use config/document_format_profile.example.json as a starting contract. In an approved private workspace, bind the exact template SHA-256, approved values and approver/version. Missing settings block final acceptance. Browallia New is the required Thai/complex-script font for the intended thesis workflow unless the approved template explicitly specifies otherwise; Latin typography, size and all dimensions follow the template. Noto fonts used by Linux previews are not substitutions accepted for the final thesis. Do not distribute proprietary font files.

## 2. Structural and visual checks
| Domain | Required checks |
|---|---|
| Font | Actual installed family and variants, Thai/Latin/complex-script assignments, size, bold/italic, diacritics, mixed Thai/English/numeric text, no missing or substituted glyphs |
| Paragraph | Alignment, first-line and hanging indents, left/right indents, line spacing, before/after spacing, tab stops, Thai word wrapping, no artificial spaces or blank paragraphs used for alignment |
| Page | Paper, margins, gutter, orientation, sections, headers/footers, page-break and widow/orphan control, no clipping or unintended blank pages |
| Heading | Named styles, hierarchy, keep-with-next, chapter and section numbering, uniform title spacing |
| Tables/figures | Width, column alignment, repeated header, row splitting, captions and numbering, image quality, source notes, no overflow or duplicated evidence |
| References | Citation style and bibliography, hanging indents, author/date/page consistency and URLs; preserve verified evidence and color mappings |
| TOC | Automatic fields, list of tables/figures when required, correct printed page numbers after update in Word |
| Content | Compare against approved source; no unintended edits to words, numbers, tables, citations, fields, comments or source shading. Flag awkward AI-like wording or Thai whitespace for human editorial review; never silently alter meaning. |

## 3. Acceptance and change control
- Separate TEXT_QA, STRUCTURAL_FORMAT_QA, WORD_VISUAL_QA and ACADEMIC_REVIEW; each reports PASS/FAIL/BLOCKED with evidence and scope. A successful PDF text extraction cannot pass visual formatting.
- Compare the approved profile to resolved Word styles and effective formatting (including direct overrides, styles, themes and complex-script settings). Inventory exceptions and review any deliberate variation. This comparison engine is a planned implementation; this document is the specification, not a claim of executed QA.
- Finalize a copy in Microsoft Word Desktop with the required licensed fonts actually available. Update fields/TOC/page numbers, render all pages, inspect full page layout, compare DOCX/PDF text and tables, record renderer/version and source/output hashes. No LibreOffice or alternate renderer can substitute for the Word-specific gate.
- Use a second reviewer to check every final page, with special attention to Thai combining marks, mixed script, table continuation, reference colors and line/page boundaries.
- Never declare FINAL ACCEPTED when the template, actual fonts, Word runtime, any required visual check or academic review is missing. Record BLOCKED and the exact reason. A generic synthetic preview may use licensed Noto fonts but must remain explicitly labeled.
