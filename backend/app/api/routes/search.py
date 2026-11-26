"""
AURA AI Search API
Direct search endpoints.
"""

import logging

from fastapi import APIRouter, Query

from app.search.search_manager import search_manager
from app.database.schemas import SearchResults, SearchResultItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResults)
async def search(body: dict):
    """
    Perform a cascading multi-provider search.

    Body: {
        "query": "string",
        "conversation_id": "string (optional)",
        "providers": ["provider_name"] (optional),
        "cascade": true/false (optional, default: true),
        "max_results": 4 (optional)
    }
    """
    query = body.get("query", "")
    conversation_id = body.get("conversation_id")
    providers = body.get("providers")
    cascade = body.get("cascade", True)
    max_results = body.get("max_results", 4)

    if not query:
        return SearchResults(query="", error="No query provided")

    result = await search_manager.search(
        query=query,
        conversation_id=conversation_id,
        providers=providers,
        cascade=cascade,
        max_results=max_results,
    )

    return SearchResults(
        query=result["query"],
        results=[
            SearchResultItem(**r) for r in result.get("results", [])
        ],
        summary=result.get("summary", ""),
        comparison=result.get("comparison", ""),
        path_taken=result.get("path_taken", []),
        cached=result.get("cached", False),
        search_time=result.get("search_time", 0.0),
        error=result.get("error"),
    )


@router.get("/cache")
async def get_cache():
    """View cached searches."""
    return search_manager.get_cache_stats()


@router.delete("/cache")
async def clear_cache():
    """Clear search cache."""
    search_manager.clear_cache()
    return {"status": "cleared"}
