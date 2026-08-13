# app.py

import os
import tempfile
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, send_file, flash

from utils.pdf_utils import process_pdf_file
from utils.grobid_client import extract_citations
from utils.citation_verifier import verify_citations_parallel
from utils.context_similarity import add_context_similarity, extract_context_sentences
from utils.phase1_normalizer import normalize_all_phase1, compute_document_phase1_score
from utils.ai_detector import analyze_ai_phase2
from utils.logical_drift import detect_logical_drift
from utils.pdf_highlighter import highlight_analysis_pdf
from utils.final_score import compute_final_score

from fpdf import FPDF

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = "secure-key"

# Store last results
app.last_results = []
app.last_uploaded_filename = ""
app.last_phase1_score = 0
app.last_ai_percentage = 0
app.last_drift_percentage = 0
app.last_final_percentage = 0


# -------------------------------------------------
# MAIN ROUTE
# -------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "GET":
        return render_template("index.html")

    if "pdf_file" not in request.files:
        flash("No file uploaded", "danger")
        return redirect(request.url)

    file = request.files["pdf_file"]

    if file.filename == "":
        flash("No file selected", "danger")
        return redirect(request.url)

    filename = file.filename
    pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(pdf_path)

    app.last_uploaded_filename = filename

    # ---------------- PHASE 1 ----------------
    processed_pdf_path, full_text, _ = process_pdf_file(pdf_path)
    citations = extract_citations(processed_pdf_path)

    verified = verify_citations_parallel(citations)
    contexts = extract_context_sentences(full_text)
    enriched = add_context_similarity(full_text, contexts, verified)
    enriched = normalize_all_phase1(enriched)

    phase1_document_score = compute_document_phase1_score(enriched)
    app.last_phase1_score = phase1_document_score
    app.last_results = enriched

    context_summary = {
        "relevant": sum(1 for c in enriched if c.get("relevancy_score", 0) >= 0.40),
        "weak": sum(1 for c in enriched if 0.30 <= c.get("relevancy_score", 0) < 0.40),
        "irrelevant": sum(1 for c in enriched if c.get("relevancy_score", 0) < 0.30),
    }

    # ---------------- PHASE 2 ----------------
    phase2 = analyze_ai_phase2(full_text)
    ai_percentage = phase2["ai_percentage"]
    app.last_ai_percentage = ai_percentage

    # highlight_ai_pdf(pdf_path, phase2["ai_sentences"],
    #                  os.path.join(UPLOAD_FOLDER, "ai_highlighted.pdf"))

    # ---------------- PHASE 3 ----------------
    drift_results = detect_logical_drift(full_text)
    drift_percentage = drift_results["drift_percentage"]
    app.last_drift_percentage = drift_percentage

    # highlight_drift_pdf(pdf_path, drift_results["drift_sentences"],
    #                     os.path.join(UPLOAD_FOLDER, "drift_highlighted.pdf"))
    highlight_analysis_pdf(
    pdf_path,
    phase2["ai_sentences"],
    phase2.get("paraphrased_sentences", []),
    drift_results["drift_sentences"],
    os.path.join(UPLOAD_FOLDER, "analysis_highlighted.pdf")
    )

    # ---------------- FINAL SCORE ----------------
    _, final_percentage = compute_final_score(
        phase1_document_score,
        ai_percentage,
        drift_percentage
    )

    app.last_final_percentage = final_percentage

    return render_template(
        "results.html",
        citations=enriched,
        phase1_document_score=phase1_document_score,
        ai_percentage=ai_percentage,
        human_percentage=100 - ai_percentage,
        drift_percentage=drift_percentage,
        final_percentage=final_percentage,
        context_summary=context_summary,
        pdf_filename=filename
    )


# -------------------------------------------------
# DOWNLOAD CSV
# -------------------------------------------------
@app.route("/download_csv")
def download_csv():

    if not app.last_results:
        flash("No results available", "warning")
        return redirect(url_for("index"))

    rows = []

    for c in app.last_results:
        rows.append({
            "Title": c.get("title"),
            "Status": c.get("status"),
            "Verification Score": c.get("verification_score"),
            "Relevancy Score": c.get("relevancy_score"),
            "Phase1 Score": c.get("phase1_score"),
        })

    df = pd.DataFrame(rows)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    df.to_csv(tmp.name, index=False)

    return send_file(tmp.name, as_attachment=True, download_name="results.csv")


# -------------------------------------------------
# DOWNLOAD FULL REPORT PDF
# -------------------------------------------------
# @app.route("/download_pdf")
# def download_pdf():

#     tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

#     pdf = FPDF()
#     pdf.add_page()
#     pdf.set_font("Arial", size=12)

#     pdf.multi_cell(0, 8, f"Source PDF: {app.last_uploaded_filename}")
#     pdf.multi_cell(0, 8, f"Citation validation Score: {app.last_phase1_score}")
#     pdf.multi_cell(0, 8, f"AI Percentage: {app.last_ai_percentage}%")
#     pdf.multi_cell(0, 8, f"Drift Percentage: {app.last_drift_percentage}%")
#     pdf.multi_cell(0, 8, f"Final Authenticity Score: {app.last_final_percentage}%")

#     pdf.output(tmp.name)

#     return send_file(tmp.name, as_attachment=True, download_name="full_report.pdf")

@app.route("/download_pdf")
def download_pdf():

    import re

    if not app.last_results:
        flash("No results to download", "warning")
        return redirect(url_for("index"))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "PaperTrust - Authenticity Verification Report", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 11)

    def clean_text_pdf(txt):
        return re.sub(r"[^\x00-\xFF]", "", str(txt))

    # -------------------------------------------------
    # DOCUMENT SUMMARY
    # -------------------------------------------------
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Document Summary", ln=True)

    pdf.set_font("Helvetica", "", 11)

    pdf.multi_cell(0, 6, f"Source PDF: {clean_text_pdf(app.last_uploaded_filename)}")
    pdf.multi_cell(0, 6, f"Citation Validation Score: {clean_text_pdf(app.last_phase1_score)}")
    pdf.multi_cell(0, 6, f"AI Generated Content: {clean_text_pdf(app.last_ai_percentage)}%")
    pdf.multi_cell(0, 6, f"Logical Drift Percentage: {clean_text_pdf(app.last_drift_percentage)}%")
    pdf.multi_cell(0, 6, f"Final Authenticity Score: {clean_text_pdf(app.last_final_percentage)}%")

    pdf.ln(5)

    # -------------------------------------------------
    # PHASE 1 SUMMARY
    # -------------------------------------------------
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Phase 1: Citation Validation Summary", ln=True)

    pdf.set_font("Helvetica", "", 11)

    real = sum(1 for c in app.last_results if c.get("status") == "REAL")
    fake = sum(1 for c in app.last_results if c.get("status") == "FAKE")
    uncertain = sum(1 for c in app.last_results if c.get("status") == "UNCERTAIN")

    pdf.multi_cell(0, 6, f"Real Citations: {real}")
    pdf.multi_cell(0, 6, f"Fake Citations: {fake}")
    pdf.multi_cell(0, 6, f"Uncertain Citations: {uncertain}")

    pdf.ln(5)

    # -------------------------------------------------
    # CONTEXT SIMILARITY SUMMARY
    # -------------------------------------------------
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Context Similarity Summary", ln=True)

    pdf.set_font("Helvetica", "", 11)

    relevant = sum(1 for c in app.last_results if c.get("relevancy_score", 0) >= 0.40)
    weak = sum(1 for c in app.last_results if 0.30 <= c.get("relevancy_score", 0) < 0.40)
    irrelevant = sum(1 for c in app.last_results if c.get("relevancy_score", 0) < 0.30)

    pdf.multi_cell(0, 6, f"Relevant Citations: {relevant}")
    pdf.multi_cell(0, 6, f"Weak Citations: {weak}")
    pdf.multi_cell(0, 6, f"Irrelevant Citations: {irrelevant}")

    pdf.ln(5)

    # -------------------------------------------------
    # PHASE 2 SUMMARY
    # -------------------------------------------------
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Phase 2: AI Content Detection", ln=True)

    pdf.set_font("Helvetica", "", 11)

    pdf.multi_cell(0, 6, f"AI Generated Content: {clean_text_pdf(app.last_ai_percentage)}%")
    pdf.multi_cell(0, 6, f"Human Written Content: {100 - app.last_ai_percentage}%")

    pdf.ln(5)

    # -------------------------------------------------
    # PHASE 3 SUMMARY
    # -------------------------------------------------
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Phase 3: Logical Drift Detection", ln=True)

    pdf.set_font("Helvetica", "", 11)

    pdf.multi_cell(0, 6, f"Logical Drift Detected: {clean_text_pdf(app.last_drift_percentage)}%")

    pdf.ln(8)

    # -------------------------------------------------
    # DETAILED CITATION RESULTS
    # -------------------------------------------------
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Detailed Citation Results", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)

    for i, c in enumerate(app.last_results, start=1):

        pdf.multi_cell(0, 6, f"{i}. {clean_text_pdf(c.get('title', 'Unknown'))}")

        pdf.multi_cell(0, 6, f"   Status: {clean_text_pdf(c.get('status', ''))}")
        pdf.multi_cell(0, 6, f"   Verification Score: {clean_text_pdf(c.get('verification_score', ''))}")
        pdf.multi_cell(0, 6, f"   Context Similarity: {clean_text_pdf(c.get('context_similarity', ''))}")

        pdf.multi_cell(0, 6, "   Matches:")

        for m in c.get("matches", []):
            pdf.multi_cell(
                0,
                6,
                f"       - {clean_text_pdf(m.get('source',''))}: "
                f"{clean_text_pdf(m.get('title',''))} "
                f"(title_score={clean_text_pdf(m.get('title_score',''))}, "
                f"author_score={clean_text_pdf(m.get('author_score',''))})"
            )

        pdf.ln(4)

    pdf.output(tmp.name)

    return send_file(tmp.name, as_attachment=True, download_name="analysis_report.pdf")


# -------------------------------------------------
# DOWNLOAD AI PDF
# -------------------------------------------------
@app.route("/download_ai_pdf")
def download_ai_pdf():
    return send_file(os.path.join(UPLOAD_FOLDER, "ai_highlighted.pdf"), as_attachment=True)


# -------------------------------------------------
# DOWNLOAD DRIFT PDF
# -------------------------------------------------
@app.route("/download_drift_pdf")
def download_drift_pdf():
    return send_file(os.path.join(UPLOAD_FOLDER, "drift_highlighted.pdf"), as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)