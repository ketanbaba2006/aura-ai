"""
AURA AI Notebook Engine
Core RAG execution specifically strictly grounded for Notebook Workspace.
"""

import json
import logging
from typing import AsyncGenerator

from app.database.schemas import ChatEventType
from app.knowledge.knowledge_manager import knowledge_manager
from app.core.llm_client import llm_client
from app.database.database import db

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are AURA Research, an advanced, highly focused, source-grounded assistant.
Your singular goal is to answer the user's request using ONLY the provided Source Context.

## INSTRUCTIONS:
1. NO HALLUCINATION. If the provided sources do not contain the answer, state clearly: "I cannot answer this based on the provided sources."
2. CITE EVERY CLAIM. Every factual statement MUST have an inline citation corresponding to the source chunk index provided in the Context.
3. CITATION FORMAT: Use standard bracket notation like [[1]], [[2], [4]]. Do not use URL links inside the citation. Just the bracketed number.
4. SYNTHESIZE clearly, but do not infer external knowledge.

## SOURCE CONTEXT:
{context_str}
"""

class NotebookEngine:
    async def chat_stream(self, query: str, conversation_id: str, doc_ids: list[str]) -> AsyncGenerator[tuple[ChatEventType, str, dict | None], None]:
        """Stream a grounded chat response back to the user via RAG."""
        try:
            # 1. Retrieve Context
            chunks = await knowledge_manager.search_knowledge(
                query=query, 
                conversation_id=conversation_id, 
                limit=15, 
                doc_ids=doc_ids
            )

            # Sort chunks by score descending
            chunks = sorted(chunks, key=lambda x: x.score, reverse=True)

            if not chunks:
                yield (
                    ChatEventType.TOKEN,
                    "I could not find any relevant information in the selected sources. Please try another query or select different sources.",
                    None
                )
                yield (ChatEventType.DONE, "", None)
                return

            # 2. Build Context String & Citation Map
            context_str = ""
            citation_map = []
            
            for i, chunk in enumerate(chunks, 1):
                # Use [i] as the citation index
                context_str += f"\n--- Source [{i}] (File: {chunk.filename}) ---\n"
                context_str += f"{chunk.content}\n"
                
                citation_map.append({
                    "id": i,
                    "filename": chunk.filename,
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id,
                    "snippet": chunk.content[:150] + "...",
                    "score": chunk.score
                })

            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context_str=context_str)

            # 3. Stream Response
            messages = [{"role": "user", "content": query}]
            
            # Send initial metadata to UI so it knows the citations
            metadata = {
                "citations": citation_map,
                "confidence_score": round(chunks[0].score * 100) if chunks else 0
            }
            
            # Since we can't yield an empty TOKEN event that won't trigger weird formatting,
            # we just yield the metadata in the first token or as a separate event if supported, 
            # but usually we attach metadata to DONE or yield a special RESEARCH metadata.
            
            full_response = ""
            async for chunk_text in llm_client.stream_chat(
                messages=messages,
                system_prompt=system_prompt,
                category="research"
            ):
                full_response += chunk_text
                yield (ChatEventType.TOKEN, chunk_text, None)

            # Yield DONE with the citation metadata
            yield (ChatEventType.DONE, "", metadata)
            
            # Save to memory
            # For simplicity we generate a UUID for messages
            import uuid
            msg_id_1 = str(uuid.uuid4())
            msg_id_2 = str(uuid.uuid4())
            
            await db.db.memory.insert_one({"id": msg_id_1, "conversation_id": conversation_id, "role": "user", "content": query})
            await db.db.memory.insert_one({"id": msg_id_2, "conversation_id": conversation_id, "role": "assistant", "content": full_response, "metadata_json": json.dumps(metadata)})
            
        except Exception as e:
            logger.error(f"NotebookEngine RAG failed: {e}", exc_info=True)
            yield (ChatEventType.ERROR, str(e), None)
            yield (ChatEventType.DONE, "", None)

notebook_engine = NotebookEngine()
