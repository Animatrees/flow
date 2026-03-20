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


async def login_user(
    client: httpx.AsyncClient,
    *,
    username: str,
    password: str = TEST_PASSWORD,
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/login",
        data={
            "username": username,
            "password": password,
        },
    )


async def authorization_header_for_existing_user(
    client: httpx.AsyncClient,
    *,
    username: str,
    password: str = TEST_PASSWORD,
) -> dict[str, str]:
    login_response = await login_user(
        client,
        username=username,
        password=password,
    )

    assert login_response.status_code == 200

    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


async def authorized_headers(
    client: httpx.AsyncClient,
    *,
    username: str,
    email: str,
    password: str = TEST_PASSWORD,
) -> dict[str, str]:
    register_response = await register_user(
        client,
        username=username,
        email=email,
        password=password,
    )
    login_response = await login_user(
        client,
        username=username,
        password=password,
    )

    assert register_response.status_code == 201
    assert login_response.status_code == 200

    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


async def test_get_user_by_id_returns_existing_user(client: httpx.AsyncClient) -> None:
    register_response = await register_user(
        client,
        username="valid.user",
        email="user@example.com",
    )
    headers = await authorized_headers(
        client,
        username="auth.user",
        email="auth@example.com",
    )

    response = await client.get(
        f"/api/v1/users/{register_response.json()['id']}",
        headers=headers,
    )

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
    headers = await authorized_headers(
        client,
        username="auth.user",
        email="auth@example.com",
    )

    response = await client.get(
        "/api/v1/users/by-username/VALID.USER",
        headers=headers,
    )

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
    headers = await authorized_headers(
        client,
        username="auth.user",
        email="auth@example.com",
    )

    response = await client.patch(
        f"/api/v1/users/{register_response.json()['id']}",
        json={"email": "Updated@Example.com"},
        headers=headers,
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
    headers = await authorization_header_for_existing_user(
        client,
        username="first.user",
    )

    response = await client.patch(
        f"/api/v1/users/{second_response.json()['id']}",
        json={"email": "first@example.com"},
        headers=headers,
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
    headers = await authorization_header_for_existing_user(
        client,
        username="first.user",
    )

    response = await client.get("/api/v1/users", headers=headers)

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
    headers = await authorized_headers(
        client,
        username="auth.user",
        email="auth@example.com",
    )

    response = await client.get(
        "/api/v1/users/by-email/USER@EXAMPLE.COM",
        headers=headers,
    )

    assert create_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == create_response.json()


async def test_get_user_by_id_returns_not_found_for_missing_user(
    client: httpx.AsyncClient,
) -> None:
    headers = await authorized_headers(
        client,
        username="auth.user",
        email="auth@example.com",
    )
    response = await client.get(
        "/api/v1/users/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {
        "message": "User with id 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' was not found."
    }


async def test_get_users_returns_unauthorized_without_token(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/v1/users")

    assert response.status_code == 401
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"message": "Not authenticated"}
