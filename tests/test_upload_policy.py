from datetime import datetime, timezone

import pytest

from course_assets.upload_policy import UploadRejected, authorize_upload


def test_submission_at_deadline_is_authorized_with_scoped_key() -> None:
    deadline = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

    decision = authorize_upload(
        course_id="risk-101",
        assignment_id="week-2",
        learner_id="learner-17",
        file_name="evidence.pdf",
        content_type="application/pdf",
        size_bytes=4096,
        deadline=deadline,
        requested_at=deadline,
    )

    assert decision.object_key == "courses/risk-101/assignments/week-2/learners/learner-17/evidence.pdf"
    assert decision.max_bytes == 4096


def test_submission_after_deadline_is_rejected() -> None:
    with pytest.raises(UploadRejected, match="deadline has passed"):
        authorize_upload(
            course_id="risk-101",
            assignment_id="week-2",
            learner_id="learner-17",
            file_name="evidence.pdf",
            content_type="application/pdf",
            size_bytes=4096,
            deadline=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
            requested_at=datetime(2026, 9, 1, 12, 1, tzinfo=timezone.utc),
        )
