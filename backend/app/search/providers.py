"""
AURA AI Search Engine Providers
Contains lightweight async query connectors for multiple search providers.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus, urlparse, parse_qs
from html.parser import HTMLParser
import httpx

logger = logging.getLogger(__name__)

# User agents for rotation/requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Documentation mapping
DOC_DOMAINS = {
    "python": "docs.python.org",
    "react": "react.dev",
    "rust": "docs.rs",
    "fastapi": "fastapi.tiangolo.com",
    "nextjs": "nextjs.org/docs",
    "typescript": "typescriptlang.org/docs",
    "golang": "go.dev/doc",
    "go": "go.dev/doc",
    "kubernetes": "kubernetes.io/docs",
    "docker": "docs.docker.com",
    "aws": "docs.aws.amazon.com",
    "postgresql": "postgresql.org/docs",
    "sqlite": "sqlite.org",
    "django": "docs.djangoproject.com",
    "flask": "flask.palletsprojects.com",
    "nodejs": "nodejs.org/docs",
    "npm": "docs.npmjs.com",
}


class DDGHTMLParser(HTMLParser):
    """Parses DuckDuckGo HTML search results page."""
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_item = None
        self.in_title = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")

        # Target results container
        if tag == "div" and "result" in class_name and "results_links" in class_name:
            self.current_item = {
                "title": "",
                "url": "",
                "snippet": "",
                "provider": "DuckDuckGo",
                "score": 0.0
            }

        if self.current_item:
            if tag == "a" and "result__a" in class_name:
                href = attrs_dict.get("href", "")
                if "uddg=" in href:
                    try:
                        parsed = urlparse(href)
                        qs = parse_qs(parsed.query)
                        if "uddg" in qs:
                            href = qs["uddg"][0]
                    except Exception:
                        pass
                self.current_item["url"] = href
                self.in_title = True
            elif tag == "a" and "result__snippet" in class_name:
                self.in_snippet = True

    def handle_endtag(self, tag):
        if tag == "a":
            self.in_title = False
            self.in_snippet = False
        elif tag == "div" and self.current_item and not self.in_title and not self.in_snippet:
            # Check if we should save completed item
            if self.current_item.get("url") and self.current_item.get("title"):
                url = self.current_item["url"]
                if not any(r["url"] == url for r in self.results):
                    # Clean whitespaces
                    self.current_item["title"] = self.current_item["title"].strip()
                    self.current_item["snippet"] = self.current_item["snippet"].strip()
                    self.results.append(self.current_item)
                self.current_item = None

    def handle_data(self, data):
        if self.current_item:
            if self.in_title:
                self.current_item["title"] += data
            elif self.in_snippet:
                self.current_item["snippet"] += data


class BingHTMLParser(HTMLParser):
    """Parses Bing HTML search results page."""
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_item = None
        self.in_title = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")

        if tag == "li" and "b_algo" in class_name:
            self.current_item = {
                "title": "",
                "url": "",
                "snippet": "",
                "provider": "Bing",
                "score": 0.0
            }

        if self.current_item:
            if tag == "a" and not self.current_item["url"]:
                href = attrs_dict.get("href", "")
                if href and href.startswith("http"):
                    self.current_item["url"] = href
                    self.in_title = True
            elif (tag == "p" or tag == "div" or tag == "span") and ("b_caption" in class_name or "b_lineclamp" in class_name or "b_snippet" in class_name):
                self.in_snippet = True

    def handle_endtag(self, tag):
        if tag == "a" and self.in_title:
            self.in_title = False
        elif (tag == "p" or tag == "div" or tag == "span") and self.in_snippet:
            self.in_snippet = False
        elif tag == "li" and self.current_item:
            if self.current_item.get("url") and self.current_item.get("title"):
                url = self.current_item["url"]
                if not any(r["url"] == url for r in self.results):
                    self.current_item["title"] = self.current_item["title"].strip()
                    self.current_item["snippet"] = self.current_item["snippet"].strip()
                    self.results.append(self.current_item)
            self.current_item = None

    def handle_data(self, data):
        if self.current_item:
            if self.in_title:
                self.current_item["title"] += data
            elif self.in_snippet:
                self.current_item["snippet"] += data


async def query_duckduckgo(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search DuckDuckGo HTML interface."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=4.0)
        if resp.status_code == 200:
            parser = DDGHTMLParser()
            parser.feed(resp.text)
            return parser.results
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
    return []


async def query_bing(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search Bing HTML interface."""
    url = f"https://www.bing.com/search?q={quote_plus(query)}"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=4.0)
        if resp.status_code == 200:
            parser = BingHTMLParser()
            parser.feed(resp.text)
            return parser.results
    except Exception as e:
        logger.warning(f"Bing search error: {e}")
    return []


async def query_wikipedia(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search Wikipedia open API."""
    url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(query)}&utf8=&format=json"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            search_items = data.get("query", {}).get("search", [])
            results = []
            for item in search_items:
                title = item.get("title", "")
                snippet_raw = item.get("snippet", "")
                # strip html tags like <span class="searchmatch">
                snippet = re.sub(r"<[^>]*>", "", snippet_raw).strip()
                results.append({
                    "title": title,
                    "url": f"https://en.wikipedia.org/wiki/{quote_plus(title)}",
                    "snippet": snippet,
                    "provider": "Wikipedia",
                    "score": 0.0
                })
            return results
    except Exception as e:
        logger.warning(f"Wikipedia search error: {e}")
    return []


async def query_mdn(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search MDN documentation index API."""
    url = f"https://developer.mozilla.org/api/v1/search?q={quote_plus(query)}"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            docs = data.get("documents", [])
            results = []
            for doc in docs:
                results.append({
                    "title": doc.get("title", ""),
                    "url": f"https://developer.mozilla.org{doc.get('mdn_url', '')}",
                    "snippet": doc.get("summary", ""),
                    "provider": "MDN",
                    "score": 0.0
                })
            return results
    except Exception as e:
        logger.warning(f"MDN search error: {e}")
    return []


async def query_stackoverflow(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search StackOverflow via StackExchange API."""
    url = f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q={quote_plus(query)}&site=stackoverflow"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            results = []
            for item in items[:5]:
                tags = item.get("tags", [])
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": f"Tags: {', '.join(tags)} | Rep: {item.get('owner', {}).get('reputation', 0)} | Answered: {'Yes' if item.get('is_answered') else 'No'}",
                    "provider": "StackOverflow",
                    "score": 0.0
                })
            return results
    except Exception as e:
        logger.warning(f"StackOverflow search error: {e}")
    return []


async def query_reddit(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search Reddit JSON endpoint."""
    url = f"https://www.reddit.com/search.json?q={quote_plus(query)}&limit=5"
    # Reddit blocks standard python requests; use a unique developer user agent
    headers = {"User-Agent": "AURA-AI-Search/0.1.0 (Developer User)"}
    try:
        resp = await client.get(url, headers=headers, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            results = []
            for child in children:
                item = child.get("data", {})
                selftext = item.get("selftext", "")
                snippet = selftext[:200] + "..." if len(selftext) > 200 else selftext
                if not snippet.strip():
                    snippet = f"Subreddit: r/{item.get('subreddit', '')}"
                else:
                    snippet = f"r/{item.get('subreddit', '')} - {snippet}"
                results.append({
                    "title": item.get("title", ""),
                    "url": f"https://www.reddit.com{item.get('permalink', '')}",
                    "snippet": snippet,
                    "provider": "Reddit",
                    "score": 0.0
                })
            return results
    except Exception as e:
        logger.warning(f"Reddit search error: {e}")
    return []


async def query_arxiv(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search scientific papers on ArXiv XML API."""
    url = f"http://export.arxiv.org/api/query?search_query=all:{quote_plus(query)}&max_results=5"
    try:
        resp = await client.get(url, headers=HEADERS, timeout=4.0)
        if resp.status_code == 200:
            xml_data = resp.text
            root = ET.fromstring(xml_data)
            results = []
            
            # Namespace map for Atom feeds
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                id_el = entry.find("atom:id", ns)
                summary_el = entry.find("atom:summary", ns)
                
                title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""
                url = id_el.text.strip() if id_el is not None and id_el.text else ""
                summary = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""
                
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                    
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": summary,
                    "provider": "ArXiv",
                    "score": 0.0
                })
            return results
    except Exception as e:
        logger.warning(f"ArXiv search error: {e}")
    return []


async def query_github(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search repositories on GitHub."""
    url = f"https://api.github.com/search/repositories?q={quote_plus(query)}&per_page=5"
    # GitHub API requires User-Agent
    headers = {"User-Agent": "AURA-AI-Search/0.1.0"}
    try:
        resp = await client.get(url, headers=headers, timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            results = []
            for item in items:
                lang = item.get("language", "Unknown")
                desc = item.get("description", "") or "No description"
                results.append({
                    "title": item.get("full_name", ""),
                    "url": item.get("html_url", ""),
                    "snippet": f"Language: {lang} | Stars: {item.get('stargazers_count', 0)} | {desc}",
                    "provider": "GitHub",
                    "score": 0.0
                })
            return results
    except Exception as e:
        logger.warning(f"GitHub search error: {e}")
    return []


async def query_youtube(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search YouTube videos via site-restricted DuckDuckGo query for stability."""
    results = await query_duckduckgo(f"site:youtube.com {query}", client)
    for r in results:
        r["provider"] = "YouTube"
    return results


async def query_docs(query: str, client: httpx.AsyncClient) -> list[dict]:
    """Search official documentation by matching query keywords or mapping."""
    query_lower = query.lower()
    matched_domains = []
    
    for kw, domain in DOC_DOMAINS.items():
        if kw in query_lower:
            matched_domains.append(domain)
            
    if matched_domains:
        # Build site restriction query
        site_str = " OR ".join([f"site:{d}" for d in matched_domains])
        doc_query = f"({site_str}) {query}"
    else:
        # Default docs search
        doc_query = f"(site:readthedocs.io OR site:developer.mozilla.org OR site:docs.microsoft.com) {query}"
        
    results = await query_duckduckgo(doc_query, client)
    for r in results:
        r["provider"] = "Official Documentation"
    return results


async def query_provider(provider: str, query: str, client: httpx.AsyncClient) -> list[dict]:
    """Dispatches search to correct provider connector."""
    prov_lower = provider.lower()
    
    if prov_lower == "google":
        # Google search is handled via GoogleSearchModule
        return []
    elif prov_lower == "duckduckgo":
        return await query_duckduckgo(query, client)
    elif prov_lower == "bing":
        return await query_bing(query, client)
    elif prov_lower == "wikipedia":
        return await query_wikipedia(query, client)
    elif prov_lower == "mdn":
        return await query_mdn(query, client)
    elif prov_lower == "stackoverflow":
        return await query_stackoverflow(query, client)
    elif prov_lower == "reddit":
        return await query_reddit(query, client)
    elif prov_lower == "arxiv":
        return await query_arxiv(query, client)
    elif prov_lower == "youtube":
        return await query_youtube(query, client)
    elif prov_lower == "github":
        return await query_github(query, client)
    elif prov_lower == "official documentation" or prov_lower == "docs":
        return await query_docs(query, client)
        
    return []
