from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Response, status

from app.api.v1.get_current_user import get_current_user
from app.domain.schemas import (
    DocumentConfirmUpload,
    DocumentCreate,
    DocumentId,
    DocumentRead,
    DocumentUpdate,
    DownloadUrlResponse,
    ProjectId,
    UploadIntentResponse,
    UserAuthRead,
)
from app.services import DocumentService

project_router = APIRouter(
    route_class=DishkaRoute,
    dependencies=[Depends(get_current_user)],
)

document_router = APIRouter(
    route_class=DishkaRoute,
    dependencies=[Depends(get_current_user)],
)


@project_router.get(
    "/{project_id}/documents",
    status_code=status.HTTP_200_OK,
)
async def get_project_documents(
    project_id: ProjectId,
    document_service: FromDishka[DocumentService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> list[DocumentRead]:
    return list(await document_service.get_all_for_project(current_user, project_id))


@project_router.post(
    "/{project_id}/documents/upload-intents",
    status_code=status.HTTP_201_CREATED,
)
async def create_upload_intent(
    project_id: ProjectId,
    data: DocumentCreate,
    document_service: FromDishka[DocumentService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> UploadIntentResponse:
    return await document_service.initiate_upload(current_user, project_id, data)


@project_router.post(
    "/{project_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
async def confirm_document_upload(
    project_id: ProjectId,
    data: DocumentConfirmUpload,
    document_service: FromDishka[DocumentService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> DocumentRead:
    return await document_service.confirm_upload(current_user, project_id, data)


@document_router.get(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
)
async def get_document_by_id(
    document_id: DocumentId,
    document_service: FromDishka[DocumentService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> DocumentRead:
    return await document_service.get_by_id(current_user, document_id)


@document_router.get(
    "/{document_id}/download-url",
    status_code=status.HTTP_200_OK,
)
async def get_document_download_url(
    document_id: DocumentId,
    document_service: FromDishka[DocumentService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> DownloadUrlResponse:
    download_url = await document_service.get_download_url(current_user, document_id)
    return DownloadUrlResponse(download_url=download_url)


@document_router.patch(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
)
async def update_document(
    document_id: DocumentId,
    data: DocumentUpdate,
    document_service: FromDishka[DocumentService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> DocumentRead:
    return await document_service.update(current_user, document_id, data)


@document_router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: DocumentId,
    document_service: FromDishka[DocumentService],
    current_user: Annotated[UserAuthRead, Depends(get_current_user)],
) -> Response:
    await document_service.delete(current_user, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
