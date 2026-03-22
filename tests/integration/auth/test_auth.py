from uuid import UUID

import httpx
import jwt
import pytest

from tests.fixtures.jwt import TEST_AUTH_JWT

pytestmark = pytest.mark.anyio

JSON_CONTENT_TYPE = "application/json"
TEST_PASSWORD = "StrongPass1!"


async def register_user(
    client: httpx.AsyncClient,
    *,
    username: str = "Valid.User",
    email: str = "User@Example.com",
    password: str = TEST_PASSWORD,
    repeat_password: str | None = None,
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "repeat_password": repeat_password or password,
        },
    )


async def test_register_returns_created_user(client: httpx.AsyncClient) -> None:
    response = await register_user(client)

    assert response.status_code == 201
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert UUID(response.json()["id"])
    assert response.json()["username"] == "valid.user"
    assert response.json()["email"] == "user@example.com"
    assert response.json()["last_login_at"] is None
    assert "password_hash" not in response.json()


async def test_register_returns_conflict_for_duplicate_username(
    client: httpx.AsyncClient,
) -> None:
    payload = {
        "username": "valid.user",
        "email": "user@example.com",
        "password": TEST_PASSWORD,
        "repeat_password": TEST_PASSWORD,
    }

    first_response = await client.post("/api/v1/auth/register", json=payload)
    second_response = await client.post(
        "/api/v1/auth/register",
        json={**payload, "email": "other@example.com"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.headers["content-type"] == JSON_CONTENT_TYPE
    assert second_response.json() == {"message": "Username 'valid.user' already exists."}


async def test_login_returns_access_token(client: httpx.AsyncClient) -> None:
    register_response = await register_user(client)

    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "valid.user",
            "password": TEST_PASSWORD,
        },
    )

    assert register_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    body = response.json()
    payload = jwt.decode(
        body["access_token"],
        TEST_AUTH_JWT.public_key_path.read_text(),
        algorithms=[TEST_AUTH_JWT.algorithm],
    )

    assert body["token_type"] == "Bearer"
    assert body["exp"] > body["iat"]
    assert payload["sub"] == register_response.json()["id"]
    assert payload["username"] == "valid.user"


async def test_login_returns_unauthorized_for_invalid_credentials(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "missing.user",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"message": "Invalid username or password."}


async def test_register_rejects_weak_password(client: httpx.AsyncClient) -> None:
    response = await register_user(
        client,
        password="weakpass",
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["message"] == "Data validation error"
    assert response.json()["details"][0]["loc"] == ["body"]
    assert "Password is too weak." in response.json()["details"][0]["msg"]


async def test_register_rejects_mismatched_passwords(client: httpx.AsyncClient) -> None:
    response = await register_user(
        client,
        repeat_password="StrongPass2!",
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {
        "message": "Data validation error",
        "details": [
            {
                "loc": ["body"],
                "msg": "Passwords do not match.",
                "type": "value_error",
            }
        ],
    }


async def test_register_rejects_invalid_email(client: httpx.AsyncClient) -> None:
    response = await register_user(
        client,
        email="not-an-email",
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["message"] == "Data validation error"
    assert response.json()["details"] == [
        {
            "loc": ["body", "email"],
            "msg": response.json()["details"][0]["msg"],
            "type": "value_error",
        }
    ]
    assert "@-sign" in response.json()["details"][0]["msg"]
