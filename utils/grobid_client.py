# utils/grobid_client.py
import requests
from bs4 import BeautifulSoup

GROBID_URL = "http://localhost:8070/api/processReferences"

def extract_citations(pdf_path):
    """
    Use GROBID to extract structured references. Returns a list of dicts:
    { title, authors (list), year, raw }
    Only biblStruct entries are used.
    """
    citations = []
    with open(pdf_path, "rb") as fh:
        try:
            r = requests.post(GROBID_URL, files={"input": fh}, data={"consolidateCitations": 1}, timeout=60)
        except Exception as e:
            print("[grobid_client] Error:", e)
            return citations

    if r.status_code != 200 or not r.text:
        print("[grobid_client] GROBID returned", r.status_code)
        return citations

    # parse XML
    soup = BeautifulSoup(r.content, "xml")
    for b in soup.find_all("biblStruct"):
        title_el = b.find("title")
        title = title_el.text.strip() if title_el else ""
        authors = []
        for pers in b.find_all("author"):
            pn = pers.find("persName")
            if pn:
                fn = pn.find("forename")
                sn = pn.find("surname")
                name_parts = []
                if fn and fn.text: name_parts.append(fn.text.strip())
                if sn and sn.text: name_parts.append(sn.text.strip())
                if name_parts:
                    authors.append(" ".join(name_parts))
            else:
                # fallback to textual content
                name = pers.text.strip()
                if name:
                    authors.append(name)
        date = None
        date_el = b.find("date")
        if date_el:
            # prefer 'when' attribute else text
            if date_el.has_attr("when"):
                date = date_el["when"]
            elif date_el.text:
                date = date_el.text.strip()
        raw = str(b)
        # only include entries that have at least a title or an author (filter out noise)
        if title or authors:
            citations.append({"title": title or None, "authors": authors, "year": date, "raw": raw})
    return citations
