from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.type_ids import DocumentId, ProjectId, UserId

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
    model_config = ConfigDict(strict=True, frozen=True)

    filename: NonEmptyString
    content_type: ContentType
    size_bytes: int
    checksum: FileChecksum | None = None


class UploadIntentResponse(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    upload_url: str
    storage_key: NonEmptyString


class DocumentConfirmUpload(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    filename: NonEmptyString
    content_type: ContentType
    storage_key: NonEmptyString
    checksum: FileChecksum | None = None


class DocumentCreateStored(DocumentCreate):
    project_id: ProjectId
    uploaded_by: UserId
    storage_key: NonEmptyString
    checksum: FileChecksum | None = None


class DocumentUpdate(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    filename: NonEmptyString | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: DocumentId
    project_id: ProjectId
    uploaded_by: UserId
    filename: str
    content_type: str
    size_bytes: int
    storage_key: str
    checksum: str | None
    created_at: datetime
