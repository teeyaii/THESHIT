# Thai PDF text extraction and OCR
Prefer a native PDF text layer. Tesseract OCR is optional and only runs for empty layers or explicit force_ocr. A poor native layer may require manually selecting OCR.
- Existing pdfplumber/Pillow; Tesseract with tha+eng language data is an optional native runtime. Upstream: https://github.com/tesseract-ocr/tesseract and https://github.com/tesseract-ocr/tessdata (review upstream Apache-2.0 notices and distribution-specific packages).
- No shell execution, no network access from the module, page/DPI/pixel/time limits. Use trusted files in isolated private runtime; untrusted PDF security and production sandboxing are separate gates.
- Reports source SHA-256, physical pages, truncation, native or OCR candidate status, OCR raster hash and pixel word boxes with confidence. Never treat confidence as semantic verification.
- Missing OCR runtime is reported as blocked. Dedicated CI installs Thai and English language data and Noto fonts, then tests a generated Thai image PDF.
- Thai synthetic fixture recognition is not an acceptance test for actual journals, scanned tables or multi-column documents. Printed page labels and visual/semantic audit are separate.
- No private PDF, names, document images or actual research data in public CI.
