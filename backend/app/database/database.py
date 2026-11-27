"""
AURA AI Database
MongoDB database setup and operations using motor.
"""

import os
import uuid
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
        if not os.environ.get("MONGODB_URI"):
            logger.info("MONGODB_URI not provided; using built-in database store.")
            self._db = None
            return

        try:
            self._client = AsyncIOMotorClient(self.uri, serverSelectionTimeoutMS=2000)
            # Verify connection
            await self._client.admin.command('ping')
            self._db = self._client[self.db_name]
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
            logger.warning(f"Failed to connect to MongoDB ({e}); falling back to built-in store.")
            self._db = None

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

import json
import sqlite3

class _FallbackCollection:
    def __init__(self, name: str, db_path: str = "./data/aura_fallback.db"):
        self.name = name
        self.db_path = db_path
        self._init_sqlite()

    def _init_sqlite(self):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.name} (
                        id TEXT PRIMARY KEY,
                        data JSON NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"Fallback SQLite init failed for {self.name}: {e}")

    def _get_all(self) -> dict:
        result = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT id, data FROM {self.name}")
                for doc_id, data_str in cursor.fetchall():
                    try:
                        result[doc_id] = json.loads(data_str)
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Fallback SQLite read error: {e}")
        return result

    def _save_one(self, doc_id: str, doc: dict):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"INSERT OR REPLACE INTO {self.name} (id, data) VALUES (?, ?)",
                    (doc_id, json.dumps(doc))
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Fallback SQLite write error: {e}")

    async def _pg_sync_save(self, doc_id: str, doc: dict):
        """Asynchronously sync user to Neon PostgreSQL if connection is available."""
        if self.name != "users":
            return
        try:
            from app.quality.database import get_pg_pool
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE,
                        name TEXT,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT,
                        role TEXT NOT NULL DEFAULT 'USER',
                        avatar_url TEXT,
                        provider TEXT NOT NULL DEFAULT 'local',
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        last_login TIMESTAMP
                    )
                """)
                await conn.execute("""
                    INSERT INTO users (id, username, name, email, password_hash, role, avatar_url, provider, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (email) DO UPDATE SET
                        username = EXCLUDED.username,
                        name = EXCLUDED.name,
                        password_hash = EXCLUDED.password_hash,
                        role = EXCLUDED.role,
                        avatar_url = EXCLUDED.avatar_url,
                        updated_at = NOW()
                """, doc.get("id", doc_id), doc.get("username"), doc.get("name"), doc.get("email"), doc.get("password_hash"), doc.get("role", "USER"), doc.get("avatar_url"), doc.get("provider", "local"), doc.get("is_active", True))
        except Exception as e:
            logger.debug(f"Neon PG user sync skipped: {e}")

    async def _pg_sync_load_user(self, filter_query: dict) -> dict | None:
        """Asynchronously load user from Neon PostgreSQL if missing in local container."""
        if self.name != "users":
            return None
        try:
            from app.quality.database import get_pg_pool
            pool = await get_pg_pool()
            async with pool.acquire() as conn:
                email = filter_query.get("email")
                username = filter_query.get("username")
                user_id = filter_query.get("id")
                row = None
                if email:
                    row = await conn.fetchrow("SELECT * FROM users WHERE LOWER(email) = LOWER($1)", email)
                elif username:
                    row = await conn.fetchrow("SELECT * FROM users WHERE LOWER(username) = LOWER($1)", username)
                elif user_id:
                    row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                elif "$or" in filter_query:
                    for sub in filter_query["$or"]:
                        sub_row = await self._pg_sync_load_user(sub)
                        if sub_row:
                            return sub_row

                if row:
                    user_data = dict(row)
                    user_data["created_at"] = str(user_data.get("created_at") or "")
                    user_data["updated_at"] = str(user_data.get("updated_at") or "")
                    user_data["last_login"] = str(user_data.get("last_login") or "")
                    self._save_one(user_data["id"], user_data)
                    return user_data
        except Exception as e:
            logger.debug(f"Neon PG user read skipped: {e}")
        return None

    def _delete(self, doc_id: str):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f"DELETE FROM {self.name} WHERE id = ?", (doc_id,))
                conn.commit()
        except Exception as e:
            logger.warning(f"Fallback SQLite delete error: {e}")

    async def create_index(self, *args, **kwargs):
        return None

    async def count_documents(self, filter_query: dict = None) -> int:
        data = self._get_all()
        if not filter_query:
            return len(data)
        count = 0
        for doc in data.values():
            if all(doc.get(k) == v for k, v in filter_query.items() if not k.startswith("$")):
                count += 1
        return count

    async def find_one(self, filter_query: dict = None, projection: dict = None, sort: list = None, *args, **kwargs) -> dict | None:
        data = self._get_all()
        if not filter_query:
            return next(iter(data.values()), None)
        
        # Handle $or queries
        if "$or" in filter_query:
            for sub in filter_query["$or"]:
                res = await self.find_one(sub)
                if res:
                    return res
            return None

        for doc in data.values():
            match = True
            for k, v in filter_query.items():
                if k.startswith("$"):
                    continue
                doc_val = doc.get(k)
                # Case-insensitive comparison for strings like email/username
                if isinstance(v, str) and isinstance(doc_val, str):
                    if doc_val.lower() != v.lower():
                        match = False
                        break
                elif doc_val != v:
                    match = False
                    break
            if match:
                return dict(doc)

        # Fallback to Neon PostgreSQL query if user not found in local cache
        pg_user = await self._pg_sync_load_user(filter_query)
        if pg_user:
            return pg_user

        return None

    async def insert_one(self, document: dict):
        doc_id = document.get("id") or str(uuid.uuid4() if 'uuid' in globals() else len(self._get_all()) + 1)
        doc = dict(document)
        doc["id"] = doc_id
        self._save_one(doc_id, doc)
        await self._pg_sync_save(doc_id, doc)
        return type("InsertResult", (), {"inserted_id": doc_id})()

    async def update_one(self, filter_query: dict, update_query: dict, upsert: bool = False):
        doc = await self.find_one(filter_query)
        if doc:
            doc_id = doc.get("id")
            if "$set" in update_query:
                doc.update(update_query["$set"])
            self._save_one(doc_id, doc)
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
            self._delete(doc["id"])
            return type("DeleteResult", (), {"deleted_count": 1})()
        return type("DeleteResult", (), {"deleted_count": 0})()

    async def delete_many(self, filter_query: dict):
        data = self._get_all()
        deleted = 0
        for doc in data.values():
            if all(doc.get(k) == v for k, v in filter_query.items() if not k.startswith("$")):
                self._delete(doc["id"])
                deleted += 1
        return type("DeleteResult", (), {"deleted_count": deleted})()

    def aggregate(self, pipeline: list):
        # Handle conversation aggregation pipeline gracefully
        data = list(self._get_all().values())
        match_stage = next((stage["$match"] for stage in pipeline if "$match" in stage), None)
        if match_stage:
            filtered = []
            for doc in data:
                if all(doc.get(k) == v for k, v in match_stage.items()):
                    filtered.append(doc)
            data = filtered

        # Populate message counts and last message if requested
        res = []
        for doc in data:
            item = dict(doc)
            item.setdefault("message_count", 0)
            item.setdefault("last_message", None)
            res.append(item)

        class _AggrCursor:
            def __init__(self, items):
                self._items = items
            async def to_list(self, length=None):
                return self._items

        return _AggrCursor(res)

    def find(self, filter_query: dict = None):
        items = list(self._get_all().values())
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
