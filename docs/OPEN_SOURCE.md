# Open Source First
Direct package versions are pinned for the adapter trial; transitive dependencies are not yet locked. No upstream code vendored. Preserve upstream notices if redistributing packages. A full dependency/license/security audit and lockfile remain pending.
| Dependency | Upstream | License (upstream project) |
| --- | --- | --- |
| pdfplumber | https://github.com/jsvine/pdfplumber | MIT |
| python-docx | https://github.com/python-openxml/python-docx | MIT |
| pandera | https://github.com/unionai-oss/pandera | MIT |
| pyreadstat | https://github.com/Roche/pyreadstat | Apache-2.0 |
Install: python -m pip install -r requirements-oss.txt
Run: python -m unittest discover -s tests -v
Adapters: candidate PDF matches with physical page, coordinates and SHA-256; Pandera schema validation; synthetic SAV roundtrip and DOCX demo.
Limitations: no OCR, no Thai extraction acceptance yet, no visual Word QA, no SPSS statistical parity yet. A candidate match is not proof of a claim. No private documents or generated participant data on public CI.
Later candidates: Docling (layout and OCR), GROBID (bibliography), Quarto (report rendering), Pingouin (statistical cross-check). Evaluate licenses, runtime, model terms and incremental benefit before adoption.
