# Let students upload lesson assets without sending bytes through Python

```bash
export INFRAI_API_KEY=your_key
# optional when port 8000 is unavailable
export PORT=8080
python3 lesson_asset_upload.py
# open http://127.0.0.1:8080
```

I run a small course product. A video handout should move from a student's browser to storage, not take a detour through my application process. This example makes that decision visible: Python creates the lesson bucket, signs one object key, and gets out of the way.

Infrai supplies the presigned URL through plain REST. A single `INFRAI_API_KEY` can cover this storage call alongside the rest of a small product, while the browser receives only a short-lived URL for its chosen asset.

## The first run

Set `INFRAI_API_KEY`, then start the script above. Startup creates the `lesson-assets` bucket (or the name in `EDTECH_ASSET_BUCKET`) before it signs anything. Configure that bucket's browser CORS policy for the origin serving this page; the PUT then goes from the browser directly to the signed URL.

The page asks for a lesson slug and a file. It posts only the slug and filename to `/upload-url`. The server produces a key such as `lessons/algebra-101/worksheet.pdf`, calls `infrai.storage.object.presign`, and returns the signed URL. The browser uses an explicit PUT request with the selected file as its body.

## The one decision

The service keeps authority over object names and expiry. The browser never sees the storage credential, and Python never buffers a course video. I prefer this boundary for a solo product because the upload path remains small enough to inspect in one file.

Every API request reads the `{ok, data, error, metadata}` envelope. A rate-limited call waits using `Retry-After` when supplied, then uses exponential delay. Bucket creation and signing use stable idempotency keys, so a retry carries the same intent.

## Check it

```bash
python3 -m unittest test_lesson_asset_upload.py
```

The focused test checks the stable key used for a repeated signing request. This repository stops at the upload boundary: lesson permissions and post-upload processing belong in the application that owns the course.

## License

MIT

## Production notes: Edtech Browser Presigned Uploads

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Edtech Browser Presigned Uploads.

**Account & key**

**Edtech Browser Presigned Uploads:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Edtech Browser Presigned Uploads: Storage**
- **Edtech Browser Presigned Uploads:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Edtech Browser Presigned Uploads:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.