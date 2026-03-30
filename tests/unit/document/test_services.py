import re
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.domain.schemas import (
    DocumentConfirmUpload,
    DocumentCreate,
    DocumentCreateStored,
    DocumentRead,
    DocumentUpdate,
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectMemberRole,
    ProjectRead,
    ProjectStatus,
    StoredDocument,
)
from app.domain.schemas import (
    UserAuthRead as UserRead,
)
from app.domain.schemas.type_ids import DocumentId, ProjectId, UserId
from app.services import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
    DocumentTooLargeError,
    InvalidUploadTokenError,
    PermissionDeniedError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    RepositoryError,
    StoredObjectMetadata,
    UnsupportedDocumentTypeError,
)
from app.services.document_service import MAX_DOCUMENT_SIZE_BYTES
from app.services.jwt_service import JWTService
from tests.fixtures.jwt import TEST_JWT_CONFIG
from tests.unit.fakes.document_repository import (
    InMemoryDocumentRepository,
    build_stored_document,
)
from tests.unit.fakes.file_storage import InMemoryFileStorage
from tests.unit.fakes.project_repository import InMemoryProjectRepository, build_project_read

OWNER_ID = UserId(UUID("11111111-1111-1111-1111-111111111111"))
PARTICIPANT_ID = UserId(UUID("22222222-2222-2222-2222-222222222222"))
OUTSIDER_ID = UserId(UUID("33333333-3333-3333-3333-333333333333"))
PROJECT_ID = ProjectId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
MISSING_PROJECT_ID = ProjectId(UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
DOCUMENT_ID = DocumentId(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))
MISSING_DOCUMENT_ID = DocumentId(UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"))
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_CONTENT_TYPE = "application/pdf"


def build_user(user_id: UUID, username: str, email: str) -> UserRead:
    return UserRead(
        id=UserId(user_id),
        username=username,
        email=email,
        password_hash="hashed-password",
        is_superuser=False,
        is_active=True,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        last_login_at=None,
        deleted_at=None,
    )


@pytest.fixture
def owner() -> UserRead:
    return build_user(OWNER_ID, "owner", "owner@example.com")


@pytest.fixture
def participant() -> UserRead:
    return build_user(PARTICIPANT_ID, "participant", "participant@example.com")


@pytest.fixture
def outsider() -> UserRead:
    return build_user(OUTSIDER_ID, "outsider", "outsider@example.com")


@pytest.fixture
def existing_project() -> ProjectRead:
    return build_project_read(
        project_id=PROJECT_ID,
        data=ProjectCreateWithOwner(
            name="Flow",
            description="Educational backend",
            owner_id=OWNER_ID,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            status=ProjectStatus.OPEN,
        ),
        created_at=CREATED_AT,
    )


@pytest.fixture
def existing_document() -> StoredDocument:
    return build_stored_document(
        document_id=DOCUMENT_ID,
        data=DocumentCreateStored(
            project_id=PROJECT_ID,
            uploaded_by=OWNER_ID,
            filename="architecture.pdf",
            content_type=PDF_CONTENT_TYPE,
            size_bytes=12,
            storage_key="documents/architecture.pdf",
            checksum="d2a84f4b8b650937ec8f73cd8be2c74f8b65d7fcb8e7f2f6a5e4f4d42e3888d2",
        ),
        created_at=CREATED_AT,
    )


@pytest.fixture
def project_repository(existing_project: ProjectRead) -> InMemoryProjectRepository:
    return InMemoryProjectRepository(
        projects=[existing_project],
        members=[
            ProjectMemberRead(
                project_id=PROJECT_ID,
                user_id=PARTICIPANT_ID,
                role=ProjectMemberRole.MEMBER,
            ),
        ],
    )


@pytest.fixture
def document_repository(existing_document: StoredDocument) -> InMemoryDocumentRepository:
    return InMemoryDocumentRepository(
        documents=[existing_document],
        id_factory=lambda: UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
    )


@pytest.fixture
def file_storage() -> InMemoryFileStorage:
    return InMemoryFileStorage()


@pytest.fixture
def jwt_service() -> JWTService:
    return JWTService(TEST_JWT_CONFIG)


@pytest.fixture
def document_service(
    document_repository: InMemoryDocumentRepository,
    project_repository: InMemoryProjectRepository,
    file_storage: InMemoryFileStorage,
    jwt_service: JWTService,
) -> DocumentService:
    return DocumentService(
        document_repository,
        project_repository,
        file_storage,
        jwt_service,
        TEST_JWT_CONFIG,
    )


def build_upload_token(
    jwt_service: JWTService,
    *,
    claims: dict[str, str] | None = None,
    expire_minutes: int | None = None,
    include_sub: bool = True,
) -> str:
    token_claims = claims.copy() if claims is not None else {}
    project_id = token_claims.get("project_id", str(PROJECT_ID))
    payload: dict[str, str] = {
        "project_id": str(PROJECT_ID),
        "uploaded_by": str(OWNER_ID),
        "type": "upload_intent",
    }
    payload.update(token_claims)
    if include_sub:
        payload["sub"] = payload.get("sub", f"projects/{project_id}/documents/generated-key")

    return jwt_service.create_token(
        payload,
        expire_minutes=expire_minutes or TEST_JWT_CONFIG.upload_token_expire_minutes,
    ).token


@pytest.mark.anyio
async def test_document_service_initiate_upload_returns_upload_intent(
    document_service: DocumentService,
    project_repository: InMemoryProjectRepository,
    owner: UserRead,
    file_storage: InMemoryFileStorage,
    jwt_service: JWTService,
) -> None:
    upload_intent = await document_service.initiate_upload(
        owner,
        PROJECT_ID,
        DocumentCreate(
            filename="flow.docx",
            content_type=DOCX_CONTENT_TYPE,
            size_bytes=16,
        ),
    )

    assert upload_intent.upload_url == file_storage.put_url
    payload = jwt_service.decode_token(upload_intent.upload_token)
    assert payload["sub"].startswith(f"projects/{PROJECT_ID}/documents/")
    assert payload["project_id"] == str(PROJECT_ID)
    assert payload["uploaded_by"] == str(owner.id)
    assert payload["type"] == "upload_intent"
    assert file_storage.presigned_put_requests == [
        (payload["sub"], DOCX_CONTENT_TYPE, MAX_DOCUMENT_SIZE_BYTES)
    ]
    assert project_repository.get_project_with_user_role_calls == [(PROJECT_ID, OWNER_ID)]
    assert project_repository.get_by_id_calls == []
    assert project_repository.has_access_to_project_calls == []


@pytest.mark.anyio
async def test_document_service_initiate_upload_allows_filename_without_extension(
    document_service: DocumentService,
    owner: UserRead,
    file_storage: InMemoryFileStorage,
) -> None:
    upload_intent = await document_service.initiate_upload(
        owner,
        PROJECT_ID,
        DocumentCreate(
            filename="flow",
            content_type=PDF_CONTENT_TYPE,
            size_bytes=16,
        ),
    )

    assert upload_intent.upload_url == file_storage.put_url


@pytest.mark.anyio
async def test_document_service_initiate_upload_raises_for_unsupported_document_type(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        UnsupportedDocumentTypeError,
        match=re.escape("Document content type 'text/plain' is not supported."),
    ):
        await document_service.initiate_upload(
            owner,
            PROJECT_ID,
            DocumentCreate(
                filename="notes.txt",
                content_type="text/plain",
                size_bytes=10,
            ),
        )


@pytest.mark.anyio
async def test_document_service_initiate_upload_raises_for_filename_extension_mismatch(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        UnsupportedDocumentTypeError,
        match=re.escape(
            "Filename 'notes.pdf' does not match the expected extension '.docx' for content type "
            "'application/vnd.openxmlformats-officedocument.wordprocessingml.document'."
        ),
    ):
        await document_service.initiate_upload(
            owner,
            PROJECT_ID,
            DocumentCreate(
                filename="notes.pdf",
                content_type=DOCX_CONTENT_TYPE,
                size_bytes=10,
            ),
        )


@pytest.mark.anyio
async def test_document_service_initiate_upload_raises_for_oversized_document(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        DocumentTooLargeError,
        match=re.escape(
            f"Document exceeds the maximum allowed size of {MAX_DOCUMENT_SIZE_BYTES} bytes."
        ),
    ):
        await document_service.initiate_upload(
            owner,
            PROJECT_ID,
            DocumentCreate(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                size_bytes=MAX_DOCUMENT_SIZE_BYTES + 1,
            ),
        )


@pytest.mark.anyio
async def test_document_service_initiate_upload_raises_for_outsider(
    document_service: DocumentService,
    outsider: UserRead,
) -> None:
    with pytest.raises(
        ProjectAccessDeniedError,
        match=re.escape("You do not have access to this project."),
    ):
        await document_service.initiate_upload(
            outsider,
            PROJECT_ID,
            DocumentCreate(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                size_bytes=16,
            ),
        )


@pytest.mark.anyio
async def test_document_service_initiate_upload_raises_for_missing_project(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        ProjectNotFoundError,
        match=re.escape(f"Project with id '{MISSING_PROJECT_ID}' was not found."),
    ):
        await document_service.initiate_upload(
            owner,
            MISSING_PROJECT_ID,
            DocumentCreate(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                size_bytes=16,
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_allows_filename_without_extension(
    document_service: DocumentService,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    storage_key = f"projects/{PROJECT_ID}/documents/generated-key"
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=12)

    created_document = await document_service.confirm_upload(
        owner,
        PROJECT_ID,
        DocumentConfirmUpload(
            filename="flow",
            content_type=PDF_CONTENT_TYPE,
            upload_token=build_upload_token(jwt_service, claims={"sub": storage_key}),
        ),
    )

    assert created_document.filename == "flow"


@pytest.mark.anyio
async def test_document_service_confirm_upload_returns_created_document(
    document_service: DocumentService,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    storage_key = f"projects/{PROJECT_ID}/documents/generated-key"
    file_storage.files[storage_key] = StoredObjectMetadata(
        size_bytes=12,
        etag="etag-1",
        content_type=PDF_CONTENT_TYPE,
    )

    created_document = await document_service.confirm_upload(
        owner,
        PROJECT_ID,
        DocumentConfirmUpload(
            filename="flow.pdf",
            content_type=PDF_CONTENT_TYPE,
            upload_token=build_upload_token(jwt_service, claims={"sub": storage_key}),
        ),
    )

    assert created_document.id == UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    assert created_document.project_id == PROJECT_ID
    assert created_document.uploaded_by == owner.id
    assert created_document.filename == "flow.pdf"
    assert created_document.content_type == PDF_CONTENT_TYPE
    assert created_document.size_bytes == 12
    assert created_document.checksum is None


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_when_file_is_missing(
    document_service: DocumentService,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    missing_storage_key = f"projects/{PROJECT_ID}/documents/missing-key"

    with pytest.raises(
        DocumentStorageError,
        match=re.escape(f"Uploaded document '{missing_storage_key}' was not found in storage."),
    ):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(
                    jwt_service,
                    claims={"sub": missing_storage_key},
                ),
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_invalid_token_type(
    document_service: DocumentService,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    with pytest.raises(InvalidUploadTokenError, match=re.escape("Upload token has invalid type.")):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(jwt_service, claims={"type": "access"}),
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_wrong_project_token(
    document_service: DocumentService,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    with pytest.raises(
        InvalidUploadTokenError,
        match=re.escape("Upload token does not belong to this project."),
    ):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(
                    jwt_service,
                    claims={"project_id": str(MISSING_PROJECT_ID)},
                ),
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_wrong_uploading_user(
    document_service: DocumentService,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    with pytest.raises(
        InvalidUploadTokenError,
        match=re.escape("Upload token does not belong to this user."),
    ):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(
                    jwt_service,
                    claims={"uploaded_by": str(PARTICIPANT_ID)},
                ),
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_missing_subject_claim(
    document_service: DocumentService,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    with pytest.raises(
        InvalidUploadTokenError,
        match=re.escape("Upload token missing required 'sub' claim."),
    ):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(jwt_service, include_sub=False),
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_expired_upload_token(
    document_service: DocumentService,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    with pytest.raises(InvalidUploadTokenError, match=re.escape("Upload token is invalid.")):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(jwt_service, expire_minutes=-1),
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_filename_extension_mismatch(
    document_service: DocumentService,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    with pytest.raises(
        UnsupportedDocumentTypeError,
        match=re.escape(
            "Filename 'flow.docx' does not match the expected extension '.pdf' for content type "
            "'application/pdf'."
        ),
    ):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.docx",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(jwt_service),
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_oversized_uploaded_document(
    document_service: DocumentService,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    storage_key = f"projects/{PROJECT_ID}/documents/generated-key"
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=MAX_DOCUMENT_SIZE_BYTES + 1)

    with pytest.raises(
        DocumentTooLargeError,
        match=re.escape(
            f"Document exceeds the maximum allowed size of {MAX_DOCUMENT_SIZE_BYTES} bytes."
        ),
    ):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(jwt_service, claims={"sub": storage_key}),
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_deletes_file_when_metadata_create_fails(
    document_service: DocumentService,
    document_repository: InMemoryDocumentRepository,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
    jwt_service: JWTService,
) -> None:
    storage_key = f"projects/{PROJECT_ID}/documents/generated-key"
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=12)
    document_repository.create_error = RepositoryError("metadata create failed")

    with pytest.raises(RepositoryError, match=re.escape("metadata create failed")):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                upload_token=build_upload_token(jwt_service, claims={"sub": storage_key}),
            ),
        )

    assert file_storage.deleted_keys == [storage_key]


@pytest.mark.anyio
async def test_document_service_get_by_id_returns_document_for_participant(
    document_service: DocumentService,
    participant: UserRead,
    existing_document: StoredDocument,
) -> None:
    document = await document_service.get_by_id(participant, existing_document.id)

    assert document == DocumentRead.model_validate(existing_document)


@pytest.mark.anyio
async def test_document_service_get_by_id_raises_for_missing_document(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        DocumentNotFoundError,
        match=re.escape(f"Document with id '{MISSING_DOCUMENT_ID}' was not found."),
    ):
        await document_service.get_by_id(owner, MISSING_DOCUMENT_ID)


@pytest.mark.anyio
async def test_document_service_get_all_for_project_returns_documents(
    document_service: DocumentService,
    owner: UserRead,
    existing_document: StoredDocument,
) -> None:
    documents = await document_service.get_all_for_project(owner, PROJECT_ID)

    assert list(documents) == [DocumentRead.model_validate(existing_document)]


@pytest.mark.anyio
async def test_document_service_update_returns_updated_document(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    updated_document = await document_service.update(
        owner,
        DOCUMENT_ID,
        DocumentUpdate(filename="renamed.pdf"),
    )

    assert updated_document.filename == "renamed.pdf"


@pytest.mark.anyio
async def test_document_service_delete_removes_document_and_file(
    document_service: DocumentService,
    document_repository: InMemoryDocumentRepository,
    project_repository: InMemoryProjectRepository,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
) -> None:
    await document_service.delete(owner, DOCUMENT_ID)

    assert await document_repository.get_by_id(DOCUMENT_ID) is None
    assert file_storage.deleted_keys == ["documents/architecture.pdf"]
    assert project_repository.get_project_with_user_role_calls == [(PROJECT_ID, OWNER_ID)]
    assert project_repository.get_by_id_calls == []
    assert project_repository.has_access_to_project_calls == []


@pytest.mark.anyio
async def test_document_service_delete_allows_participant_to_remove_own_document(
    document_repository: InMemoryDocumentRepository,
    project_repository: InMemoryProjectRepository,
    file_storage: InMemoryFileStorage,
    participant: UserRead,
    jwt_service: JWTService,
) -> None:
    participant_document = build_stored_document(
        document_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        data=DocumentCreateStored(
            project_id=PROJECT_ID,
            uploaded_by=PARTICIPANT_ID,
            filename="participant.pdf",
            content_type=PDF_CONTENT_TYPE,
            size_bytes=11,
            storage_key="documents/participant.pdf",
            checksum=None,
        ),
        created_at=CREATED_AT,
    )
    document_repository.documents[participant_document.id] = participant_document
    document_service = DocumentService(
        document_repository,
        project_repository,
        file_storage,
        jwt_service,
        TEST_JWT_CONFIG,
    )

    await document_service.delete(participant, participant_document.id)

    assert await document_repository.get_by_id(participant_document.id) is None
    assert file_storage.deleted_keys == ["documents/participant.pdf"]


@pytest.mark.anyio
async def test_document_service_delete_raises_for_participant_deleting_foreign_document(
    document_service: DocumentService,
    participant: UserRead,
) -> None:
    with pytest.raises(
        PermissionDeniedError,
        match=re.escape("You do not have sufficient permissions to perform this action."),
    ):
        await document_service.delete(participant, DOCUMENT_ID)


@pytest.mark.anyio
async def test_document_service_delete_ignores_storage_delete_failure(
    document_service: DocumentService,
    document_repository: InMemoryDocumentRepository,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
) -> None:
    file_storage.delete_error = DocumentStorageError("storage delete failed")

    await document_service.delete(owner, DOCUMENT_ID)

    assert await document_repository.get_by_id(DOCUMENT_ID) is None


@pytest.mark.anyio
async def test_document_service_get_download_url_returns_presigned_url(
    document_service: DocumentService,
    file_storage: InMemoryFileStorage,
    participant: UserRead,
) -> None:
    download_url = await document_service.get_download_url(participant, DOCUMENT_ID)

    assert download_url == file_storage.get_url
    assert file_storage.presigned_get_requests == ["documents/architecture.pdf"]
