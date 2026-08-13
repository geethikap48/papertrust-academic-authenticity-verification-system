# utils/context_similarity.py
from sentence_transformers import SentenceTransformer, util
import re
from rapidfuzz import fuzz

# Load model once globally
_model = SentenceTransformer("all-MiniLM-L6-v2")

def extract_context_sentences(text):
    """Return list of sentences that look like in-text citations (heuristic)."""
    matches = re.findall(
        r"([^.]*\[[0-9]{1,3}\][^.]*\.)|([^.]*\([^)]*\)[^.]*\.)",
        text,
        flags=re.S
    )
    cleaned = [(a or b).strip() for a, b in matches]
    return cleaned

def compute_metadata_similarity(local_meta, matched_meta):
    """Compare title, author, and keywords for metadata-based similarity."""
    title_sim = fuzz.token_sort_ratio(local_meta.get("title", ""), matched_meta.get("title", "")) / 100
    author_sim = fuzz.token_sort_ratio(
        " ".join(local_meta.get("authors", [])),
        " ".join(matched_meta.get("authors", []))
    ) / 100
    keyword_sim = fuzz.token_sort_ratio(
        " ".join(local_meta.get("keywords", [])),
        " ".join(matched_meta.get("keywords", []))
    ) / 100
    return round((0.5 * title_sim + 0.3 * author_sim + 0.2 * keyword_sim), 2)

def compute_citation_mention_rate(full_text, title):
    """Count how many times the cited paper (or author keywords) appear."""
    if not title:
        return 0
    occurrences = len(re.findall(re.escape(title.split()[0]), full_text, flags=re.I))
    total_sentences = max(len(re.split(r"[.!?]", full_text)), 1)
    return round(min(occurrences / total_sentences, 1.0), 3)  # normalized

def add_context_similarity(full_text, contexts, verified_citations):
    """
    Adds context-based + metadata + mention-rate similarity and computes final relevancy score.
    Also collects irrelevant contexts per reference for visualization.
    """
    results = []

    for i, cit in enumerate(verified_citations):
        # Skip context similarity for clear fakes
        if cit.get("status") == "❌ Fake":
            cit["context_similarity"] = "Irrelevant ❌"
            cit["relevancy_score"] = 0.0
            cit["irrelevant_contexts"] = []
            results.append(cit)
            continue

        # === CONTEXT SIMILARITY ===
        context_text = contexts[i] if i < len(contexts) else ""
        compare_text = ""
        for m in cit.get("matches", []):
            if m.get("abstract"):
                compare_text = m["abstract"]
                break
        if not compare_text and cit.get("matches"):
            compare_text = cit["matches"][0].get("title", "")
        if not compare_text:
            compare_text = cit.get("title", "")

        if context_text and compare_text:
            emb = _model.encode([context_text, compare_text], convert_to_tensor=True)
            content_sim = util.cos_sim(emb[0], emb[1]).item()
        else:
            content_sim = 0

        # === METADATA SIMILARITY ===
        meta_sim = 0
        if cit.get("matches"):
            meta_sim = compute_metadata_similarity(cit, cit["matches"][0])

        # === CITATION MENTION RATE ===
        mention_rate = compute_citation_mention_rate(full_text, cit.get("title", ""))

        # === FINAL WEIGHTED RELEVANCY ===
        relevancy = round((0.5 * meta_sim + 0.3 * content_sim + 0.2 * mention_rate), 2)

        # === LABEL CLASSIFICATION ===
        if relevancy >= 0.40:
            label = f"Relevant ✅ ({relevancy})"
        elif relevancy >= 0.30:
            label = f"Weak ⚠️ ({relevancy})"
        else:
            label = f"Irrelevant ❌ ({relevancy})"

        # === Irrelevant Contexts Detection ===
        irrelevant_contexts = []
        if relevancy < 0.30 and context_text.strip():
            irrelevant_contexts.append({
                "paragraph": context_text.strip()[:500] + ("..." if len(context_text) > 500 else ""),
                "similarity_score": round(content_sim, 2)
            })

        cit.update({
            "metadata_similarity": meta_sim,
            "content_similarity": round(content_sim, 2),
            "mention_rate": mention_rate,
            "relevancy_score": relevancy,
            "context_similarity": label,
            "irrelevant_contexts": irrelevant_contexts
        })

        results.append(cit)

    return results
