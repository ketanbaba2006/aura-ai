import re

with open("backend/app/api/routes/auth.py", "r") as f:
    text = f.read()

# Replace db.fetch_one -> db.db.<collection>.find_one
text = re.sub(
    r'await db\.fetch_one\(\s*"SELECT.*?FROM\s+([a-zA-Z_]+)\s+WHERE\s+(.*?)"\s*,\s*\((.*?)\)\s*\)',
    r'await db.db.\1.find_one({ /* \2: \3 */ })', 
    text
)

with open("scratch.py", "w") as f:
    f.write(text)
