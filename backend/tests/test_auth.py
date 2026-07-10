import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_register_login_flow(client: AsyncClient):
    # 1. Register a new user
    register_payload = {
        "email": "testuser@example.com",
        "password": "SecurePass123",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # 2. Duplicate registration should fail
    response_dup = await client.post("/api/v1/auth/register", json=register_payload)
    assert response_dup.status_code == 409
    assert response_dup.json()["detail"] == "An account with this email already exists"

    # 3. Login with valid credentials
    login_payload = {
        "email": "testuser@example.com",
        "password": "SecurePass123",
    }
    response_login = await client.post("/api/v1/auth/login", json=login_payload)
    assert response_login.status_code == 200
    login_data = response_login.json()
    assert "access_token" in login_data
    token = login_data["access_token"]

    # 4. Login with invalid credentials should fail
    login_payload_wrong = {
        "email": "testuser@example.com",
        "password": "WrongPassword123",
    }
    response_login_wrong = await client.post("/api/v1/auth/login", json=login_payload_wrong)
    assert response_login_wrong.status_code == 401
    assert response_login_wrong.json()["detail"] == "Invalid email or password"

    # 5. Fetch profile using access token
    headers = {"Authorization": f"Bearer {token}"}
    response_me = await client.get("/api/v1/auth/me", headers=headers)
    assert response_me.status_code == 200
    me_data = response_me.json()
    assert me_data["email"] == "testuser@example.com"
    assert me_data["full_name"] == "Test User"
    assert me_data["role"] == "user"
    assert me_data["is_active"] is True
    assert "hashed_password" not in me_data


@pytest.mark.asyncio
async def test_invalid_jwt(client: AsyncClient):
    headers = {"Authorization": "Bearer invalid_token_value_here"}
    response_me = await client.get("/api/v1/auth/me", headers=headers)
    assert response_me.status_code == 401
    assert "detail" in response_me.json()
