from __future__ import annotations

import os
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_storage import InfraiError, InfraiStorage
from .upload_policy import UploadRejected, authorize_upload

BUCKET = os.environ.get("COURSE_ASSET_BUCKET", "course-delivery-assets")
app = FastAPI(title="Course asset upload authorization")


class UploadRequest(BaseModel):
    course_id: str = Field(min_length=1, max_length=80)
    assignment_id: str = Field(min_length=1, max_length=80)
    learner_id: str = Field(min_length=1, max_length=80)
    submission_id: UUID
    file_name: str = Field(min_length=1, max_length=180)
    content_type: str
    size_bytes: int
    deadline: datetime
    requested_at: datetime


class UploadAuthorization(BaseModel):
    upload_url: str
    method: str
    object_key: str
    expires_seconds: int


class EducatorReport(BaseModel):
    course_id: str
    stored_asset_count: int
    object_keys: list[str]


async def storage_dependency() -> InfraiStorage:
    storage = InfraiStorage()
    try:
        yield storage
    finally:
        await storage.close()


StorageDep = Annotated[InfraiStorage, Depends(storage_dependency)]


def _client_error(error: InfraiError) -> HTTPException:
    status = error.status_code if 400 <= error.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": error.code, "message": str(error)})


@app.post("/upload-authorizations", response_model=UploadAuthorization)
async def create_upload_authorization(request: UploadRequest, storage: StorageDep) -> UploadAuthorization:
    try:
        decision = authorize_upload(
            course_id=request.course_id,
            assignment_id=request.assignment_id,
            learner_id=request.learner_id,
            file_name=request.file_name,
            content_type=request.content_type,
            size_bytes=request.size_bytes,
            deadline=request.deadline,
            requested_at=request.requested_at,
        )
        signed = await storage.presign_put(
            BUCKET,
            decision.object_key,
            content_type=request.content_type,
            max_bytes=decision.max_bytes,
            idempotency_key=str(request.submission_id),
        )
    except UploadRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InfraiError as exc:
        raise _client_error(exc) from exc
    return UploadAuthorization(
        upload_url=str(signed["url"]),
        method="PUT",
        object_key=decision.object_key,
        expires_seconds=600,
    )


@app.get("/educator/courses/{course_id}/assets", response_model=EducatorReport)
async def educator_asset_report(course_id: str, storage: StorageDep) -> EducatorReport:
    prefix = f"courses/{course_id}/"
    try:
        items = await storage.list_objects(BUCKET)
    except InfraiError as exc:
        raise _client_error(exc) from exc
    keys = sorted(str(item["key"]) for item in items if str(item.get("key", "")).startswith(prefix))
    return EducatorReport(course_id=course_id, stored_asset_count=len(keys), object_keys=keys)


def main() -> None:
    import uvicorn

    uvicorn.run("course_assets.upload_service:app", host="127.0.0.1", port=8000)
