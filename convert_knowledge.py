import re
with open("backend/app/knowledge/knowledge_manager.py", "r") as f:
    text = f.read()

# 1. create_document_placeholder
text = text.replace(
    'await db.execute(\n            """\n            INSERT INTO knowledge_documents (id, filename, file_size, upload_time, chunk_count, conversation_id, status, file_type)\n            VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n            """,\n            (doc_id, filename, file_size, now, 0, conversation_id, "processing", file_type),\n        )',
    'await db.db.knowledge_documents.insert_one({"id": doc_id, "filename": filename, "file_size": file_size, "upload_time": now, "chunk_count": 0, "conversation_id": conversation_id, "status": "processing", "file_type": file_type})'
)

# 2. ingest_document_background
text = text.replace(
    'await db.execute(\n                """\n                UPDATE knowledge_documents \n                SET chunk_count = ?, status = \'completed\', file_type = ?, file_size = ?\n                WHERE id = ?\n                """,\n                (chunk_count, detected_type, file_size, doc_id),\n            )',
    'await db.db.knowledge_documents.update_one({"id": doc_id}, {"$set": {"chunk_count": chunk_count, "status": "completed", "file_type": detected_type, "file_size": file_size}})'
)

text = text.replace(
    'await db.execute(\n                """\n                UPDATE knowledge_documents \n                SET status = \'failed\', error_message = ?\n                WHERE id = ?\n                """,\n                (err_msg, doc_id),\n            )',
    'await db.db.knowledge_documents.update_one({"id": doc_id}, {"$set": {"status": "failed", "error_message": err_msg}})'
)

# 3. upload_document
text = text.replace(
    'await db.fetch_one("SELECT * FROM knowledge_documents WHERE id = ?", (doc_id,))',
    'await db.db.knowledge_documents.find_one({"id": doc_id})'
)

# 4. list_documents
text = text.replace(
    'await db.fetch_all(\n            "SELECT * FROM knowledge_documents ORDER BY upload_time DESC"\n        )',
    'await db.db.knowledge_documents.find({}).sort("upload_time", -1).to_list(length=None)'
)

# 5. list_conversation_documents
text = text.replace(
    'await db.fetch_all(\n            "SELECT * FROM knowledge_documents WHERE conversation_id = ? ORDER BY upload_time DESC",\n            (conversation_id,),\n        )',
    'await db.db.knowledge_documents.find({"conversation_id": conversation_id}).sort("upload_time", -1).to_list(length=None)'
)

# 6. delete_document
text = text.replace(
    'await db.execute("DELETE FROM knowledge_documents WHERE id = ?", (doc_id,))',
    'await db.db.knowledge_documents.delete_one({"id": doc_id})'
)

with open("backend/app/knowledge/knowledge_manager.py", "w") as f:
    f.write(text)
