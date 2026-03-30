import httpx
import pytest

from app.services import StoredObjectMetadata
from app.services.jwt_service import JWTService
from tests.fixtures.jwt import TEST_JWT_CONFIG
from tests.unit.fakes.file_storage import InMemoryFileStorage

pytestmark = pytest.mark.anyio

JSON_CONTENT_TYPE = "application/json"
PDF_CONTENT_TYPE = "application/pdf"
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
) -> httpx.Response:
    return await client.post(
        "/api/v1/projects",
        json={
            "name": "Flow",
            "description": "Educational backend",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "status": "open",
        },
        headers=headers,
    )


def upload_token_subject(upload_token: str) -> str:
    return JWTService(TEST_JWT_CONFIG).decode_token(upload_token)["sub"]


async def confirm_uploaded_document(
    client: httpx.AsyncClient,
    *,
    project_id: str,
    headers: dict[str, str],
    payload: dict[str, str],
) -> httpx.Response:
    return await client.post(
        f"/api/v1/projects/{project_id}/documents",
        json=payload,
        headers=headers,
    )


async def test_create_upload_intent_returns_presigned_upload_data(
    client: httpx.AsyncClient,
) -> None:
    headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    project_response = await create_project(client, headers=headers)

    response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/documents/upload-intents",
        json={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "size_bytes": 128,
        },
        headers=headers,
    )

    assert project_response.status_code == 201
    assert response.status_code == 201
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["upload_url"] == "https://storage.example.com/upload"
    assert "upload_token" in response.json()


async def test_confirm_upload_creates_document_without_exposing_storage_key(
    client: httpx.AsyncClient,
    file_storage: InMemoryFileStorage,
) -> None:
    headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    project_response = await create_project(client, headers=headers)
    upload_intent_response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/documents/upload-intents",
        json={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "size_bytes": 128,
        },
        headers=headers,
    )
    storage_key = upload_token_subject(upload_intent_response.json()["upload_token"])
    file_storage.files[storage_key] = StoredObjectMetadata(
        size_bytes=128,
        content_type=PDF_CONTENT_TYPE,
    )

    response = await confirm_uploaded_document(
        client,
        project_id=project_response.json()["id"],
        headers=headers,
        payload={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "upload_token": upload_intent_response.json()["upload_token"],
        },
    )

    assert upload_intent_response.status_code == 201
    assert response.status_code == 201
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["filename"] == "architecture.pdf"
    assert response.json()["content_type"] == PDF_CONTENT_TYPE
    assert response.json()["size_bytes"] == 128
    assert "storage_key" not in response.json()


async def test_get_project_documents_returns_only_public_document_fields(
    client: httpx.AsyncClient,
    file_storage: InMemoryFileStorage,
) -> None:
    headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    project_response = await create_project(client, headers=headers)
    upload_intent_response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/documents/upload-intents",
        json={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "size_bytes": 128,
        },
        headers=headers,
    )
    storage_key = upload_token_subject(upload_intent_response.json()["upload_token"])
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=128)
    create_document_response = await confirm_uploaded_document(
        client,
        project_id=project_response.json()["id"],
        headers=headers,
        payload={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "upload_token": upload_intent_response.json()["upload_token"],
        },
    )

    response = await client.get(
        f"/api/v1/projects/{project_response.json()['id']}/documents",
        headers=headers,
    )

    assert create_document_response.status_code == 201
    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == create_document_response.json()["id"]
    assert "storage_key" not in response.json()[0]


async def test_get_document_download_url_returns_json_payload(
    client: httpx.AsyncClient,
    file_storage: InMemoryFileStorage,
) -> None:
    headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    project_response = await create_project(client, headers=headers)
    upload_intent_response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/documents/upload-intents",
        json={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "size_bytes": 128,
        },
        headers=headers,
    )
    storage_key = upload_token_subject(upload_intent_response.json()["upload_token"])
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=128)
    create_document_response = await confirm_uploaded_document(
        client,
        project_id=project_response.json()["id"],
        headers=headers,
        payload={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "upload_token": upload_intent_response.json()["upload_token"],
        },
    )

    response = await client.get(
        f"/api/v1/documents/{create_document_response.json()['id']}/download-url",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json() == {"download_url": "https://storage.example.com/download"}


async def test_update_document_renames_document(
    client: httpx.AsyncClient,
    file_storage: InMemoryFileStorage,
) -> None:
    headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    project_response = await create_project(client, headers=headers)
    upload_intent_response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/documents/upload-intents",
        json={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "size_bytes": 128,
        },
        headers=headers,
    )
    storage_key = upload_token_subject(upload_intent_response.json()["upload_token"])
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=128)
    create_document_response = await confirm_uploaded_document(
        client,
        project_id=project_response.json()["id"],
        headers=headers,
        payload={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "upload_token": upload_intent_response.json()["upload_token"],
        },
    )

    response = await client.patch(
        f"/api/v1/documents/{create_document_response.json()['id']}",
        json={"filename": "renamed.pdf"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == JSON_CONTENT_TYPE
    assert response.json()["filename"] == "renamed.pdf"
    assert "storage_key" not in response.json()


async def test_delete_document_allows_uploader_member_and_removes_stored_file(
    client: httpx.AsyncClient,
    file_storage: InMemoryFileStorage,
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
    project_response = await create_project(client, headers=owner_headers)
    membership_response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/members",
        params={"user": "participant"},
        headers=owner_headers,
    )
    upload_intent_response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/documents/upload-intents",
        json={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "size_bytes": 128,
        },
        headers=participant_headers,
    )
    storage_key = upload_token_subject(upload_intent_response.json()["upload_token"])
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=128)
    create_document_response = await confirm_uploaded_document(
        client,
        project_id=project_response.json()["id"],
        headers=participant_headers,
        payload={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "upload_token": upload_intent_response.json()["upload_token"],
        },
    )

    response = await client.delete(
        f"/api/v1/documents/{create_document_response.json()['id']}",
        headers=participant_headers,
    )

    assert membership_response.status_code == 201
    assert create_document_response.status_code == 201
    assert response.status_code == 204
    assert storage_key in file_storage.deleted_keys


async def test_delete_document_rejects_member_who_is_not_uploader(
    client: httpx.AsyncClient,
    file_storage: InMemoryFileStorage,
) -> None:
    owner_headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    member_headers = await authorized_headers(
        client,
        username="member",
        email="member@example.com",
    )
    project_response = await create_project(client, headers=owner_headers)
    membership_response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/members",
        params={"user": "member"},
        headers=owner_headers,
    )
    upload_intent_response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/documents/upload-intents",
        json={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "size_bytes": 128,
        },
        headers=owner_headers,
    )
    storage_key = upload_token_subject(upload_intent_response.json()["upload_token"])
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=128)
    create_document_response = await confirm_uploaded_document(
        client,
        project_id=project_response.json()["id"],
        headers=owner_headers,
        payload={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "upload_token": upload_intent_response.json()["upload_token"],
        },
    )

    response = await client.delete(
        f"/api/v1/documents/{create_document_response.json()['id']}",
        headers=member_headers,
    )

    assert membership_response.status_code == 201
    assert create_document_response.status_code == 201
    assert response.status_code == 403
    assert (
        response.json()["message"]
        == "You do not have sufficient permissions to perform this action."
    )


async def test_confirm_upload_rejects_invalid_token(
    client: httpx.AsyncClient,
) -> None:
    headers = await authorized_headers(
        client,
        username="owner",
        email="owner@example.com",
    )
    project_response = await create_project(client, headers=headers)

    response = await client.post(
        f"/api/v1/projects/{project_response.json()['id']}/documents",
        json={
            "filename": "architecture.pdf",
            "content_type": PDF_CONTENT_TYPE,
            "upload_token": "invalid-token",
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["message"] == "Upload token is invalid."


async def test_document_routes_require_authentication(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/documents/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 401
    assert response.json()["message"] == "Not authenticated"
