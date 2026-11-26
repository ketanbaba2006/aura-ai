"""
AURA AI Vector Store (SQLite-backed Custom Vector Engine)
Replaces ChromaDB to resolve dependency compiling issues on modern Python (e.g. 3.14) on macOS.
Provides exact Chroma-compatible collection API for query, add, and delete.
Uses API-based cloud embeddings only, 100% Ollama dependencies removed.
"""

import json
import logging
import sqlite3
from pathlib import Path
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two numeric lists."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = sum(a * a for a in v1) ** 0.5
    norm_v2 = sum(b * b for b in v2) ** 0.5
    if not norm_v1 or not norm_v2:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


class CloudEmbeddingFunction:
    """Generates embeddings using Google Gemini API, falling back to OpenRouter API."""

    def __init__(self):
        # Determine active cloud embedding model and dimensions based on configured keys
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "INSECURE_DEFAULT_GEMINI_KEY":
            self.model = "text-embedding-004"
            self.dimension = 768
            self.provider = "gemini"
            self.url = "https://generativelanguage.googleapis.com/v1beta/openai/embeddings"
            self.key = settings.GEMINI_API_KEY
        elif settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY != "INSECURE_DEFAULT_OPENROUTER_KEY":
            self.model = "openai/text-embedding-3-small"
            self.dimension = 1536
            self.provider = "openrouter"
            self.url = "https://openrouter.ai/api/v1/embeddings"
            self.key = settings.OPENROUTER_API_KEY
        else:
            self.model = "fallback-zeros"
            self.dimension = 768
            self.provider = "none"
            self.url = ""
            self.key = ""

    def __call__(self, input_docs: list[str]) -> list[list[float]]:
        if not input_docs:
            return []
            
        if self.provider == "none":
            logger.warning("No cloud embedding API key configured. Returning default zero vectors.")
            return [[0.0] * self.dimension for _ in input_docs]

        try:
            headers = {
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "input": input_docs
            }
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(self.url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    # Sort data by index to guarantee correct ordering matching input_docs
                    sorted_data = sorted(data, key=lambda x: x.get("index", 0))
                    embeddings = [item["embedding"] for item in sorted_data]
                    if len(embeddings) == len(input_docs):
                        return embeddings
                
                logger.error(f"Cloud embeddings API error: status {resp.status_code}, details: {resp.text}")
        except Exception as e:
            logger.error(f"Failed to generate cloud embeddings: {e}")

        # Safe fallback default vectors on network or parsing error
        return [[0.0] * self.dimension for _ in input_docs]


class LocalCollection:
    """Mimics ChromaDB Collection API using SQLite-backed embeddings and pure python cosine similarity."""

    def __init__(self, name: str, embedding_function: CloudEmbeddingFunction, db_path: str):
        self.name = name
        self.embedding_function = embedding_function
        self.db_path = db_path

    def add(self, ids: list[str], documents: list[str], metadatas: list[dict] | None = None) -> None:
        """Embed text and insert or replace vectors in SQLite."""
        if not ids or not documents:
            return

        embeddings = self.embedding_function(documents)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for idx, id_ in enumerate(ids):
                meta = metadatas[idx] if metadatas else {}
                emb = embeddings[idx]
                doc = documents[idx]
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO vector_embeddings (id, collection_name, document, metadata, embedding)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (id_, self.name, doc, json.dumps(meta), json.dumps(emb)),
                )
            conn.commit()
            conn.close()
            logger.debug(f"Added {len(ids)} items to vector collection '{self.name}'")
        except Exception as e:
            logger.error(f"Failed to save embeddings to SQLite: {e}")

    def delete(self, ids: list[str] | None = None, where: dict | None = None) -> None:
        """Delete records from SQLite vector_embeddings."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if ids:
                placeholders = ",".join("?" for _ in ids)
                cursor.execute(
                    f"DELETE FROM vector_embeddings WHERE collection_name = ? AND id IN ({placeholders})",
                    (self.name, *ids),
                )
            elif where:
                # Query all matching records from collection to filter
                cursor.execute(
                    "SELECT id, metadata FROM vector_embeddings WHERE collection_name = ?",
                    (self.name,),
                )
                rows = cursor.fetchall()
                to_delete = []
                for row_id, meta_str in rows:
                    meta = json.loads(meta_str)
                    match = True
                    for key, val in where.items():
                        if meta.get(key) != val:
                            match = False
                            break
                    if match:
                        to_delete.append(row_id)

                if to_delete:
                    placeholders = ",".join("?" for _ in to_delete)
                    cursor.execute(
                        f"DELETE FROM vector_embeddings WHERE collection_name = ? AND id IN ({placeholders})",
                        (self.name, *to_delete),
                    )
            conn.commit()
            conn.close()
            logger.debug(f"Deleted items from vector collection '{self.name}'")
        except Exception as e:
            logger.error(f"Failed to delete embeddings from SQLite: {e}")

    def query(self, query_texts: list[str], n_results: int = 5, where: dict | None = None) -> dict:
        """Query SQLite vectors and calculate cosine similarity ranking."""
        if not query_texts:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        query_embs = self.embedding_function(query_texts)
        q_emb = query_embs[0]

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, document, metadata, embedding FROM vector_embeddings WHERE collection_name = ?",
                (self.name,),
            )
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row_id, doc, meta_str, emb_str in rows:
                meta = json.loads(meta_str)
                emb = json.loads(emb_str)

                # Metadata filter
                if where:
                    match = True
                    for key, val in where.items():
                        if meta.get(key) != val:
                            match = False
                            break
                    if not match:
                        continue

                # Ensure dimensions match before calculating similarity
                if len(q_emb) != len(emb):
                    continue

                sim = cosine_similarity(q_emb, emb)
                distance = 1.0 - sim  # Cosine distance
                results.append((row_id, doc, meta, distance))

            # Sort by distance ascending
            results.sort(key=lambda x: x[3])
            results = results[:n_results]

            return {
                "ids": [[r[0] for r in results]],
                "documents": [[r[1] for r in results]],
                "metadatas": [[r[2] for r in results]],
                "distances": [[r[3] for r in results]],
            }
        except Exception as e:
            logger.error(f"Failed to query local vector database: {e}")
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


class VectorStore:
    """Manager for SQLite-backed vector store mimicking ChromaDB."""

    def __init__(self):
        self.memories_col = None
        self.knowledge_col = None

    def initialize(self) -> None:
        """Initialize local Collections using SQLite database path and Cloud embeddings."""
        db_path = settings.DATABASE_PATH
        embedding_fn = CloudEmbeddingFunction()

        # Check existing vector size to prevent dimension conflicts
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_embeddings (
                    id TEXT,
                    collection_name TEXT,
                    document TEXT,
                    metadata TEXT,
                    embedding TEXT,
                    PRIMARY KEY (id, collection_name)
                )
            """)
            cursor.execute("SELECT embedding FROM vector_embeddings LIMIT 1")
            row = cursor.fetchone()
            if row:
                sample_vector = json.loads(row[0])
                if len(sample_vector) != embedding_fn.dimension:
                    logger.warning(
                        f"Vector Store dimensions changed from {len(sample_vector)} to {embedding_fn.dimension}. "
                        "Flushing vector tables to ensure consistency."
                    )
                    cursor.execute("DELETE FROM vector_embeddings")
                    conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed checking vector dimension shapes in SQLite: {e}")

        self.memories_col = LocalCollection("memories", embedding_fn, db_path)
        self.knowledge_col = LocalCollection("knowledge", embedding_fn, db_path)
        logger.info(f"SQLite-backed Vector Store client initialized using {db_path}")


# Global instance
vector_store = VectorStore()
