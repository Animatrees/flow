from datetime import date, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

type TrimmedString = Annotated[str, StringConstraints(strip_whitespace=True)]
type NonEmptyString = Annotated[TrimmedString, StringConstraints(min_length=1)]


class ProjectStatus(StrEnum):
    OPEN = "open"
    WIP = "wip"
    DONE = "done"


class ProjectCreate(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    name: NonEmptyString
    description: TrimmedString = ""
    start_date: date
    end_date: date
    status: ProjectStatus = ProjectStatus.OPEN


class ProjectCreateWithOwner(ProjectCreate):
    owner_id: UUID


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    name: NonEmptyString | None = None
    description: TrimmedString | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectStatus | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    owner_id: UUID
    start_date: date
    end_date: date
    status: ProjectStatus
    created_at: datetime


class ProjectMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    project_id: UUID
    user_id: UUID
