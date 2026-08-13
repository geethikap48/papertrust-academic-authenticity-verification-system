# utils/pdf_utils.py
import fitz
import pdfplumber
import pytesseract
from PIL import Image
import os
import re
import tempfile

# -----------------------
# Check if PDF is scanned
# -----------------------
def is_scanned_pdf(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t and t.strip():
                    return False
    except Exception:
        # fallback to PyMuPDF check
        try:
            with fitz.open(pdf_path) as doc:
                for p in doc:
                    if p.get_text().strip():
                        return False
        except Exception:
            pass
    return True

# -----------------------
# OCR scanned PDFs
# -----------------------
def ocr_pdf_to_searchable(pdf_path):
    doc = fitz.open(pdf_path)
    out_pdf = fitz.open()
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(img, extension='pdf')
        temp = fitz.open("pdf", pdf_bytes)
        out_pdf.insert_pdf(temp)
    out_fd, out_path = tempfile.mkstemp(suffix=".pdf")
    os.close(out_fd)
    out_pdf.save(out_path)
    return out_path

# -----------------------
# Extract full text
# -----------------------
def extract_full_text(pdf_path):
    text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text.append(t)
    except Exception:
        try:
            with fitz.open(pdf_path) as doc:
                for p in doc:
                    text.append(p.get_text())
        except Exception:
            pass
    return "\n\n".join(text)

# -----------------------
# Extract References block
# -----------------------
def extract_references_block(full_text: str) -> str:
    """
    Extract only the References section from the paper text.
    Looks for common section headers like 'References' or 'Bibliography'.
    """
    patterns = [r"\nreferences\n", r"\nbibliography\n", r"\nreference\n"]
    start = None
    for pat in patterns:
        m = re.search(pat, full_text, flags=re.IGNORECASE)
        if m:
            start = m.end()
            break

    if start is None:
        return ""  # fallback: no references detected

    # cut from 'References' until the end
    ref_block = full_text[start:]
    return ref_block.strip()

# -----------------------
# Extract citation strings from References
# -----------------------
def extract_citations_from_references(ref_text: str):
    """
    Extract individual reference entries from the References block.
    Handles [1], [2]... or numbered styles without brackets.
    """
    if not ref_text:
        return []

    # Matches references like:
    # [1] Author, Title...
    # 1. Author, Title...
    pattern = r"(?:\[\d{1,3}\]|\d{1,3}[.)])\s+.*?(?=(?:\[\d{1,3}\]|\d{1,3}[.)])\s+|$)"

    refs = re.findall(pattern, ref_text, flags=re.S)
    return [r.strip() for r in refs if r.strip()]

# -----------------------
# Main processing pipeline
# -----------------------
def process_pdf_file(pdf_path):
    if is_scanned_pdf(pdf_path):
        processed_pdf = ocr_pdf_to_searchable(pdf_path)
    else:
        processed_pdf = pdf_path

    full_text = extract_full_text(processed_pdf)

    # ✅ Extract only the References section
    references_text = extract_references_block(full_text)

    # ✅ Parse references into individual citations
    citations = extract_citations_from_references(references_text)

    return processed_pdf, full_text, citations

def extract_full_text_and_contexts(pdf_path):
    processed_pdf, full_text, citations = process_pdf_file(pdf_path)
    return full_text, citations
