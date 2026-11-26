"""
AURA AI Notebook Generators
Specialized tasks (Study Guide, FAQ, Mind Map, Timeline, Podcast Script) based on source documents.
"""

import json
import logging
from typing import Any

from app.knowledge.knowledge_manager import knowledge_manager
from app.core.llm_client import llm_client

logger = logging.getLogger(__name__)

GENERATOR_PROMPTS = {
    "study_guide": "Generate a comprehensive study guide based strictly on the provided sources. Include key concepts, definitions, and important relationships.",
    "faq": "Generate a list of Frequently Asked Questions (FAQ) with detailed answers based strictly on the provided sources.",
    "mind_map": "Generate a Mind Map layout detailing the hierarchical concepts in the provided sources. Use a nested bullet point structure.",
    "timeline": "Generate a chronological timeline of events, processes, or historical facts mentioned in the provided sources.",
    "podcast": "Generate a 2-host conversational podcast script discussing the key themes of the provided sources. Make it engaging and informative."
}

class NotebookGenerators:
    async def generate_document(self, task_type: str, conversation_id: str, doc_ids: list[str]) -> str:
        """Generates a specialized document based on selected sources."""
        if task_type not in GENERATOR_PROMPTS:
            raise ValueError(f"Unknown generation task type: {task_type}")

        # Retrieve Context
        chunks = await knowledge_manager.search_knowledge(
            query="Extract all core concepts, timelines, FAQs, and overarching themes.", 
            conversation_id=conversation_id, 
            limit=30, # larger context for full generation
            doc_ids=doc_ids
        )

        if not chunks:
            return "Cannot generate document: No relevant sources found or sources are empty."

        context_str = ""
        for i, chunk in enumerate(chunks, 1):
            context_str += f"\n--- Source (File: {chunk.filename}) ---\n{chunk.content}\n"

        system_prompt = (
            f"You are AURA Research Generator. Your task is to {GENERATOR_PROMPTS[task_type]}\n\n"
            f"RULES:\n"
            f"1. Use Markdown formatting.\n"
            f"2. Only use the provided sources. Do not hallucinate external information.\n"
            f"3. Do not include XML tags or wrap the output in json.\n\n"
            f"SOURCES:\n{context_str}"
        )

        response = await llm_client.chat(
            messages=[{"role": "user", "content": f"Please generate the {task_type}."}],
            system_prompt=system_prompt,
            category="research"
        )
        return response
        
    async def get_source_summary(self, doc_id: str) -> dict[str, Any]:
        """Generate a quick summary and key concepts for a specific document."""
        # Grab top chunks from just this document
        chunks = await knowledge_manager.search_knowledge(
            query="What is this document about? Extract summary and key concepts.", 
            conversation_id="global", # it doesn't matter for specific doc_id if doc_ids is passed
            limit=10, 
            doc_ids=[doc_id]
        )
        
        if not chunks:
            return {"summary": "No content available.", "key_concepts": [], "quotes": []}
            
        context_str = "\n".join([c.content for c in chunks])
        
        system_prompt = """You are AURA Research. Analyze the following document text and extract:
1. A concise summary (2-3 sentences).
2. A list of 3-5 key concepts.
3. 2-3 important direct quotes from the text.

Respond ONLY in valid JSON format:
{
  "summary": "...",
  "key_concepts": ["concept 1", "concept 2"],
  "quotes": ["quote 1", "quote 2"]
}

DOCUMENT TEXT:
""" + context_str

        try:
            res = await llm_client.generate_json(
                prompt="Extract summary, concepts, and quotes in JSON.",
                system_prompt=system_prompt,
                category="research"
            )
            return res
        except Exception as e:
            logger.error(f"Failed to generate source summary: {e}")
            return {"summary": "Failed to generate summary.", "key_concepts": [], "quotes": []}

notebook_generators = NotebookGenerators()
