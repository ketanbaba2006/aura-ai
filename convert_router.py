import re
with open("backend/app/router/router_engine.py", "r") as f:
    text = f.read()

# 1. web_search_mode
text = text.replace(
    'await db.fetch_one("SELECT value FROM system_settings WHERE key = \'web_search_mode\'")',
    'await db.db.system_settings.find_one({"key": "web_search_mode"}, {"value": 1})'
)

# 2. last_assistant_msg
text = text.replace(
    'await db.fetch_one(\n                "SELECT content FROM messages WHERE conversation_id = ? AND role = \'assistant\' ORDER BY created_at DESC LIMIT 1",\n                (conversation_id,)\n            )',
    'await db.db.messages.find_one({"conversation_id": conversation_id, "role": "assistant"}, sort=[("created_at", -1)], projection={"content": 1})'
)

# 3. user_msgs
text = text.replace(
    'await db.fetch_all(\n                    "SELECT content FROM messages WHERE conversation_id = ? AND role = \'user\' ORDER BY created_at DESC LIMIT 2",\n                    (conversation_id,)\n                )',
    'await db.db.messages.find({"conversation_id": conversation_id, "role": "user"}, projection={"content": 1}).sort("created_at", -1).limit(2).to_list(length=None)'
)

# 4. docs
text = text.replace(
    'await db.fetch_all(\n                    "SELECT * FROM knowledge_documents WHERE conversation_id = ?",\n                    (conversation_id,)\n                )',
    'await db.db.knowledge_documents.find({"conversation_id": conversation_id}).to_list(length=None)'
)

with open("backend/app/router/router_engine.py", "w") as f:
    f.write(text)
