"""
AURA AI Web Search Tool
BaseTool wrapper around SearchManager for the tool system.
Supports cascading, summaries, comparisons, and de-duplication.
"""

import logging
from typing import Any

from app.database.schemas import ToolResult
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """
    Web search tool using multi-provider cascade search.
    Checks memory, KB, and parallel web sources.
    """

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web or local workspace files using Google, DuckDuckGo, Bing, "
            "Wikipedia, MDN, StackOverflow, Reddit, ArXiv, GitHub, YouTube, and official documentation. "
            "Returns relevant synthesized facts, source comparisons, and lists of links."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to query the cascade engine",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 4)",
                },
                "cascade": {
                    "type": "boolean",
                    "description": "Whether to run cascade: Memory -> KB -> Web (default: true)",
                },
                "providers": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "google", "duckduckgo", "bing", "wikipedia", "mdn", 
                            "stackoverflow", "reddit", "arxiv", "youtube", 
                            "github", "docs"
                        ]
                    },
                    "description": "List of providers to use (default: all)",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 4)
        cascade = kwargs.get("cascade", True)
        providers = kwargs.get("providers")
        conversation_id = kwargs.get("conversation_id")

        if not query:
            return ToolResult(success=False, error="No search query provided")

        try:
            # Import here to avoid circular imports
            from app.search.search_manager import search_manager

            results = await search_manager.search(
                query=query,
                conversation_id=conversation_id,
                cascade=cascade,
                max_results=max_results,
                providers=providers,
            )

            if results.get("error") and not results.get("results"):
                return ToolResult(success=False, error=results["error"])

            # Format results for LLM context
            output = self._format_results(results)

            return ToolResult(
                success=True,
                output=output,
            )

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ToolResult(success=False, error=f"Search error: {str(e)}")

    def _format_results(self, search_data: dict) -> str:
        """Format search results as readable text for LLM context."""
        results = search_data.get("results", [])
        query = search_data.get("query", "")
        cached = search_data.get("cached", False)
        search_time = search_data.get("search_time", 0)
        summary = search_data.get("summary", "")
        comparison = search_data.get("comparison", "")
        path_taken = search_data.get("path_taken", [])

        if not results:
            return f"No results found for: {query}"

        lines = [
            f"🔍 Cascade Search Results for: \"{query}\"",
            f"   Search Path taken: {' -> '.join(path_taken)}",
            f"   Found {len(results)} sources"
            + (f" (cached)" if cached else f" in {search_time}s"),
            "",
            "━━━ Synthesized Summary ━━━",
            summary,
            "",
            "━━━ Source Comparison ━━━",
            comparison,
            "",
            "━━━ Detailed Sources ━━━"
        ]

        for i, r in enumerate(results, 1):
            lines.append(f"━━━ Result {i}: {r.get('title', 'Untitled')} ━━━")
            lines.append(f"🔗 {r.get('url', '')}")
            lines.append(f"🏢 Provider: {r.get('provider', 'Web')}")

            if r.get("snippet"):
                lines.append(f"📋 {r['snippet']}")

            dups = r.get("duplicates", [])
            if dups:
                lines.append(f"   [Detected {len(dups)} duplicate(s)]:")
                for d in dups:
                    lines.append(f"   - 🔗 {d.get('url')} ({d.get('provider')})")

            lines.append("")

        # Add source list at end
        lines.append("━━━ Sources ━━━")
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('url', '')}")

        return "\n".join(lines)
