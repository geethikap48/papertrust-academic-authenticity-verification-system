# utils/pdf_highlighter.py

import fitz


# -------------------------------------------------
# Utility: Break sentence into searchable chunks
# -------------------------------------------------
def chunk_text(text, chunk_size=6):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])

        if len(chunk) > 15:
            chunks.append(chunk)

    return chunks


# -------------------------------------------------
# Unified Highlight Function
# -------------------------------------------------
def highlight_analysis_pdf(
    original_pdf,
    ai_sentences,
    paraphrased_sentences,
    drift_sentences,
    output_path
):

    doc = fitz.open(original_pdf)

    # Color Mapping (RGB)
    COLORS = {
        "AI": (1, 0, 0),            # Red
        "HUMAN": (0, 0.8, 0),       # Green
        "PARAPHRASED": (0, 0, 1),   # Blue
        "DRIFT": (1, 0.8, 0)        # Yellow
    }

    # Prepare lookup sets
    ai_texts = {item.get("sentence", "").strip() for item in ai_sentences}
    paraphrased_texts = {item.get("sentence", "").strip() for item in paraphrased_sentences}
    drift_texts = {text.strip() for text in drift_sentences}

    for page in doc:

        page_text = page.get_text()

        # Split page into sentences
        sentences = page_text.split(". ")

        for sentence in sentences:

            sentence_clean = sentence.strip()

            if not sentence_clean:
                continue

            # Determine type
            if sentence_clean in ai_texts:
                color = COLORS["AI"]

            elif sentence_clean in paraphrased_texts:
                color = COLORS["PARAPHRASED"]

            elif sentence_clean in drift_texts:
                color = COLORS["DRIFT"]

            else:
                color = COLORS["HUMAN"]

            # Highlight sentence in chunks
            for chunk in chunk_text(sentence_clean):

                areas = page.search_for(chunk)

                for inst in areas:
                    highlight = page.add_highlight_annot(inst)
                    highlight.set_colors(stroke=color)
                    highlight.update()

    doc.save(output_path)
    doc.close()