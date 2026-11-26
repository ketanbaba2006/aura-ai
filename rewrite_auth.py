import re
with open("backend/app/api/routes/auth.py", "r") as f:
    text = f.read()

# 1. signup
text = text.replace(
    'await db.fetch_one("SELECT id FROM users WHERE email = ?", (email,))',
    'await db.db.users.find_one({"email": email})'
)
text = text.replace(
    'await db.fetch_one("SELECT COUNT(*) as count FROM users")',
    '{"count": await db.db.users.count_documents({})}'
)
text = text.replace(
    'await db.execute(\n            """\n            INSERT INTO users (id, name, email, password_hash, avatar_url, provider, role, is_active)\n            VALUES (?, ?, ?, ?, ?, \'local\', ?, 1)\n            """,\n            (user_id, body.name, email, pw_hash, avatar_url, role)\n        )',
    'await db.db.users.insert_one({"id": user_id, "name": body.name, "email": email, "password_hash": pw_hash, "avatar_url": avatar_url, "provider": "local", "role": role, "is_active": True})'
)
text = text.replace(
    'await db.execute(\n        "INSERT INTO auth_tokens (id, user_id, token, token_type, expires_at) VALUES (?, ?, ?, \'email_verification\', ?)",\n        (str(uuid.uuid4()), user_id, verification_token, expires.isoformat())\n    )',
    'await db.db.auth_tokens.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "token": verification_token, "token_type": "email_verification", "expires_at": expires.isoformat()})'
)

# 2. login
text = text.replace(
    'await db.fetch_one(\n        "SELECT id, name, email, password_hash, role, is_active FROM users WHERE email = ? AND provider = \'local\'",\n        (email,)\n    )',
    'await db.db.users.find_one({"email": email, "provider": "local"})'
)
text = text.replace(
    'await db.execute(\n        """\n        INSERT INTO user_sessions (id, user_id, token_jti, device_info, ip_address)\n        VALUES (?, ?, ?, ?, ?)\n        """,\n        (str(uuid.uuid4()), user_id, jti, device_info, ip_address)\n    )',
    'await db.db.user_sessions.insert_one({"id": str(uuid.uuid4()), "user_id": user_id, "token_jti": jti, "device_info": device_info, "ip_address": ip_address, "created_at": datetime.utcnow().isoformat(), "last_active": datetime.utcnow().isoformat()})'
)
text = text.replace(
    'await db.execute("UPDATE users SET last_login = ?, updated_at = ? WHERE id = ?", (now, now, user_id))',
    'await db.db.users.update_one({"id": user_id}, {"$set": {"last_login": now, "updated_at": now}})'
)

# 3. refresh
text = text.replace(
    'await db.fetch_one("SELECT id FROM user_sessions WHERE user_id = ? AND token_jti = ?", (user_id, jti))',
    'await db.db.user_sessions.find_one({"user_id": user_id, "token_jti": jti})'
)
text = text.replace(
    'await db.fetch_one("SELECT id, name, email, role, is_active FROM users WHERE id = ?", (user_id,))',
    'await db.db.users.find_one({"id": user_id})'
)
text = text.replace(
    'await db.execute("UPDATE user_sessions SET last_active = ? WHERE token_jti = ?", (now, jti))',
    'await db.db.user_sessions.update_one({"token_jti": jti}, {"$set": {"last_active": now}})'
)

# 4. logout
text = text.replace(
    'await db.execute("DELETE FROM user_sessions WHERE user_id = ? AND token_jti = ?", (user_id, jti))',
    'await db.db.user_sessions.delete_one({"user_id": user_id, "token_jti": jti})'
)

# 5. forgot password
text = text.replace(
    'await db.fetch_one("SELECT id FROM users WHERE email = ? AND provider = \'local\'", (email,))',
    'await db.db.users.find_one({"email": email, "provider": "local"})'
)
text = text.replace(
    'await db.execute(\n        "INSERT INTO auth_tokens (id, user_id, token, token_type, expires_at) VALUES (?, ?, ?, \'password_reset\', ?)",\n        (str(uuid.uuid4()), user["id"], reset_token, expires.isoformat())\n    )',
    'await db.db.auth_tokens.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "token": reset_token, "token_type": "password_reset", "expires_at": expires.isoformat()})'
)

# 6. reset password
text = text.replace(
    'await db.fetch_one(\n        "SELECT user_id, expires_at FROM auth_tokens WHERE token = ? AND token_type = \'password_reset\'",\n        (body.token,)\n    )',
    'await db.db.auth_tokens.find_one({"token": body.token, "token_type": "password_reset"})'
)
text = text.replace(
    'await db.execute("DELETE FROM auth_tokens WHERE token = ?", (body.token,))',
    'await db.db.auth_tokens.delete_one({"token": body.token})'
)
text = text.replace(
    'await db.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?", (new_hash, datetime.utcnow().isoformat(), user_id))',
    'await db.db.users.update_one({"id": user_id}, {"$set": {"password_hash": new_hash, "updated_at": datetime.utcnow().isoformat()}})'
)
text = text.replace(
    'await db.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))',
    'await db.db.user_sessions.delete_many({"user_id": user_id})'
)
text = text.replace(
    'await db.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))',
    'await db.db.auth_tokens.delete_one({"token": token})'
)

# 7. verify email
text = text.replace(
    'await db.fetch_one(\n        "SELECT user_id, expires_at FROM auth_tokens WHERE token = ? AND token_type = \'email_verification\'",\n        (token,)\n    )',
    'await db.db.auth_tokens.find_one({"token": token, "token_type": "email_verification"})'
)
text = text.replace(
    'await db.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))',
    'await db.db.users.update_one({"id": user_id}, {"$set": {"is_active": True}})'
)

# 8. sessions
text = text.replace(
    'await db.fetch_all(\n        "SELECT id, token_jti, device_info, ip_address, last_active, created_at FROM user_sessions WHERE user_id = ? ORDER BY created_at DESC",\n        (current_user["id"],)\n    )',
    'await db.db.user_sessions.find({"user_id": current_user["id"]}).sort("created_at", -1).to_list(length=None)'
)
text = text.replace(
    'await db.execute("DELETE FROM user_sessions WHERE user_id = ?", (current_user["id"],))',
    'await db.db.user_sessions.delete_many({"user_id": current_user["id"]})'
)

# 9. oauth
text = text.replace(
    'await db.fetch_one("SELECT id, name, email, role, is_active FROM users WHERE email = ?", (email,))',
    'await db.db.users.find_one({"email": email})'
)
text = text.replace(
    'await db.execute(\n            """\n            INSERT INTO users (id, name, email, avatar_url, provider, role, is_active)\n            VALUES (?, ?, ?, ?, \'google\', ?, 1)\n            """,\n            (user_id, name, email, avatar_url, role)\n        )',
    'await db.db.users.insert_one({"id": user_id, "name": name, "email": email, "avatar_url": avatar_url, "provider": "google", "role": role, "is_active": True})'
)
text = text.replace(
    'await db.execute(\n            """\n            INSERT INTO users (id, name, email, avatar_url, provider, role, is_active)\n            VALUES (?, ?, ?, ?, ?, ?, 1)\n            """,\n            (user_id, name, email, avatar_url, provider, role)\n        )',
    'await db.db.users.insert_one({"id": user_id, "name": name, "email": email, "avatar_url": avatar_url, "provider": provider, "role": role, "is_active": True})'
)

with open("backend/app/api/routes/auth.py", "w") as f:
    f.write(text)
