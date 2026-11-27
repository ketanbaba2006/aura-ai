"""
AURA AI Database
MongoDB database setup and operations using motor.
"""

import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

logger = logging.getLogger(__name__)

class Database:
    """Async MongoDB database wrapper."""

    def __init__(self):
        self.uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        self.db_name = "aura_ai"
        self._client = None
        self._db = None

    async def connect(self) -> None:
        """Initialize database connection."""
        try:
            self._client = AsyncIOMotorClient(self.uri)
            self._db = self._client[self.db_name]
            
            # Verify connection
            await self._client.admin.command('ping')
            logger.info(f"MongoDB connected: {self.uri} (database: {self.db_name})")
            
            # Setup initial collections/indexes if necessary
            await self._setup_indexes()
            
            # Seed settings if not exist
            await self._db.system_settings.update_one(
                {"key": "web_search_mode"},
                {"$setOnInsert": {"key": "web_search_mode", "value": "ask_first"}},
                upsert=True
            )
            
            # Seed Deep Research settings
            research_defaults = {
                "research_provider": "bedrock",
                "research_api_key": "",
                "research_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "research_aws_region": "us-east-1",
                "research_temperature": "0.3",
                "research_depth": "standard",
                "research_sources_limit": "8",
                "research_timeout": "300",
            }
            for key, default_value in research_defaults.items():
                await self._db.system_settings.update_one(
                    {"key": key},
                    {"$setOnInsert": {"key": key, "value": default_value}},
                    upsert=True
                )
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def _setup_indexes(self):
        if self._db is None: return
        
        await self._db.users.create_index("email", unique=True)
        await self._db.user_sessions.create_index([("user_id", 1), ("token_jti", 1)])
        await self._db.auth_tokens.create_index("token", unique=True)
        await self._db.conversations.create_index([("user_id", 1), ("updated_at", -1)])
        await self._db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
        await self._db.activity_logs.create_index("timestamp")
        await self._db.tasks.create_index([("goal_id", 1), ("order_index", 1)])
        await self._db.system_settings.create_index("key", unique=True)

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB disconnected")

    @property
    def db(self):
        """Get active database instance with seamless fallback."""
        if self._db is not None:
            return self._db
        return _fallback_store

class _FallbackCollection:
    def __init__(self, name: str):
        self.name = name
        self._data = {}

    async def create_index(self, *args, **kwargs):
        return None

    async def count_documents(self, filter_query: dict = None) -> int:
        if not filter_query:
            return len(self._data)
        count = 0
        for doc in self._data.values():
            if all(doc.get(k) == v for k, v in filter_query.items() if not k.startswith("$")):
                count += 1
        return count

    async def find_one(self, filter_query: dict = None) -> dict | None:
        if not filter_query:
            return next(iter(self._data.values()), None)
        
        # Handle $or queries
        if "$or" in filter_query:
            for sub in filter_query["$or"]:
                res = await self.find_one(sub)
                if res:
                    return res
            return None

        for doc in self._data.values():
            match = True
            for k, v in filter_query.items():
                if k.startswith("$"):
                    continue
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return dict(doc)
        return None

    async def insert_one(self, document: dict):
        doc_id = document.get("id") or str(len(self._data) + 1)
        self._data[doc_id] = dict(document)
        return type("InsertResult", (), {"inserted_id": doc_id})()

    async def update_one(self, filter_query: dict, update_query: dict, upsert: bool = False):
        doc = await self.find_one(filter_query)
        if doc:
            doc_id = doc.get("id")
            if "$set" in update_query:
                self._data[doc_id].update(update_query["$set"])
            return type("UpdateResult", (), {"modified_count": 1, "matched_count": 1})()
        elif upsert:
            new_doc = {}
            if "$set" in update_query:
                new_doc.update(update_query["$set"])
            if "$setOnInsert" in update_query:
                new_doc.update(update_query["$setOnInsert"])
            for k, v in filter_query.items():
                if not k.startswith("$"):
                    new_doc[k] = v
            await self.insert_one(new_doc)
            return type("UpdateResult", (), {"modified_count": 0, "matched_count": 0, "upserted_id": new_doc.get("id")})()
        return type("UpdateResult", (), {"modified_count": 0, "matched_count": 0})()

    async def delete_one(self, filter_query: dict):
        doc = await self.find_one(filter_query)
        if doc and "id" in doc:
            self._data.pop(doc["id"], None)
            return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()

    def find(self, filter_query: dict = None):
        items = list(self._data.values())
        if filter_query:
            filtered = []
            for doc in items:
                if all(doc.get(k) == v for k, v in filter_query.items() if not k.startswith("$")):
                    filtered.append(doc)
            items = filtered

        class _Cursor:
            def __init__(self, data):
                self._items = data
                self._iter = iter(data)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._iter)
                except StopIteration:
                    raise StopAsyncIteration

            def sort(self, *a, **kw):
                return self

            def limit(self, *a, **kw):
                return self

            async def to_list(self, length=None):
                return list(self._items)

        return _Cursor(items)

class _FallbackDatabase:
    def __init__(self):
        self._collections = {}

    def __getattr__(self, name: str):
        if name not in self._collections:
            self._collections[name] = _FallbackCollection(name)
        return self._collections[name]

    def __getitem__(self, name: str):
        return self.__getattr__(name)

_fallback_store = _FallbackDatabase()

# Global database instance
db = Database()
