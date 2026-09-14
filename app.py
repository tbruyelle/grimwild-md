from pathlib import Path
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
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
