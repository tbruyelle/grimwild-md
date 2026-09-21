import hashlib
import os
import secrets
import sys
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from grimwild import validate, parse, build_pdf

SALT = os.environ.get("TRACKING_SALT") or ""
if not SALT:
    SALT = secrets.token_hex(16)
    print(
        "warning: TRACKING_SALT not set; using a random per-process salt "
        "(hashes won't correlate across restarts)",
        file=sys.stderr,
    )


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(f"{SALT}:{ip}".encode()).hexdigest()[:16]


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")


@app.middleware("http")
async def track(request: Request, call_next):
    rid = uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - start) * 1000)
    fwd = request.headers.get("x-forwarded-for", "")
    ip = (fwd.split(",")[0].strip() if fwd else "") or (
        request.client.host if request.client else ""
    )
    ua = (request.headers.get("user-agent") or "")[:80].replace('"', "'")
    print(
        f'ts={time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} '
        f'rid={rid} method={request.method} path={request.url.path} '
        f'status={response.status_code} dur_ms={duration_ms} '
        f'ip_hash={_hash_ip(ip)} ua="{ua}"',
        file=sys.stderr,
    )
    return response


@app.get("/", response_class=HTMLResponse)
async def index():
    return Path("static/index.html").read_text()


@app.post("/convert")
async def convert(file: UploadFile = File(...), print_mode: bool = Form(False)):
    text = (await file.read()).decode("utf-8")
    issues = validate(text)
    if issues:
        items = "".join(
            f"<li><b>line {i['line']}</b>: {i['message']}</li>" for i in issues
        )
        html = (
            "<!doctype html><meta charset='utf-8'>"
            "<title>Validation errors</title>"
            "<link rel='stylesheet' href='/static/styles.css'>"
            "<main class='errors'>"
            "<h1>Validation failed</h1>"
            f"<ul>{items}</ul>"
            "<a class='btn' href='/'>Back</a>"
            "</main>"
        )
        return HTMLResponse(html, status_code=400)
    pdf_bytes = build_pdf(parse(text), print_mode=print_mode)
    stem = Path(file.filename or "module").stem
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{stem}.pdf"'},
    )
