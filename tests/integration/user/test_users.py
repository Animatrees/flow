from uuid import UUID

import httpx
import pytest
from dishka.integrations.fastapi import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User

pytestmark = pytest.mark.anyio

JSON_CONTENT_TYPE = "application/json"
TEST_PASSWORD = "StrongPass1!"


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


async def promote_user_to_admin(container: AsyncContainer, user_id: str) -> None:
    async with container() as request_container:
        session = await request_container.get(AsyncSession)
        user = await session.get(User, UUID(user_id))
        assert user is not None
        user.is_superuser = True
        await session.flush()


async def test_get_me_returns_current_user(client: httpx.AsyncClient) -> None:
    await register_user(
        client,
        username="valid.user",
        email="user@example.com",
    )
    headers = await authorization_header_for_existing_user(
        client,
        username="valid.user",
    )

    response = await client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["username"] == "valid.user"
    assert response.json()["email"] == "user@example.com"
    assert UUID(response.json()["id"])
    assert response.json()["last_login_at"] is not None


async def test_get_user_by_id_returns_public_view(client: httpx.AsyncClient) -> None:
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

    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {
        "id": register_response.json()["id"],
        "username": "valid.user",
        "last_login_at": register_response.json()["last_login_at"],
    }


async def test_update_me_returns_updated_user(client: httpx.AsyncClient) -> None:
    await register_user(
        client,
        username="valid.user",
        email="user@example.com",
    )
    headers = await authorization_header_for_existing_user(
        client,
        username="valid.user",
    )

    response = await client.patch(
        "/api/v1/users/me",
        json={"email": "Updated@Example.com"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["username"] == "valid.user"
    assert response.json()["email"] == "updated@example.com"


async def test_delete_me_returns_no_content_and_blocks_future_login(
    client: httpx.AsyncClient,
) -> None:
    await register_user(
        client,
        username="valid.user",
        email="user@example.com",
    )
    headers = await authorization_header_for_existing_user(
        client,
        username="valid.user",
    )

    delete_response = await client.delete("/api/v1/users/me", headers=headers)
    login_response = await login_user(
        client,
        username="valid.user",
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert login_response.status_code == 401
    assert login_response.headers["content-type"] == JSON_CONTENT_TYPE
    assert login_response.json() == {"message": "Invalid username or password."}


async def test_get_users_list_is_not_available_for_regular_user(client: httpx.AsyncClient) -> None:
    headers = await authorized_headers(
        client,
        username="valid.user",
        email="user@example.com",
    )

    response = await client.get("/api/v1/users", headers=headers)

    assert response.status_code == 404
    assert response.headers["content-type"] == JSON_CONTENT_TYPE


async def test_admin_get_users_returns_full_user_views(
    client: httpx.AsyncClient,
    container: AsyncContainer,
) -> None:
    admin_response = await register_user(
        client,
        username="admin.user",
        email="admin@example.com",
    )
    await register_user(
        client,
        username="regular.user",
        email="regular@example.com",
    )
    await promote_user_to_admin(container, admin_response.json()["id"])
    headers = await authorization_header_for_existing_user(
        client,
        username="admin.user",
    )

    response = await client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert len(response.json()) == 2
    assert response.json()[0].keys() == {
        "id",
        "username",
        "email",
        "is_superuser",
        "is_active",
        "created_at",
        "updated_at",
        "last_login_at",
        "deleted_at",
    }
    assert any(user["is_superuser"] is True for user in response.json())


async def test_admin_patch_user_updates_role_and_activity(
    client: httpx.AsyncClient,
    container: AsyncContainer,
) -> None:
    admin_response = await register_user(
        client,
        username="admin.user",
        email="admin@example.com",
    )
    target_response = await register_user(
        client,
        username="regular.user",
        email="regular@example.com",
    )
    await promote_user_to_admin(container, admin_response.json()["id"])
    headers = await authorization_header_for_existing_user(
        client,
        username="admin.user",
    )

    response = await client.patch(
        f"/api/v1/admin/users/{target_response.json()['id']}",
        json={"is_superuser": True, "is_active": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["is_superuser"] is True
    assert response.json()["is_active"] is False


async def test_admin_delete_user_by_id_soft_deletes_target(
    client: httpx.AsyncClient,
    container: AsyncContainer,
) -> None:
    admin_response = await register_user(
        client,
        username="admin.user",
        email="admin@example.com",
    )
    target_response = await register_user(
        client,
        username="regular.user",
        email="regular@example.com",
    )
    await promote_user_to_admin(container, admin_response.json()["id"])
    headers = await authorization_header_for_existing_user(
        client,
        username="admin.user",
    )

    delete_response = await client.delete(
        f"/api/v1/admin/users/{target_response.json()['id']}",
        headers=headers,
    )
    login_response = await login_user(
        client,
        username="regular.user",
    )

    assert delete_response.status_code == 204
    assert login_response.status_code == 401


async def test_admin_get_user_by_id_returns_soft_deleted_user(
    client: httpx.AsyncClient,
    container: AsyncContainer,
) -> None:
    admin_response = await register_user(
        client,
        username="admin.user",
        email="admin@example.com",
    )
    target_response = await register_user(
        client,
        username="regular.user",
        email="regular@example.com",
    )
    await promote_user_to_admin(container, admin_response.json()["id"])
    headers = await authorization_header_for_existing_user(
        client,
        username="admin.user",
    )
    delete_response = await client.delete(
        f"/api/v1/admin/users/{target_response.json()['id']}",
        headers=headers,
    )

    response = await client.get(
        f"/api/v1/admin/users/{target_response.json()['id']}",
        headers=headers,
    )

    assert delete_response.status_code == 204
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["id"] == target_response.json()["id"]
    assert response.json()["deleted_at"] is not None
    assert response.json()["is_active"] is False


async def test_admin_endpoints_return_forbidden_for_regular_user(
    client: httpx.AsyncClient,
) -> None:
    headers = await authorized_headers(
        client,
        username="valid.user",
        email="user@example.com",
    )

    response = await client.get("/api/v1/admin/users", headers=headers)

    assert response.status_code == 403
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {
        "message": "You do not have sufficient permissions to perform this action."
    }


async def test_admin_routes_are_hidden_from_openapi(client: httpx.AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/admin/users" not in response.json()["paths"]
    assert "/api/v1/admin/users/{user_id}" not in response.json()["paths"]


async def test_users_endpoints_require_authentication(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"message": "Not authenticated"}
