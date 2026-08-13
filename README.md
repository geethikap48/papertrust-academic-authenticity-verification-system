# PaperTrust — Academic Authenticity Verification System

PaperTrust is a Python-based academic paper analysis system designed to identify potentially unreliable or fabricated research content through citation verification, semantic relevance analysis, AI-generated content analysis, and logical consistency assessment.

The system processes an academic PDF and performs multiple stages of analysis, combining document processing, scholarly metadata retrieval, fuzzy matching, natural language processing, and semantic embeddings.



---

## 1. Project Overview

The increasing availability of automatically generated and manipulated academic content creates challenges in evaluating the reliability of research papers. Fabricated references, irrelevant citations, AI-generated text, and semantic inconsistencies can reduce the credibility of academic documents.

PaperTrust addresses these challenges through a multi-phase analysis pipeline:

1. Citation Authenticity and Relevance Analysis
2. AI-Generated Content Analysis
3. Logical and Semantic Consistency Analysis

The system is implemented as a Flask-based web application with supporting NLP, PDF-processing, scholarly metadata, and machine-learning components.

---

## 2. Objectives

The primary objectives of PaperTrust are:

* Extract bibliographic references from academic PDF documents.
* Identify and process scanned PDFs using OCR when necessary.
* Verify extracted citations against scholarly metadata sources.
* Compare citation metadata using fuzzy title and author matching.
* Determine whether cited publications are relevant to their surrounding context.
* Detect potential AI-generated writing patterns.
* Analyze semantic changes and potential logical drift across document sections.
* Provide confidence and analysis scores through a web-based interface.
* Generate structured analysis results for further examination.

---

## 3. System Architecture

The overall processing pipeline can be represented as:

```text
                         Academic PDF
                              |
                              v
                    PDF Processing Layer
                              |
                  +-----------+-----------+
                  |                       |
                  v                       v
           Text Extraction             OCR
                  |                       |
                  +-----------+-----------+
                              |
                              v
                     Citation Extraction
                              |
            +-----------------+-----------------+
            |                 |                 |
            v                 v                 v
       Phase 1            Phase 2            Phase 3
   Citation Analysis    AI Detection      Logical Analysis
            |                 |                 |
            v                 v                 v
   Scholarly APIs        Sapling API       Embeddings
   and Matching         + Heuristics       and Drift
            |                 |                 |
            +-----------------+-----------------+
                              |
                              v
                       Final Analysis
                              |
                              v
                       Flask Web Interface
```

---

## 4. Analysis Phases

### Phase 1 — Citation Authenticity and Relevance

Phase 1 focuses on determining whether references extracted from an academic paper correspond to genuine scholarly publications and whether the cited publication is semantically relevant to its citation context.

The system uses GROBID to extract structured bibliographic information from academic documents.

Extracted metadata may include:

* Title
* Authors
* Publication year
* DOI
* Raw reference text

The extracted references are subsequently searched across multiple scholarly metadata services.

### Scholarly Sources

* CrossRef
* OpenAlex
* Semantic Scholar

Because metadata can differ between sources, the system uses multiple sources rather than relying on a single database.

### Metadata Matching

The verification process compares:

* Reference title
* Retrieved publication title
* Author information
* Publication metadata

Fuzzy string matching is used to handle differences in:

* Capitalization
* Punctuation
* Abbreviations
* Formatting
* Minor title variations

### Citation Classification

The verification process produces confidence information that can be used to classify references into categories such as:

* Verified
* Uncertain
* Potentially fabricated

A citation that cannot be found in one database is not automatically treated as fabricated. Multiple scholarly sources are considered before determining the verification result.

---

## 5. Citation Context Similarity

Finding a publication with a matching title is not sufficient to establish that a citation is appropriate.

PaperTrust therefore analyzes the context surrounding an in-text citation.

The system uses Sentence-BERT embeddings to represent textual content as numerical vectors and calculates semantic similarity between the citation context and information associated with the cited publication.

The current similarity interpretation is:

| Similarity Score | Interpretation |
| ---------------: | -------------- |
|   0.75 and above | Relevant       |
|      0.50 – 0.74 | Weak           |
|       Below 0.50 | Irrelevant     |

This analysis helps identify citations where the referenced publication exists but may not actually support the claim for which it is cited.

---

## 6. Phase 2 — AI-Generated Content Analysis

Phase 2 analyzes the textual content of the document for characteristics associated with AI-generated or highly structured writing.

The current implementation uses the Sapling AI Detection API together with local heuristic analysis.

The analysis includes:

* Text chunking
* Sentence segmentation
* AI probability estimation
* Repetition analysis
* Lexical diversity
* Phrase repetition
* Identification of potentially AI-like sentences

The system calculates an estimated AI percentage and corresponding human percentage based on the available analysis.

AI detection results should be treated as an analytical indicator rather than definitive proof that text was generated by an AI system.

---

## 7. Phase 3 — Logical and Semantic Consistency

Phase 3 focuses on identifying potential semantic drift and logical inconsistencies across different sections of an academic document.

The implementation uses text embeddings to represent document sections and compare their semantic relationships.

The purpose of this phase is to identify situations where:

* The topic changes unexpectedly.
* Consecutive sections have weak semantic relationships.
* The document contains potential logical or contextual discontinuities.
* The semantic direction of the document changes significantly.

This phase is intended to complement citation and AI-content analysis rather than replace human evaluation of academic quality.

---

## 8. PDF Processing

PaperTrust supports academic PDF processing through multiple libraries and techniques.

The document processing pipeline can include:

* Text-based PDF extraction
* Scanned PDF detection
* OCR using Tesseract
* Image-to-text conversion
* PDF manipulation using PyMuPDF
* PDF processing using pdfplumber
* Result generation using fpdf2

OCR processing allows the system to handle documents where the text layer is unavailable or incomplete.

---

## 9. GROBID Integration

PaperTrust uses GROBID for structured extraction of bibliographic references from academic documents.

GROBID converts scholarly documents into structured representations that can be processed by the citation verification pipeline.

The project uses GROBID through Docker.

### Pull the GROBID Image

```bash
docker pull lfoppiano/grobid:0.8.2
```

### Start GROBID

```bash
docker run -d --name grobid -p 8070:8070 lfoppiano/grobid:0.8.2
```

### Verify the Container

```bash
docker ps
```

The GROBID service is expected to be available at:

```text
http://localhost:8070
```

---

## 10. Technologies Used

### Programming Language

* Python

### Web Development

* Flask
* Flask-CORS
* HTML
* CSS

### Natural Language Processing

* Sentence Transformers
* Sentence-BERT
* Transformers
* NLTK
* Scikit-learn

### Machine Learning

* PyTorch
* Sentence embeddings
* Cosine similarity

### PDF and OCR Processing

* PyMuPDF
* pdfplumber
* PyTesseract
* Pillow
* pdf2image
* fpdf2

### Citation Processing

* GROBID
* CrossRef
* OpenAlex
* Semantic Scholar

### Text Matching

* RapidFuzz

### External AI Detection

* Sapling AI API

### Infrastructure

* Docker

---

## 11. Project Structure

```text
fake_paper/
│
├── README.md
├── .gitignore
├── .env.example
├── app.py
├── calculate_accuracy.py
├── requirements.txt
│
├── fonts/
│   └── PDF generation fonts
│
├── static/
│   └── style.css
│
├── templates/
│   ├── index.html
│   └── results.html
│
└── utils/
    ├── ai_detector.py
    ├── api_helpers.py
    ├── citation_verifier.py
    ├── context_similarity.py
    ├── final_score.py
    ├── grobid_client.py
    ├── logical_drift.py
    ├── pdf_highlighter.py
    ├── pdf_utils.py
    └── phase1_normalizer.py
```

---

## 12. Installation

### Prerequisites

The following software is required:

* Python 3.10 or later
* Docker
* Tesseract OCR
* Git

### Clone the Repository

```bash
git clone https://github.com/geethikap48/papertrust-academic-authenticity-verification-system.git
```

Navigate to the project directory:

```bash
cd papertrust-academic-authenticity-verification-system
```

### Create a Virtual Environment

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 13. Environment Configuration

API credentials are stored outside the source code using environment variables.

Create a `.env` file in the project root:

```text
SAPLING_API_KEYS=your_sapling_api_key
```

Multiple keys can be configured using comma-separated values:

```text
SAPLING_API_KEYS=key1,key2,key3
```

The repository includes `.env.example` as a configuration template.

The actual `.env` file is excluded from version control using `.gitignore`.

Never commit API keys, passwords, access tokens, or other credentials to the repository.

---

## 14. Running the Application

Start the GROBID container:

```bash
docker start grobid
```

Then start the Flask application:

```bash
python app.py
```

The application will display its local address in the terminal. The default Flask development address is typically:

```text
http://127.0.0.1:5000
```

Open the address in a web browser and upload an academic PDF for analysis.

---

## 15. Output

The system provides analysis results through the Flask web interface.

Depending on the analysis phase, results can include:

### Citation Analysis

* Extracted citation information
* Matched scholarly publication
* Authors
* Verification status
* Verification score
* Matching sources

### Context Analysis

* Citation context
* Semantic similarity score
* Relevance classification

### AI Analysis

* Estimated AI percentage
* Estimated human percentage
* Potentially AI-like sentences
* Textual pattern indicators

### Document Analysis

* Semantic drift information
* Logical consistency indicators
* Overall analysis results

---

## 16. Security and Data Handling

The project follows basic credential protection practices.

The following files and directories are excluded from version control:

```text
.env
uploads/
results/
__pycache__/
venv/
```

API credentials are loaded through environment variables rather than being stored directly in the source code.

The `.env.example` file contains only placeholder values and does not contain actual credentials.

---

## 17. Current Project Status

The current implementation provides the core components required for the PaperTrust analysis pipeline, including:

* Academic PDF processing
* OCR-based text extraction
* GROBID-based reference extraction
* Multi-source citation verification
* Fuzzy title and author matching
* Citation-context semantic similarity
* AI-content analysis
* Textual heuristic analysis
* Logical and semantic drift analysis
* Flask-based web interface
* Result generation

The system is intended as a research and academic prototype. Detection results should be interpreted as indicators requiring further human evaluation rather than as definitive judgments of academic misconduct.

---

## 18. Future Enhancements

Potential future improvements include:

* Support for additional citation formats and styles
* Improved reference parsing for complex academic documents
* Additional scholarly metadata providers
* Citation network construction and visualization
* Advanced embedding-trail visualization
* Improved semantic drift detection
* Improved AI-generated content detection
* Confidence calibration using larger evaluation datasets
* Automated benchmarking against labeled academic-paper datasets
* Cloud deployment
* Authentication and user management
* Persistent analysis history
* REST API support

---

## 19. Academic Context

**Project Title:** PaperTrust — Academic Authenticity Verification System

**Domain:** Natural Language Processing, Machine Learning, Information Retrieval, Document Analysis, and Web Application Development

The project demonstrates the application of machine learning and natural language processing techniques to the analysis and validation of academic documents.

---

## 20. Author

**Geethika Prakash**

GitHub:
https://github.com/geethikap48

---

## 21. License

This project is currently developed for academic and educational purposes.

The project does not currently include a formal open-source license. If released for public or commercial use in the future, an appropriate license will be added.
