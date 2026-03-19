import httpx
import pytest

pytestmark = pytest.mark.anyio

JSON_CONTENT_TYPE = "application/json"
TEST_PASSWORD = "StrongPass1!"
TEST_PASSWORD_HASH = "hashed-password"


async def register_user(
    client: httpx.AsyncClient,
    *,
    username: str,
    email: str,
    password: str = TEST_PASSWORD,
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "repeat_password": password,
        },
    )


async def test_get_user_by_id_returns_existing_user(client: httpx.AsyncClient) -> None:
    register_response = await register_user(
        client,
        username="valid.user",
        email="user@example.com",
    )

    response = await client.get(f"/api/v1/users/{register_response.json()['id']}")

    assert register_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == register_response.json()


async def test_get_user_by_username_returns_existing_user(
    client: httpx.AsyncClient,
) -> None:
    register_response = await register_user(
        client,
        username="valid.user",
        email="user@example.com",
    )

    response = await client.get("/api/v1/users/by-username/VALID.USER")

    assert register_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == register_response.json()


async def test_update_user_returns_updated_user(client: httpx.AsyncClient) -> None:
    register_response = await register_user(
        client,
        username="valid.user",
        email="user@example.com",
    )

    response = await client.patch(
        f"/api/v1/users/{register_response.json()['id']}",
        json={"email": "Updated@Example.com"},
    )

    assert register_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["username"] == "valid.user"
    assert response.json()["email"] == "updated@example.com"


async def test_update_user_returns_conflict_for_duplicate_email(
    client: httpx.AsyncClient,
) -> None:
    first_response = await register_user(
        client,
        username="first.user",
        email="first@example.com",
    )
    second_response = await register_user(
        client,
        username="second.user",
        email="second@example.com",
    )

    response = await client.patch(
        f"/api/v1/users/{second_response.json()['id']}",
        json={"email": "first@example.com"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert response.status_code == 409
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"message": "Email 'first@example.com' already exists."}


async def test_get_users_returns_all_users(client: httpx.AsyncClient) -> None:
    first_response = await register_user(
        client,
        username="first.user",
        email="first@example.com",
    )
    second_response = await register_user(
        client,
        username="second.user",
        email="second@example.com",
    )

    response = await client.get("/api/v1/users")

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert sorted(response.json(), key=lambda user: user["username"]) == sorted(
        [first_response.json(), second_response.json()],
        key=lambda user: user["username"],
    )


async def test_get_user_by_email_returns_existing_user(
    client: httpx.AsyncClient,
) -> None:
    create_response = await register_user(
        client,
        username="valid.user",
        email="user@example.com",
    )

    response = await client.get("/api/v1/users/by-email/USER@EXAMPLE.COM")

    assert create_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == create_response.json()


async def test_get_user_by_id_returns_not_found_for_missing_user(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/v1/users/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    assert response.status_code == 404
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {
        "message": "User with id 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' was not found."
    }
