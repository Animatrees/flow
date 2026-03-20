import re
from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from app.schemas import (
    DocumentCreate,
    DocumentCreateStored,
    DocumentRead,
    DocumentUpdate,
    ProjectCreateWithOwner,
    ProjectMemberRead,
    ProjectRead,
    ProjectStatus,
    UserRead,
)
from app.schemas.type_ids import DocumentId, ProjectId, UserId
from app.services import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
    DocumentTooLargeError,
    ProjectAccessDeniedError,
    ProjectNotFoundError,
    RepositoryError,
    UnsupportedDocumentTypeError,
)
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
        created_at=CREATED_AT,
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
    return DocumentService(
        document_repository,
        project_repository,
        file_storage,
        max_document_size_bytes=32,
    )


@pytest.mark.anyio
async def test_document_service_create_returns_created_document(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    created_document = await document_service.create(
        owner,
        PROJECT_ID,
        DocumentCreate(filename="flow.docx", content_type=DOCX_CONTENT_TYPE),
        b"document-content",
    )

    assert created_document.id == UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    assert created_document.project_id == PROJECT_ID
    assert created_document.uploaded_by == owner.id
    assert created_document.filename == "flow.docx"
    assert created_document.content_type == DOCX_CONTENT_TYPE
    assert created_document.size_bytes == len(b"document-content")
    assert created_document.storage_key == "documents/generated-key"
    assert (
        created_document.checksum
        == "f53a7ee9b0257605da71b5df4dfde3a12924bdf5ac7200c42b886ba55b53a517"
    )


@pytest.mark.anyio
async def test_document_service_create_raises_for_unsupported_document_type(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        UnsupportedDocumentTypeError,
        match=re.escape("Document content type 'text/plain' is not supported."),
    ):
        await document_service.create(
            owner,
            PROJECT_ID,
            DocumentCreate(filename="notes.txt", content_type="text/plain"),
            b"plain-text",
        )


@pytest.mark.anyio
async def test_document_service_create_raises_for_oversized_document(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        DocumentTooLargeError,
        match=re.escape("Document exceeds the maximum allowed size of 32 bytes."),
    ):
        await document_service.create(
            owner,
            PROJECT_ID,
            DocumentCreate(filename="flow.pdf", content_type=PDF_CONTENT_TYPE),
            b"x" * 33,
        )


@pytest.mark.anyio
async def test_document_service_create_raises_for_outsider(
    document_service: DocumentService,
    outsider: UserRead,
) -> None:
    with pytest.raises(
        ProjectAccessDeniedError,
        match=re.escape("You do not have access to this project."),
    ):
        await document_service.create(
            outsider,
            PROJECT_ID,
            DocumentCreate(filename="flow.pdf", content_type=PDF_CONTENT_TYPE),
            b"document-content",
        )


@pytest.mark.anyio
async def test_document_service_create_raises_for_missing_project(
    document_service: DocumentService,
    owner: UserRead,
) -> None:
    with pytest.raises(
        ProjectNotFoundError,
        match=re.escape(f"Project with id '{MISSING_PROJECT_ID}' was not found."),
    ):
        await document_service.create(
            owner,
            MISSING_PROJECT_ID,
            DocumentCreate(filename="flow.pdf", content_type=PDF_CONTENT_TYPE),
            b"document-content",
        )


@pytest.mark.anyio
async def test_document_service_create_deletes_file_when_metadata_create_fails(
    document_service: DocumentService,
    document_repository: InMemoryDocumentRepository,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
) -> None:
    document_repository.create_error = RepositoryError("metadata create failed")

    with pytest.raises(RepositoryError, match=re.escape("metadata create failed")):
        await document_service.create(
            owner,
            PROJECT_ID,
            DocumentCreate(filename="flow.pdf", content_type=PDF_CONTENT_TYPE),
            b"document-content",
        )

    assert file_storage.deleted_keys == ["documents/generated-key"]


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
async def test_document_service_delete_ignores_storage_delete_failure(
    document_service: DocumentService,
    document_repository: InMemoryDocumentRepository,
    file_storage: InMemoryFileStorage,
    owner: UserRead,
) -> None:
    file_storage.delete_error = DocumentStorageError("storage delete failed")

    await document_service.delete(owner, DOCUMENT_ID)

    assert await document_repository.get_by_id(DOCUMENT_ID) is None
