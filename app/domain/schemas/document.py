from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.domain.schemas.type_ids import DocumentId, ProjectId, UserId

type TrimmedString = Annotated[str, StringConstraints(strip_whitespace=True)]
type NonEmptyString = Annotated[TrimmedString, StringConstraints(min_length=1)]
type ContentType = Annotated[NonEmptyString, StringConstraints(max_length=255)]
type FileChecksum = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-f0-9]{64}$",
        to_lower=True,
    ),
]


class DocumentCreate(BaseModel):
    """Schema for document upload metadata."""

    model_config = ConfigDict(strict=True, frozen=True)

    filename: NonEmptyString
    content_type: ContentType
    size_bytes: int
    checksum: FileChecksum | None = None


class UploadIntentResponse(BaseModel):
    """Schema for upload intent responses."""

    model_config = ConfigDict(strict=True, frozen=True)

    upload_url: str
    upload_token: NonEmptyString


class DocumentConfirmUpload(BaseModel):
    """Schema for upload confirmation requests."""

    model_config = ConfigDict(strict=True, frozen=True)

    filename: NonEmptyString
    content_type: ContentType
    upload_token: NonEmptyString
    checksum: FileChecksum | None = None


class DocumentCreateStored(DocumentCreate):
    """Schema for persisted document creation data."""

    project_id: ProjectId
    uploaded_by: UserId
    storage_key: NonEmptyString
    checksum: FileChecksum | None = None


class DocumentUpdate(BaseModel):
    """Schema for document updates."""

    model_config = ConfigDict(strict=True, frozen=True)

    filename: NonEmptyString | None = None


class DocumentRead(BaseModel):
    """Schema for document read responses."""

    model_config = ConfigDict(from_attributes=True)

    id: DocumentId
    project_id: ProjectId
    uploaded_by: UserId
    filename: str
    content_type: str
    size_bytes: int
    checksum: str | None
    created_at: datetime


class StoredDocument(DocumentRead):
    """Schema for a persisted document record."""

    storage_key: str


class DownloadUrlResponse(BaseModel):
    """Schema for document download URL responses."""

    model_config = ConfigDict(strict=True, frozen=True)

    download_url: str
