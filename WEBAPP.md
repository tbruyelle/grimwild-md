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
- Validator runs first; on failure the errors are rendered as an HTML
  page (HTTP 400) instead of returning a PDF. The build is skipped.
- Response returns the PDF with `Content-Disposition: inline`. The page
  intercepts the submit with a tiny vanilla-JS handler, fetches the PDF
  as a blob, shows it in an iframe (browser's native PDF viewer), and
  exposes a "Download PDF" button. No JS framework, no build step.

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
from grimwild import validate, parse, build_pdf

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/fonts", StaticFiles(directory="fonts"), name="fonts")


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
```

#### `static/index.html`
HTML form: file input, "Print mode" checkbox, submit, plus a hidden
preview section with an iframe and a Download button. A small inline
script intercepts the submit, POSTs the file to `/convert` via `fetch`,
and on success shows the PDF in the iframe (browser's native PDF
viewer) using a blob URL. On HTTP 400 it swaps the page for the
server-rendered error document. No JS framework, no build step.

#### `static/styles.css`
Same parchment palette, gradient, and fonts as the rendered PDF (Capito
TRIAL 04 from `fonts/`), so the form and error page sit in the same
visual world as the document they produce.

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

1. Add `build_pdf()` to `grimwild.py` (validation stays in `app.py` —
   it runs before `parse` and short-circuits the build).
2. Create `requirements.txt`, `.dockerignore`.
3. Create `static/index.html`, `static/styles.css`.
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
