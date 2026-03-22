from datetime import date

import httpx
import pytest

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


async def create_project(
    client: httpx.AsyncClient,
    *,
    headers: dict[str, str],
    payload: dict[str, str] | None = None,
) -> httpx.Response:
    return await client.post(
        "/api/v1/projects",
        json=payload
        or {
            "name": "Flow",
            "description": "Educational backend",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": "open",
        },
        headers=headers,
    )


async def test_create_project_returns_created_project(client: httpx.AsyncClient) -> None:
    headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )

    response = await create_project(client, headers=headers)

    assert response.status_code == 201
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["name"] == "Flow"
    assert response.json()["description"] == "Educational backend"
    assert response.json()["status"] == "open"
    assert response.json()["start_date"] == "2026-01-01"
    assert response.json()["end_date"] == "2026-12-31"


async def test_get_projects_returns_only_accessible_projects(client: httpx.AsyncClient) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    participant_headers = await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    second_owner_headers = await authorized_headers(
        client,
        username="second.owner",
        email="second.owner@example.com",
    )

    owned_project_response = await create_project(
        client,
        headers=participant_headers,
        payload={
            "name": "Participant owned project",
            "description": "Educational backend",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": "open",
        },
    )
    member_project_response = await create_project(
        client,
        headers=owner_headers,
        payload={
            "name": "Shared project",
            "description": "Educational backend",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": "open",
        },
    )
    second_owner_project_response = await create_project(
        client,
        headers=second_owner_headers,
        payload={
            "name": "Private project",
            "description": "Educational backend",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": "open",
        },
    )
    membership_response = await client.post(
        f"/api/v1/projects/{member_project_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    response = await client.get("/api/v1/projects", headers=participant_headers)

    assert owned_project_response.status_code == 201
    assert member_project_response.status_code == 201
    assert second_owner_project_response.status_code == 201
    assert membership_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert {project["name"] for project in response.json()} == {
        "Participant owned project",
        "Shared project",
    }


async def test_get_project_by_id_returns_project_for_participant(client: httpx.AsyncClient) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    participant_headers = await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)
    membership_response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    response = await client.get(
        f"/api/v1/projects/{create_response.json()['id']}",
        headers=participant_headers,
    )

    assert create_response.status_code == 201
    assert membership_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == create_response.json()


async def test_get_project_by_id_returns_forbidden_for_outsider(client: httpx.AsyncClient) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    outsider_headers = await authorized_headers(
        client,
        username="outsider",
        email="outsider@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)

    response = await client.get(
        f"/api/v1/projects/{create_response.json()['id']}",
        headers=outsider_headers,
    )

    assert create_response.status_code == 201
    assert response.status_code == 403
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"message": "You do not have access to this project."}


async def test_get_project_members_returns_members_for_owner(client: httpx.AsyncClient) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)
    membership_response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    response = await client.get(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        headers=owner_headers,
    )

    assert create_response.status_code == 201
    assert membership_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == [
        {
            "project_id": create_response.json()["id"],
            "user_id": membership_response.json()["user_id"],
            "role": "member",
        },
        {
            "project_id": create_response.json()["id"],
            "user_id": create_response.json()["owner_id"],
            "role": "owner",
        },
    ]


async def test_get_project_members_returns_members_for_participant(
    client: httpx.AsyncClient,
) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    participant_headers = await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)
    membership_response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    response = await client.get(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        headers=participant_headers,
    )

    assert create_response.status_code == 201
    assert membership_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == [
        {
            "project_id": create_response.json()["id"],
            "user_id": membership_response.json()["user_id"],
            "role": "member",
        },
        {
            "project_id": create_response.json()["id"],
            "user_id": create_response.json()["owner_id"],
            "role": "owner",
        },
    ]


async def test_get_project_members_returns_forbidden_for_outsider(
    client: httpx.AsyncClient,
) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    outsider_headers = await authorized_headers(
        client,
        username="outsider",
        email="outsider@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)

    response = await client.get(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        headers=outsider_headers,
    )

    assert create_response.status_code == 201
    assert response.status_code == 403
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"message": "You do not have access to this project."}


async def test_update_project_returns_updated_project_for_participant(
    client: httpx.AsyncClient,
) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    participant_headers = await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)
    membership_response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    response = await client.patch(
        f"/api/v1/projects/{create_response.json()['id']}",
        json={
            "description": "Participant update",
            "end_date": "2026-11-30",
        },
        headers=participant_headers,
    )

    assert create_response.status_code == 201
    assert membership_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["description"] == "Participant update"
    assert response.json()["end_date"] == "2026-11-30"


async def test_delete_project_returns_no_content_for_owner(client: httpx.AsyncClient) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)

    response = await client.delete(
        f"/api/v1/projects/{create_response.json()['id']}",
        headers=owner_headers,
    )
    get_response = await client.get(
        f"/api/v1/projects/{create_response.json()['id']}",
        headers=owner_headers,
    )

    assert create_response.status_code == 201
    assert response.status_code == 204
    assert get_response.status_code == 404


async def test_delete_project_returns_forbidden_for_participant(client: httpx.AsyncClient) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    participant_headers = await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)
    membership_response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    response = await client.delete(
        f"/api/v1/projects/{create_response.json()['id']}",
        headers=participant_headers,
    )

    assert create_response.status_code == 201
    assert membership_response.status_code == 201
    assert response.status_code == 403
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {
        "message": "You do not have sufficient permissions to perform this action."
    }


async def test_add_project_member_returns_created_membership(
    client: httpx.AsyncClient,
) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)

    response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "PARTICIPANT"},
        headers=owner_headers,
    )

    assert create_response.status_code == 201
    assert response.status_code == 201
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["project_id"] == create_response.json()["id"]
    assert response.json()["role"] == "member"


async def test_add_project_member_returns_conflict_for_duplicate_participant(
    client: httpx.AsyncClient,
) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)
    first_membership_response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    assert create_response.status_code == 201
    assert first_membership_response.status_code == 201
    assert response.status_code == 409
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"message": "User is already a member of this project."}


async def test_add_project_member_returns_not_found_for_unknown_user(
    client: httpx.AsyncClient,
) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)

    response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "missing.user"},
        headers=owner_headers,
    )

    assert create_response.status_code == 201
    assert response.status_code == 404
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"message": "User with username 'missing.user' was not found."}


async def test_add_project_member_returns_forbidden_for_participant(
    client: httpx.AsyncClient,
) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    participant_headers = await authorized_headers(
        client,
        username="participant",
        email="participant@example.com",
    )
    await authorized_headers(
        client,
        username="outsider",
        email="outsider@example.com",
    )
    create_response = await create_project(client, headers=owner_headers)
    first_membership_response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )

    response = await client.post(
        f"/api/v1/projects/{create_response.json()['id']}/members",
        params={"user": "outsider"},
        headers=participant_headers,
    )

    assert create_response.status_code == 201
    assert first_membership_response.status_code == 201
    assert response.status_code == 403
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {
        "message": "You do not have sufficient permissions to perform this action."
    }


async def test_create_project_returns_validation_error_for_invalid_dates(
    client: httpx.AsyncClient,
) -> None:
    headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )

    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Flow",
            "description": "Educational backend",
            "start_date": date(2026, 12, 31).isoformat(),
            "end_date": date(2026, 1, 1).isoformat(),
            "status": "open",
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {
        "message": "Project end date must be greater than or equal to the start date."
    }
