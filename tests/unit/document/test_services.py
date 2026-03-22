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
    ProjectRead,
    ProjectStatus,
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
    PermissionDeniedError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    RepositoryError,
    StoredObjectMetadata,
    UnsupportedDocumentTypeError,
)
from app.services.document_service import MAX_DOCUMENT_SIZE_BYTES
from tests.unit.fakes.document_repository import (
    InMemoryDocumentRepository,
    build_document_read,
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
def existing_document() -> DocumentRead:
    return build_document_read(
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
            ProjectMemberRead(project_id=PROJECT_ID, user_id=PARTICIPANT_ID),
        ],
    )


@pytest.fixture
def document_repository(existing_document: DocumentRead) -> InMemoryDocumentRepository:
    return InMemoryDocumentRepository(
        documents=[existing_document],
        id_factory=lambda: UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
    )


@pytest.fixture
def file_storage() -> InMemoryFileStorage:
    return InMemoryFileStorage()


@pytest.fixture
def document_service(
    document_repository: InMemoryDocumentRepository,
    project_repository: InMemoryProjectRepository,
    file_storage: InMemoryFileStorage,
) -> DocumentService:
    return DocumentService(document_repository, project_repository, file_storage)


@pytest.mark.anyio
async def test_document_service_initiate_upload_returns_upload_intent(
    document_service: DocumentService,
    owner: UserRead,
    file_storage: InMemoryFileStorage,
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
    assert upload_intent.storage_key.startswith(f"projects/{PROJECT_ID}/documents/")
    assert file_storage.presigned_put_requests == [
        (upload_intent.storage_key, DOCX_CONTENT_TYPE, MAX_DOCUMENT_SIZE_BYTES)
    ]


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
) -> None:
    storage_key = f"projects/{PROJECT_ID}/documents/generated-key"
    file_storage.files[storage_key] = StoredObjectMetadata(size_bytes=12)

    created_document = await document_service.confirm_upload(
        owner,
        PROJECT_ID,
        DocumentConfirmUpload(
            filename="flow",
            content_type=PDF_CONTENT_TYPE,
            storage_key=storage_key,
        ),
    )

    assert created_document.filename == "flow"


@pytest.mark.anyio
async def test_document_service_confirm_upload_returns_created_document(
    document_service: DocumentService,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
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
            storage_key=storage_key,
        ),
    )

    assert created_document.id == UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    assert created_document.project_id == PROJECT_ID
    assert created_document.uploaded_by == owner.id
    assert created_document.filename == "flow.pdf"
    assert created_document.content_type == PDF_CONTENT_TYPE
    assert created_document.size_bytes == 12
    assert created_document.storage_key == storage_key
    assert created_document.checksum is None


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_when_file_is_missing(
    document_service: DocumentService,
    owner: UserRead,
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
                storage_key=missing_storage_key,
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_foreign_project_storage_key(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    foreign_storage_key = f"projects/{MISSING_PROJECT_ID}/documents/generated-key"

    with pytest.raises(
        DocumentStorageError,
        match=re.escape(
            f"Storage key '{foreign_storage_key}' does not belong to project '{PROJECT_ID}'."
        ),
    ):
        await document_service.confirm_upload(
            owner,
            PROJECT_ID,
            DocumentConfirmUpload(
                filename="flow.pdf",
                content_type=PDF_CONTENT_TYPE,
                storage_key=foreign_storage_key,
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_filename_extension_mismatch(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    storage_key = f"projects/{PROJECT_ID}/documents/generated-key"

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
                storage_key=storage_key,
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_raises_for_oversized_uploaded_document(
    document_service: DocumentService,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
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
                storage_key=storage_key,
            ),
        )


@pytest.mark.anyio
async def test_document_service_confirm_upload_deletes_file_when_metadata_create_fails(
    document_service: DocumentService,
    document_repository: InMemoryDocumentRepository,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
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
                storage_key=storage_key,
            ),
        )

    assert file_storage.deleted_keys == [storage_key]


@pytest.mark.anyio
async def test_document_service_get_by_id_returns_document_for_participant(
    document_service: DocumentService,
    participant: UserRead,
    existing_document: DocumentRead,
) -> None:
    document = await document_service.get_by_id(participant, existing_document.id)

    assert document == existing_document


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
    existing_document: DocumentRead,
) -> None:
    documents = await document_service.get_all_for_project(owner, PROJECT_ID)

    assert list(documents) == [existing_document]


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
    file_storage: InMemoryFileStorage,
    owner: UserRead,
) -> None:
    await document_service.delete(owner, DOCUMENT_ID)

    assert await document_repository.get_by_id(DOCUMENT_ID) is None
    assert file_storage.deleted_keys == ["documents/architecture.pdf"]


@pytest.mark.anyio
async def test_document_service_delete_allows_participant_to_remove_own_document(
    document_repository: InMemoryDocumentRepository,
    project_repository: InMemoryProjectRepository,
    file_storage: InMemoryFileStorage,
    participant: UserRead,
) -> None:
    participant_document = build_document_read(
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
