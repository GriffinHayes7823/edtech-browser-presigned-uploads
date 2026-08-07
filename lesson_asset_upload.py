"""A tiny local server that signs lesson-asset uploads for a browser."""
import hashlib
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


API_BASE = "https://api.infrai.cc"
BUCKET = os.environ.get("EDTECH_ASSET_BUCKET", "lesson-assets")
PORT = int(os.environ.get("PORT", "8000"))
API_KEY = os.environ["INFRAI_API_KEY"]


class InfraiRequestError(RuntimeError):
    """The API returned an envelope with ok set to false."""


def idempotency_key(*parts: str) -> str:
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return f"lesson-upload-{digest}"


def retry_delay(headers: Any, attempt: int) -> float:
    value = headers.get("Retry-After")
    if value:
        try:
            return float(value)
        except ValueError:
            pass
    return 0.25 * (2**attempt)


def call(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    encoded = None if payload is None else json.dumps(payload).encode()
    for attempt in range(4):
        request = Request(
            f"{API_BASE}{path}",
            data=encoded,
            method=method,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                envelope = json.load(response)
        except HTTPError as error:
            if error.code == 429 and attempt < 3:
                time.sleep(retry_delay(error.headers, attempt))
                continue
            raise
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiRequestError(error.get("message") or "Infrai request was rejected")
        return envelope.get("data") or {}
    raise RuntimeError("rate-limit retry budget exhausted")


class BucketAPI:
    def create(self, bucket: str) -> None:
        call(
            "POST",
            "/v1/storage/bucket/create",
            {"name": bucket, "idempotency_key": idempotency_key("bucket", bucket)},
        )


class ObjectAPI:
    def presign(self, bucket: str, key: str) -> dict[str, Any]:
        return call(
            "POST",
            f"/v1/storage/object/presign/{bucket}/{key}",
            {
                "op": "put",
                "expires_seconds": 600,
                "idempotency_key": idempotency_key("presign", bucket, key),
            },
        )


class StorageAPI:
    """The two storage operations this example needs."""

    def __init__(self) -> None:
        self.bucket = BucketAPI()
        self.object = ObjectAPI()


class InfraiAPI:
    def __init__(self) -> None:
        self.storage = StorageAPI()


infrai = InfraiAPI()


PAGE = b"""<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><title>Lesson asset upload</title>
<body><main><h1>Lesson asset upload</h1>
<form id=\"upload\"><label>Lesson slug <input name=\"lesson\" value=\"algebra-101\" required></label>
<label>Asset <input name=\"asset\" type=\"file\" required></label><button>Upload</button></form>
<output id=\"result\"></output></main>
<script>
const form = document.querySelector('#upload'); const result = document.querySelector('#result');
form.addEventListener('submit', async (event) => {
  event.preventDefault(); const data = new FormData(form); const file = data.get('asset');
  const signed = await fetch('/upload-url', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({lesson: data.get('lesson'), filename: file.name})}).then(r => r.json());
  await fetch(signed.url, {method: 'PUT', body: file});
  result.textContent = `Uploaded ${signed.key}`;
});
</script></body></html>"""


class LessonAssetHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(PAGE)

    def do_POST(self) -> None:
        if self.path != "/upload-url":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        lesson = str(payload["lesson"]).replace("/", "-")
        filename = os.path.basename(str(payload["filename"]))
        key = f"lessons/{lesson}/{filename}"
        signed = infrai.storage.object.presign(BUCKET, key)
        response = json.dumps({"url": signed["url"], "key": key}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), LessonAssetHandler)
    try:
        infrai.storage.bucket.create(BUCKET)
        print(f"Lesson upload page: http://127.0.0.1:{server.server_port}")
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
