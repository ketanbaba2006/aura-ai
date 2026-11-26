import re
with open("backend/app/memory/project_manager.py", "r") as f:
    text = f.read()

# 1. create_project
text = text.replace(
    'await db.execute(\n            """INSERT INTO projects (\n                id, name, description, conversation_id, project_type, design_choices, user_goals, created_at, updated_at\n               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",\n            (project_id, name, description, conversation_id, project_type, design_choices, user_goals, now, now),\n        )',
    'await db.db.projects.insert_one({"id": project_id, "name": name, "description": description, "conversation_id": conversation_id, "project_type": project_type, "design_choices": design_choices, "user_goals": user_goals, "created_at": now, "updated_at": now})'
)

# 2. get_project
text = text.replace(
    'await db.fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))',
    'await db.db.projects.find_one({"id": project_id})'
)

# 3. list_projects
text = text.replace(
    'await db.fetch_all("SELECT * FROM projects ORDER BY updated_at DESC")',
    'await db.db.projects.find({}).sort("updated_at", -1).to_list(length=None)'
)
text = text.replace(
    'await db.fetch_all("SELECT * FROM projects WHERE archived = 0 ORDER BY updated_at DESC")',
    'await db.db.projects.find({"archived": 0}).sort("updated_at", -1).to_list(length=None)'
)

# 4. archive_project
text = text.replace(
    'await db.execute(\n            "UPDATE projects SET archived = ?, updated_at = ? WHERE id = ?",\n            (val, now, project_id),\n        )',
    'await db.db.projects.update_one({"id": project_id}, {"$set": {"archived": val, "updated_at": now}})'
)

# 5. get_active_project
text = text.replace(
    'await db.fetch_one(\n            "SELECT active_project_id FROM conversations WHERE id = ?", (conversation_id,)\n        )',
    'await db.db.conversations.find_one({"id": conversation_id}, {"active_project_id": 1})'
)

# 6. set_active_project
text = text.replace(
    'await db.execute(\n            "UPDATE conversations SET active_project_id = ?, updated_at = ? WHERE id = ?",\n            (project_id, now, conversation_id),\n        )',
    'await db.db.conversations.update_one({"id": conversation_id}, {"$set": {"active_project_id": project_id, "updated_at": now}})'
)
text = text.replace(
    'await db.execute(\n            "UPDATE projects SET updated_at = ? WHERE id = ?",\n            (now, project_id),\n        )',
    'await db.db.projects.update_one({"id": project_id}, {"$set": {"updated_at": now}})'
)

# 7. reset_active_project
text = text.replace(
    'await db.execute(\n            "UPDATE conversations SET active_project_id = NULL, updated_at = ? WHERE id = ?",\n            (datetime.utcnow().isoformat(), conversation_id),\n        )',
    'await db.db.conversations.update_one({"id": conversation_id}, {"$set": {"active_project_id": None, "updated_at": datetime.utcnow().isoformat()}})'
)

# 8. detect_and_link_project
text = text.replace(
    'await db.fetch_one("SELECT id FROM projects ORDER BY updated_at DESC LIMIT 1")',
    'await db.db.projects.find_one({}, sort=[("updated_at", -1)])'
)

# 9. goals and tasks
text = text.replace(
    'await db.fetch_all(\n            "SELECT id, title, status FROM goals WHERE project_id = ? ORDER BY created_at ASC",\n            (project_id,)\n        )',
    'await db.db.goals.find({"project_id": project_id}).sort("created_at", 1).to_list(length=None)'
)
text = text.replace(
    'await db.fetch_all(\n                    "SELECT title, status FROM tasks WHERE goal_id = ? ORDER BY order_index ASC",\n                    (g["id"],)\n                )',
    'await db.db.tasks.find({"goal_id": g["id"]}).sort("order_index", 1).to_list(length=None)'
)

with open("backend/app/memory/project_manager.py", "w") as f:
    f.write(text)
