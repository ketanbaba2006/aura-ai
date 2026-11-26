"""
AURA AI Memory Engine
Short-term caching, MongoDB persistence, and ChromaDB vector-based semantic memory.
"""

import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime

from app.config import settings
from app.database.database import db
from app.database.schemas import MemorySearchResult, MessageRole
from app.memory.vector_store import vector_store

logger = logging.getLogger(__name__)


class MemoryEngine:
    """
    Manages conversation memory across three tiers:
    - Short-term: In-memory cache for fast session access
    - Long-term (Persistent): MongoDB database for structured storage
    - Long-term (Semantic): ChromaDB vector store for similarity search
    """

    def __init__(self):
        # Short-term memory: {conversation_id: [messages]}
        self._short_term: dict[str, list[dict]] = defaultdict(list)

    # ─── Conversation Management ──────────────────────────

    async def create_conversation(self, title: str = "New Conversation", user_id: str | None = None) -> str:
        """Create a new conversation and return its ID."""
        conv_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        await db.db.conversations.insert_one({"id": conv_id, "user_id": user_id, "title": title, "created_at": now, "updated_at": now})

        logger.info(f"Created conversation: {conv_id} for user {user_id}")
        return conv_id

    async def get_conversation(self, conversation_id: str, user_id: str | None = None) -> dict | None:
        """Get conversation metadata. Enforces user isolation when user_id provided."""
        query = {"id": conversation_id}
        if user_id:
            query["user_id"] = user_id
        return await db.db.conversations.find_one(query)

    async def list_conversations(self, user_id: str | None = None) -> list[dict]:
        """List all conversations, most recent first."""
        match_stage = {}
        if user_id:
            match_stage["user_id"] = user_id
            
        pipeline = [
            {"$match": match_stage},
            {"$lookup": {
                "from": "messages",
                "localField": "id",
                "foreignField": "conversation_id",
                "as": "messages"
            }},
            {"$project": {
                "id": 1, "title": 1, "created_at": 1, "updated_at": 1, 
                "message_count": {"$size": "$messages"},
                "last_message": {"$arrayElemAt": [{"$map": {"input": {"$slice": [{"$sortArray": {"input": "$messages", "sortBy": {"created_at": -1}}}, 1]}, "as": "m", "in": "$$m.content"}}, 0]}
            }},
            {"$sort": {"updated_at": -1}}
        ]
        return await db.db.conversations.aggregate(pipeline).to_list(length=None)

    async def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> None:
        """Update conversation title."""
        await db.db.conversations.update_one({"id": conversation_id}, {"$set": {"title": title, "updated_at": datetime.utcnow().isoformat()}})

    async def delete_conversation(self, conversation_id: str, user_id: str | None = None) -> None:
            """Delete conversation, all its messages, and clear vectors. Enforces user isolation."""
            query = {"id": conversation_id}
            if user_id:
                query["user_id"] = user_id
            result = await db.db.conversations.delete_one(query)
            if result.deleted_count == 0:
                return
            
            await db.db.messages.delete_many({"conversation_id": conversation_id})
        
            # Clear short-term memory
            self._short_term.pop(conversation_id, None)
        
            # Remove matching vectors from ChromaDB
            try:
                if vector_store.memories_col:
                    vector_store.memories_col.delete(
                        where={"conversation_id": conversation_id}
                    )
            except Exception as e:
                logger.error(f"Failed to delete ChromaDB memories for conv {conversation_id}: {e}")
        
            logger.info(f"Deleted conversation: {conversation_id}")

    # ─── Message Management ───────────────────────────────

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        """
        Store a message in short-term cache, MongoDB database, and ChromaDB vector store.
        Returns the message ID.
        """
        msg_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        meta_json = json.dumps(metadata) if metadata else None

        # 1. Store in MongoDB
        await db.db.messages.insert_one({"id": msg_id, "conversation_id": conversation_id, "role": role, "content": content, "metadata": meta_json, "created_at": now})

        # Update conversation timestamp
        await db.db.conversations.update_one({"id": conversation_id}, {"$set": {"updated_at": now}})

        # 2. Store in short-term memory cache
        msg = {
            "id": msg_id,
            "role": role,
            "content": content,
            "metadata": metadata,
            "created_at": now,
        }
        self._short_term[conversation_id].append(msg)

        # Trim short-term memory cache
        max_size = settings.SHORT_TERM_MEMORY_SIZE
        if len(self._short_term[conversation_id]) > max_size:
            self._short_term[conversation_id] = self._short_term[conversation_id][
                -max_size:
            ]

        # 3. Store in ChromaDB Vector Collection (Semantic Long-Term Memory)
        try:
            if vector_store.memories_col and content.strip():
                # Avoid vectorizing very short snippets like "yes", "no", "ok" to prevent noise
                if len(content.strip()) > 3:
                    vector_store.memories_col.add(
                        ids=[msg_id],
                        documents=[content],
                        metadatas=[
                            {
                                "conversation_id": conversation_id,
                                "role": role,
                                "created_at": now,
                            }
                        ],
                    )
        except Exception as e:
            logger.error(f"Failed to add message to vector store: {e}")

        return msg_id

    async def get_history(
        self, conversation_id: str, limit: int | None = None
    ) -> list[dict]:
        """
        Get conversation history.
        Tries short-term memory cache first, falls back to database.
        """
        limit = limit or settings.MAX_CONVERSATION_HISTORY

        # Check short-term memory first
        if conversation_id in self._short_term:
            messages = self._short_term[conversation_id]
            if len(messages) >= 2:  # Useful amount cached
                return messages[-limit:]

        # Fallback to database
        rows = await db.db.messages.find({"conversation_id": conversation_id}).sort("created_at", 1).limit(limit).to_list(length=None)

        # Parse metadata JSON (Since it's stored as JSON string in mongo to match old schema)
        messages = []
        for row in rows:
            msg = dict(row)
            if msg.get("metadata"):
                try:
                    msg["metadata"] = json.loads(msg["metadata"])
                except json.JSONDecodeError:
                    pass
            messages.append(msg)

        # Populate short-term cache
        self._short_term[conversation_id] = messages[-settings.SHORT_TERM_MEMORY_SIZE :]

        return messages

    async def get_messages_for_llm(
        self, conversation_id: str, limit: int | None = None
    ) -> list[dict]:
        """Get messages formatted for LLM input (role + content only)."""
        history = await self.get_history(conversation_id, limit)
        return [{"role": msg["role"], "content": msg["content"]} for msg in history]

    # ─── Memory Search (Hybrid / Semantic) ────────────────

    async def search_memory(
        self, query: str, conversation_id: str | None = None, limit: int = 10
    ) -> list[MemorySearchResult]:
        """
        Search conversation memory using vector semantic query (with keyword fallback).
        """
        results = []

        # Try ChromaDB semantic query first
        try:
            if vector_store.memories_col:
                where_filter = {}
                if conversation_id:
                    where_filter = {"conversation_id": conversation_id}

                query_results = vector_store.memories_col.query(
                    query_texts=[query],
                    n_results=limit,
                    where=where_filter if where_filter else None,
                )

                if query_results and query_results["ids"] and query_results["ids"][0]:
                    ids = query_results["ids"][0]
                    documents = query_results["documents"][0]
                    metadatas = query_results["metadatas"][0]
                    distances = query_results["distances"][0]

                    for idx, msg_id in enumerate(ids):
                        # Convert cosine distance to cosine similarity/relevance score
                        # Chroma cosine space distance is 1 - similarity. So similarity is 1 - distance
                        distance = distances[idx]
                        relevance = max(0.0, min(1.0, 1.0 - distance))

                        results.append(
                            MemorySearchResult(
                                message_id=msg_id,
                                content=documents[idx],
                                role=MessageRole(metadatas[idx]["role"]),
                                relevance=relevance,
                                created_at=datetime.fromisoformat(
                                    metadatas[idx]["created_at"]
                                ),
                            )
                        )
                    return results
        except Exception as e:
            logger.error(f"Semantic memory search failed: {e}. Falling back to MongoDB.")

        # Fallback to MongoDB regex query
        query_lower = query.lower()
        search_filter = {"content": {"$regex": query_lower, "$options": "i"}}
        if conversation_id:
            search_filter["conversation_id"] = conversation_id
            
        rows = await db.db.messages.find(search_filter).sort("created_at", -1).limit(limit).to_list(length=None)

        for row in rows:
            content_lower = row["content"].lower()
            query_terms = query.lower().split()
            matches = sum(1 for term in query_terms if term in content_lower)
            relevance = matches / max(len(query_terms), 1)

            # Try parsing timestamp
            try:
                dt = datetime.fromisoformat(row["created_at"])
            except ValueError:
                dt = datetime.utcnow()

            results.append(
                MemorySearchResult(
                    message_id=row["id"],
                    content=row["content"],
                    role=MessageRole(row["role"]),
                    relevance=relevance,
                    created_at=dt,
                )
            )

        # Sort by relevance
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]

    # ─── Auto Title Generation ────────────────────────────

    def generate_title_from_message(self, message: str) -> str:
        """Generate a conversation title from the first message."""
        title = message.strip()[:50]
        if len(message) > 50:
            last_space = title.rfind(" ")
            if last_space > 20:
                title = title[:last_space]
            title += "..."
        return title


# Global instance
memory_engine = MemoryEngine()
