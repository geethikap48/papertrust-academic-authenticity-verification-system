# utils/citation_verifier.py
import concurrent.futures
from rapidfuzz import fuzz
from .api_helpers import (
    search_semantic_scholar,
    search_crossref,
    search_openalex,
    search_base
)
import re

# -----------------------
# Text Normalization
# -----------------------
def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()

def normalize_author(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r"[.,]", "", name).strip()
    return " ".join(name.split()).lower()

# -----------------------
# Fuzzy Matching
# -----------------------
def title_similarity(t1: str, t2: str) -> int:
    return fuzz.token_sort_ratio(normalize_text(t1), normalize_text(t2))

def author_similarity(list1, list2) -> int:
    """Return % similarity based on overlap of authors"""
    if not list1 or not list2:
        return 0

    scores = []
    for a1 in list1:
        n1 = normalize_author(a1)
        best = 0
        for a2 in list2:
            n2 = normalize_author(a2)
            if not n1 or not n2:
                continue
            if n1 == n2:
                best = 100
            elif n1[0] == n2[0] and n1.split()[-1] == n2.split()[-1]:
                best = max(best, 95)  # e.g., C Manning vs Christopher Manning
            else:
                best = max(best, fuzz.partial_ratio(n1, n2))
        scores.append(best)
    return sum(scores) // len(scores) if scores else 0

def author_match_exists(list1, list2) -> bool:
    """Check if at least one author matches (abbreviated or expanded)"""
    for a1 in list1:
        n1 = normalize_author(a1)
        for a2 in list2:
            n2 = normalize_author(a2)
            if not n1 or not n2:
                continue
            if n1 == n2:
                return True
            if n1[0] == n2[0] and n1.split()[-1] == n2.split()[-1]:
                return True
            if fuzz.partial_ratio(n1, n2) >= 85:
                return True
    return False

# -----------------------
# Citation Verification
# -----------------------
def verify_one(citation: dict):
    title = citation.get("title", "") or ""
    authors = citation.get("authors", []) or []

    results = []
    author_found_anywhere = False

    api_sources = [
        ("CrossRef", search_crossref),
        ("Semantic Scholar", search_semantic_scholar),
        ("OpenAlex", search_openalex),
        ("BASE", search_base),
    ]

    norm_title = normalize_text(title)

    for source_name, func in api_sources:
        try:
            matches = func(title)
        except Exception as e:
            matches = []
            print(f"[ERROR] {source_name} lookup failed: {e}")

        for m in matches:
            m_title = m.get("title", "") or ""
            m_authors = m.get("authors", []) or []
            norm_m_title = normalize_text(m_title)

            # ✅ Exact title match shortcut
            if norm_m_title == norm_title:
                citation["status"] = "✅ Real"
                citation["verification_score"] = 100
                citation["matches"] = [{
                    "source": source_name,
                    "title": m_title,
                    "title_score": 100,
                    "author_score": author_similarity(authors, m_authors),
                    "authors": m_authors,
                    "doi": m.get("doi", "N/A"),
                    "year": m.get("year", "N/A"),
                }]
                return citation

            # Compute fuzzy scores
            t_score = title_similarity(title, m_title)
            a_score = author_similarity(authors, m_authors)
            has_author_match = author_match_exists(authors, m_authors)

            if a_score > 0 or has_author_match:
                author_found_anywhere = True

            results.append({
                "source": source_name,
                "title": m_title,
                "title_score": t_score,
                "author_score": a_score,
                "authors": m_authors,
                "doi": m.get("doi", "N/A"),
                "year": m.get("year", "N/A"),
                "author_match": has_author_match,
            })

    # -----------------------
    # Aggregated decision rules with weighted scoring
    # -----------------------
    status = "⚠️ Unverifiable"
    verification_score = 0
    existence_score = 0

    if results:
        # best result per source
        per_source_best = []
        sources_seen = set()
        for r in results:
            if r["source"] not in sources_seen:
                per_source_best.append(r)
                sources_seen.add(r["source"])
            else:
                # keep best match per source
                for idx, existing in enumerate(per_source_best):
                    if existing["source"] == r["source"]:
                        if (r["title_score"] + r["author_score"]) > (
                            existing["title_score"] + existing["author_score"]
                        ):
                            per_source_best[idx] = r

        # count existence across sources
        confident_sources = [
            r
            for r in per_source_best
            if r["title_score"] >= 80 and (r["author_score"] >= 70 or r["author_match"])
        ]
        existence_score = (len(confident_sources) / len(api_sources)) * 100

        best_match = max(per_source_best, key=lambda r: (r["title_score"], r["author_score"]))
        ts, ascore, has_author = (
            best_match["title_score"],
            best_match["author_score"],
            best_match.get("author_match", False),
        )

        # -----------------------
        # BOOST RULE: exact/near-exact + DOI
        # -----------------------
        for src in per_source_best:
            has_doi = src.get("doi") and src.get("doi") != "N/A"
            if src["title_score"] >= 95 and src["author_score"] >= 90 and has_doi:
                verification_score = 100.0
                status = "✅ Real"
                citation.update({
                    "status": status,
                    "verification_score": verification_score,
                    "existence_score": round(existence_score, 2),
                    "best_match": src,
                    "matches": per_source_best
                })
                return citation
        
           # -----------------------
        # BOOST RULE: strong single-source match even without DOI
        # -----------------------
        for src in per_source_best:
            if src["title_score"] >= 90 and (src["author_score"] >= 70 or src["author_match"]):
                verification_score = max(verification_score, 90.0)
                status = "✅ Real"
                citation.update({
                    "status": status,
                    "verification_score": verification_score,
                    "existence_score": round(existence_score, 2),
                    "best_match": src,
                    "matches": per_source_best
                })
                return citation

        # Weighted scoring
        verification_score = (
            0.5 * existence_score
            + 0.3 * ts
            + 0.2 * ascore
        )

        # Decision thresholds
        if verification_score >= 75 and (ts >= 85 or ascore >= 80):
            status = "✅ Real"
        elif verification_score >= 50:
            status = "⚠️ Unverifiable"
        else:
            status = "❌ Fake"
    else:
        status = "❌ Fake" if not author_found_anywhere else "⚠️ Unverifiable"

    citation.update({
        "status": status,
        "verification_score": round(verification_score, 2),
        "existence_score": round(existence_score, 2),
        "matches": results
    })
    return citation

# -----------------------
# Parallel Verification
# -----------------------
def verify_citations_parallel(citations, max_workers=6):
    verified = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(verify_one, cit) for cit in citations]
        for future in concurrent.futures.as_completed(futures):
            try:
                verified.append(future.result())
            except Exception as e:
                print("[verify_citations_parallel] worker failed:", e)
    return verified
