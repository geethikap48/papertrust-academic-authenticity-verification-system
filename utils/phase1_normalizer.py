# utils/phase1_normalizer.py

"""
Normalize Phase 1 (Citation + Relevance) scores
All outputs are in range [0,1]
"""


def normalize_verification_score(score: float) -> float:
    """
    Convert 0–100 → 0–1 safely
    """
    if score is None:
        return 0.0
    return round(max(0.0, min(score / 100, 1.0)), 3)


def normalize_relevancy_score(score: float) -> float:
    """
    Relevancy already 0–1 but clamp safely
    """
    if score is None:
        return 0.0
    return round(max(0.0, min(score, 1.0)), 3)


def compute_normalized_phase1_score(citation: dict) -> dict:
    """
    Adds:
        verification_norm
        relevancy_norm
        phase1_score (0–1)
    """

    verification_norm = normalize_verification_score(
        citation.get("verification_score", 0)
    )

    relevancy_norm = normalize_relevancy_score(
        citation.get("relevancy_score", 0)
    )

    # Weighted fusion of verification + relevance
    phase1_score = round(
        0.6 * verification_norm +
        0.4 * relevancy_norm,
        3
    )

    citation.update({
        "verification_norm": verification_norm,
        "relevancy_norm": relevancy_norm,
        "phase1_score": phase1_score
    })

    return citation


def normalize_all_phase1(citations: list) -> list:
    return [compute_normalized_phase1_score(c) for c in citations]


def compute_document_phase1_score(citations: list) -> float:
    """
    Average of citation-level normalized scores
    """
    if not citations:
        return 0.0

    scores = [c.get("phase1_score", 0) for c in citations]
    return round(sum(scores) / len(scores), 3)
