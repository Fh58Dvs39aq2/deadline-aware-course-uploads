from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePath


class UploadRejected(ValueError):
    pass


@dataclass(frozen=True)
class UploadDecision:
    object_key: str
    max_bytes: int


ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "video/mp4"}
MAX_ASSET_BYTES = 25 * 1024 * 1024


def authorize_upload(
    *,
    course_id: str,
    assignment_id: str,
    learner_id: str,
    file_name: str,
    content_type: str,
    size_bytes: int,
    deadline: datetime,
    requested_at: datetime,
) -> UploadDecision:
    if deadline.tzinfo is None or requested_at.tzinfo is None:
        raise UploadRejected("deadline and requested_at must include a timezone")
    if requested_at.astimezone(timezone.utc) > deadline.astimezone(timezone.utc):
        raise UploadRejected("submission deadline has passed")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadRejected("content type is not allowed")
    if size_bytes <= 0 or size_bytes > MAX_ASSET_BYTES:
        raise UploadRejected("asset size is outside the allowed range")
    safe_name = PurePath(file_name).name
    if safe_name in {"", ".", ".."}:
        raise UploadRejected("file name is required")
    key = f"courses/{course_id}/assignments/{assignment_id}/learners/{learner_id}/{safe_name}"
    return UploadDecision(object_key=key, max_bytes=size_bytes)
