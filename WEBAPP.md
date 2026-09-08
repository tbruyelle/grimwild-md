# Grimwild MD Webapp Plan

Turn the existing `grimwild.py` CLI into a small web service that renders
markdown modules to PDF on demand, deployable on Render.

## Architecture

- **Backend**: FastAPI service exposing two routes (`GET /`, `POST /convert`).
- **PDF rendering**: same pipeline as the CLI — Python parses markdown,
  Chromium renders the styled HTML to PDF, `pdfinfo` settles the page count.
- **Frontend**: a single static `index.html` with a file-upload form. No JS
  framework, no build step.
- **Deployment**: Docker image on Render (free tier). Push to GitHub → Render
  auto-deploys via Blueprint (`render.yaml`).

## Decisions

- Render PDFs on the server with Chromium (matches current output exactly).
- Upload-only UX (MVP): no editor, no persistence.
- Public, no auth.
- Render as the host (free tier, easiest Docker deploy, GitHub-integrated).
- Print-mode toggle exposed on the form.

## Files

### Modify

#### `grimwild.py` — add `build_pdf()` library function
Pure addition; `main()` and the CLI stay untouched.

```python
def build_pdf(mod, print_mode=False) -> bytes:
    """Build PDF bytes from a parsed module. Iterates until page count settles."""
    tmp_html = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    tmp_html.close()
    html_path = Path(tmp_html.name)
    tmp_pdf = tempfile.NamedTemporaryFile("wb", suffix=".pdf", delete=False)
    tmp_pdf.close()
    pdf_path = Path(tmp_pdf.name)
    try:
        def build(pages):
            html_path.write_text(render(mod, pages=pages, print_mode=print_mode), encoding="utf-8")
            to_pdf(html_path, pdf_path)
        build(1)
        pages = pdf_pages(pdf_path)
        if pages is None:
            print("warning: pdfinfo not available, page numbers skipped", file=sys.stderr)
        else:
            for _ in range(3):
                if pages < 2:
                    break
                build(pages)
                settled = pdf_pages(pdf_path)
                if settled is None or settled == pages:
                    break
                pages = settled
        return pdf_path.read_bytes()
    finally:
        html_path.unlink(missing_ok=True)
        pdf_path.unlink(missing_ok=True)
```

#### `AGENTS.md` — add a "Webapp" section
Brief notes on running locally and deploying.

### Create

#### `app.py`
```python
from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, Response
from grimwild import parse, build_pdf

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def index():
    return Path("static/index.html").read_text()


@app.post("/convert")
async def convert(file: UploadFile = File(...), print_mode: bool = Form(False)):
    text = (await file.read()).decode("utf-8")
    pdf_bytes = build_pdf(parse(text), print_mode=print_mode)
    stem = Path(file.filename or "module").stem
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{stem}.pdf"'},
    )
```

#### `static/index.html`
Minimal HTML form: file input, "Print mode" checkbox, submit. Inline CSS,
no JS framework. Posts to `/convert`.

#### `requirements.txt`
```
fastapi
uvicorn[standard]
python-multipart
markdown-it-py
```

#### `Dockerfile`
```dockerfile
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium poppler-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY grimwild.py app.py ./
COPY fonts/ ./fonts/
COPY static/ ./static/
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `.dockerignore`
```
.git
.gitignore
*.pdf
example-golden.pdf
__pycache__
*.pyc
*.pyo
.DS_Store
.vscode
.idea
```

#### `render.yaml` (Blueprint)
```yaml
services:
  - type: web
    name: grimwild
    runtime: docker
    plan: free
```

## Order of work

1. Add `build_pdf()` to `grimwild.py`.
2. Create `requirements.txt`, `.dockerignore`.
3. Create `static/index.html`.
4. Create `app.py`.
5. Create `Dockerfile`.
6. Local smoke test: `docker build && docker run -p 8000:8000 grimwild`.
7. Create `render.yaml`.
8. Update `AGENTS.md`.

## Local dev

```bash
pip install -r requirements.txt
uvicorn app:app --reload
# open http://localhost:8000
```

## Deploy

1. Push the repo to GitHub.
2. On render.com: New → Blueprint → pick the repo.
3. Render detects `render.yaml` and provisions the service.
4. URL is `https://grimwild.onrender.com` (or whatever name).

## Known constraints

- **Cold start**: Render free tier sleeps after 15min of inactivity. The
  first request after sleep takes ~30s while Chromium boots. Subsequent
  requests are fast.
- **Memory**: 512MB RAM on the free tier supports one Chromium at a time.
  Two simultaneous conversions may OOM. Mitigation: add an
  `asyncio.Semaphore(1)` in `app.py` if this becomes an issue.
- **No file-size limit**: a huge `.md` would lock up the container. Add a
  body-size middleware (`max_upload_size`) if needed.
- **Public, no auth**: anyone with the URL can use it (and DOS it). Fine
  for a personal tool; not for sharing publicly.
