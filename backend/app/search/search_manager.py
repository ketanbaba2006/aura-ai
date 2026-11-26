"""
AURA AI Search Manager
Orchestrates search cascade: Memory -> KB -> Web.
Fetches from multiple providers in parallel with timeout handling.
Includes duplicate detection, smart ranking, and LLM-based summarization/comparison.
"""

import asyncio
import logging
import time
import httpx
from dataclasses import dataclass

from app.config import settings
from app.search.google_search import GoogleSearchModule
from app.search.result_ranker import ResultRanker
from app.search.content_extractor import ContentExtractor
from app.core.llm_client import llm_client
from app.memory.memory_engine import memory_engine
from app.knowledge.knowledge_manager import knowledge_manager

logger = logging.getLogger(__name__)


@dataclass
class CachedSearch:
    """A cached search result with expiry."""
    query: str
    results: list[dict]
    summary: str
    comparison: str
    path_taken: list[str]
    timestamp: float
    search_time: float


class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, max_per_minute: int = 6):
        self.max_per_minute = max_per_minute
        self.timestamps: list[float] = []

    def can_search(self) -> bool:
        """Check if we can perform a search."""
        now = time.time()
        # Remove timestamps older than 60s
        self.timestamps = [t for t in self.timestamps if now - t < 60]
        return len(self.timestamps) < self.max_per_minute

    def record(self) -> None:
        """Record a search timestamp."""
        self.timestamps.append(time.time())

    def wait_time(self) -> float:
        """How long to wait before next search is allowed."""
        if self.can_search():
            return 0
        oldest = min(self.timestamps)
        return max(0, 60 - (time.time() - oldest))


class SearchManager:
    """
    Orchestrates the full search pipeline:
    1. Check memory first
    2. Check knowledge base second
    3. Query parallel web providers third
    4. Run duplicate detection and ranking
    5. Summarize and compare sources via LLM
    6. Cache results
    """

    def __init__(self):
        self.google = GoogleSearchModule()
        self.extractor = ContentExtractor()
        self.ranker = ResultRanker()
        self.rate_limiter = RateLimiter(max_per_minute=10)

        # Cache: {normalized_query: CachedSearch}
        self._cache: dict[str, CachedSearch] = {}
        self._cache_ttl = settings.SEARCH_CACHE_TTL

    async def initialize(self) -> None:
        """Initialize Playwright browser (only initialized when Google is used)."""
        await self.google.initialize()

    async def shutdown(self) -> None:
        """Shutdown browser."""
        await self.google.shutdown()

    async def search(
        self,
        query: str,
        conversation_id: str | None = None,
        providers: list[str] | None = None,
        cascade: bool = True,
        max_results: int | None = None,
    ) -> dict:
        """
        Perform unified cascading search.

        Returns dict with:
        - query: str
        - results: list[dict]
        - summary: str
        - comparison: str
        - path_taken: list[str]
        - cached: bool
        - search_time: float
        - error: str | None
        """
        start_time = time.time()
        normalized_query = query.lower().strip()
        max_results = max_results or settings.SEARCH_MAX_RESULTS
        
        path_taken = []

        # 0. Check cache first
        cached = self._get_cached(normalized_query)
        if cached:
            logger.info(f"Cache hit for: {query}")
            return {
                "query": query,
                "results": cached.results,
                "summary": cached.summary,
                "comparison": cached.comparison,
                "path_taken": cached.path_taken,
                "cached": True,
                "search_time": 0.0,
                "error": None,
            }

        # --- Priority 1: Search Memory First ---
        if cascade and conversation_id:
            try:
                mem_matches = await memory_engine.search_memory(query, conversation_id, limit=3)
                # Find high relevance semantic memories
                high_rel_mems = [m for m in mem_matches if m.relevance > 0.85]
                if high_rel_mems:
                    path_taken.append("memory_hit")
                    logger.info(f"Cascade Memory hit for: {query}")
                    
                    # Call LLM to summarize based on recalled memories
                    mem_context = "\n".join([f"- [Recalled Memory]: \"{m.content}\"" for m in high_rel_mems])
                    system_prompt = (
                        "You are AURA's Memory Recall Synthesis engine. "
                        "Draft a direct answer using ONLY the recalled user conversation memory context. "
                        "Include inline bracketed citations like [1] where appropriate. "
                        "Return a JSON block with keys 'summary' and 'comparison' (state that this was retrieved from short-term memory)."
                    )
                    prompt = f"Query: {query}\n\nRecalled Context:\n{mem_context}"
                    
                    res_json = await llm_client.generate_json(prompt, system_prompt=system_prompt)
                    summary = res_json.get("summary", "") or res_json.get("raw", "")
                    comparison = res_json.get("comparison", "Recalled from conversation memory.")
                    
                    results = [{
                        "title": "Recalled Chat Memory",
                        "url": f"/conversations/{conversation_id}/memory",
                        "snippet": m.content,
                        "provider": "Memory",
                        "score": m.relevance,
                        "duplicates": []
                    } for m in high_rel_mems]
                    
                    search_time = round(time.time() - start_time, 2)
                    return {
                        "query": query,
                        "results": results,
                        "summary": summary,
                        "comparison": comparison,
                        "path_taken": path_taken,
                        "cached": False,
                        "search_time": search_time,
                        "error": None
                    }
                else:
                    path_taken.append("memory_skipped")
            except Exception as e:
                logger.error(f"Cascade memory search error: {e}")
                path_taken.append("memory_error")

        # --- Priority 2: Search Knowledge Base Second ---
        if cascade and conversation_id:
            try:
                kb_matches = await knowledge_manager.search_knowledge(query, conversation_id, limit=3)
                high_rel_kb = [k for k in kb_matches if k.score > 0.78]
                if high_rel_kb:
                    path_taken.append("kb_hit")
                    logger.info(f"Cascade KB hit for: {query}")
                    
                    # Call LLM to summarize based on document chunks
                    kb_context = ""
                    for idx, match in enumerate(high_rel_kb, 1):
                        kb_context += f"[{idx}] Source Document: {match.filename}\nContent:\n{match.content}\n\n"
                        
                    system_prompt = (
                        "You are AURA's Knowledge Base Synthesis engine. "
                        "Draft a direct answer using ONLY the uploaded documents chunks. "
                        "Always use inline bracketed citations corresponding to the source indices (e.g. [1]). "
                        "Return a JSON block with keys 'summary' and 'comparison' (state how the document sources align or differ)."
                    )
                    prompt = f"Query: {query}\n\nKnowledge Base Chunks:\n{kb_context}"
                    
                    res_json = await llm_client.generate_json(prompt, system_prompt=system_prompt)
                    summary = res_json.get("summary", "") or res_json.get("raw", "")
                    comparison = res_json.get("comparison", "Retrieved from local documents.")
                    
                    results = [{
                        "title": f"Document: {k.filename}",
                        "url": f"/conversations/{conversation_id}/documents/{k.doc_id}",
                        "snippet": k.content[:300] + "...",
                        "provider": "Knowledge Base",
                        "score": k.score,
                        "duplicates": []
                    } for k in high_rel_kb]
                    
                    search_time = round(time.time() - start_time, 2)
                    return {
                        "query": query,
                        "results": results,
                        "summary": summary,
                        "comparison": comparison,
                        "path_taken": path_taken,
                        "cached": False,
                        "search_time": search_time,
                        "error": None
                    }
                else:
                    path_taken.append("kb_skipped")
            except Exception as e:
                logger.error(f"Cascade knowledge base search error: {e}")
                path_taken.append("kb_error")

        # --- Priority 3: Search Web Third ---
        path_taken.append("web_search")
        if not self.rate_limiter.can_search():
            wait = self.rate_limiter.wait_time()
            return {
                "query": query,
                "results": [],
                "summary": "Rate limit hit.",
                "comparison": "N/A",
                "path_taken": path_taken,
                "cached": False,
                "search_time": 0.0,
                "error": f"Rate limited. Try again in {wait:.0f} seconds.",
            }
        
        self.rate_limiter.record()

        # Run multi-provider queries in parallel with hard 4.5s timeout
        web_results = await self._run_parallel_web_queries(query, providers, max_results)
        
        if not web_results:
            return {
                "query": query,
                "results": [],
                "summary": "No web results could be retrieved in time.",
                "comparison": "N/A",
                "path_taken": path_taken,
                "cached": False,
                "search_time": round(time.time() - start_time, 2),
                "error": "No web results found (possible timeouts or connection issues)",
            }

        # Rank and de-duplicate results
        ranked_results = self.ranker.rank(web_results, query)
        
        # Limit to max results
        final_results = ranked_results[:max_results]

        # Call LLM to summarize & compare
        summary = "No summary generated."
        comparison = "No source comparison generated."
        
        if final_results:
            try:
                sources_context = ""
                for idx, r in enumerate(final_results, 1):
                    sources_context += f"[{idx}] URL: {r.get('url', 'N/A')}\nTitle: {r.get('title', 'N/A')}\nSnippet: {r.get('snippet', 'N/A')}\nProvider: {r.get('provider', 'N/A')}\n\n"
                
                system_prompt = (
                    "You are AURA's Search Engine Synthesis engine. "
                    "Read the provided search sources and synthesize an answer to the query.\n"
                    "Requirements:\n"
                    "1. Construct a clear summary ('summary' key) answering the user request. Use inline bracketed citation tags (like [1], [2]) linking assertions to source indices.\n"
                    "2. Construct an explicit comparison ('comparison' key) evaluating source alignment, discrepancies, or consensus.\n"
                    "Return strictly a JSON object with 'summary' and 'comparison' fields."
                )
                prompt = f"Query: {query}\n\nWeb Search Sources:\n{sources_context}"
                
                res_json = await llm_client.generate_json(prompt, system_prompt=system_prompt)
                summary = res_json.get("summary", "") or res_json.get("raw", "")
                comparison = res_json.get("comparison", "")
            except Exception as e:
                logger.error(f"Failed to generate LLM search summary: {e}")
                summary = f"Synthesized Summary: (LLM Error: {e})"

        search_time = round(time.time() - start_time, 2)

        # Cache final results
        self._cache[normalized_query] = CachedSearch(
            query=query,
            results=final_results,
            summary=summary,
            comparison=comparison,
            path_taken=path_taken,
            timestamp=time.time(),
            search_time=search_time
        )

        return {
            "query": query,
            "results": final_results,
            "summary": summary,
            "comparison": comparison,
            "path_taken": path_taken,
            "cached": False,
            "search_time": search_time,
            "error": None
        }

    async def _run_parallel_web_queries(
        self, query: str, providers: list[str] | None, max_results: int
    ) -> list[dict]:
        """Perform concurrent provider queries with timeout bounds."""
        from app.search.providers import query_provider
        
        # Default providers list
        if not providers:
            providers = ["google", "duckduckgo", "wikipedia", "mdn", "stackoverflow", "reddit", "arxiv", "youtube", "github", "docs"]

        # Normalize names
        providers_lower = [p.lower() for p in providers]

        web_results = []
        tasks = []

        async with httpx.AsyncClient() as client:
            # 1. Playwright Google Scraper Task
            google_task = None
            if "google" in providers_lower:
                async def run_google():
                    try:
                        await self.initialize()
                        results = await self.google.search(query, num_results=max_results + 1)
                        return [{
                            "title": r.title,
                            "url": r.url,
                            "snippet": r.snippet,
                            "provider": "Google",
                            "score": 0.0
                        } for r in results]
                    except Exception as e:
                        logger.warning(f"Google search error: {e}")
                        return []
                google_task = asyncio.create_task(run_google())
                tasks.append(google_task)

            # 2. HTTP providers tasks
            for provider in providers:
                if provider.lower() == "google":
                    continue
                tasks.append(asyncio.create_task(query_provider(provider, query, client)))

            if not tasks:
                return []

            # Wait with a strict 4.5 seconds timeout limit
            done, pending = await asyncio.wait(tasks, timeout=4.5)

            # Cancel lagging queries
            for task in pending:
                task.cancel()

            # Gather completed results
            for task in done:
                try:
                    res = task.result()
                    if res:
                        web_results.extend(res)
                except Exception as e:
                    logger.warning(f"Search provider task exception: {e}")

        return web_results

    def _get_cached(self, query: str) -> CachedSearch | None:
        """Get cached search result."""
        cached = self._cache.get(query)
        if not cached:
            return None

        if (time.time() - cached.timestamp) > self._cache_ttl:
            del self._cache[query]
            return None

        return cached

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        now = time.time()
        active = {
            k: v for k, v in self._cache.items()
            if now - v.timestamp < self._cache_ttl
        }
        return {
            "total_cached": len(self._cache),
            "active_cached": len(active),
            "queries": [
                {
                    "query": v.query,
                    "result_count": len(v.results),
                    "age_seconds": round(now - v.timestamp),
                    "search_time": v.search_time,
                }
                for v in active.values()
            ],
        }

    def clear_cache(self) -> None:
        """Clear all cached searches."""
        self._cache.clear()


# Global instance
search_manager = SearchManager()
