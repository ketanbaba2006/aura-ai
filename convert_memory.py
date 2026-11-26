import re
with open("backend/app/memory/memory_engine.py", "r") as f:
    text = f.read()

# 1. create_conversation
text = text.replace(
    'await db.execute(\n            "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",\n            (conv_id, user_id, title, now, now),\n        )',
    'await db.db.conversations.insert_one({"id": conv_id, "user_id": user_id, "title": title, "created_at": now, "updated_at": now})'
)

# 2. list_conversations
text = text.replace(
    '        rows = await db.fetch_all(\n            """\n            SELECT c.id, c.title, c.created_at, c.updated_at, COUNT(m.id) as message_count\n            FROM conversations c\n            LEFT JOIN messages m ON c.id = m.conversation_id\n            WHERE c.user_id = ?\n            GROUP BY c.id\n            ORDER BY c.updated_at DESC\n            """,\n            (user_id,)\n        )',
    '        pipeline = [\n            {"$match": {"user_id": user_id}},\n            {"$lookup": {\n                "from": "messages",\n                "localField": "id",\n                "foreignField": "conversation_id",\n                "as": "messages"\n            }},\n            {"$project": {\n                "id": 1, "title": 1, "created_at": 1, "updated_at": 1, \n                "message_count": {"$size": "$messages"}\n            }},\n            {"$sort": {"updated_at": -1}}\n        ]\n        rows = await db.db.conversations.aggregate(pipeline).to_list(length=None)'
)

# 3. get_conversation
text = text.replace(
    'await db.fetch_one("SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))',
    'await db.db.conversations.find_one({"id": conv_id, "user_id": user_id})'
)

# 4. update_conversation_title
text = text.replace(
    'await db.execute(\n            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",\n            (title, datetime.utcnow().isoformat(), conv_id),\n        )',
    'await db.db.conversations.update_one({"id": conv_id}, {"$set": {"title": title, "updated_at": datetime.utcnow().isoformat()}})'
)

# 5. delete_conversation
text = text.replace(
    'await db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))',
    'await db.db.conversations.delete_one({"id": conv_id})'
)

# 6. save_message
text = text.replace(
    '        await db.execute(\n            "INSERT INTO messages (id, conversation_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",\n            (msg_id, conversation_id, role, content, meta_str, now),\n        )',
    '        await db.db.messages.insert_one({"id": msg_id, "conversation_id": conversation_id, "role": role, "content": content, "metadata": meta_str, "created_at": now})'
)
text = text.replace(
    '        await db.execute(\n            "UPDATE conversations SET updated_at = ? WHERE id = ?",\n            (now, conversation_id),\n        )',
    '        await db.db.conversations.update_one({"id": conversation_id}, {"$set": {"updated_at": now}})'
)

# 7. get_history
text = text.replace(
    '        rows = await db.fetch_all(\n            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",\n            (conversation_id,)\n        )',
    '        rows = await db.db.messages.find({"conversation_id": conversation_id}).sort("created_at", 1).to_list(length=None)'
)

# 8. search_memory
text = text.replace(
    '        recent = await db.fetch_all(\n            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 5",\n            (conversation_id,)\n        )',
    '        recent = await db.db.messages.find({"conversation_id": conversation_id}).sort("created_at", -1).limit(5).to_list(length=None)'
)

with open("backend/app/memory/memory_engine.py", "w") as f:
    f.write(text)
