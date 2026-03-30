import re
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, Project, User
from app.db.repositories import (
    ConflictError,
    DocumentRepository,
    RepositoryError,
)
from app.domain.schemas import DocumentCreateStored, DocumentUpdate, ProjectStatus
from app.domain.schemas.type_ids import DocumentId, ProjectId, UserId

pytestmark = pytest.mark.anyio

OWNER_ID = UserId(UUID("11111111-1111-1111-1111-111111111111"))
UPLOADER_ID = UserId(UUID("22222222-2222-2222-2222-222222222222"))
SECOND_UPLOADER_ID = UserId(UUID("33333333-3333-3333-3333-333333333333"))
PROJECT_ID = ProjectId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
SECOND_PROJECT_ID = ProjectId(UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))
MISSING_PROJECT_ID = ProjectId(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))
MISSING_USER_ID = UserId(UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"))
FIRST_DOCUMENT_ID = DocumentId(UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"))
SECOND_DOCUMENT_ID = DocumentId(UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"))
MISSING_DOCUMENT_ID = DocumentId(UUID("abababab-abab-abab-abab-abababababab"))
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)
LATER_CREATED_AT = datetime(2026, 2, 1, tzinfo=UTC)
PDF_CONTENT_TYPE = "application/pdf"


async def seed_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    username: str,
    email: str,
) -> User:
    user = User(
        id=user_id,
        username=username,
        email=email,
        password_hash="hashed-password",
        is_active=True,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
        last_login_at=None,
        deleted_at=None,
    )
    session.add(user)
    await session.flush()
    return user


async def seed_project(
    session: AsyncSession,
    *,
    project_id: UUID,
    owner_id: UUID,
) -> Project:
    project = Project(
        id=project_id,
        name=f"Project-{project_id}",
        description="",
        owner_id=owner_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        status=ProjectStatus.OPEN,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )
    session.add(project)
    await session.flush()
    return project


async def seed_document(  # noqa: PLR0913
    session: AsyncSession,
    *,
    document_id: UUID,
    project_id: UUID,
    uploaded_by: UUID,
    filename: str,
    storage_key: str,
    created_at: datetime,
) -> Document:
    document = Document(
        id=document_id,
        project_id=project_id,
        uploaded_by=uploaded_by,
        filename=filename,
        content_type=PDF_CONTENT_TYPE,
        size_bytes=128,
        storage_key=storage_key,
        checksum=None,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(document)
    await session.flush()
    return document


@pytest.fixture
async def repository(db_session: AsyncSession) -> DocumentRepository:
    return DocumentRepository(db_session)


async def test_create_persists_document_and_returns_read_model(
    repository: DocumentRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_user(
        db_session,
        user_id=UPLOADER_ID,
        username="uploader",
        email="uploader@example.com",
    )
    await seed_project(
        db_session,
        project_id=PROJECT_ID,
        owner_id=OWNER_ID,
    )

    created_document = await repository.create(
        DocumentCreateStored(
            project_id=PROJECT_ID,
            uploaded_by=UPLOADER_ID,
            filename="architecture.pdf",
            content_type=PDF_CONTENT_TYPE,
            size_bytes=1024,
            storage_key=f"projects/{PROJECT_ID}/documents/architecture",
            checksum=None,
        )
    )

    persisted_document = await repository.get_by_id(created_document.id)

    assert persisted_document == created_document
    assert created_document.project_id == PROJECT_ID
    assert created_document.uploaded_by == UPLOADER_ID
    assert created_document.filename == "architecture.pdf"


async def test_get_by_id_returns_none_for_missing_document(
    repository: DocumentRepository,
) -> None:
    document = await repository.get_by_id(MISSING_DOCUMENT_ID)

    assert document is None


async def test_get_all_returns_documents_sorted_by_created_at_then_id(
    repository: DocumentRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_project(
        db_session,
        project_id=PROJECT_ID,
        owner_id=OWNER_ID,
    )
    first_document = await seed_document(
        db_session,
        document_id=FIRST_DOCUMENT_ID,
        project_id=PROJECT_ID,
        uploaded_by=OWNER_ID,
        filename="a.pdf",
        storage_key=f"projects/{PROJECT_ID}/documents/a",
        created_at=CREATED_AT,
    )
    second_document = await seed_document(
        db_session,
        document_id=SECOND_DOCUMENT_ID,
        project_id=PROJECT_ID,
        uploaded_by=OWNER_ID,
        filename="b.pdf",
        storage_key=f"projects/{PROJECT_ID}/documents/b",
        created_at=LATER_CREATED_AT,
    )

    documents = await repository.get_all()

    assert [document.id for document in documents] == [first_document.id, second_document.id]


async def test_get_all_for_project_filters_and_sorts_documents(
    repository: DocumentRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_project(
        db_session,
        project_id=PROJECT_ID,
        owner_id=OWNER_ID,
    )
    await seed_project(
        db_session,
        project_id=SECOND_PROJECT_ID,
        owner_id=OWNER_ID,
    )
    first_project_document = await seed_document(
        db_session,
        document_id=FIRST_DOCUMENT_ID,
        project_id=PROJECT_ID,
        uploaded_by=OWNER_ID,
        filename="first.pdf",
        storage_key=f"projects/{PROJECT_ID}/documents/first",
        created_at=CREATED_AT,
    )
    second_project_document = await seed_document(
        db_session,
        document_id=SECOND_DOCUMENT_ID,
        project_id=PROJECT_ID,
        uploaded_by=OWNER_ID,
        filename="second.pdf",
        storage_key=f"projects/{PROJECT_ID}/documents/second",
        created_at=LATER_CREATED_AT,
    )
    await seed_document(
        db_session,
        document_id=MISSING_DOCUMENT_ID,
        project_id=SECOND_PROJECT_ID,
        uploaded_by=OWNER_ID,
        filename="third.pdf",
        storage_key=f"projects/{SECOND_PROJECT_ID}/documents/third",
        created_at=CREATED_AT,
    )

    documents = await repository.get_all_for_project(PROJECT_ID)

    assert [document.id for document in documents] == [
        first_project_document.id,
        second_project_document.id,
    ]


async def test_update_persists_changed_filename(
    repository: DocumentRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_project(
        db_session,
        project_id=PROJECT_ID,
        owner_id=OWNER_ID,
    )
    await seed_document(
        db_session,
        document_id=FIRST_DOCUMENT_ID,
        project_id=PROJECT_ID,
        uploaded_by=OWNER_ID,
        filename="old.pdf",
        storage_key=f"projects/{PROJECT_ID}/documents/old",
        created_at=CREATED_AT,
    )

    updated_document = await repository.update(
        FIRST_DOCUMENT_ID,
        DocumentUpdate(filename="new.pdf"),
    )

    assert updated_document is not None
    assert updated_document.filename == "new.pdf"


async def test_update_returns_none_for_missing_document(
    repository: DocumentRepository,
) -> None:
    updated_document = await repository.update(
        MISSING_DOCUMENT_ID,
        DocumentUpdate(filename="new.pdf"),
    )

    assert updated_document is None


async def test_delete_removes_existing_document(
    repository: DocumentRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_project(
        db_session,
        project_id=PROJECT_ID,
        owner_id=OWNER_ID,
    )
    await seed_document(
        db_session,
        document_id=FIRST_DOCUMENT_ID,
        project_id=PROJECT_ID,
        uploaded_by=OWNER_ID,
        filename="delete-me.pdf",
        storage_key=f"projects/{PROJECT_ID}/documents/delete-me",
        created_at=CREATED_AT,
    )

    success = await repository.delete(FIRST_DOCUMENT_ID)

    assert success is True
    assert await repository.get_by_id(FIRST_DOCUMENT_ID) is None


async def test_delete_returns_false_for_missing_document(
    repository: DocumentRepository,
) -> None:
    success = await repository.delete(MISSING_DOCUMENT_ID)

    assert success is False


async def test_create_raises_for_missing_project(
    repository: DocumentRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=UPLOADER_ID,
        username="uploader",
        email="uploader@example.com",
    )

    with pytest.raises(RepositoryError):
        await repository.create(
            DocumentCreateStored(
                project_id=MISSING_PROJECT_ID,
                uploaded_by=UPLOADER_ID,
                filename="missing-project.pdf",
                content_type=PDF_CONTENT_TYPE,
                size_bytes=16,
                storage_key=f"projects/{MISSING_PROJECT_ID}/documents/missing-project",
                checksum=None,
            )
        )


async def test_create_raises_for_missing_uploader(
    repository: DocumentRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_project(
        db_session,
        project_id=PROJECT_ID,
        owner_id=OWNER_ID,
    )

    with pytest.raises(RepositoryError):
        await repository.create(
            DocumentCreateStored(
                project_id=PROJECT_ID,
                uploaded_by=MISSING_USER_ID,
                filename="missing-user.pdf",
                content_type=PDF_CONTENT_TYPE,
                size_bytes=16,
                storage_key=f"projects/{PROJECT_ID}/documents/missing-user",
                checksum=None,
            )
        )


async def test_create_maps_storage_key_uniqueness_violation(
    repository: DocumentRepository,
    db_session: AsyncSession,
) -> None:
    await seed_user(
        db_session,
        user_id=OWNER_ID,
        username="owner",
        email="owner@example.com",
    )
    await seed_user(
        db_session,
        user_id=SECOND_UPLOADER_ID,
        username="second-uploader",
        email="second-uploader@example.com",
    )
    await seed_project(
        db_session,
        project_id=PROJECT_ID,
        owner_id=OWNER_ID,
    )

    duplicate_storage_key = f"projects/{PROJECT_ID}/documents/duplicate"
    await repository.create(
        DocumentCreateStored(
            project_id=PROJECT_ID,
            uploaded_by=OWNER_ID,
            filename="first.pdf",
            content_type=PDF_CONTENT_TYPE,
            size_bytes=16,
            storage_key=duplicate_storage_key,
            checksum=None,
        )
    )

    with pytest.raises(
        ConflictError,
        match=re.escape(f"Document with storage key '{duplicate_storage_key}' already exists."),
    ):
        await repository.create(
            DocumentCreateStored(
                project_id=PROJECT_ID,
                uploaded_by=SECOND_UPLOADER_ID,
                filename="second.pdf",
                content_type=PDF_CONTENT_TYPE,
                size_bytes=16,
                storage_key=duplicate_storage_key,
                checksum=None,
            )
        )
