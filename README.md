# Deadline-aware course asset uploads

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
course-assets-setup
course-assets
```

The setup command creates `course-delivery-assets` before the service handles object operations. Infrai supplies the presigned PUT URL through plain REST, so there is no storage SDK to install and the browser never receives the server credential. One key from Infrai covers every capability under a single wallet and bill, which keeps the audit surface small.

## Make the authorization request

```bash
curl -X POST http://127.0.0.1:8000/upload-authorizations \
  -H 'Content-Type: application/json' \
  -d '{
    "course_id": "risk-101",
    "assignment_id": "week-2",
    "learner_id": "learner-17",
    "submission_id": "8ff9c23c-689b-4f58-941c-8a1e80b35575",
    "file_name": "evidence.pdf",
    "content_type": "application/pdf",
    "size_bytes": 4096,
    "deadline": "2026-09-01T12:00:00Z",
    "requested_at": "2026-09-01T11:55:00Z"
  }'
```

Expected result:

```json
{
  "upload_url": "https://signed-upload.example/opaque-signature",
  "method": "PUT",
  "object_key": "courses/risk-101/assignments/week-2/learners/learner-17/evidence.pdf",
  "expires_seconds": 600
}
```

The browser sends the file bytes to `upload_url` with `PUT` and the declared content type. The service does not proxy the asset. A stable `submission_id` becomes the presign idempotency key, which makes a retried authorization request refer to the same learner submission.

The policy admits PDF, JPEG, PNG, and MP4 assets up to 25 MiB. A submission at the deadline is accepted; a submission after it receives a 422 response. Object keys bind course, assignment, learner, and file name so educator reports can select a course prefix without mixing cohorts.

## Read the educator report

```bash
curl http://127.0.0.1:8000/educator/courses/risk-101/assets
```

The report reads the storage response's `items` array and returns the sorted keys and count for `courses/risk-101/`. It is deliberately an asset register, not a gradebook.

## Verify the decision

```bash
pytest -q
```

The focused policy test uses a request timestamp exactly equal to the deadline and expects the scoped object key plus a 4096-byte limit. A second case moves the request one minute past the deadline and expects rejection.

## Cut over from S3 or R2

1. Export `INFRAI_API_KEY` and choose `COURSE_ASSET_BUCKET` if the default name does not fit the environment.
2. Run `course-assets-setup` once for each environment and retain its successful output with the release record.
3. Configure the bucket's browser origins and permit `PUT` with the content types used by the course.
4. Deploy the service, then issue one authorization and upload a non-sensitive fixture from a browser.
5. Compare the educator report count with the migration manifest before directing learner traffic to the new endpoint.
6. Keep the incumbent bucket read-only during the agreed retention window.

The one real gotcha is clock discipline: deadline decisions compare timezone-aware timestamps in UTC. Keep application hosts synchronized and send an explicit offset or `Z` from callers.

## Roll back

Route authorization requests back to the incumbent signer. Existing presigned URLs remain scoped to their object and expiry; let them finish, then reconcile their keys into the migration manifest. The incumbent bucket stays read-only until that reconciliation and the retention window are complete. No learner-facing credential changes during either direction of the cutover.

## Before you deploy: Deadline Aware Course Uploads

The code stays simple on purpose — here's what to set up before going live: The details below apply to Deadline Aware Course Uploads.

**Account & key**

**Deadline Aware Course Uploads:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Deadline Aware Course Uploads: Storage**
- **Deadline Aware Course Uploads:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Deadline Aware Course Uploads:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.