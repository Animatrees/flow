from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Query, Response, status

from app.api.v1.get_current_user import get_current_user
from app.domain.schemas import (
    ProjectCreate,
    ProjectId,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
    UserRead,
)
from app.domain.schemas.user import Username
from app.services import ProjectService, UserService

router = APIRouter(
    route_class=DishkaRoute,
    dependencies=[Depends(get_current_user)],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectCreate,
    project_service: FromDishka[ProjectService],
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ProjectRead:
    return await project_service.create(current_user, data)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def get_projects(
    project_service: FromDishka[ProjectService],
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> list[ProjectRead]:
    return list(await project_service.get_all_for_user(current_user))


@router.get(
    "/{project_id}",
    status_code=status.HTTP_200_OK,
)
async def get_project_by_id(
    project_id: ProjectId,
    project_service: FromDishka[ProjectService],
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ProjectRead:
    return await project_service.get_by_id(current_user, project_id)


@router.patch(
    "/{project_id}",
    status_code=status.HTTP_200_OK,
)
async def update_project(
    project_id: ProjectId,
    data: ProjectUpdate,
    project_service: FromDishka[ProjectService],
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ProjectRead:
    return await project_service.update(current_user, project_id, data)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: ProjectId,
    project_service: FromDishka[ProjectService],
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> Response:
    await project_service.delete(current_user, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/invite",
    status_code=status.HTTP_201_CREATED,
)
async def invite_user_to_project(
    project_id: ProjectId,
    user: Annotated[Username, Query()],
    project_service: FromDishka[ProjectService],
    user_service: FromDishka[UserService],
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> ProjectMemberRead:
    invited_user = await user_service.get_by_username(user)
    return await project_service.add_member(current_user, project_id, invited_user.id)
