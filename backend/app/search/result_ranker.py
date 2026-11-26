"""
AURA AI Result Ranker
Scores, ranks, and de-duplicates search results by relevance and context.
"""

import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Domain credibility scores
CREDIBLE_DOMAINS = {
    "wikipedia.org": 0.9,
    "stackoverflow.com": 0.85,
    "github.com": 0.85,
    "docs.python.org": 0.9,
    "developer.mozilla.org": 0.9,
    "medium.com": 0.6,
    "reddit.com": 0.5,
    "arxiv.org": 0.9,
    "nature.com": 0.9,
    "bbc.com": 0.8,
    "reuters.com": 0.85,
    "nytimes.com": 0.8,
    "theguardian.com": 0.75,
    "cnn.com": 0.7,
    "techcrunch.com": 0.7,
    "arstechnica.com": 0.75,
    "wired.com": 0.7,
}

# Low-quality domains to penalize
LOW_QUALITY_DOMAINS = {
    "pinterest.com", "quora.com", "facebook.com",
    "twitter.com", "x.com", "instagram.com",
    "tiktok.com",
}

class ResultRanker:
    """
    Scores, ranks, and de-duplicates search results.
    """

    def rank(
        self, results: list[dict], query: str
    ) -> list[dict]:
        """
        Rank results by relevance score and nest duplicates.
        """
        if not results:
            return []

        query_terms = self._tokenize(query)
        query_lower = query.lower()

        # 1. Determine query context to apply provider boosts
        is_code = any(k in query_lower for k in [
            "code", "program", "function", "bug", "error", "exception", "class", "method",
            "api", "compile", "run", "git", "install", "npm", "pip", "python", "js", "javascript",
            "html", "css", "rust", "golang", "c++", "java", "react", "fastapi", "nextjs"
        ])
        is_research = any(k in query_lower for k in [
            "arxiv", "paper", "research", "science", "theory", "math", "physics", "formula",
            "study", "explain", "why", "wikipedia", "definition", "history"
        ])
        is_discussion = any(k in query_lower for k in [
            "reddit", "opinion", "review", "thoughts", "versus", "vs", "experience", "best way to"
        ])
        is_video = any(k in query_lower for k in [
            "youtube", "video", "tutorial", "watch", "clip", "screen", "visual"
        ])

        # 2. Score results
        scored = []
        for result in results:
            # Score first
            score = self._score_result(result, query_terms)
            
            # Apply context boosts
            prov = result.get("provider", "").lower()
            if is_code and prov in ["stackoverflow", "mdn", "github", "official documentation"]:
                score += 0.2
            if is_research and prov in ["arxiv", "wikipedia"]:
                score += 0.2
            if is_discussion and prov == "reddit":
                score += 0.2
            if is_video and prov == "youtube":
                score += 0.2

            result["score"] = round(score, 3)
            result["duplicates"] = []
            scored.append(result)

        # 3. Sort by score descending
        scored.sort(key=lambda r: r["score"], reverse=True)

        # 4. De-duplicate (URL normalization + title Token Jaccard Similarity)
        unique_results = []
        seen_urls = set()

        for res in scored:
            url = res.get("url", "")
            norm_url = self._normalize_url(url) if url else ""
            title = res.get("title", "")
            
            is_dup = False
            
            # Check URL match
            if norm_url and norm_url in seen_urls:
                is_dup = True
            
            # Check title similarity with existing unique results
            if not is_dup:
                for unique_res in unique_results:
                    sim = self._title_similarity(title, unique_res.get("title", ""))
                    if sim > 0.75:
                        # Also check if same host or similar
                        u1 = urlparse(url).netloc
                        u2 = urlparse(unique_res.get("url", "")).netloc
                        if u1 == u2:
                            is_dup = True
                            # Attach as duplicate to the unique result
                            unique_res["duplicates"].append(res)
                            break
            
            if is_dup:
                # Find matching unique result to attach URL-based duplicate
                if norm_url:
                    for unique_res in unique_results:
                        if self._normalize_url(unique_res.get("url", "")) == norm_url:
                            unique_res["duplicates"].append(res)
                            break
            else:
                if norm_url:
                    seen_urls.add(norm_url)
                unique_results.append(res)

        return unique_results

    def _normalize_url(self, url: str) -> str:
        """Strip parameters, www, protocol, and trailing slashes for canonical checking."""
        try:
            parsed = urlparse(url.lower())
            netloc = parsed.netloc
            if netloc.startswith("www."):
                netloc = netloc[4:]
            path = parsed.path.rstrip("/")
            return f"{netloc}{path}"
        except Exception:
            return url.lower()

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate Jaccard similarity of token sets between titles."""
        t1_tokens = set(self._tokenize(title1))
        t2_tokens = set(self._tokenize(title2))
        if not t1_tokens or not t2_tokens:
            return 0.0
        return len(t1_tokens & t2_tokens) / len(t1_tokens | t2_tokens)

    def _score_result(self, result: dict, query_terms: list[str]) -> float:
        """Calculate relevance score for a single result."""
        score = 0.0

        # 1. Keyword overlap in title (weight: 0.3)
        title = result.get("title", "").lower()
        title_terms = self._tokenize(title)
        if query_terms and title_terms:
            title_overlap = len(set(query_terms) & set(title_terms)) / len(query_terms)
            score += title_overlap * 0.3

        # 2. Keyword overlap in snippet (weight: 0.2)
        snippet = result.get("snippet", "").lower()
        snippet_terms = self._tokenize(snippet)
        if query_terms and snippet_terms:
            snippet_overlap = len(set(query_terms) & set(snippet_terms)) / len(
                query_terms
            )
            score += snippet_overlap * 0.2

        # 3. Keyword overlap in content (weight: 0.2)
        content = result.get("content", "").lower()
        if content and query_terms:
            content_terms = self._tokenize(content[:2000])
            content_overlap = len(set(query_terms) & set(content_terms)) / len(
                query_terms
            )
            score += content_overlap * 0.2

        # 4. Content length score (weight: 0.15)
        content_length = len(result.get("content", ""))
        if content_length > 500:
            length_score = min(content_length / 2000, 1.0)
            score += length_score * 0.15
        elif result.get("snippet"):
            length_score = min(len(result["snippet"]) / 200, 1.0)
            score += length_score * 0.05

        # 5. Domain credibility (weight: 0.15)
        domain = result.get("source_domain", "")
        if not domain and result.get("url"):
            domain = urlparse(result["url"]).netloc.replace("www.", "")
            
        domain_score = self._domain_score(domain)
        score += domain_score * 0.15

        return score

    def _domain_score(self, domain: str) -> float:
        """Score domain credibility."""
        if not domain:
            return 0.3

        if domain in CREDIBLE_DOMAINS:
            return CREDIBLE_DOMAINS[domain]

        for credible, cred_score in CREDIBLE_DOMAINS.items():
            if domain.endswith(f".{credible}"):
                return cred_score * 0.9

        if domain in LOW_QUALITY_DOMAINS:
            return 0.1

        for low_q in LOW_QUALITY_DOMAINS:
            if domain.endswith(f".{low_q}"):
                return 0.1

        return 0.4

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric, filter short."""
        if not text:
            return []
        words = re.findall(r"[a-z0-9]+", text.lower())
        # Filter stop words and very short tokens
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "about", "it", "its", "this", "that", "these",
            "those", "and", "or", "but", "not", "no", "if", "then",
            "what", "which", "who", "whom", "how", "when", "where", "why",
        }
        return [w for w in words if len(w) > 1 and w not in stop_words]
