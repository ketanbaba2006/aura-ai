"""
AURA AI Knowledge Retrieval Tool
Retrieves relevant text chunks from uploaded knowledge base documents.
"""

import logging
from typing import Any

from app.database.schemas import ToolResult
from app.tools.base import BaseTool
from app.knowledge.knowledge_manager import knowledge_manager

logger = logging.getLogger(__name__)


class KnowledgeRetrievalTool(BaseTool):
    """
    Knowledge retrieval tool queries the vector store for matching document chunks.
    It returns document names, similarity scores, and content matching the query.
    """

    @property
    def name(self) -> str:
        return "knowledge_retrieval"

    @property
    def description(self) -> str:
        return (
            "Retrieve facts, context, and information from uploaded PDFs, Word files, "
            "and text documents in your knowledge base. Always use this when the user "
            "asks about their documents, uploaded files, or knowledge base content."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to match against uploaded documents",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of document chunks to retrieve (default: 3)",
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum similarity score (0-1) for results (default: 0.0)",
                },
                "filter_filename": {
                    "type": "string",
                    "description": "Filter results to only include chunks from a specific filename",
                },
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 5)  # Increased default limit
        min_score = kwargs.get("min_score", 0.0)
        filter_filename = kwargs.get("filter_filename")
        conversation_id = kwargs.get("conversation_id")

        if not query:
            return ToolResult(success=False, error="No query provided")

        try:
            matches = await knowledge_manager.search_knowledge(query, conversation_id=conversation_id, limit=limit)
            
            # Apply filters
            filtered_matches = []
            for match in matches:
                if match.score < min_score:
                    continue
                if filter_filename and filter_filename.lower() not in match.filename.lower():
                    continue
                filtered_matches.append(match)
            
            if not filtered_matches:
                return ToolResult(
                    success=True,
                    output="No matching information found in the knowledge base documents.",
                )

            # Format the matches nicely for user display and LLM context
            lines = [f"Found {len(filtered_matches)} matching document sections:"]
            for idx, match in enumerate(filtered_matches, 1):
                lines.append(f"\n[{idx}] Document: {match.filename} (Score: {match.score:.2f})")
                lines.append(f"Content excerpt:\n{match.content.strip()}")

            return ToolResult(
                success=True,
                output="\n".join(lines),
            )
        except Exception as e:
            logger.error(f"Knowledge retrieval tool execution failed: {e}")
            return ToolResult(success=False, error=f"Knowledge retrieval error: {str(e)}")
