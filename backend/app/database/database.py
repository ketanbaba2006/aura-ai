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
        """Get active database instance."""
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

# Global database instance
db = Database()
