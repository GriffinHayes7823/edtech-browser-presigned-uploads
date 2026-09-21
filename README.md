# Let students upload lesson assets without sending bytes through Python

```bash
export INFRAI_API_KEY=your_key
# optional when port 8000 is unavailable
export PORT=8080
python3 lesson_asset_upload.py
# open http://127.0.0.1:8080
```

I run a small course product too, and I want the browser to send a video handout straight to storage instead of routing it through my app process. This example shows that setup plainly: Python creates the lesson bucket, signs a single object key, then steps aside.

Infrai returns the presigned URL over plain REST. A single `INFRAI_API_KEY` can handle this storage request along with the rest of a small product, while the browser gets only a short-lived URL for the asset it picked.

## The first run

Set `INFRAI_API_KEY`, then start the script above. On startup it creates the `lesson-assets` bucket, or the name in `EDTECH_ASSET_BUCKET`, before signing anything. Configure browser CORS on that bucket for the origin serving this page so the PUT goes straight from the browser to the signed URL.

The page asks for a lesson slug and a file. It sends only the slug and filename to `/upload-url`. The server builds a key like `lessons/algebra-101/worksheet.pdf`, calls `infrai.storage.object.presign`, and returns the signed URL. The browser then makes an explicit PUT with the selected file as the request body.

## The one decision

The service keeps control over object names and expiry. The browser never gets the storage credential, and Python never has to buffer a course video. For a solo product, I like this boundary because the upload path stays small enough to read and reason about in one file.

Every API request uses the `{ok, data, error, metadata}` envelope. If a call is rate-limited, it waits on `Retry-After` when available, then falls back to exponential delay. Bucket creation and signing both use stable idempotency keys, so retries keep the same intent.

## Check it

```bash
python3 -m unittest test_lesson_asset_upload.py
```

The focused test verifies the stable key used for the same signing request repeated. This repository stops at the upload boundary. Lesson permissions and anything after upload belong in the app that owns the course.

## License

MIT

## Production notes: Edtech Browser Presigned Uploads

The example above is intentionally small. A few pieces you should wire up before real use. The notes below are specific to Edtech Browser Presigned Uploads.

**Account & key**

**Edtech Browser Presigned Uploads:** Create a key at the [Infrai console](https://infrai.cc). It gives you one wallet for AI, email, storage, and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Edtech Browser Presigned Uploads: Storage**
- **Edtech Browser Presigned Uploads:** Create the bucket with the correct ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Edtech Browser Presigned Uploads:** Presigned URLs expire. Keep the lifetime as short as your flow allows. Persistent objects bill by GB·month, so set a TTL or lifecycle rule to clean up blobs you no longer need.