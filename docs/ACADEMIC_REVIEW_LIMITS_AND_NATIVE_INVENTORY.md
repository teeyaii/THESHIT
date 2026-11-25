# Academic QA: capability limits and native dependency review queue
Report-only inventory, not legal clearance or source redistribution approval.

| Component | Used for | License family reported in review (verify installed package and transitive components) |
|---|---|---|
| Poppler / pdftotext | independent PDF text extraction | GPL family |
| Tesseract / tha+eng traineddata | OCR | Apache-2.0 family; verify actual traineddata distribution |
| LibreOffice Writer | synthetic PDF preview only | MPL-2.0 and component-specific terms |
| fontconfig | local font lookup | verify actual package notices |
| Noto Sans / Noto Sans Thai | preview fixture fonts | SIL OFL family |
| Microsoft Word Desktop | actual Word visual QA | proprietary; user-installed licensed environment |
| Browallia New / UPC | RU requested fonts | proprietary; do not distribute font files |

Record executable version, package origin, actual license and notices, redistribution obligations and reviewer approval for each installed native component. Dependency metadata and vulnerability scans do not resolve licensing. No distribution approval is inferred. Gate remains BLOCKED.

## Methodology and literature scope
- Existing discovery providers generate candidates; no guarantee of comprehensive ThaiJO/TCI coverage. Verify every source at publisher, record study region separately from language, and check contrary/null findings independently.
- Source and highlight linkage is declared and reviewed; it does not prove independent reviewers or semantics. Multi-source colors are explicit conventions only.
- Synthetic-only alignment registry is not IOC, translation equivalence, cognitive interview, pilot, or content validity.
- Current numeric implementation includes OLS/HC3, VIF, BP, JB, Cook D, coefficient CI and synthetic Cronbach alpha. Power/sample size, alpha-if-deleted, item-total, IOC calculator and other missing-data methods are not implemented. Human approval and ethics requirements remain.
- Complex manuscript editing is conservatively refused where preservation cannot be proved. No claims of complete real manuscript support.

## Academic vocabulary (working glossary)
OLS: การประมาณค่าด้วยวิธีกำลังสองน้อยที่สุดแบบสามัญ; HC3: ความคลาดเคลื่อนมาตรฐานแบบทนทานต่อความแปรปรวนไม่คงที่ HC3; standard error: ความคลาดเคลื่อนมาตรฐาน; confidence interval: ช่วงความเชื่อมั่น; Cook's distance: ระยะห่างของคุก (เกณฑ์ตรวจสอบ ไม่ลบกรณีอัตโนมัติ); association: ความสัมพันธ์ ไม่ใช่เหตุและผล.
