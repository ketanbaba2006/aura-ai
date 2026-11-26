import re
with open("backend/app/notebook/notebook_engine.py", "r") as f:
    text = f.read()

text = text.replace(
    'await db.execute(\n                "INSERT INTO memory (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",\n                (msg_id_1, conversation_id, "user", query)\n            )',
    'await db.db.memory.insert_one({"id": msg_id_1, "conversation_id": conversation_id, "role": "user", "content": query})'
)
text = text.replace(
    'await db.execute(\n                "INSERT INTO memory (id, conversation_id, role, content, metadata_json) VALUES (?, ?, ?, ?, ?)",\n                (msg_id_2, conversation_id, "assistant", full_response, json.dumps(metadata))\n            )',
    'await db.db.memory.insert_one({"id": msg_id_2, "conversation_id": conversation_id, "role": "assistant", "content": full_response, "metadata_json": json.dumps(metadata)})'
)

with open("backend/app/notebook/notebook_engine.py", "w") as f:
    f.write(text)
