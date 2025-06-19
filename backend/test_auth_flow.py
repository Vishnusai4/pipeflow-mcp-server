import pytest
from httpx import AsyncClient
from app.main import app

USERNAME = "testuser"  # <-- Replace with a valid username from your USERS dict
PASSWORD = "testpass"  # <-- Replace with the correct password

@pytest.mark.asyncio
async def test_login_and_session():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Login
        resp = await ac.post("/login", json={"username": USERNAME, "password": PASSWORD})
        print("LOGIN RESPONSE:", resp.status_code, resp.text)
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        cookies = resp.cookies
        assert "access_token" in cookies, "No access_token cookie set"

        # 2. Authenticated endpoint using cookie
        resp2 = await ac.get("/user/sessions", cookies={"access_token": cookies["access_token"]})
        print("SESSION RESPONSE (cookie):", resp2.status_code, resp2.text)
        assert resp2.status_code == 200, f"Session (cookie) failed: {resp2.text}"

        # 3. Authenticated endpoint using Bearer token
        token = resp.json()["access_token"]
        resp3 = await ac.get("/user/sessions", headers={"Authorization": f"Bearer {token}"})
        print("SESSION RESPONSE (header):", resp3.status_code, resp3.text)
        assert resp3.status_code == 200, f"Session (header) failed: {resp3.text}"
