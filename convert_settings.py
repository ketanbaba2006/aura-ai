import re
with open("backend/app/api/routes/settings.py", "r") as f:
    text = f.read()

text = text.replace(
    'await db.fetch_all("SELECT key, value FROM system_settings")',
    'await db.db.system_settings.find({}, {"key": 1, "value": 1}).to_list(length=None)'
)

text = text.replace(
    'await db.fetch_one("SELECT value FROM system_settings WHERE key = ?", (key,))',
    'await db.db.system_settings.find_one({"key": key}, {"value": 1})'
)

text = text.replace(
    'await db.execute(\n            "INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)",\n            (key, body.value)\n        )',
    'await db.db.system_settings.update_one({"key": key}, {"$set": {"value": body.value}}, upsert=True)'
)

with open("backend/app/api/routes/settings.py", "w") as f:
    f.write(text)
