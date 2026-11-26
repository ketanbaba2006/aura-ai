import httpx

def test():
    # Login to get token
    res = httpx.post("http://localhost:8000/api/v1/auth/login", data={"username": "admin", "password": "password"})
    if not res.is_success:
        print("Login failed", res.text)
        return
    token = res.json()["access_token"]
    print("Token:", token)

    # Upload
    with open("frontend/package.json", "rb") as f:
        res = httpx.post(
            "http://localhost:8000/api/v1/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": f},
            data={"conversation_id": "test"}
        )
    print("Upload status:", res.status_code)
    print("Upload response:", res.text)

test()
