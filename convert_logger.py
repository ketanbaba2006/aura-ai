import re
with open("backend/app/logs/activity_logger.py", "r") as f:
    text = f.read()

# 1. log
text = text.replace(
    'await db.execute(\n                """\n                INSERT INTO activity_logs (id, timestamp, action_type, category, description, details, status)\n                VALUES (?, ?, ?, ?, ?, ?, ?)\n                """,\n                (log_id, now, action_type, category, description, details_json, status),\n            )',
    'await db.db.activity_logs.insert_one({"id": log_id, "timestamp": now, "action_type": action_type, "category": category, "description": description, "details": details_json, "status": status})'
)

# 2. get_logs
text = text.replace(
    '        sql = "SELECT * FROM activity_logs"\n        params = []\n        conditions = []\n\n        if category:\n            conditions.append("category = ?")\n            params.append(category)\n        if status:\n            conditions.append("status = ?")\n            params.append(status)\n\n        if conditions:\n            sql += " WHERE " + " AND ".join(conditions)\n\n        sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"\n        params.extend([limit, offset])\n\n        return await db.fetch_all(sql, tuple(params))',
    '        filter_query = {}\n        if category:\n            filter_query["category"] = category\n        if status:\n            filter_query["status"] = status\n        return await db.db.activity_logs.find(filter_query).sort("timestamp", -1).skip(offset).limit(limit).to_list(length=None)'
)

# 3. clear_logs
text = text.replace(
    'await db.execute("DELETE FROM activity_logs")',
    'await db.db.activity_logs.delete_many({})'
)

with open("backend/app/logs/activity_logger.py", "w") as f:
    f.write(text)
