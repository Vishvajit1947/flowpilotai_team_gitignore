import pytest
from httpx import AsyncClient

# Helper function to register and login a user, returning auth header
async def get_auth_headers(client: AsyncClient, email: str) -> dict:
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123",
            "full_name": "Test User",
        },
    )
    assert reg_response.status_code == 201
    token = reg_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_submit_inbox_success(client: AsyncClient):
    headers = await get_auth_headers(client, "user1@example.com")
    response = await client.post(
        "/api/v1/inbox/submit",
        json={"content": "Hello, this is a valid inbox content submit request."},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Hello, this is a valid inbox content submit request."
    assert data["status"] == "pending"
    assert data["file_url"] is None
    assert "id" in data


@pytest.mark.asyncio
async def test_submit_inbox_too_short(client: AsyncClient):
    headers = await get_auth_headers(client, "user2@example.com")
    response = await client.post(
        "/api/v1/inbox/submit",
        json={"content": "ab"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_inbox_too_long(client: AsyncClient):
    headers = await get_auth_headers(client, "user3@example.com")
    response = await client.post(
        "/api/v1/inbox/submit",
        json={"content": "a" * 5001},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_inbox_invalid_file_url(client: AsyncClient):
    headers = await get_auth_headers(client, "user4@example.com")
    response = await client.post(
        "/api/v1/inbox/submit",
        json={
            "content": "Valid text content",
            "file_url": "http://invalid-url.com/file.png",  # non-https
        },
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_inbox_unauthorized(client: AsyncClient):
    response = await client.post(
        "/api/v1/inbox/submit",
        json={"content": "Valid text content"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_submission_by_id_owner(client: AsyncClient):
    headers = await get_auth_headers(client, "owner@example.com")
    submit_response = await client.post(
        "/api/v1/inbox/submit",
        json={"content": "This submission will be fetched by ID."},
        headers=headers,
    )
    assert submit_response.status_code == 201
    sub_id = submit_response.json()["id"]

    response = await client.get(
        f"/api/v1/inbox/{sub_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["id"] == sub_id
    assert response.json()["content"] == "This submission will be fetched by ID."


@pytest.mark.asyncio
async def test_get_submission_by_id_non_existent(client: AsyncClient):
    headers = await get_auth_headers(client, "fetch_not_found@example.com")
    non_existent_uuid = "550e8400-e29b-41d4-a716-446655440000"
    response = await client.get(
        f"/api/v1/inbox/{non_existent_uuid}",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_submission_by_id_non_owner(client: AsyncClient):
    owner_headers = await get_auth_headers(client, "owner_get@example.com")
    other_headers = await get_auth_headers(client, "other_get@example.com")

    submit_response = await client.post(
        "/api/v1/inbox/submit",
        json={"content": "Private submission content"},
        headers=owner_headers,
    )
    sub_id = submit_response.json()["id"]

    # Request as non-owner
    response = await client.get(
        f"/api/v1/inbox/{sub_id}",
        headers=other_headers,
    )
    assert response.status_code == 404  # owner enforcement: 404 to avoid ID enumeration


@pytest.mark.asyncio
async def test_get_submission_by_id_invalid_uuid(client: AsyncClient):
    headers = await get_auth_headers(client, "invalid_uuid@example.com")
    response = await client.get(
        "/api/v1/inbox/invalid-uuid-format-string",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_submissions_pagination(client: AsyncClient):
    headers = await get_auth_headers(client, "list_paginated@example.com")

    # Create 5 submissions
    for i in range(5):
        await client.post(
            "/api/v1/inbox/submit",
            json={"content": f"Submission number {i}"},
            headers=headers,
        )

    # Fetch page 1 with size 3
    response = await client.get(
        "/api/v1/inbox/?page=1&size=3",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["size"] == 3
    assert data["pages"] == 2

    # Fetch page 2
    response2 = await client.get(
        "/api/v1/inbox/?page=2&size=3",
        headers=headers,
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["items"]) == 2


@pytest.mark.asyncio
async def test_list_submissions_size_cap(client: AsyncClient):
    headers = await get_auth_headers(client, "list_cap@example.com")
    response = await client.get(
        "/api/v1/inbox/?page=1&size=150",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["size"] == 100  # Cap at 100
