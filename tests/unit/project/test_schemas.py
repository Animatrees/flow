from datetime import date

import pytest
from pydantic import ValidationError

from app.domain.schemas import ProjectCreate, ProjectStatus, ProjectUpdate


def test_project_create_accepts_valid_payload() -> None:
    project = ProjectCreate(
        name="  Flow  ",
        description="  Educational backend  ",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert project.name == "Flow"
    assert project.description == "Educational backend"
    assert project.start_date == date(2026, 1, 1)
    assert project.end_date == date(2026, 12, 31)
    assert project.status == ProjectStatus.OPEN


def test_project_create_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(
            name="   ",
            description="Educational backend",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )


def test_project_create_normalizes_empty_description_to_empty_string() -> None:
    project = ProjectCreate(
        name="Flow",
        description="   ",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )

    assert project.description == ""


def test_project_update_accepts_valid_payload() -> None:
    project_update = ProjectUpdate(
        name="Updated Flow",
        status=ProjectStatus.WIP,
    )

    assert project_update.name == "Updated Flow"
    assert project_update.description is None
    assert project_update.start_date is None
    assert project_update.end_date is None
    assert project_update.status == ProjectStatus.WIP


def test_project_update_accepts_partial_payload() -> None:
    project_update = ProjectUpdate(description="  Updated description  ")

    assert project_update.description == "Updated description"
    assert project_update.model_dump(exclude_unset=True) == {"description": "Updated description"}
