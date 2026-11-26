"""
AURA AI Knowledge Base Manager
Document processing, text extraction, chunking, vector ingestion, and search.
"""

import io
import os
import uuid
import logging
from datetime import datetime

from app.database.database import db
from app.memory.vector_store import vector_store
from app.database.schemas import KnowledgeChunkResponse
from app.knowledge.file_processors import file_processor

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """Manages document uploads, text extraction, semantic chunking, background status, and search."""

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks, trying to split at sentence boundaries."""
        import re
        
        if not text:
            return []

        # First, split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Handle overlap: keep last N sentences or chars
                # Find overlap
                overlap_length = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    if overlap_length + len(s) > overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_length += len(s) + 1  # +1 for space
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for space
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    async def create_document_placeholder(
        self, filename: str, file_size: int, conversation_id: str | None = None, file_type: str = "text"
    ) -> str:
        """Create a placeholder document in SQLite tracking processing status."""
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        await db.db.knowledge_documents.insert_one({"id": doc_id, "filename": filename, "file_size": file_size, "upload_time": now, "chunk_count": 0, "conversation_id": conversation_id, "status": "processing", "file_type": file_type})
        logger.info(f"Created ingestion database placeholder for '{filename}' (ID: {doc_id})")
        return doc_id

    async def ingest_document_background(
        self, doc_id: str, filepath: str, filename: str, conversation_id: str | None = None
    ) -> None:
        """Background worker that parses the document, splits text, creates embeddings, and saves to vector db."""
        try:
            logger.info(f"Background parsing started for document: {filename} (ID: {doc_id})")
            
            # 1. Read file bytes
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Source file not found at path: {filepath}")
                
            with open(filepath, "rb") as f:
                file_bytes = f.read()

            file_size = len(file_bytes)
            
            # 2. Extract text and auto-detect format
            raw_text, detected_type = file_processor.extract_text(filename, file_bytes)

            if not raw_text.strip():
                raise ValueError("Document has no extractable text content.")

            # 3. Chunk text
            chunks = self._chunk_text(raw_text)
            chunk_count = len(chunks)

            # 4. Ingest chunks into ChromaDB Vector Collection
            if vector_store.knowledge_col and chunks:
                ids = [f"{doc_id}_chunk_{i}" for i in range(chunk_count)]
                metadatas = [
                    {
                        "doc_id": doc_id,
                        "filename": filename,
                        "chunk_index": i,
                        "conversation_id": conversation_id or "global",
                    }
                    for i in range(chunk_count)
                ]
                
                # Ingest in batches to handle larger documents
                batch_size = 100
                for i in range(0, chunk_count, batch_size):
                    end = min(i + batch_size, chunk_count)
                    vector_store.knowledge_col.add(
                        ids=ids[i:end],
                        documents=chunks[i:end],
                        metadatas=metadatas[i:end],
                    )

            # 5. Update SQLite metadata status to 'completed'
            await db.db.knowledge_documents.update_one({"id": doc_id}, {"$set": {"chunk_count": chunk_count, "status": "completed", "file_type": detected_type, "file_size": file_size}})
            logger.info(f"Background ingestion succeeded for '{filename}' ({chunk_count} chunks).")
            
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Background Ingestion failed for document '{filename}' (ID: {doc_id}): {err_msg}", exc_info=True)
            
            # Update SQLite metadata status to 'failed'
            await db.db.knowledge_documents.update_one({"id": doc_id}, {"$set": {"status": "failed", "error_message": err_msg}})

    async def upload_document(self, filename: str, content_type: str, file_bytes: bytes) -> dict:
        """
        Synchronous wrapper matching original API specifications.
        Used for small direct upload requirements.
        """
        doc_id = await self.create_document_placeholder(filename, len(file_bytes), file_type=content_type)
        
        # Write to temp path to run ingestion pipeline
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent.parent
        filepath = root / "user_files" / "Uploaded Files" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(file_bytes)
        
        # Run process synchronously
        await self.ingest_document_background(doc_id, str(filepath), filename)
        
        # Fetch updated details
        row = await db.db.knowledge_documents.find_one({"id": doc_id})
        return dict(row) if row else {"id": doc_id, "filename": filename, "status": "completed"}

    async def list_documents(self) -> list[dict]:
        """List all registered knowledge base documents from SQLite."""
        rows = await db.db.knowledge_documents.find({}).sort("upload_time", -1).to_list(length=None)
        return [dict(row) for row in rows]

    async def list_conversation_documents(self, conversation_id: str) -> list[dict]:
        """List documents associated with a specific conversation room."""
        rows = await db.db.knowledge_documents.find({"conversation_id": conversation_id}).sort("upload_time", -1).to_list(length=None)
        return [dict(row) for row in rows]

    async def delete_document(self, doc_id: str) -> None:
        """Deletes a document metadata from SQLite and all associated chunks from ChromaDB."""
        # Delete from SQLite
        await db.db.knowledge_documents.delete_one({"id": doc_id})

        # Delete chunks from vector store
        try:
            if vector_store.knowledge_col:
                vector_store.knowledge_col.delete(where={"doc_id": doc_id})
        except Exception as e:
            logger.error(f"Failed to delete ChromaDB vectors for document {doc_id}: {e}")

        logger.info(f"Deleted document: {doc_id}")

    async def search_knowledge(self, query: str, conversation_id: str | None = None, limit: int = 5, doc_ids: list[str] | None = None) -> list[KnowledgeChunkResponse]:
        """
        Queries ChromaDB knowledge collection for matching text chunks.
        Limits search scope to specific doc_ids if provided, otherwise falls back to conversation_id.
        """
        results = []
        try:
            if vector_store.knowledge_col:
                where_clause = None
                if doc_ids and len(doc_ids) > 0:
                    if len(doc_ids) == 1:
                        where_clause = {"doc_id": doc_ids[0]}
                    else:
                        where_clause = {"doc_id": {"$in": doc_ids}}
                elif conversation_id:
                    # ChromaDB supports filtering where metadata matches conversation_id OR global
                    where_clause = {
                        "$or": [
                            {"conversation_id": conversation_id},
                            {"conversation_id": "global"}
                        ]
                    }

                query_results = vector_store.knowledge_col.query(
                    query_texts=[query],
                    n_results=limit,
                    where=where_clause,
                )

                if query_results and query_results["ids"] and query_results["ids"][0]:
                    ids = query_results["ids"][0]
                    documents = query_results["documents"][0]
                    metadatas = query_results["metadatas"][0]
                    distances = query_results["distances"][0]

                    for idx, chunk_id in enumerate(ids):
                        distance = distances[idx]
                        score = max(0.0, min(1.0, 1.0 - distance))

                        results.append(
                            KnowledgeChunkResponse(
                                chunk_id=chunk_id,
                                doc_id=metadatas[idx]["doc_id"],
                                filename=metadatas[idx]["filename"],
                                content=documents[idx],
                                score=score,
                            )
                        )
        except Exception as e:
            logger.error(f"Vector search in knowledge failed: {e}")

        return results

# Global instance
knowledge_manager = KnowledgeManager()
