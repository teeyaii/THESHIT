"""Script-aware runs for new synthetic Word documents only.

Do not use this to rewrite existing manuscripts, fields or tracked changes.
Structural flags are not Microsoft Word visual acceptance.
"""
import re
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

THAI = re.compile(r"[\u0e00-\u0e7f]")
CHUNKS = re.compile(r"[\u0e00-\u0e7f]+|[^\u0e00-\u0e7f]+")

def add_script_runs(paragraph, text):
    """Append exact text, assigning Thai complex-script and language properties."""
    for chunk in CHUNKS.findall(text):
        run = paragraph.add_run(chunk)
        if THAI.search(chunk):
            pr = run._r.get_or_add_rPr()
            # Use schema-ordered insertion; complex-script font/size inherit named style.
            pr.insert_element_before(OxmlElement("w:cs"), "w:rtl", "w:em", "w:lang",
                                     "w:eastAsianLayout", "w:specVanish", "w:oMath", "w:rPrChange")
            lang = OxmlElement("w:lang")
            lang.set(qn("w:val"), "th-TH")
            lang.set(qn("w:bidi"), "th-TH")
            pr.insert_element_before(lang, "w:eastAsianLayout", "w:specVanish", "w:oMath", "w:rPrChange")
    return paragraph
