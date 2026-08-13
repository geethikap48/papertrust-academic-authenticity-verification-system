# utils/api_helpers.py
import requests
from rapidfuzz import fuzz

# -----------------------
# CrossRef
# -----------------------
def search_crossref(title, max_results=5):
    url = "https://api.crossref.org/works"
    params = {"query.title": title, "rows": max_results}
    try:
        r = requests.get(url, params=params, timeout=12)
        data = r.json().get("message", {}).get("items", [])
    except Exception as e:
        print(f"[CrossRef] ERROR: {e}")
        return []

    results = []
    for it in data:
        t = it.get("title", [""])[0] if it.get("title") else ""
        authors = []
        for a in it.get("author", []):
            name = (a.get("given", "") + " " + a.get("family", "")).strip()
            if name:
                authors.append(name)
        doi = it.get("DOI")
        results.append({"title": t, "authors": authors, "doi": doi, "abstract": None, "year": None})
    return results

# -----------------------
# Semantic Scholar
# -----------------------
def search_semantic_scholar(title, max_results=5):
    import re
    clean_title = re.sub(r'\s+', ' ', title).strip().rstrip(".")
    # use up to 20 words to reduce missed matches
    query = " ".join(clean_title.split()[:20]) if len(clean_title.split()) > 20 else clean_title

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": max_results,
        "fields": "title,abstract,authors,year,externalIds"
    }
    headers = {"User-Agent": "FakePaperDetector/1.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=12)
        if r.status_code != 200:
            print(f"[SemanticScholar] HTTP {r.status_code} for query: {query}")
            return []
        data = r.json().get("data", [])
    except Exception as e:
        print(f"[SemanticScholar] ERROR for '{query}': {e}")
        return []

    results = []
    for d in data:
        authors = [a.get("name") for a in d.get("authors", []) if a.get("name")]
        results.append({
            "title": d.get("title", ""),
            "authors": authors,
            "abstract": d.get("abstract"),
            "doi": d.get("externalIds", {}).get("DOI"),
            "year": d.get("year")
        })
    return results

# -----------------------
# OpenAlex
# -----------------------
def search_openalex(title, limit=5):
    url = f"https://api.openalex.org/works?filter=title.search:{title}&per-page={limit}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json().get("results", [])
        results = []
        for item in data:
            authors = [auth["author"]["display_name"] for auth in item.get("authorships", [])]
            results.append({
                "title": item.get("title", ""),
                "authors": authors,
                "doi": item.get("doi"),
                "year": item.get("publication_year")
            })
        return results
    except Exception as e:
        print(f"[OpenAlex] ERROR: {e}")
        return []

# -----------------------
# BASE API
# -----------------------
def search_base(title, max_results=5):
    url = "https://www.base-search.net/Search/Results"
    params = {
        "q": f'title:"{title}"',
        "output": "json",
        "size": max_results
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code != 200:
            print(f"[BASE] HTTP {r.status_code} for title: {title}")
            return []
        data = r.json().get("records", [])
        results = []
        for d in data:
            authors = [a.get("name") for a in d.get("creators", []) if a.get("name")]
            results.append({
                "title": d.get("title", ""),
                "authors": authors,
                "doi": d.get("doi"),
                "year": d.get("date"),
            })
        return results
    except Exception as e:
        print(f"[BASE] ERROR for '{title}': {e}")
        return []

# -----------------------
# Fuzzy Helpers
# -----------------------
def fuzzy_title_match(title, candidate_titles):
    best_score = 0
    best_title = None
    if not title:
        return None, 0
    for c in candidate_titles:
        if not c:
            continue
        score = fuzz.token_set_ratio(title, c)
        if score > best_score:
            best_score = score
            best_title = c
    return best_title, best_score

def author_match(authors, candidate_authors):
    if not authors or not candidate_authors:
        return 0
    best = 0
    for a in authors:
        for c in candidate_authors:
            s = fuzz.token_set_ratio(a, c)
            if s > best:
                best = s
    return best
