import re
with open("backend/app/execution/agent_engine.py", "r") as f:
    text = f.read()

# 1. Insert goal
text = text.replace(
    'await db.execute(\n            "INSERT INTO goals (id, project_id, title, description, status) VALUES (?, ?, ?, ?, ?)",\n            (goal_id, active_project["id"], goal_text, "Decomposed goal", "in_progress")\n        )',
    'await db.db.goals.insert_one({"id": goal_id, "project_id": active_project["id"], "title": goal_text, "description": "Decomposed goal", "status": "in_progress", "created_at": datetime.utcnow().isoformat()})'
)

# 2. Insert tasks
text = text.replace(
    'await db.execute(\n                "INSERT INTO tasks (id, goal_id, title, description, status, order_index) VALUES (?, ?, ?, ?, ?, ?)",\n                (task_id, goal_id, t["title"], t["description"], "pending", idx)\n            )',
    'await db.db.tasks.insert_one({"id": task_id, "goal_id": goal_id, "title": t["title"], "description": t["description"], "status": "pending", "order_index": idx, "created_at": datetime.utcnow().isoformat()})'
)

# 3. Update task completed
text = text.replace(
    'await db.execute(\n                    "UPDATE tasks SET status = \'completed\', updated_at = ? WHERE title = ? AND goal_id = ?",\n                    (datetime.utcnow().isoformat(), task["title"], goal_id)\n                )',
    'await db.db.tasks.update_one({"title": task["title"], "goal_id": goal_id}, {"$set": {"status": "completed", "updated_at": datetime.utcnow().isoformat()}})'
)

# 4. Update task failed
text = text.replace(
    'await db.execute(\n                    "UPDATE tasks SET status = \'failed\', updated_at = ? WHERE title = ? AND goal_id = ?",\n                    (datetime.utcnow().isoformat(), task["title"], goal_id)\n                )',
    'await db.db.tasks.update_one({"title": task["title"], "goal_id": goal_id}, {"$set": {"status": "failed", "updated_at": datetime.utcnow().isoformat()}})'
)

# 5. Update goal status
text = text.replace(
    'await db.execute(\n            "UPDATE goals SET status = ?, created_at = ? WHERE id = ?",\n            (final_goal_status, datetime.utcnow().isoformat(), goal_id)\n        )',
    'await db.db.goals.update_one({"id": goal_id}, {"$set": {"status": final_goal_status, "updated_at": datetime.utcnow().isoformat()}})'
)

with open("backend/app/execution/agent_engine.py", "w") as f:
    f.write(text)
